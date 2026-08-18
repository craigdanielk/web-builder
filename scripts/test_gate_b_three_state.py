#!/usr/bin/env python3
"""Gate B's three-state contract — PASS (0) · FAIL (1) · NOT_MEASURED (3).

WHY THIS FILE EXISTS
--------------------
`shopify-integration-layer/verify_gate_b.py` had no NOT_MEASURED outcome at all,
and its B-CDN half self-skipped IN SILENCE when cdn_url_map.json was absent,
falling through to `print("VERIFY GATE B: PASS")` and exit 0. A run that checked
zero media URLs was indistinguishable from one that checked all of them.

There are no Shopify credentials on this machine and this file must not invent a
network: the live branches are driven by monkeypatching `urllib.request.urlopen`
inside the gate module, and the environment branches by subprocess with a
scrubbed env.

MUTATION LOG (a test that cannot fail is not a test)
    MUTATION  in verify_gate_b.check_cdn, the absent-cdn_url_map.json branch was
              changed from `v.unmeasured(...)` back to the old silent `return`.
              -> 3 failed, 13 passed. The mutated gate printed
                 "VERIFY GATE B: PASS - 2 check(s) ran and conformed" having
                 checked zero media URLs — the exact original defect.
                 test_absent_cdn_map_is_not_measured_and_says_so,
                 test_absent_cdn_map_is_reported_on_stdout,
                 test_store_ok_but_no_cdn_map_is_partial_not_pass
    RESTORED  -> 16 passed
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

WEB_BUILDER = Path(__file__).resolve().parent.parent
GATE = WEB_BUILDER.parent / "shopify-integration-layer" / "verify_gate_b.py"

PASS, FAIL, NOT_MEASURED = 0, 1, 3

# Every credential the gate can read. Scrubbed so a machine that happens to have
# one does not turn "absent credentials" into a live call.
CREDENTIAL_KEYS = (
    "SHOPIFY_STORE_DOMAIN", "SHOPIFY_STORE",
    "SHOPIFY_ADMIN_ACCESS_TOKEN", "SHOPIFY_ACCESS_TOKEN", "PRIVATE_ACCESS_TOKEN",
    "SHOPIFY_STOREFRONT_ACCESS_TOKEN", "PUBLIC_ACCESS_TOKEN",
)


def _clean_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k not in CREDENTIAL_KEYS}
    return env


def run_gate(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the gate as the chain runs it. `--env` is pointed at a path that does
    not exist so the (absent) repo-root .env can never leak a credential in."""
    return subprocess.run(
        [sys.executable, str(GATE), "--env", "/nonexistent/.env", *args],
        capture_output=True, text=True, timeout=120,
        env=env if env is not None else _clean_env(),
    )


def load_gate():
    """Import the gate as a module so its network calls can be monkeypatched."""
    spec = importlib.util.spec_from_file_location("verify_gate_b_under_test", GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def store_dir(tmp_path: Path) -> Path:
    d = tmp_path / "layer4"
    d.mkdir()
    (d / "shopify_config.json").write_text(json.dumps({
        "store_domain": "test-store.myshopify.com",
        "storefront_access_token": "sf_token_for_test",
    }), encoding="utf-8")
    return d


def _args(**kw):
    """A stand-in for argparse.Namespace with the gate's five flags."""
    class A:
        output_dir = kw.get("output_dir")
        compiled_dir = kw.get("compiled_dir")
        skip_head = kw.get("skip_head", False)
        dry_run = kw.get("dry_run", False)
    return A()


# ── absent credentials must be NOT_MEASURED, never FAIL ───────────────────

def test_absent_credentials_is_not_measured_not_fail(store_dir: Path):
    """No storefront token anywhere. The old gate appended an error and returned
    1, making 'we could not check' identical to 'the store is broken'."""
    (store_dir / "shopify_config.json").write_text(json.dumps({
        "store_domain": "test-store.myshopify.com",
        # the literal placeholder the checked-in config ships
        "storefront_access_token": "[set SHOPIFY_STOREFRONT_ACCESS_TOKEN or PUBLIC_ACCESS_TOKEN]",
    }), encoding="utf-8")
    r = run_gate("--output-dir", str(store_dir))
    assert r.returncode == NOT_MEASURED, f"expected 3, got {r.returncode}\n{r.stdout}\n{r.stderr}"
    assert r.returncode != FAIL
    assert "NOT_MEASURED" in r.stdout
    assert "storefront token" in r.stdout


def test_absent_shopify_config_is_not_measured(tmp_path: Path):
    """Layer 4 never ran. Nothing was verified and nothing was broken."""
    empty = tmp_path / "empty"
    empty.mkdir()
    r = run_gate("--output-dir", str(empty))
    assert r.returncode == NOT_MEASURED, r.stdout + r.stderr
    assert "shopify_config.json" in r.stdout


def test_no_dirs_at_all_is_not_measured(tmp_path: Path):
    """WAS: 'Provide --output-dir and/or --compiled-dir' -> exit 1."""
    r = run_gate()
    assert r.returncode == NOT_MEASURED, r.stdout + r.stderr
    assert "nothing to check" in r.stdout


# ── B-CDN may never again contribute silence to a PASS ────────────────────

def test_absent_cdn_map_is_not_measured_and_says_so(store_dir: Path, monkeypatch):
    """The headline defect: no cdn_url_map.json meant the whole B-CDN half was
    skipped with NOTHING printed, and the gate exited 0."""
    mod = load_gate()
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_storefront_ok())
    v = mod.Verdict()
    mod.check_store(_args(output_dir=store_dir), v)
    mod.check_cdn(_args(output_dir=store_dir), v)
    code = v.report()
    assert code == NOT_MEASURED
    states = {name: state for name, state, _ in v.checks}
    assert states["b-cdn"] == "NOT_MEASURED"


def test_absent_cdn_map_is_reported_on_stdout(store_dir: Path, capsys, monkeypatch):
    mod = load_gate()
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_storefront_ok())
    v = mod.Verdict()
    mod.check_cdn(_args(output_dir=store_dir), v)
    v.report()
    out = capsys.readouterr().out
    assert "NOT_MEASURED" in out
    assert "cdn_url_map.json" in out
    assert "ZERO media URLs were checked" in out


def test_skip_head_is_not_measured(store_dir: Path, monkeypatch):
    (store_dir / "cdn_url_map.json").write_text(json.dumps({
        "section_media": {"hero": "https://cdn.example/1.jpg"},
    }), encoding="utf-8")
    mod = load_gate()
    v = mod.Verdict()
    mod.check_cdn(_args(output_dir=store_dir, skip_head=True), v)
    assert v.report() == NOT_MEASURED


# ── a measured failure is still FAIL ──────────────────────────────────────

def _fake_storefront_ok():
    class Resp:
        def read(self): return json.dumps({"data": {"shop": {"name": "Test"}}}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    return lambda *a, **k: Resp()


def test_measured_storefront_failure_is_fail(store_dir: Path, monkeypatch):
    """The store answered and the answer was wrong. That is measured."""
    class Resp:
        def read(self): return json.dumps({"data": {}}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    mod = load_gate()
    monkeypatch.setattr(mod.urllib.request, "urlopen", lambda *a, **k: Resp())
    v = mod.Verdict()
    mod.check_store(_args(output_dir=store_dir), v)
    assert v.report() == FAIL


def test_unreachable_store_is_not_measured_not_fail(store_dir: Path, monkeypatch):
    """A transport failure means we never reached the store."""
    import urllib.error

    def boom(*a, **k):
        raise urllib.error.URLError("Name or service not known")
    mod = load_gate()
    monkeypatch.setattr(mod.urllib.request, "urlopen", boom)
    v = mod.Verdict()
    mod.check_store(_args(output_dir=store_dir), v)
    code = v.report()
    assert code == NOT_MEASURED, [c for c in v.checks]
    assert code != FAIL


def test_dead_cdn_urls_are_a_measured_failure(store_dir: Path, monkeypatch):
    (store_dir / "cdn_url_map.json").write_text(json.dumps({
        "section_media": {f"s{i}": f"https://cdn.example/{i}.jpg" for i in range(5)},
    }), encoding="utf-8")
    mod = load_gate()
    monkeypatch.setattr(mod.urllib.request, "urlopen", _raise_always())
    v = mod.Verdict()
    mod.check_cdn(_args(output_dir=store_dir), v)
    assert v.report() == FAIL


def _raise_always():
    import urllib.error

    def boom(*a, **k):
        raise urllib.error.URLError("dead")
    return boom


# ── the HEAD sweep must count ALL failures, not stop at the first ─────────

def test_head_sweep_counts_every_failure(store_dir: Path, monkeypatch):
    """WAS: `break` after the first failure, so '1 error' and '200 errors' were
    the same output."""
    (store_dir / "cdn_url_map.json").write_text(json.dumps({
        "section_media": {f"s{i}": f"https://cdn.example/{i}.jpg" for i in range(7)},
    }), encoding="utf-8")
    calls = []

    def boom(req, *a, **k):
        calls.append(getattr(req, "full_url", req))
        raise OSError("dead")
    mod = load_gate()
    monkeypatch.setattr(mod.urllib.request, "urlopen", boom)
    v = mod.Verdict()
    mod.check_cdn(_args(output_dir=store_dir), v)
    assert len(calls) == 7, "the sweep stopped early"
    detail = [d for n, s, d in v.checks if n == "b-cdn.head"][0]
    assert "7 of 7" in detail


def test_head_cap_is_reported_when_it_truncates(store_dir: Path, monkeypatch):
    """A silent truncation reads as 'checked everything'."""
    mod = load_gate()
    n = mod.HEAD_URL_CAP + 3
    (store_dir / "cdn_url_map.json").write_text(json.dumps({
        "section_media": {f"s{i}": f"https://cdn.example/{i}.jpg" for i in range(n)},
    }), encoding="utf-8")
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_storefront_ok())
    v = mod.Verdict()
    mod.check_cdn(_args(output_dir=store_dir), v)
    caps = [d for name, state, d in v.checks if name == "b-cdn.cap"]
    assert caps and "were not checked" in caps[0]
    assert v.report() == NOT_MEASURED


# ── the swallowed Admin exception ─────────────────────────────────────────

def test_admin_count_exception_is_not_measured_with_its_message(tmp_path: Path, monkeypatch):
    """WAS: `except Exception: pass` — an expired Admin token vanished and the
    gate still passed."""
    compiled = tmp_path / "compiled"
    compiled.mkdir()
    (compiled / "architecture.json").write_text(json.dumps({
        "collections": [{"handle": "a"}], "summary": {"estimated_products": 12},
    }), encoding="utf-8")
    mod = load_gate()
    monkeypatch.setenv("SHOPIFY_STORE_DOMAIN", "test-store.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "expired")

    def boom(*a, **k):
        raise RuntimeError("HTTP Error 401: Unauthorized")
    monkeypatch.setattr(mod, "admin_request", boom)
    v = mod.Verdict()
    mod.check_compiled_counts(_args(compiled_dir=compiled), v)
    assert v.report() == NOT_MEASURED
    detail = [d for n, s, d in v.checks if n == "b-counts"][0]
    assert "401" in detail


# ── the partial-measurement rule ──────────────────────────────────────────

def test_store_ok_but_no_cdn_map_is_partial_not_pass(store_dir: Path, capsys, monkeypatch):
    """One half measured and passed, the other could not be measured. That is 3."""
    mod = load_gate()
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_storefront_ok())
    v = mod.Verdict()
    mod.check_store(_args(output_dir=store_dir), v)
    mod.check_cdn(_args(output_dir=store_dir), v)
    code = v.report()
    out = capsys.readouterr().out
    assert code == NOT_MEASURED, out
    assert code != PASS
    assert "partially-measured gate is not a passed gate" in out


def test_pass_requires_every_attempted_check_to_have_run(store_dir: Path, monkeypatch):
    """The one road to 0: both halves ran and conformed."""
    (store_dir / "cdn_url_map.json").write_text(json.dumps({
        "section_media": {"hero": "https://cdn.example/1.jpg"},
    }), encoding="utf-8")
    mod = load_gate()
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_storefront_ok())
    v = mod.Verdict()
    mod.check_store(_args(output_dir=store_dir), v)
    mod.check_cdn(_args(output_dir=store_dir), v)
    assert v.report() == PASS


def test_dry_run_is_not_measured(store_dir: Path):
    """--dry-run calls nothing live, so it cannot pass a live gate."""
    r = run_gate("--output-dir", str(store_dir), "--dry-run")
    assert r.returncode == NOT_MEASURED, r.stdout + r.stderr


# ── the declaration must describe THIS behaviour ──────────────────────────

def test_describe_declares_the_three_state_contract():
    r = run_gate("--describe")
    assert r.returncode == 0
    spec = json.loads(r.stdout)
    assert spec["id"] == "aurelix.gate.shopify-b"
    assert "3" in spec["exit_contract"], "no NOT_MEASURED code declared"
    assert "NOT_MEASURED" in spec["exit_contract"]["3"]
    for owned in ("status", "evidence"):
        assert owned not in spec, f"{owned} is compiler-owned"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

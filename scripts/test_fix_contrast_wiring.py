#!/usr/bin/env python3
"""`--fix-contrast` is wired, opt-in, and cannot move the build's verdict.

WHAT IS BEING GUARDED, and why each assertion can actually fail:

  * `scripts/quality/render-fix-contrast.js` was a complete, unit-tested fixer
    with `reachable_from: []`. Nothing invoked it. The first test here drives
    `stage_render_audit` for real (with the npm build and the Next server
    replaced by fakes that still speak the real protocol — the fake server
    binds the port the code chose and the code really connects to it) and
    asserts the fixer is invoked exactly once with the flag and zero times
    without it. Delete the call site and it fails.

  * The fixer MUTATES globals.css and site-spec.json and re-measures nothing.
    So it must not be able to move the build: `test_a_repaired_fixer_cannot_
    upgrade_a_failing_build` gives the fixer its most flattering possible
    verdict (REPAIRED, exit 0) alongside a recorded build failure and asserts
    the outcome is still failed / exit 1. It also asserts the fixer never
    enters GATE_RESULTS, because `unmeasured_gates()` feeds
    `resolve_build_outcome()` and a fixer landing there WOULD change the exit
    code — in either direction.

  * `test_the_fixer_really_runs_and_writes_its_verdict` runs the real node
    script against a SCRATCH copy (tmp_path, never a git checkout) and asserts
    the artifact lands on disk. That is the one test that proves the argument
    names and the exit contract were read correctly rather than guessed.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import orchestrate  # noqa: E402


# ── the flag itself ────────────────────────────────────────────────

def test_the_flag_is_declared_and_documented_as_default_off():
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "orchestrate.py"), "--help"],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[:400]
    assert "--fix-contrast" in proc.stdout
    # A store_true flag prints no "(default: ...)"; the operator-facing promise
    # that it is off unless asked is the help text itself. argparse re-wraps
    # the help, so compare on collapsed whitespace.
    flat = " ".join(proc.stdout.split())
    assert "DEFAULT OFF" in flat
    assert "MUTATES globals.css" in flat


def test_stage_render_audit_defaults_the_flag_to_false():
    import inspect
    param = inspect.signature(orchestrate.stage_render_audit).parameters["fix_contrast"]
    assert param.default is False


def test_both_call_sites_forward_the_flag():
    """A default of False is worthless if main() never overrides it."""
    src = (SCRIPTS / "orchestrate.py").read_text(encoding="utf-8")
    forwards = src.count('fix_contrast=getattr(args, "fix_contrast", False)')
    assert forwards == 2, f"expected both stage_render_audit call sites to forward, saw {forwards}"


# ── the wiring: invoked with the flag, not without ─────────────────

class _FakeNextServer:
    """Stands in for `npm run start`, and really listens on the chosen port.

    stage_render_audit picks a free port, then polls it with a real socket
    connect. A fake that did not listen would make the stage return 'failed'
    before it ever reached the fixer, and the test would pass for the wrong
    reason.
    """

    def __init__(self, argv, **_kw):
        port = int(argv[argv.index("--port") + 1])
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", port))
        self.sock.listen(8)

    def terminate(self):
        self.sock.close()

    def kill(self):
        self.sock.close()

    def wait(self, timeout=None):
        return 0


class _FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def audited_build(tmp_path, monkeypatch):
    """A minimal output tree, with the heavy halves of the stage faked."""
    out_root = tmp_path / "output"
    site_dir = out_root / "proj" / "site"
    site_dir.mkdir(parents=True)
    monkeypatch.setattr(orchestrate, "OUTPUT_DIR", out_root)
    monkeypatch.setattr(orchestrate, "run_production_build", lambda *a, **k: True)
    monkeypatch.setattr(orchestrate.subprocess, "Popen", _FakeNextServer)

    real_run = orchestrate.subprocess.run

    def fake_run(cmd, *a, **kw):
        if any("render-audit.js" in str(c) for c in cmd):
            return _FakeCompleted(0, json.dumps({"total_defects": 0, "by_severity": {}}))
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(orchestrate.subprocess, "run", fake_run)
    orchestrate.GATE_RESULTS.clear()
    return out_root


def _record_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(
        orchestrate, "run_contrast_fixer",
        lambda *a, **k: calls.append((a, k)) or {"status": "REPAIRED", "exit_code": 0},
    )
    return calls


def test_without_the_flag_the_fixer_is_not_invoked(audited_build, monkeypatch):
    calls = _record_calls(monkeypatch)
    status = orchestrate.stage_render_audit(project_name="proj")
    assert status == "passed"
    assert calls == [], "the fixer ran on a default build — it mutates source and must not"


def test_with_the_flag_the_fixer_is_invoked_once(audited_build, monkeypatch):
    calls = _record_calls(monkeypatch)
    status = orchestrate.stage_render_audit(project_name="proj", fix_contrast=True)
    assert status == "passed"
    assert len(calls) == 1, "the fixer was not invoked under --fix-contrast"


def test_the_fixer_verdict_cannot_change_the_render_audit_status(audited_build, monkeypatch):
    """Its most alarming verdict must leave the audit's own status alone."""
    monkeypatch.setattr(
        orchestrate, "run_contrast_fixer",
        lambda *a, **k: {"status": "FAIL", "exit_code": 1},
    )
    assert orchestrate.stage_render_audit(project_name="proj", fix_contrast=True) == "passed"


def test_the_fixer_never_enters_gate_results(audited_build, monkeypatch):
    """GATE_RESULTS feeds unmeasured_gates() feeds resolve_build_outcome().

    A fixer recorded there would change the exit code, which is exactly the
    thing it is not allowed to do.
    """
    monkeypatch.setattr(
        orchestrate, "run_contrast_fixer",
        lambda *a, **k: {"status": "NOT_MEASURED", "exit_code": 3},
    )
    orchestrate.stage_render_audit(project_name="proj", fix_contrast=True)
    assert not [g for g in orchestrate.GATE_RESULTS if "contrast" in g]
    assert orchestrate.unmeasured_gates() == []


def test_a_repaired_fixer_cannot_upgrade_a_failing_build(audited_build, monkeypatch):
    """The whole point of the flag being information rather than a verdict."""
    monkeypatch.setattr(orchestrate, "BUILD_FAILURES", [{"stage": "sections", "detail": "dropped"}])
    monkeypatch.setattr(
        orchestrate, "run_contrast_fixer",
        lambda *a, **k: {"status": "REPAIRED", "exit_code": 0, "adjustments": [{"role": "x"}]},
    )
    orchestrate.stage_render_audit(project_name="proj", fix_contrast=True)
    status, code = orchestrate.resolve_build_outcome(
        "passed", deploy_requested=True, audit_ran=True,
        unmeasured_gates=orchestrate.unmeasured_gates(),
    )
    assert (status, code) == ("failed", orchestrate.EXIT_FAILED)


# ── the real script, on a scratch copy ─────────────────────────────

def test_the_fixer_really_runs_and_writes_its_verdict(tmp_path, monkeypatch):
    """Runs the actual node script. Scratch dirs only — it mutates source."""
    out_root = tmp_path / "output"
    proj = out_root / "proj"
    app = proj / "site" / "src" / "app"
    app.mkdir(parents=True)
    audit_out = proj / "render-audit-results"
    audit_out.mkdir(parents=True)
    monkeypatch.setattr(orchestrate, "OUTPUT_DIR", out_root)

    # #9aa0a6 on #ffffff measures 2.34:1 — a real failure the fixer can reach,
    # because #9aa0a6 is a palette value and #0b0d10 is another one.
    (audit_out / "report.json").write_text(json.dumps({
        "routes": [{
            "route": "/",
            "facts": {"contrast": [
                {"fg": "#9aa0a6", "bg": "#ffffff", "ratio": 2.34, "need": 4.5,
                 "pass": False, "selector": "p.muted"},
            ]},
        }],
    }), encoding="utf-8")
    (proj / "site-spec.json").write_text(json.dumps({
        "style": {
            "design_source": "benchmark",
            "palette": {
                "bg_primary": "#ffffff", "text_primary": "#0b0d10",
                "text_muted": "#9aa0a6", "accent": "#004e89",
            },
        },
    }), encoding="utf-8")
    (app / "globals.css").write_text(
        ":root{--background:#ffffff;--foreground:#0b0d10;--muted:#9aa0a6;--accent:#004e89;}\n",
        encoding="utf-8",
    )

    verdict = orchestrate.run_contrast_fixer("proj", audit_out, proj / "site")

    assert verdict["status"] == "REPAIRED", verdict
    assert verdict["affects_build_outcome"] is False
    assert verdict["exit_code"] == 0, "the script's PASS/REPAIRED exit is 0"
    written = json.loads((audit_out / "contrast-fix.json").read_text(encoding="utf-8"))
    assert written["status"] == "REPAIRED"
    # The verdict is on disk, not only on a console nobody captured.
    assert "--muted:#9aa0a6" not in (app / "globals.css").read_text(encoding="utf-8")


def test_a_missing_report_is_not_measured_not_a_pass(tmp_path, monkeypatch):
    out_root = tmp_path / "output"
    proj = out_root / "proj"
    (proj / "site" / "src" / "app").mkdir(parents=True)
    audit_out = proj / "render-audit-results"
    audit_out.mkdir(parents=True)
    monkeypatch.setattr(orchestrate, "OUTPUT_DIR", out_root)

    verdict = orchestrate.run_contrast_fixer("proj", audit_out, proj / "site")
    assert verdict["status"] == "NOT_MEASURED"
    assert verdict["exit_code"] == 3


# ── the node's own declaration ─────────────────────────────────────

def test_describe_returns_a_valid_declaration_before_argparse():
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "orchestrate.py"), "--describe"],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[:400]
    spec = json.loads(proc.stdout)          # no positional <project> was passed
    assert spec["id"] == "aurelix.harness.orchestrate"
    assert spec["kind"] == "harness"

    from lib.capability import validate, COMPILER_OWNED
    validate(spec, "orchestrate --describe")
    assert not (COMPILER_OWNED & set(spec)), "compiler-owned fields must not be declared"
    assert spec["cannot_see"], "cannot_see may never be empty"

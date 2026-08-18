#!/usr/bin/env python3
"""`build_templates.py --verify` — the rails library's drift detector.

The MANIFEST records a `template_sha256` per emitted file and, until now,
nothing re-checked it: drift from the Xago source was detectable by hand only
(census 2026-08-18 §3.2). These tests hold the three states it must answer —
MATCH / DRIFTED / MISSING — and the fourth answer that is NOT a pass: a
manifest it cannot read is NOT_MEASURED, exit 3.

The fixture tests build their own tiny manifest, so they test the verifier and
not the rails corpus. One test does run against the real corpus — that is the
regression guard, and it fails the day someone hand-edits an emitted template
without re-running the builder.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BUILDER = REPO / "rails-templates" / "build_templates.py"

_spec = importlib.util.spec_from_file_location("build_templates", BUILDER)
bt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bt)


def _fixture_corpus(root: Path, bodies: dict[str, str]) -> Path:
    """A minimal emitted corpus + a manifest whose shas match it."""
    dest = root / "cms"
    files = []
    for rel, text in bodies.items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        files.append({"path": rel, "template_sha256": bt.sha(text)})
    (dest / "MANIFEST.json").write_text(json.dumps({"files": files}, indent=2))
    return dest


BODIES = {"src/lib/cms.ts": "export const a = 1;\n", "db/migrations/0001.sql": "select 1;\n"}


# ── the three states ──────────────────────────────────────────────────────────

def test_intact_corpus_is_all_match(tmp_path):
    dest = _fixture_corpus(tmp_path, BODIES)
    verdicts, unlisted = bt.verify(dest)
    assert [v for _, v in verdicts] == ["MATCH", "MATCH"]
    assert unlisted == []
    assert bt.run_verify(dest) == bt.EXIT_OK


def test_altered_bytes_are_DRIFTED_and_exit_1(tmp_path):
    dest = _fixture_corpus(tmp_path, BODIES)
    (dest / "src/lib/cms.ts").write_text("export const a = 2;\n")
    verdicts, _ = bt.verify(dest)
    assert dict(verdicts)["src/lib/cms.ts"] == "DRIFTED"
    assert dict(verdicts)["db/migrations/0001.sql"] == "MATCH"
    assert bt.run_verify(dest) == bt.EXIT_DRIFT


def test_a_whitespace_only_change_is_DRIFTED(tmp_path):
    """sha256 over bytes, not over a normalised form — a trailing space drifts."""
    dest = _fixture_corpus(tmp_path, BODIES)
    (dest / "src/lib/cms.ts").write_text("export const a = 1; \n")
    assert dict(bt.verify(dest)[0])["src/lib/cms.ts"] == "DRIFTED"


def test_deleted_file_is_MISSING_not_MATCH(tmp_path):
    dest = _fixture_corpus(tmp_path, BODIES)
    (dest / "src/lib/cms.ts").unlink()
    verdicts, _ = bt.verify(dest)
    assert dict(verdicts)["src/lib/cms.ts"] == "MISSING"
    assert bt.run_verify(dest) == bt.EXIT_DRIFT


def test_a_file_the_manifest_does_not_name_is_reported(tmp_path):
    """Not a verdict — but an unrecorded file in a library corpus is a fact."""
    dest = _fixture_corpus(tmp_path, BODIES)
    (dest / "src/lib/stray.ts").write_text("// nobody recorded me\n")
    verdicts, unlisted = bt.verify(dest)
    assert unlisted == ["src/lib/stray.ts"]
    assert all(v == "MATCH" for _, v in verdicts)


# ── NOT_MEASURED is not a pass ────────────────────────────────────────────────

def test_absent_manifest_is_NOT_MEASURED_exit_3(tmp_path):
    dest = _fixture_corpus(tmp_path, BODIES)
    (dest / "MANIFEST.json").unlink()
    with pytest.raises(bt.NotMeasured):
        bt.verify(dest)
    assert bt.run_verify(dest) == bt.EXIT_NOT_MEASURED


def test_unparseable_manifest_is_NOT_MEASURED_exit_3(tmp_path):
    dest = _fixture_corpus(tmp_path, BODIES)
    (dest / "MANIFEST.json").write_text("{ not json")
    assert bt.run_verify(dest) == bt.EXIT_NOT_MEASURED


def test_manifest_without_files_list_is_NOT_MEASURED(tmp_path):
    dest = _fixture_corpus(tmp_path, BODIES)
    (dest / "MANIFEST.json").write_text(json.dumps({"provenance": {}}))
    assert bt.run_verify(dest) == bt.EXIT_NOT_MEASURED


def test_entry_without_a_sha_cannot_be_verified(tmp_path):
    """An entry with nothing to compare against must NOT silently pass."""
    dest = _fixture_corpus(tmp_path, BODIES)
    manifest = json.loads((dest / "MANIFEST.json").read_text())
    manifest["files"][0].pop("template_sha256")
    (dest / "MANIFEST.json").write_text(json.dumps(manifest))
    assert bt.run_verify(dest) == bt.EXIT_NOT_MEASURED


# ── the real corpus ───────────────────────────────────────────────────────────

def test_the_shipped_rails_corpus_verifies():
    verdicts, _ = bt.verify(bt.DEST)
    drifted = [p for p, v in verdicts if v != "MATCH"]
    assert len(verdicts) == 43, f"expected 43 manifest entries, got {len(verdicts)}"
    assert drifted == [], f"rails templates drifted from MANIFEST.json: {drifted}"


def test_the_cli_exits_0_on_the_shipped_corpus():
    """The exit code is the contract; a library check nobody can shell is not one."""
    proc = subprocess.run([sys.executable, str(BUILDER), "--verify"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "43 MATCH" in proc.stdout
    assert "PASS" in proc.stdout

#!/usr/bin/env python3
"""The contract mirror must stay current, or it is worse than absent.

WHY
A contract an agent never sees is a contract nobody corrects — that is how
`agents/AURELIX.yaml` came to describe an "e-commerce sub-system owned by KIRA"
with 7 workers while the measured system has 55 declared instruments. The mirror
puts those contracts in front of an agent at session start. A STALE mirror is
worse than none, because it looks authoritative and is not.

MUTATION RUN 2026-08-19 (a test that cannot fail is not a test):
    appended a line to .claude/contracts/agents/AURELIX.yaml
      -> sync_contracts.py --check  exit 1, "1 file(s) stale or missing"
      -> test_the_mirror_is_current FAILED
    re-synced
      -> exit 0, 5 passed
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]        # services/aurelix-ag
SYNC = ROOT / "scripts" / "sync_contracts.py"
MIRROR = ROOT / ".claude" / "contracts"
EXIT_NOT_MEASURED = 3


def _check() -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SYNC), "--check"],
                          cwd=ROOT, capture_output=True, text=True)


def test_the_sync_script_exists():
    assert SYNC.is_file(), f"{SYNC} is missing"


def test_the_mirror_is_current():
    """Fails when control-tower's contracts have moved and nobody re-synced."""
    proc = _check()
    if proc.returncode == EXIT_NOT_MEASURED:
        pytest.skip("control-tower not on this machine — NOT_MEASURED, not a pass")
    assert proc.returncode == 0, (proc.stdout + proc.stderr)


def test_every_mirrored_file_says_it_is_a_mirror():
    """A copy that looks editable will be edited."""
    if not MIRROR.is_dir():
        pytest.skip("mirror not present")
    files = list(MIRROR.rglob("*.yaml")) + list(MIRROR.rglob("*.md"))
    assert files, "mirror directory is empty"
    for f in files:
        if f.name == "README.md":
            continue
        head = f.read_text(encoding="utf-8")[:400]
        assert "MIRRORED" in head and "DO NOT EDIT" in head, f"{f.name} carries no mirror header"


def test_the_mirror_names_its_source_of_truth():
    if not (MIRROR / "README.md").is_file():
        pytest.skip("mirror not present")
    readme = (MIRROR / "README.md").read_text(encoding="utf-8")
    assert "control-tower" in readme
    assert "capability-register.yaml" in readme


def test_the_drift_against_the_register_is_reported_not_hidden():
    """Mirroring a wrong contract silently would make things worse. The README
    must carry the comparison so the disagreement is visible."""
    if not (MIRROR / "README.md").is_file():
        pytest.skip("mirror not present")
    readme = (MIRROR / "README.md").read_text(encoding="utf-8")
    assert "capability tokens claimed by the contracts" in readme
    assert "instruments in" in readme

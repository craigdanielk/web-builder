#!/usr/bin/env python3
"""A measured verdict must survive the act of reporting it.

Both gates guarded here used to lose a real answer to a traceback:

  verify_rails_gate.py   `write_verdict()` did not create its --output-dir, so a
                         run against a directory that did not exist yet measured
                         correctly and then died with FileNotFoundError. The
                         process exited 1 — indistinguishable, in any status
                         list, from a measured FAIL.
  verify_gate_c.py       `subprocess.run(..., timeout=180)` had no handler. A
                         slow build raised TimeoutExpired out of main(). A
                         timeout is the definition of "I could not measure"; it
                         must be exit 3, with the limit stated.

These tests assert the exit CODE and the stated reason, never a log line alone,
and they assert the absence of "Traceback" — the whole defect was that a crash
was being read as a verdict.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import verify_gate_c  # noqa: E402
import verify_rails_gate  # noqa: E402

RAILS_GATE = SCRIPTS / "verify_rails_gate.py"
GATE_C = SCRIPTS / "verify_gate_c.py"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args], capture_output=True, text=True, timeout=120
    )


# ── verify_rails_gate.py: the verdict reaches disk ────────────────────────────

def test_rails_gate_creates_a_missing_output_dir_and_keeps_its_measured_code(tmp_path):
    """A --output-dir that does not exist yet is not a measurement failure."""
    site = tmp_path / "site"
    site.mkdir()
    output = tmp_path / "does" / "not" / "exist"
    assert not output.exists()

    proc = _run([str(RAILS_GATE), "--site-dir", str(site), "--output-dir", str(output)])

    assert "Traceback" not in proc.stderr, proc.stderr
    # The measured verdict here is FAIL (no rails-emission.json), and FAIL is
    # what must be reported — not the 1 a FileNotFoundError also produced.
    assert proc.returncode == verify_rails_gate.EXIT_FAIL, proc.stdout + proc.stderr
    assert "VERIFY RAILS GATE: FAIL" in proc.stdout
    written = output / "rails-gate.json"
    assert written.exists(), "the verdict was measured and then thrown away"
    assert json.loads(written.read_text())["verdict"] == "FAIL"


def test_rails_gate_write_verdict_returns_the_path_it_created(tmp_path):
    output = tmp_path / "a" / "b" / "c"
    path, error = verify_rails_gate.write_verdict(output, {"verdict": "PASS", "reasons": []})
    assert error is None
    assert path is not None and path.exists()
    assert json.loads(path.read_text())["verdict"] == "PASS"


def test_rails_gate_unwritable_output_is_not_measured_with_a_stated_reason(tmp_path):
    """A file where the output directory should be: a genuine write failure."""
    site = tmp_path / "site"
    site.mkdir()
    output = tmp_path / "occupied"
    output.write_text("this is a file, not a directory\n")

    proc = _run([str(RAILS_GATE), "--site-dir", str(site), "--output-dir", str(output)])

    assert "Traceback" not in proc.stderr, proc.stderr
    assert proc.returncode == verify_rails_gate.EXIT_NOT_MEASURED, proc.stdout + proc.stderr
    assert "NOT_MEASURED" in proc.stdout
    assert "could not be written" in proc.stdout, proc.stdout


def test_rails_gate_write_verdict_reports_the_oserror_instead_of_raising(tmp_path):
    output = tmp_path / "occupied"
    output.write_text("not a directory\n")
    path, error = verify_rails_gate.write_verdict(output, {"verdict": "PASS"})
    assert path is None
    assert error and "could not be written" in error


# ── verify_gate_c.py: a timeout is NOT_MEASURED, not a crash ──────────────────

def _fake_app(tmp_path: Path) -> Path:
    app = tmp_path / "site"
    (app / "app").mkdir(parents=True)
    (app / "package.json").write_text('{"name":"x","scripts":{"build":"next build"}}\n')
    (app / "app" / "page.tsx").write_text("export default function P(){return null}\n")
    return app


def test_gate_c_timeout_is_not_measured_with_the_limit_stated(tmp_path, monkeypatch, capsys):
    app = _fake_app(tmp_path)

    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["npm", "run", "build"], timeout=180)

    monkeypatch.setattr(verify_gate_c.subprocess, "run", _timeout)
    monkeypatch.setattr(sys, "argv", ["verify_gate_c.py", "--site-dir", str(app)])

    code = verify_gate_c.main()
    out = capsys.readouterr().out

    assert code == verify_gate_c.NOT_MEASURED
    assert "NOT_MEASURED" in out
    assert str(verify_gate_c.BUILD_TIMEOUT) in out, out
    assert "PASS" not in out


def test_gate_c_missing_npm_is_not_measured(tmp_path, monkeypatch, capsys):
    app = _fake_app(tmp_path)

    def _no_npm(*args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory: 'npm'")

    monkeypatch.setattr(verify_gate_c.subprocess, "run", _no_npm)
    monkeypatch.setattr(sys, "argv", ["verify_gate_c.py", "--site-dir", str(app)])

    code = verify_gate_c.main()
    out = capsys.readouterr().out
    assert code == verify_gate_c.NOT_MEASURED
    assert "npm is not on PATH" in out


def test_gate_c_still_fails_a_build_that_actually_failed(tmp_path, monkeypatch, capsys):
    """The honesty fix must not turn a measured FAIL into NOT_MEASURED."""
    app = _fake_app(tmp_path)

    class _Done:
        returncode = 1
        stderr = "type error"
        stdout = ""

    monkeypatch.setattr(verify_gate_c.subprocess, "run", lambda *a, **k: _Done())
    monkeypatch.setattr(sys, "argv", ["verify_gate_c.py", "--site-dir", str(app)])
    assert verify_gate_c.main() == 1
    capsys.readouterr()


def test_gate_c_still_passes_a_build_that_succeeded(tmp_path, monkeypatch, capsys):
    app = _fake_app(tmp_path)

    class _Done:
        returncode = 0
        stderr = ""
        stdout = ""

    monkeypatch.setattr(verify_gate_c.subprocess, "run", lambda *a, **k: _Done())
    monkeypatch.setattr(sys, "argv", ["verify_gate_c.py", "--site-dir", str(app)])
    assert verify_gate_c.main() == 0
    assert "VERIFY GATE C: PASS" in capsys.readouterr().out


# ── the declarations still load, and still describe these branches ────────────

@pytest.mark.parametrize("script", [RAILS_GATE, GATE_C])
def test_describe_exits_zero_with_valid_json(script):
    proc = _run([str(script), "--describe"])
    assert proc.returncode == 0, proc.stderr
    spec = json.loads(proc.stdout)
    assert spec["kind"] == "gate"
    assert "3" in {str(k) for k in spec["exit_contract"]}


def test_gate_c_no_longer_claims_it_crashes_on_a_timeout():
    """A stale blindness claim is as bad as a stale doc."""
    blind = " ".join(verify_gate_c.CAPABILITY["cannot_see"])
    assert "crashes with a traceback" not in blind


def test_rails_gate_declares_the_unpersisted_verdict_branch():
    assert "written" in str(verify_rails_gate.CAPABILITY["exit_contract"][3])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

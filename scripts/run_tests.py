#!/usr/bin/env python3
"""Run every Python test in this repo, both conventions, one command.

WHY THIS EXISTS
This repo has two test idioms and no runner that covers both:

  * script-style  — a `test(name, cond, detail)` helper, PASS/FAIL counters and
    a module-level `sys.exit(...)`. Twelve files. `pytest` cannot collect them:
    the `sys.exit` fires at import and pytest reports INTERNALERROR, aborting
    the whole run — so ONE script-style file makes `pytest scripts/` collect
    nothing at all.
  * pytest-style — plain `def test_*` functions. Eight files, and growing,
    because every task added this session used it.

The consequence was measured on 2026-08-17: `pytest scripts/` exits non-zero
having run zero tests, and agents worked around it by naming individual files.
A suite nobody can run in one command stops being run — and a test that never
runs is indistinguishable from one that does not exist.

This runner shells each file in its own process, so a `sys.exit` in one cannot
end the run, and reports one summary. It never swallows a failure: any file
that exits non-zero makes the runner exit 1.

    python3 scripts/run_tests.py            # everything
    python3 scripts/run_tests.py -k phase0  # substring filter on the filename
    python3 scripts/run_tests.py --list     # show what would run, run nothing
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent

# A file is script-style iff it calls sys.exit() at module level. That is the
# exact property that breaks pytest collection, so it is the right test — not a
# hand-maintained list, which would drift the first time someone adds a file.
def is_script_style(path: Path) -> bool:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("sys.exit"):
            return True
    return False


def discover(pattern: str | None) -> list[Path]:
    files = sorted(SCRIPTS.glob("test_*.py"))
    if pattern:
        files = [f for f in files if pattern in f.name]
    return files


def run_one(path: Path) -> tuple[str, str]:
    """Run one test file in its own process.

    Returns (state, last_meaningful_line) where state is PASS | FAIL |
    NOT_MEASURED. The third state exists for the same reason every gate in this
    system has one: a file that could not run has not passed, and recording it
    as a failure is equally false — it hides the real defect, which is that
    nobody can run it. Three files need a <build-dir> argument no caller
    supplies; they have therefore never run in CI or in any session.
    """
    cmd = ([sys.executable, str(path)] if is_script_style(path)
           else [sys.executable, "-m", "pytest", str(path), "-q"])
    proc = subprocess.run(cmd, cwd=SCRIPTS.parent, capture_output=True, text=True)
    out = proc.stdout or proc.stderr
    tail = [ln for ln in out.splitlines() if ln.strip()]
    last = tail[-1].strip() if tail else "(no output)"

    if proc.returncode == 0:
        return "PASS", last
    # A usage banner means the file demands arguments — it did not measure
    # anything and did not fail anything.
    if out.lstrip().startswith("usage:") or "usage: test_" in out:
        return "NOT_MEASURED", "needs arguments — no caller supplies them"
    return "FAIL", last


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-k", dest="pattern", help="substring filter on the filename")
    ap.add_argument("--list", action="store_true", help="list files, run nothing")
    args = ap.parse_args()

    files = discover(args.pattern)
    if not files:
        print("no test files matched — that is a failure, not an empty pass",
              file=sys.stderr)
        return 1

    if args.list:
        for f in files:
            print(f"{'script' if is_script_style(f) else 'pytest':>6}  {f.name}")
        return 0

    failed: list[str] = []
    unmeasured: list[str] = []
    for f in files:
        state, tail = run_one(f)
        print(f"{state:<12}  {f.name:<42} {tail[:66]}")
        if state == "FAIL":
            failed.append(f.name)
        elif state == "NOT_MEASURED":
            unmeasured.append(f.name)

    passed = len(files) - len(failed) - len(unmeasured)
    print(f"\n{passed}/{len(files)} passed · {len(failed)} failed · "
          f"{len(unmeasured)} not measured")
    if failed:
        print("FAILED: " + ", ".join(failed), file=sys.stderr)
    if unmeasured:
        print("NOT MEASURED (needs arguments, so has never run): "
              + ", ".join(unmeasured), file=sys.stderr)
    # Exit codes mirror the build's own contract: 0 ok · 1 failed ·
    # 3 NOT_MEASURED. A green-looking 0 while three files never ran is exactly
    # the dishonesty this repo spent a session removing.
    if failed:
        return 1
    if unmeasured:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

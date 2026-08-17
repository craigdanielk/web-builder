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
import ast
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def _module_level_sys_exit(tree: ast.Module) -> bool:
    """True iff the module body reaches a sys.exit() call without a def/class.

    Descends into module-level `if`/`try`/`with`/`for` bodies — a
    `if __name__ == "__main__": sys.exit(main())` guard and a
    `if FAIL > 0:\n    sys.exit(1)` tail are both module level and both make
    the file script-style. It does NOT descend into function or class bodies:
    a `sys.exit` inside a helper is called by whoever calls the helper, not at
    import, and pytest collects such a file fine.
    """
    def walk(body) -> bool:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                fn = node.value.func
                if isinstance(fn, ast.Attribute) and fn.attr == "exit" and \
                        isinstance(fn.value, ast.Name) and fn.value.id == "sys":
                    return True
            for field in ("body", "orelse", "finalbody"):
                inner = getattr(node, field, None)
                if isinstance(inner, list) and walk(inner):
                    return True
            for handler in getattr(node, "handlers", []) or []:
                if walk(handler.body):
                    return True
        return False

    return walk(tree.body)


# A file is script-style iff it calls sys.exit() at module level. That is the
# exact property that breaks pytest collection, so it is the right test — not a
# hand-maintained list, which would drift the first time someone adds a file.
#
# Measured 2026-08-17: a `startswith("sys.exit")` line scan misses every
# indented one, so two script-style files (test_captures_wiring.py,
# test_deploy_adapter.py) were handed to pytest, which then collected their
# `def test(name, condition, detail="")` helper as a test case and errored on a
# missing `name` fixture. Worse than the error: pytest reported the remaining
# `test_*` functions as PASSED, because the helper only *prints* on failure and
# never raises — four tests that could not fail. The AST check ends both.
def is_script_style(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    return _module_level_sys_exit(tree)


# ── The three post-build files, and the build directory they were never given ──
#
# test_asset_coverage / test_empty_sections / test_section_artifact_emit each
# assert over a completed build: artifacts on disk, the omission register, the
# coverage counters. They take `<build-dir>` and exit 2 with a usage banner
# without one, and NO caller ever supplied it — so as of 2026-08-17 none of the
# three had run, in CI or in any session. Three suites that exist and measure
# nothing.
#
# They cannot be made to run on a synthetic fixture without becoming a test of
# the fixture, so the runner finds a real build instead. If there is none, they
# stay NOT_MEASURED — which is the true answer, not a green pass.
#
# The build is COPIED first, minus site/ (508M of node_modules against 430K of
# everything else). test_asset_coverage re-runs the real stage_resolve_assets
# to prove idempotence, i.e. it WRITES; output/cape-crypto is read by other
# sessions and must not be mutated by running the suite.
NEEDS_BUILD_DIR = {
    "test_asset_coverage.py",
    "test_empty_sections.py",
    "test_section_artifact_emit.py",
}
_BUILD_COPY_DIRS = ("sections", "section-artifacts", "shared")


def find_build_dir() -> Path | None:
    """Newest output/<project>/ that carries the artifacts these tests read."""
    output = SCRIPTS.parent / "output"
    if not output.is_dir():
        return None
    candidates = [d for d in output.iterdir()
                  if d.is_dir()
                  and (d / "section-artifacts").is_dir()
                  and any((d / "section-artifacts").rglob("*.json"))
                  and (d / "asset-coverage.json").exists()]
    if not candidates:
        return None
    return max(candidates, key=lambda d: d.stat().st_mtime)


def copy_build(src: Path, dest: Path) -> Path:
    """Copy just the parts the post-build tests read. Never copies site/."""
    import shutil
    dest.mkdir(parents=True, exist_ok=True)
    for sub in _BUILD_COPY_DIRS:
        if (src / sub).is_dir():
            shutil.copytree(src / sub, dest / sub, dirs_exist_ok=True)
    for f in src.glob("*.json"):
        shutil.copy2(f, dest / f.name)
    return dest


def discover(pattern: str | None) -> list[Path]:
    files = sorted(SCRIPTS.glob("test_*.py"))
    if pattern:
        files = [f for f in files if pattern in f.name]
    return files


def run_one(path: Path, build_dir: Path | None = None) -> tuple[str, str]:
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
    if path.name in NEEDS_BUILD_DIR:
        if build_dir is None:
            return "NOT_MEASURED", "no completed build on disk to assert against"
        cmd.append(str(build_dir))
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

    import tempfile

    failed: list[str] = []
    unmeasured: list[str] = []
    source_build = find_build_dir() if any(f.name in NEEDS_BUILD_DIR for f in files) else None
    tmp = tempfile.TemporaryDirectory() if source_build else None
    build_dir = None
    if source_build and tmp:
        build_dir = copy_build(source_build, Path(tmp.name) / source_build.name)
        print(f"post-build suites assert against a copy of output/{source_build.name}/ "
              f"(the original is never written to)\n")

    for f in files:
        state, tail = run_one(f, build_dir)
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

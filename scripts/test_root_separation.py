#!/usr/bin/env python3
"""Inputs and outputs are separate roots. Moving one must never move the other.

WHY THIS EXISTS

`--output-root` re-rooted the module-level OUTPUT_DIR, and the crawl store was
derived as `OUTPUT_DIR / "extractions"`. So a build into a scratch root looked
for `<scratch>/extractions/`, found nothing, left `extraction_dir = None`, and
resolved ZERO assets — while exiting 0.

Measured on the M3 cape-crypto build, 2026-08-17:

    output/cape-crypto      asset-coverage  extracted: 5   unresolved: 0
    <scratch>/cape-crypto   asset-coverage  extracted: 0   unresolved: 5

The five that vanished are the tenant's own imagery — aluma, dave, idatco,
numeral, xago. A build that silently drops a licensed FSP's real logos and
founder photo, and reports success, is the exact failure mode this repo exists
to remove: degrade toward fabrication rather than toward stopping.

A crawl is an INPUT — expensive, cached, reused across builds of the same
tenant. `--output-root` moves outputs. `--extractions-root` moves inputs.
Neither moves the other, and this file holds that line.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import orchestrate  # noqa: E402

ROOT = Path(__file__).parent.parent

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {detail}")


print("\n─── roots are independent ───")

# ── 1. The default: the crawl store is under the repo, not derived at import
# time from whatever OUTPUT_DIR happens to be later.
check("EXTRACTIONS_DIR defaults under the repo output tree",
      orchestrate.EXTRACTIONS_DIR == ROOT / "output" / "extractions",
      f"got {orchestrate.EXTRACTIONS_DIR}")

# ── 2. The load-bearing one: rebinding OUTPUT_DIR must not move the input
# store. This is the regression — the old code recomputed
# `OUTPUT_DIR / "extractions"` at every call site, so this assertion could not
# even be expressed.
_saved_out = orchestrate.OUTPUT_DIR
_saved_ex = orchestrate.EXTRACTIONS_DIR
try:
    with tempfile.TemporaryDirectory() as tmp:
        orchestrate.OUTPUT_DIR = Path(tmp) / "scratch"
        check("re-rooting OUTPUT_DIR leaves EXTRACTIONS_DIR untouched",
              orchestrate.EXTRACTIONS_DIR == _saved_ex,
              f"EXTRACTIONS_DIR moved to {orchestrate.EXTRACTIONS_DIR}")
        check("EXTRACTIONS_DIR is not a child of the overridden OUTPUT_DIR",
              Path(tmp) not in orchestrate.EXTRACTIONS_DIR.parents,
              f"{orchestrate.EXTRACTIONS_DIR} is under {tmp}")
finally:
    orchestrate.OUTPUT_DIR = _saved_out
    orchestrate.EXTRACTIONS_DIR = _saved_ex

# ── 3. No call site may reconstruct the input root from the output root.
# Grepping the source is the only way to assert this: a call site that says
# `OUTPUT_DIR / "extractions"` reintroduces the coupling no matter what the
# module constant says, and it is one careless line away at all times.
#
# Comment lines are excluded — the constant's own docstring quotes the banned
# expression to explain why it is banned, and a bare substring scan flags the
# documentation as the defect. (test_empty_sections.py had exactly this bug
# against `src=""`; it failed a correct build on two comment lines the first
# time it ever ran.)
src = (ROOT / "scripts" / "orchestrate.py").read_text(encoding="utf-8")
derived = [ln.strip() for ln in src.splitlines()
           if ('OUTPUT_DIR / "extractions"' in ln or "OUTPUT_DIR / 'extractions'" in ln)
           and not ln.strip().startswith(("#", "*", '"""'))]
check("no call site derives the extraction store from OUTPUT_DIR",
      not derived, str(derived[:3]))

# ── 4. Both roots are declarable on the CLI. An input root you cannot name is
# an input root that will be re-derived by the next person who needs it moved.
help_text = subprocess.run(
    [sys.executable, str(ROOT / "scripts" / "orchestrate.py"), "--help"],
    capture_output=True, text=True, timeout=120).stdout
check("--output-root is declarable", "--output-root" in help_text)
check("--extractions-root is declarable", "--extractions-root" in help_text)

# ── 5. Resolution actually reads the input root. A prior crawl must be found
# when only the OUTPUT root has moved — the precise case that returned zero.
check("a prior crawl for cape-crypto exists to be resolved",
      orchestrate.EXTRACTIONS_DIR.is_dir()
      and any(orchestrate.EXTRACTIONS_DIR.glob("cape-crypto-*")),
      f"no cape-crypto-* under {orchestrate.EXTRACTIONS_DIR}")

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)

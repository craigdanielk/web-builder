#!/usr/bin/env python3
"""A library component that uses hooks without "use client" breaks the build.

Next.js App Router treats every module as a Server Component unless it declares
otherwise. A component calling useState/useEffect/useRef without the directive
does not degrade — `next build` FAILS:

    You're importing a component that needs `useState`. This React Hook only
    works in a Client Component.

Found by the first --deploy run after Task 7 began injecting real library
components into built sections. Nine components were affected. Before Task 7
the library was copied but rarely imported, so the defect was unreachable and
nothing measured it.

This is a LIBRARY defect, not a generation defect. No amount of pipeline
correctness fixes a component that cannot compile, which is the argument for
treating the library as the binding constraint on output quality.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
LIB = ROOT / "skills" / "animation-components"

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {detail}")


HOOK = re.compile(r"\buse(State|Effect|Ref|Layout Effect|LayoutEffect|"
                  r"Callback|Memo|Reducer|Context)\s*\(")
DIRECTIVE = re.compile(r"""^\s*['"]use client['"]""", re.M)


def declares_client(text: str) -> bool:
    """The directive must precede any import to take effect."""
    m = DIRECTIVE.search(text)
    if not m:
        return False
    first_import = text.find("import ")
    return first_import == -1 or m.start() < first_import


offenders = []
checked = 0
for path in sorted(LIB.rglob("*.tsx")):
    text = path.read_text(encoding="utf-8", errors="replace")
    if not HOOK.search(text):
        continue
    checked += 1
    if not declares_client(text):
        offenders.append(str(path.relative_to(ROOT)))

test("every hook-using library component declares \"use client\"",
     not offenders, f"{len(offenders)}: {offenders[:6]}")

# The directive must come BEFORE imports — placed after them it is inert and
# next build fails exactly as if it were absent, while a naive grep says it is
# present. That combination (looks fixed, still broken) is worth its own check.
misplaced = []
for path in sorted(LIB.rglob("*.tsx")):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = DIRECTIVE.search(text)
    if not m:
        continue
    first_import = text.find("import ")
    if first_import != -1 and m.start() > first_import:
        misplaced.append(str(path.relative_to(ROOT)))

test("no \"use client\" directive sits after an import (inert)",
     not misplaced, str(misplaced[:6]))

print(f"\n  {checked} hook-using component(s) checked of "
      f"{len(list(LIB.rglob('*.tsx')))} total")
print(f"  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)

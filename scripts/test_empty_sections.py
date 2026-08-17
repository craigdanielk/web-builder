#!/usr/bin/env python3
"""A heading over empty space is worse than no section.

Run against a build directory. Asserts the sourced-or-absent rule end to end:

  - no EMITTED section has zero sourced slots
  - omissions are recorded, with the archetype named
  - the register is a real register: its count agrees with what is on disk
  - no shipped .tsx carries an empty image src (next/image THROWS on one, so
    the route errors at runtime while every brace and string check passes)

The last two exist because the first two can be satisfied by a file that
records nothing. A register that always says "0 omitted" and a build that
emits nothing both pass a naive check.
"""
import json
import sys
from pathlib import Path

BUILD = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if not BUILD:
    print("usage: test_empty_sections.py <build-dir>")
    sys.exit(2)

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


art_dir = BUILD / "section-artifacts"
if not art_dir.is_dir():
    print(f"  ✗ no section-artifacts/ under {BUILD} — nothing measured")
    sys.exit(1)

arts = [json.loads(p.read_text()) for p in sorted(art_dir.rglob("*.json"))]


def sourced(a):
    return sum(1 for r in (a.get("provenance") or [])
               if r.get("source") in ("harvested", "phase0"))


# ── 1. nothing emitted with zero sourced content ─────────────────────────
empty = [a for a in arts if sourced(a) == 0]
test("no emitted section has zero sourced slots", not empty,
     str([(a.get("archetype"), a.get("origin")) for a in empty][:5]))

# ── 2. the register exists and names archetypes ──────────────────────────
reg_path = BUILD / "omitted-sections.json"
test("omissions are recorded", reg_path.exists(), str(reg_path))

if reg_path.exists():
    reg = json.loads(reg_path.read_text())
    omitted = reg.get("omitted") or []
    test("omission records name the archetype",
         all("archetype" in o for o in omitted), str(omitted[:2]))
    test("omission records name a reason",
         all(o.get("reason") for o in omitted), str(omitted[:2]))
    test("every omission is attributed to a page",
         all(o.get("page") for o in omitted), str(omitted[:2]))

    # ── 3. the register is not vacuous ───────────────────────────────────
    # A build that omitted nothing is possible; a register that DISAGREES
    # with its own summary is not. This is the check a stub register fails.
    test("summary count matches the record count",
         reg.get("summary", {}).get("omitted") == len(omitted),
         f"summary={reg.get('summary', {}).get('omitted')} records={len(omitted)}")

    # An omission must not also be on disk — that would mean it was recorded
    # as dropped and shipped anyway.
    on_disk = {p.name for p in BUILD.glob("sections/*/*.tsx")}
    shipped_anyway = [o["file"] for o in omitted
                      if o.get("file") in on_disk
                      and any(o["file"] == p.name
                              for p in (BUILD / "sections" / o.get("page", "")
                                        .replace("sections/", "")).glob("*.tsx"))]
    test("no section is recorded as omitted and shipped anyway",
         not shipped_anyway, str(shipped_anyway[:5]))

# ── 4. no empty image src survives into shipped code ─────────────────────
#
# Comment lines are excluded. Several generated sections carry a header
# comment that QUOTES this very rule — `<Image src="">` THROWS in next/image
# — and a plain substring scan flagged the documentation as the defect. The
# first time this file ever ran (2026-08-17; it had never been given a build
# dir) it failed the committed cape-crypto build on two comment lines. A test
# that fails on its own rule being written down measures nothing.
def _is_comment(stripped: str) -> bool:
    return stripped.startswith(("*", "//", "/*"))


bad_src = []
for tsx in list(BUILD.glob("sections/*/*.tsx")) + list(BUILD.glob("shared/*.tsx")):
    for n, line in enumerate(tsx.read_text().splitlines(), 1):
        if 'src=""' in line and not _is_comment(line.strip()):
            bad_src.append(f"{tsx.parent.name}/{tsx.name}:{n}")
test("no shipped section renders an image with an empty src",
     not bad_src, str(bad_src[:5]))

print(f"\n  {len(arts)} artifact(s) checked")
print(f"  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)

#!/usr/bin/env python3
"""Every emitted section must have a companion artifact JSON that validates."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.section_artifact import SectionArtifact, validate

BUILD = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if not BUILD:
    print("usage: test_section_artifact_emit.py <build-dir>")
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

tsx_files = sorted((BUILD / "sections").rglob("*.tsx"))
art_files = sorted((BUILD / "section-artifacts").rglob("*.json"))

test("at least one section was built", len(tsx_files) > 0, f"found {len(tsx_files)}")
test("one artifact per section", len(art_files) == len(tsx_files),
     f"{len(art_files)} artifacts vs {len(tsx_files)} sections")

bad = []
for f in art_files:
    a = SectionArtifact.from_dict(json.loads(f.read_text()))
    problems = validate(a)
    if problems:
        bad.append((f.name, problems))
test("every artifact validates", not bad, str(bad[:3]))

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)

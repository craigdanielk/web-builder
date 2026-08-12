#!/usr/bin/env python3
"""The contract every pipeline stage speaks."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.section_artifact import SectionArtifact, validate

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

a = SectionArtifact(
    tsx="export default function X() { return <section/>; }",
    archetype="HERO",
    variant="centered",
    section_uid="9fab231b0d31",
    intensity="moderate",
    origin="supabase_template",
    provenance=[{"section_uid": "9fab231b0d31", "slot": "headline",
                 "value": "Buy Bitcoin South Africa", "source": "harvested"}],
    assets=[],
    animation=None,
)

test("round-trips through dict", SectionArtifact.from_dict(a.to_dict()) == a)
test("valid artifact has no violations", validate(a) == [])

bad_origin = SectionArtifact.from_dict({**a.to_dict(), "origin": "magic"})
test("unknown origin is rejected", "origin" in " ".join(validate(bad_origin)))

bad_prov = SectionArtifact.from_dict({
    **a.to_dict(),
    "provenance": [{"section_uid": "x", "slot": "headline", "value": "v", "source": "default"}],
})
test("source 'default' is rejected", "default" in " ".join(validate(bad_prov)))

empty_tsx = SectionArtifact.from_dict({**a.to_dict(), "tsx": ""})
test("empty tsx is rejected", "tsx" in " ".join(validate(empty_tsx)))

# Hardened validator tests: malformed input should return violations, not crash
non_dict_row = SectionArtifact.from_dict({**a.to_dict(), "provenance": ["not_a_dict"]})
test("non-dict provenance row returns violation", "row 0" in " ".join(validate(non_dict_row)))

none_provenance = SectionArtifact(
    tsx=a.tsx, archetype=a.archetype, variant=a.variant,
    section_uid=a.section_uid, intensity=a.intensity, origin=a.origin,
    provenance=None, assets=[], animation=None,
)
test("None provenance returns violation", "provenance is None" in " ".join(validate(none_provenance)))

none_assets = SectionArtifact(
    tsx=a.tsx, archetype=a.archetype, variant=a.variant,
    section_uid=a.section_uid, intensity=a.intensity, origin=a.origin,
    provenance=[], assets=None, animation=None,
)
test("None assets returns violation", "assets is None" in " ".join(validate(none_assets)))

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)

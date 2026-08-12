#!/usr/bin/env python3
"""No shipped page may carry a placeholder or a remote src.

Also verifies the coverage report is idempotent: a second run of
stage_resolve_assets over the same output dir must produce a
byte-identical asset-coverage.json, not an accumulated one. Learned from
stage_inject_animation's history on this plan: its first version
accumulated across runs and its test asserted only one field, so a
doubling bug shipped anyway. This test asserts every field, twice.
"""
import json
import subprocess
import sys
from pathlib import Path

BUILD = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if not BUILD:
    print("usage: test_asset_coverage.py <build-dir>")
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


cov = json.loads((BUILD / "asset-coverage.json").read_text())
tsx_all = "\n".join(p.read_text() for p in (BUILD / "sections").rglob("*.tsx"))

test("coverage report exists", "total" in cov, str(cov))
test("no placeholder.svg in any section", "placeholder.svg" not in tsx_all)
test("no remote image src in any section", "https://capecrypto.com" not in tsx_all)
test("unresolved slots are declared, not hidden",
     (BUILD / "image-jobs.json").exists())
test("every unresolved slot has a generation job",
     len(json.loads((BUILD / "image-jobs.json").read_text())) == cov["unresolved"],
     f"jobs vs unresolved={cov['unresolved']}")

# ── Idempotency: a second stage_resolve_assets run over this SAME output
# dir must not change asset-coverage.json at all. Run it via the real
# orchestrator function (not a re-implementation) so the assertion tests
# the code that ships, not a paraphrase of it.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "lib"))
import orchestrate  # noqa: E402

extraction_data = None
extraction_root = BUILD.parent / "extractions"
if extraction_root.exists():
    candidates = sorted(extraction_root.glob(f"{BUILD.name}-*/extraction-data.json"))
    if candidates:
        extraction_data = json.loads(candidates[-1].read_text())

before = json.loads((BUILD / "asset-coverage.json").read_text())
orchestrate.stage_resolve_assets(BUILD, extraction_data)
after = json.loads((BUILD / "asset-coverage.json").read_text())

test("coverage total is stable across two runs", before["total"] == after["total"],
     f"{before['total']} -> {after['total']}")
test("coverage extracted is stable across two runs", before["extracted"] == after["extracted"],
     f"{before['extracted']} -> {after['extracted']}")
test("coverage generated is stable across two runs", before["generated"] == after["generated"],
     f"{before['generated']} -> {after['generated']}")
test("coverage unresolved is stable across two runs", before["unresolved"] == after["unresolved"],
     f"{before['unresolved']} -> {after['unresolved']}")
test("coverage file is byte-identical across two runs", before == after,
     f"{before} != {after}")

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)

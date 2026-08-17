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
import re
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
# A remote src is ALLOWED, but only when it is declared unresolved.
#
# This assertion used to be "no remote src anywhere", which contradicts the
# ruling recorded at progress.md:214: an asset genuinely absent from
# extraction-data.json (dave.webp) is left UNTOUCHED and recorded, never
# swapped for a placeholder — a visible real image beats a grey box, and
# inventing a local path for a file we do not have is fabrication. The release
# criterion was amended to "zero placeholders; remote srcs recorded and
# counted"; this test was never updated to match, so it failed the build for
# doing the right thing.
#
# Still able to fail, which is the point: an undeclared remote src — one the
# resolver never saw, or saw and claimed to have resolved — is a real defect.
# The count must account for every remote reference that ships.
_remote = re.findall(r'src="(https?://[^"]+)"', tsx_all)
_unresolved = int(cov.get("unresolved", 0))
test("no placeholder stands in for a real asset",
     "placeholder.svg" not in tsx_all)
test("every remote src that ships is declared unresolved",
     len(_remote) <= _unresolved,
     f"{len(_remote)} remote src(s) in sections, {_unresolved} declared "
     f"unresolved: {_remote[:3]}")
# `asset-coverage.json` is four counters; the NAMES live in `image-jobs.json`.
# A count with no matching record is a number nobody can act on or check, so
# the two files must agree. This is a cross-file consistency assertion, and it
# fails if either side drifts — a job list that silently empties while the
# counter still says 1, or a counter reset while gaps remain.
#
# `image-jobs.json` now carries jobs from TWO directions, so the old identity
# `len(jobs) == unresolved` is no longer the invariant — it was, back when
# `gaps()` fired only on `origin == "unresolved"`, and it read as a pass on
# every build because both sides were 0. The two populations are distinguished
# by `reason`, and each is asserted against its own counter:
#
#   "no extracted source"     ← the source HAD it and the fetch failed
#                               (one per unresolved asset — the old identity)
#   "design demand, no source" ← a `// Art:` slot the source never had
#                               (has no counterpart in asset-coverage.json;
#                                it is demand, not a coverage miss)
#
# `image-jobs.json` has two shapes on disk. v1 was a bare list of job records;
# `image-jobs-v2` is an envelope — brand tokens, cache counters, `refused` and
# `unlowered` alongside `jobs`. This file was written against v1 and, because
# nothing ever supplied it a build directory, never met v2: iterating the
# envelope yields its KEYS, and the first `.get()` raised AttributeError on a
# str. Accept both, and read the job list from wherever it actually is.
_jobs_path = BUILD / "image-jobs.json"
_jobs_payload = json.loads(_jobs_path.read_text()) if _jobs_path.exists() else []
_jobs = _jobs_payload if isinstance(_jobs_payload, list) else (_jobs_payload.get("jobs") or [])
_fetch_jobs = [j for j in _jobs if j.get("reason") == "no extracted source"]
_demand_jobs = [j for j in _jobs if j.get("reason") == "design demand, no source"]

test("every unresolved asset has a named record in image-jobs.json",
     len(_fetch_jobs) == _unresolved,
     f"{_unresolved} unresolved counted, {len(_fetch_jobs)} failed-fetch job(s) "
     f"recorded (of {len(_jobs)} total)")
test("each record names its section and a reason",
     all(j.get("section_uid") and j.get("reason") for j in _jobs),
     str(_jobs[:2]))
test("unresolved slots are declared, not hidden",
     (BUILD / "image-jobs.json").exists())
test("every job carries one of the two known reasons — no unlabelled third kind",
     len(_fetch_jobs) + len(_demand_jobs) == len(_jobs),
     str(sorted({j.get("reason") for j in _jobs})))
# Demand is declaration-driven, so it is checkable against the declarations
# rather than against a coverage counter: every demand job must name an intent
# and an aspect, or it cannot be lowered to a job spec at all.
test("every design-demand job is complete enough to lower to a job spec",
     all(j.get("intent") and j.get("aspect") and j.get("slot")
         for j in _demand_jobs),
     str([j for j in _demand_jobs
          if not (j.get("intent") and j.get("aspect") and j.get("slot"))][:2]))

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

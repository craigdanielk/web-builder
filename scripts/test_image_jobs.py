#!/usr/bin/env python3
"""A gap lowers to a job the real pipeline will accept — and to the same job twice.

Validated against the ACTUAL schema file in services/image-pipeline, not a
paraphrase of it: every object in that schema sets `additionalProperties:
false`, so a field invented from a plan's prose fails at the far end of a spend.

The hash test runs a SECOND INTERPRETER with a different PYTHONHASHSEED. A
determinism claim checked inside one process is not checked at all — Python's
builtin `hash()` is stable within a run and salted between runs, which is
exactly the shape of bug this test exists to catch.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.image_jobs import (
    to_job_v1, job_hash, canonical_json, cache_key_json, ClaimBearingJob,
    NEGATIVE_PROMPT,
)

JOB_SCHEMA = Path.home() / "Developer/GitHub/services/image-pipeline/core/job.schema.json"

GAP = {
    "section_uid": "4f64a50d32d2",
    "archetype": "HERO",
    "variant": "centered",
    "slot": "backdrop_url",
    "intent": "texture",
    "aspect": "16:9",
    "role": "decorative",
    "reason": "design demand, no source",
}

CAPE_BRAND = {
    "name": "Cape Crypto",
    "accent": "#004E89",
    "background": "#ffffff",
    "foreground": "#242d35",
    "reference_images": [
        "benchmarks/captures/capecrypto-vs-bvnk-20260814/bvnk-home-1440.png",
    ],
}

PASS = 0
FAIL = 0
SKIP = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")
        if detail:
            print(f"      {detail}")


def skip(name, why):
    global SKIP
    SKIP += 1
    print(f"  ○ SKIP {name} ({why})")


# ── 1. The real schema ─────────────────────────────────────────────────────
print("\n1. Validation against the real job.schema.json")

job = to_job_v1(GAP, CAPE_BRAND)

try:
    import jsonschema
except ImportError:
    jsonschema = None

if jsonschema is None:
    skip("jsonschema validation", "jsonschema not installed")
elif not JOB_SCHEMA.exists():
    test(f"the schema file exists at {JOB_SCHEMA}", False,
         "services/image-pipeline not on this machine — the contract cannot be checked")
else:
    schema = json.loads(JOB_SCHEMA.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(job, schema)
        test("the emitted job validates against the real schema", True)
    except jsonschema.ValidationError as e:
        test("the emitted job validates against the real schema", False,
             f"{list(e.absolute_path)}: {e.message}")

    # A no-reference job takes a different engine model and must validate too.
    plain = to_job_v1(GAP, {"name": "X", "accent": "#004E89"})
    try:
        jsonschema.validate(plain, schema)
        test("a job with no look anchor also validates", True)
    except jsonschema.ValidationError as e:
        test("a job with no look anchor also validates", False, e.message)

test("schema_version is the contract version, not a guess",
     job["schema_version"] == "job-v1", job["schema_version"])
test("id matches the schema's slug pattern",
     __import__("re").fullmatch(r"[a-z0-9][a-z0-9-]*", job["id"]) is not None,
     job["id"])
test("the id names the section that demanded it, so a job traces back",
     GAP["section_uid"] in job["id"], job["id"])
test("engine carries both required fields",
     set(job["engine"]) >= {"name", "model"}, str(job["engine"]))

# ── 2. The brand reaches the picture ───────────────────────────────────────
print("\n2. The tenant's palette is the job's palette")

test("the accent reaches output.colors",
     CAPE_BRAND["accent"].lower() in job["output"]["colors"], str(job["output"]))
test("and the background token with it",
     "#ffffff" in job["output"]["colors"], str(job["output"]["colors"]))
test("output.background names the palette rather than a house default",
     CAPE_BRAND["accent"].lower() in job["output"]["background"],
     job["output"]["background"])
test("the brand name reaches the subject map",
     job["subject"]["brand_name"] == "Cape Crypto", str(job["subject"]))
test("the benchmark's captured imagery is the look anchor",
     job["reference"][0]["image"].endswith("bvnk-home-1440.png"), str(job.get("reference")))
test("a missing capture is a warning, not a hard failure",
     job["reference"][0]["optional"] is True)
test("with no captures the job is text-to-image, not a broken reference",
     "reference" not in to_job_v1(GAP, {"name": "X"}))

test("the declared aspect reaches the output requirement",
     job["output"]["aspect_ratio"] == "16:9", str(job["output"]))
test("every prompt placeholder resolves from subject or output",
     all(k in job["subject"] or k in job["output"]
         for k in __import__("re").findall(r"\{(\w+)\}", job["spec"]["prompt_template"])),
     job["spec"]["prompt_template"])

# ── 3. The boundary holds a second time ────────────────────────────────────
print("\n3. Claim-bearing gaps are refused here too")

try:
    to_job_v1({**GAP, "intent": "product"}, CAPE_BRAND)
    test("a product depiction is refused at lowering", False, "no exception raised")
except ClaimBearingJob as e:
    test("a product depiction is refused at lowering", True)

for banned in ("charts", "screenshots", "certificates", "people", "logos", "numbers"):
    test(f"the negative prompt forbids {banned}", banned in NEGATIVE_PROMPT)

test("the prompt itself states the prohibition, not only the negative field",
     "no data of any kind" in job["spec"]["prompt_template"])

try:
    to_job_v1({**GAP, "intent": "vibes"}, CAPE_BRAND)
    test("an unknown intent is refused, not defaulted", False, "no exception raised")
except ValueError:
    test("an unknown intent is refused, not defaulted", True)

# ── 4. The hash ────────────────────────────────────────────────────────────
print("\n4. job_hash is a cache key, so it must be stable and sensitive")

h = job_hash(job)
test("the same job hashes identically within a process", h == job_hash(to_job_v1(GAP, CAPE_BRAND)))
test("key order is irrelevant — the canonical form sorts",
     job_hash(job) == job_hash(json.loads(json.dumps(dict(reversed(list(job.items())))))),
     h)

changed_brand = job_hash(to_job_v1(GAP, {**CAPE_BRAND, "accent": "#123456"}))
test("a changed brand changes the hash", changed_brand != h, f"{h} vs {changed_brand}")

changed_decl = job_hash(to_job_v1({**GAP, "intent": "abstract"}, CAPE_BRAND))
test("a changed declaration changes the hash", changed_decl != h)
changed_aspect = job_hash(to_job_v1({**GAP, "aspect": "4:3"}, CAPE_BRAND))
test("a changed aspect changes the hash", changed_aspect != h)
changed_slot = job_hash(to_job_v1({**GAP, "slot": "hero_art"}, CAPE_BRAND))
test("a different slot is a different job", changed_slot != h)

# Cross-process: a different PYTHONHASHSEED must not move the hash. This is the
# assertion the module's docstring makes; asserting it in-process would prove
# nothing.
child = (
    "import json,sys;"
    "sys.path.insert(0, %r);"
    "from lib.image_jobs import to_job_v1, job_hash;"
    "print(job_hash(to_job_v1(json.loads(sys.argv[1]), json.loads(sys.argv[2]))))"
    % str(Path(__file__).parent)
)
env = dict(os.environ, PYTHONHASHSEED="1")
r1 = subprocess.run([sys.executable, "-c", child, json.dumps(GAP), json.dumps(CAPE_BRAND)],
                    capture_output=True, text=True, env=env)
env2 = dict(os.environ, PYTHONHASHSEED="424242")
r2 = subprocess.run([sys.executable, "-c", child, json.dumps(GAP), json.dumps(CAPE_BRAND)],
                    capture_output=True, text=True, env=env2)
test("the hash survives two processes with different PYTHONHASHSEEDs",
     r1.returncode == 0 and r2.returncode == 0
     and r1.stdout.strip() == r2.stdout.strip() == h,
     f"seed1={r1.stdout.strip()!r} seed2={r2.stdout.strip()!r} local={h!r} "
     f"err={r1.stderr[-200:]}{r2.stderr[-200:]}")

test("canonical json is byte-identical for an equal job",
     canonical_json(job) == canonical_json(to_job_v1(GAP, CAPE_BRAND)))

# ── 5. The cache key must not carry the ASKER's identity ───────────────────
# Measured on the real cape-crypto build: five HERO | centered sections declare
# the SAME `slot=backdrop_url intent=texture aspect=16:9`. The picture they ask
# for is byte-identical. If `section_uid` reaches the hash they are five cache
# entries and five charges for one picture — the exact re-billing this module's
# docstring promises to prevent. The uid stays IN the job (a generated file must
# trace back to the artifact that asked for it); it stays OUT of the digest.
print("\n5. One picture, one charge — the uid traces but does not key")

sibling = to_job_v1({**GAP, "section_uid": "9fab231b0d31"}, CAPE_BRAND)
test("two sections making the same request share one cache key",
     job_hash(sibling) == h, f"{job_hash(sibling)} vs {h}")
test("...while each job still names the section that asked",
     sibling["id"] != job["id"]
     and "9fab231b0d31" in sibling["id"] and GAP["section_uid"] in job["id"],
     f"{sibling['id']} vs {job['id']}")
test("the digest is taken over the picture, not over the id",
     cache_key_json(job) == cache_key_json(sibling)
     and canonical_json(job) != canonical_json(sibling))
test("a different DECLARATION still splits the key, uid held constant",
     job_hash(to_job_v1({**GAP, "aspect": "1:1"}, CAPE_BRAND)) != h)

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed, {SKIP} skipped\n")
sys.exit(1 if FAIL else 0)

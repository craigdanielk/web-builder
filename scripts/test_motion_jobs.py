#!/usr/bin/env python3
"""Motion is the image contract with a `media_type`, and the extension is proved
back-compatible before it is written.

Order matters here and is deliberate. Section 1 is the back-compat corpus: every
`job-v1` job this repo can produce or find on disk, validated against the REAL
schema file in `services/image-pipeline`. It was written and run BEFORE the
schema was touched, so "the v2 schema still accepts v1" is a measured before/after
and not an assertion made once the change was already in.

The rest asserts the extension the motion census
(`docs/census/2026-08-17-motion-engine.md` §5) specifies field by field: a
defaulting `media_type` discriminator, a `motion` object, a `remotion` object,
`job_hash` covering the props so a token change invalidates the render, and the
engine policy (Remotion canonical; generative for atmospheric backdrops only).
"""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

WEB_BUILDER = Path(__file__).resolve().parent.parent

IMAGE_PIPELINE = Path(
    os.environ.get("IMAGE_PIPELINE_ROOT")
    or (Path.home() / "Developer/GitHub/services/image-pipeline")
)
JOB_SCHEMA = IMAGE_PIPELINE / "core" / "job.schema.json"

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


try:
    import jsonschema
except ImportError:
    jsonschema = None

SCHEMA = None
if jsonschema is not None and JOB_SCHEMA.exists():
    SCHEMA = json.loads(JOB_SCHEMA.read_text(encoding="utf-8"))


def valid(job):
    """(ok, message) against the real schema. Never a bare boolean — a
    validation failure has to say which field, or the test is unusable."""
    try:
        jsonschema.validate(job, SCHEMA)
        return True, ""
    except jsonschema.ValidationError as e:
        return False, "%s: %s" % (list(e.absolute_path), e.message)


# ── The v1 corpus ──────────────────────────────────────────────────────────
#
# Two sources, both real:
#
#   * every `image-jobs.json` envelope on disk under `output/` — what a build
#     actually wrote. Measured 2026-08-17: `output/cape-crypto/image-jobs.json`
#     exists and carries 0 jobs (the tracked build's demand rows were 0 after
#     the root-separation fix), so it contributes an envelope but no job. The
#     count is asserted rather than assumed, so a future build's jobs are picked
#     up automatically and a disappearing file is visible.
#   * jobs lowered here by `to_job_v1`, which is the ONLY producer of v1 jobs in
#     this repo. A corpus of zero on-disk jobs would otherwise make section 1 a
#     test that cannot fail.

from lib.image_jobs import to_job_v1  # noqa: E402

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
    "accent": "#004e89",
    "background": "#ffffff",
    "foreground": "#242d35",
    "surface": "#f1f7ff",
    "surface_inverse": "#242d35",
}

ON_DISK = sorted((WEB_BUILDER / "output").glob("*/image-jobs.json"))
on_disk_jobs = []
for path in ON_DISK:
    try:
        env = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        on_disk_jobs.append(("%s (unreadable: %s)" % (path, e), None))
        continue
    for entry in (env.get("jobs") or []) if isinstance(env, dict) else []:
        on_disk_jobs.append((str(path), entry.get("job")))

LOWERED = [
    ("lowered: texture/decorative + reference", to_job_v1(
        GAP, dict(CAPE_BRAND, reference_images=["benchmarks/x.png"]))),
    ("lowered: texture/decorative, no anchor", to_job_v1(GAP, CAPE_BRAND)),
    ("lowered: scene/load-bearing", to_job_v1(
        dict(GAP, intent="scene", role="load-bearing", aspect="4:5"), CAPE_BRAND)),
    ("lowered: abstract/decorative", to_job_v1(
        dict(GAP, intent="abstract"), CAPE_BRAND)),
    ("lowered: diagram/load-bearing", to_job_v1(
        dict(GAP, intent="diagram", role="load-bearing"), CAPE_BRAND)),
    ("lowered: no brand palette", to_job_v1(GAP, {"name": "X"})),
]

print("\n1. BACK-COMPAT: every job-v1 on disk and every job-v1 this repo can "
      "produce validates unchanged")
print("   corpus: %d envelope(s) on disk contributing %d job(s), %d lowered"
      % (len(ON_DISK), len(on_disk_jobs), len(LOWERED)))

if jsonschema is None:
    skip("back-compat validation", "jsonschema not installed")
elif SCHEMA is None:
    test("the schema file exists at %s" % JOB_SCHEMA, False,
         "services/image-pipeline not on this machine — the contract cannot "
         "be checked. Set IMAGE_PIPELINE_ROOT.")
else:
    test("the corpus is not empty — a back-compat test over 0 jobs cannot fail",
         len(on_disk_jobs) + len(LOWERED) > 0)
    for label, job in on_disk_jobs:
        if job is None:
            test("on-disk job is readable: %s" % label, False)
            continue
        ok, why = valid(job)
        test("on-disk v1 job validates: %s / %s" % (label, job.get("id")),
             ok, why)
        test("...and still declares job-v1: %s" % job.get("id"),
             job.get("schema_version") == "job-v1", str(job.get("schema_version")))
    for label, job in LOWERED:
        ok, why = valid(job)
        test("%s validates" % label, ok, why)

    test("to_job_v1 still emits schema_version 'job-v1', unbumped",
         all(j["schema_version"] == "job-v1" for _, j in LOWERED))
    test("to_job_v1 emits NO media_type — absence is what back-compat means",
         all("media_type" not in j for _, j in LOWERED))


# ── 2. The discriminator defaults ──────────────────────────────────────────
print("\n2. media_type DEFAULTS to image — absence is the back-compat mechanism")

from lib.image_jobs import (  # noqa: E402
    media_type_of, is_motion, to_motion_job, to_generative_motion_job,
    lower_motion_demand, job_hash, cache_key_json, canonical_json,
    EnginePolicyViolation, PropsNotMeasured,
    MEDIA_TYPE_IMAGE, MEDIA_TYPE_VIDEO, SCHEMA_VERSION_MOTION,
    ENGINE_REMOTION, ENGINE_GENERATIVE,
)

v1_job = to_job_v1(GAP, CAPE_BRAND)
test("a v1 job with no media_type reads as an image job",
     media_type_of(v1_job) == MEDIA_TYPE_IMAGE, media_type_of(v1_job))
test("...and is not motion", is_motion(v1_job) is False)
test("an explicit media_type: image reads as image",
     media_type_of(dict(v1_job, media_type="image")) == MEDIA_TYPE_IMAGE)
test("an empty dict reads as image, so a partial artefact does not crash a "
     "dispatch table", media_type_of({}) == MEDIA_TYPE_IMAGE)

refused = None
try:
    media_type_of(dict(v1_job, media_type="audio"))
except ValueError as e:
    refused = str(e)
test("an unknown media_type is REFUSED, not defaulted to image",
     refused is not None and "audio" in refused, str(refused))

if SCHEMA is not None:
    ok, why = valid(dict(v1_job, media_type="audio"))
    test("...and the real schema refuses it too", not ok, why)
    ok, why = valid(dict(v1_job, schema_version="job-v2", media_type="image"))
    test("an explicit job-v2 image job validates", ok, why)


# ── 3. A Remotion motion job ───────────────────────────────────────────────
print("\n3. A motion job carries a composition, its props and their provenance")

PROPS = json.loads((WEB_BUILDER / "motion/props/cape-crypto-product-rail.json")
                   .read_text(encoding="utf-8"))

DEMAND = {
    "section_uid": "4f64a50d32d2",
    "archetype": "PRODUCT-RAIL",
    "variant": "cards",
    "slot": "motion_url",
    "composition_id": "CapeCryptoProductRail",
    "entry": "motion/src/index.ts",
    "width": 1280,
    "height": 720,
    "fps": 30,
    "container": "mp4",
    "loop": False,
}

test("the prototype props are on disk (the census names them as the evidence)",
     isinstance(PROPS.get("tokens"), dict) and PROPS["tokens"]
     and isinstance(PROPS.get("items"), list) and PROPS["items"],
     "%d token(s), %d item(s)" % (len(PROPS.get("tokens") or {}),
                                  len(PROPS.get("items") or [])))

mjob = to_motion_job(DEMAND, PROPS)

if SCHEMA is not None:
    ok, why = valid(mjob)
    test("the motion job validates against the real schema", ok, why)

test("it declares job-v2", mjob["schema_version"] == SCHEMA_VERSION_MOTION)
test("it declares media_type video", media_type_of(mjob) == MEDIA_TYPE_VIDEO)
test("...and reads as motion", is_motion(mjob) is True)
test("engine is remotion — canonical for the deterministic class",
     mjob["motion"]["engine"] == ENGINE_REMOTION)
test("duration is DERIVED the way Root.tsx derives it (intro + items*per)",
     mjob["motion"]["duration_frames"]
     == PROPS["introFrames"] + len(PROPS["items"]) * PROPS["framesPerItem"],
     str(mjob["motion"]["duration_frames"]))
test("the id names the section that demanded it, so a render traces back",
     DEMAND["section_uid"] in mjob["id"], mjob["id"])
test("the props carry the compiled token subset",
     mjob["remotion"]["props"]["tokens"]["accent"] == "#004e89")
test("provenance covers every rendered item",
     len(mjob["remotion"]["props_provenance"]) == len(PROPS["items"]))
test("...and every row names a field_key and a permitted source",
     all(r["field_key"] and r["source"] in ("harvested", "phase0")
         for r in mjob["remotion"]["props_provenance"]),
     json.dumps(mjob["remotion"]["props_provenance"][:1]))

# The three refusals. Each is a defaulting branch that does not exist.
for label, mutate, exc in (
    ("props with no tokens", lambda p: {k: v for k, v in p.items() if k != "tokens"},
     PropsNotMeasured),
    ("props with empty tokens", lambda p: dict(p, tokens={}), PropsNotMeasured),
    ("props with no items", lambda p: dict(p, items=[]), PropsNotMeasured),
    ("an item with source 'default'",
     lambda p: dict(p, items=[dict(p["items"][0], source="default")]),
     PropsNotMeasured),
    ("an item with no field_key",
     lambda p: dict(p, items=[{"value": "x", "source": "phase0"}]),
     PropsNotMeasured),
):
    got = None
    try:
        to_motion_job(DEMAND, mutate(PROPS))
    except Exception as e:  # noqa: BLE001 — the type IS the assertion
        got = e
    test("REFUSED rather than defaulted: %s" % label,
         isinstance(got, exc), "%r" % got)

got = None
try:
    to_motion_job(dict(DEMAND, font_files=["https://fonts.example/p.woff2"]), PROPS)
except ValueError as e:
    got = e
test("a font by URL is refused — it breaks portable determinism",
     got is not None, "%r" % got)

got = None
try:
    to_motion_job(dict(DEMAND, container="gif"), PROPS)
except ValueError as e:
    got = e
test("an unknown container is refused", got is not None, "%r" % got)


# ── 4. The hash is the cache key, and the props are inside it ───────────────
print("\n4. job_hash covers the props, so a token change invalidates the render")

h = job_hash(mjob)
test("the hash is 16 hex chars, as for stills",
     re.fullmatch(r"[0-9a-f]{16}", h) is not None, h)

repalette = json.loads(json.dumps(PROPS))
repalette["tokens"]["accent"] = "#ff0000"
test("moving the accent moves the hash — the design system can invalidate a "
     "video", job_hash(to_motion_job(DEMAND, repalette)) != h)

test("a mobile cut is a DIFFERENT hash, same composition",
     job_hash(to_motion_job(dict(DEMAND, width=390, height=844), PROPS)) != h)
test("...because the resolved dimensions are written back into the props",
     to_motion_job(dict(DEMAND, width=390, height=844),
                   PROPS)["remotion"]["props"]["width"] == 390)

sibling = to_motion_job(dict(DEMAND, section_uid="9fab231b0d31"), PROPS)
test("two sections asking for the same render share one cache key",
     job_hash(sibling) == h, "%s vs %s" % (job_hash(sibling), h))
test("...while each job still names the section that asked",
     sibling["id"] != mjob["id"] and "9fab231b0d31" in sibling["id"])
test("the digest is over the render, not over the id",
     cache_key_json(sibling) == cache_key_json(mjob)
     and canonical_json(sibling) != canonical_json(mjob))

# A second interpreter with a different PYTHONHASHSEED. Same reason as the
# stills test: a determinism claim checked inside one process is not checked.
child = (
    "import json,sys;"
    "sys.path.insert(0, %r);"
    "from lib.image_jobs import to_motion_job, job_hash;"
    "print(job_hash(to_motion_job(json.loads(sys.argv[1]), json.loads(sys.argv[2]))))"
    % str(Path(__file__).parent)
)
outs = []
for seed in ("1", "424242"):
    r = subprocess.run([sys.executable, "-c", child, json.dumps(DEMAND),
                        json.dumps(PROPS)], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONHASHSEED=seed))
    outs.append((r.returncode, r.stdout.strip(), r.stderr[-200:]))
test("the motion hash survives two processes with different PYTHONHASHSEEDs",
     all(rc == 0 for rc, _, _ in outs)
     and outs[0][1] == outs[1][1] == h, str(outs))


# ── 5. The cache round-trips a motion job by job_hash ──────────────────────
print("\n5. The cache round-trips a render by job_hash, medium-aware")

from lib.media_cache import (  # noqa: E402
    cache_path, resolve_cached, publish_to_site, CACHE_EXTENSIONS,
    MOTION_EXTENSIONS, MOTION_PUBLIC_PREFIX, PUBLIC_PREFIX,
)

test("motion containers are a SEPARATE tuple from image extensions",
     not set(MOTION_EXTENSIONS) & set(CACHE_EXTENSIONS),
     "%s vs %s" % (MOTION_EXTENSIONS, CACHE_EXTENSIONS))
test("a directory of frames is not cacheable as one file",
     "png-sequence" not in MOTION_EXTENSIONS)

with tempfile.TemporaryDirectory() as tmp:
    cache = Path(tmp) / "generated"
    cache.mkdir()
    test("a miss is None, not an error",
         resolve_cached(cache, h, "video") is None)

    dest = cache_path(cache, h, mjob["motion"]["container"])
    dest.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"0" * 64)
    got = resolve_cached(cache, h, "video")
    test("the render round-trips by job_hash", got == dest, str(got))
    test("...and the filename is the hash and nothing else",
         dest.name == "%s.mp4" % h, dest.name)

    test("an IMAGE lookup does NOT resolve to the mp4 — a wrong-medium hit is "
         "worse than a miss", resolve_cached(cache, h, "image") is None)
    test("the default media_type is image, so every existing caller is "
         "unchanged", resolve_cached(cache, h) is None)

    zero = cache_path(cache, "a" * 16, "mp4")
    zero.write_bytes(b"")
    test("a zero-byte render counts as a miss",
         resolve_cached(cache, "a" * 16, "video") is None)

    bad = None
    try:
        resolve_cached(cache, h, "audio")
    except ValueError as e:
        bad = e
    test("an unknown media_type is refused by the cache too", bad is not None)

    public = Path(tmp) / "site" / "public"
    src, size = publish_to_site(dest, public, MOTION_PUBLIC_PREFIX)
    test("a published render is served from a motion-specific path",
         src == "%s/%s.mp4" % (MOTION_PUBLIC_PREFIX, h), src)
    test("...and the bytes landed", size == dest.stat().st_size)

    img = cache_path(cache, "b" * 16, "png")
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 8)
    isrc, _ = publish_to_site(img, public)
    test("the image prefix is unchanged when no prefix is passed",
         isrc.startswith(PUBLIC_PREFIX), isrc)


# ── 6. Engine policy — generation is atmospheric-backdrop only ─────────────
print("\n6. Engine policy: Remotion canonical, generation atmospheric only")

ATMO = dict(GAP, intent="texture", role="decorative")
gjob = to_generative_motion_job(ATMO, CAPE_BRAND, duration_frames=150,
                                width=1920, height=1080, loop=True)
if SCHEMA is not None:
    ok, why = valid(gjob)
    test("a generative backdrop job validates against the real schema", ok, why)
test("it is job-v2 video with engine generative",
     gjob["schema_version"] == SCHEMA_VERSION_MOTION
     and media_type_of(gjob) == MEDIA_TYPE_VIDEO
     and gjob["motion"]["engine"] == ENGINE_GENERATIVE)
test("it REUSES the image contract — same prompt, negative and engine block",
     gjob["spec"]["prompt_template"] == v1_job["spec"]["prompt_template"]
     and gjob["spec"]["negative"] == v1_job["spec"]["negative"]
     and gjob["engine"] == v1_job["engine"])
test("loop is recorded, because a loop-point pass is still owed",
     gjob["motion"]["loop"] is True)

for label, gap in (
    ("a load-bearing slot", dict(GAP, intent="texture", role="load-bearing")),
    ("intent=scene (a viewer reads it)", dict(GAP, intent="scene", role="decorative")),
    ("intent=diagram", dict(GAP, intent="diagram", role="decorative")),
):
    got = None
    try:
        to_generative_motion_job(gap, CAPE_BRAND, duration_frames=150,
                                 width=1920, height=1080)
    except Exception as e:  # noqa: BLE001
        got = e
    test("generation REFUSED for %s" % label,
         isinstance(got, EnginePolicyViolation), "%r" % got)


# ── 7. Lowering a demand set, with the three recorded outcomes ─────────────
print("\n7. lower_motion_demand records three outcomes, none silent")

low = lower_motion_demand(
    [
        DEMAND,
        dict(DEMAND, section_uid="9fab231b0d31"),          # same render
        dict(DEMAND, width=390, height=844),               # mobile cut
        dict(DEMAND, composition_id="NoSuchComposition"),  # no props
        dict(ATMO, engine=ENGINE_GENERATIVE, duration_frames=150,
             width=1920, height=1080),                     # generative, allowed
        dict(GAP, engine=ENGINE_GENERATIVE, intent="scene", role="load-bearing",
             duration_frames=150, width=1920, height=1080),  # refused
        dict(DEMAND, engine="veo"),                        # unknown engine
    ],
    props_by_composition={"CapeCryptoProductRail": PROPS},
    brand=CAPE_BRAND,
)
test("identical renders collapse to one job with two demands",
     len(low["jobs"][0]["demands"]) == 2,
     str(len(low["jobs"][0]["demands"])))
test("desktop, mobile and the backdrop are three distinct renders",
     len(low["jobs"]) == 3, str(len(low["jobs"])))
test("the policy refusal is RECORDED with a reason",
     len(low["refused"]) == 1 and "atmospheric" in low["refused"][0]["reason"],
     json.dumps(low["refused"]))
test("missing props and an unknown engine are recorded as unlowered",
     len(low["unlowered"]) == 2, json.dumps(low["unlowered"])[:300])
test("an unknown engine names the policy in its reason",
     any("veo" in u["reason"] for u in low["unlowered"]),
     json.dumps(low["unlowered"])[:300])
test("lowering is deterministic — the same set lowers to the same hashes",
     [j["job_hash"] for j in low["jobs"]]
     == [j["job_hash"] for j in lower_motion_demand(
         [DEMAND, dict(DEMAND, width=390, height=844),
          dict(ATMO, engine=ENGINE_GENERATIVE, duration_frames=150,
               width=1920, height=1080)],
         props_by_composition={"CapeCryptoProductRail": PROPS},
         brand=CAPE_BRAND)["jobs"]])
if SCHEMA is not None:
    bad = [j["job"]["id"] for j in low["jobs"] if not valid(j["job"])[0]]
    test("every lowered job validates against the real schema", not bad, str(bad))


# ── 8. The commissioner dispatches by media_type, and the build does not ───
print("\n8. The out-of-band commissioner dispatches motion; the build never does")

COMMISSIONER = WEB_BUILDER / "scripts/quality/commission-media.py"


def code_only(path):
    """The module's EXECUTABLE source — comments and docstrings removed.

    A raw `in` over the file text is not a usable assertion in this repo: the
    modules here carry long docstrings that quote the very anti-patterns they
    forbid, so "the build does not invoke the commissioner" failed on a
    docstring in `orchestrate.py` that says the commissioner is hand-run. The
    prose that explains a rule must not be able to break the test for the rule.
    """
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        body = node.body
        if body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


src_code = code_only(COMMISSIONER)
test("the commissioner reads the discriminator through media_type_of, never a "
     "bare subscript",
     "media_type_of" in src_code
     and re.search(r"""job\[['"]media_type['"]\]""", src_code) is None)
test("it dispatches a remotion job to the contained Remotion project",
     "_run_remotion" in src_code and "'remotion', 'render'" in src_code)
test("generative motion is NOT_MEASURED and says so rather than spending",
     "NOT_MEASURED" in src_code and "hf auth login" in src_code)

orch_code = code_only(WEB_BUILDER / "scripts/orchestrate.py")
test("orchestrate.py does not invoke the commissioner — the build reads the "
     "cache and nothing else",
     "commission-media" not in orch_code)
test("orchestrate.py does not shell out to remotion",
     "remotion" not in orch_code.lower())

# The renderer, exercised end to end against the fake provider: a motion job
# lowers, misses, is "generated", and is then a cache HIT on the second run.
with tempfile.TemporaryDirectory() as tmp:
    cache = Path(tmp) / "generated"
    jobs_file = Path(tmp) / "image-jobs.json"
    jobs_file.write_text(json.dumps({
        "schema": "image-jobs-v2",
        "jobs": [{"job_hash": h, "job": mjob, "demands": [DEMAND]},
                 {"job_hash": job_hash(v1_job), "job": v1_job,
                  "demands": [GAP]}],
    }), encoding="utf-8")

    env = dict(os.environ, MEDIA_COMMISSION_FAKE_PROVIDER="1")
    run = lambda: subprocess.run(  # noqa: E731
        [sys.executable, str(COMMISSIONER), "--jobs", str(jobs_file),
         "--cache", str(cache), "--json"],
        capture_output=True, text=True, env=env, cwd=str(WEB_BUILDER))

    r1 = run()
    s1 = json.loads(r1.stdout.strip().splitlines()[-1]) if r1.returncode in (0, 3) else {}
    test("first pass commissions both media types",
         r1.returncode == 0 and s1.get("generated") == 2,
         "rc=%d %s %s" % (r1.returncode, r1.stdout[-400:], r1.stderr[-400:]))
    test("...and counts them by media_type",
         s1.get("by_media_type") == {"video": 1, "image": 1},
         json.dumps(s1.get("by_media_type")))
    test("the motion render landed in the cache under its hash",
         resolve_cached(cache, h, "video") is not None,
         str(sorted(p.name for p in cache.glob("*"))))

    r2 = run()
    s2 = json.loads(r2.stdout.strip().splitlines()[-1]) if r2.returncode in (0, 3) else {}
    test("second pass is all cache hits — a re-render is never re-billed",
         r2.returncode == 0 and s2.get("cached") == 2 and s2.get("generated") == 0,
         json.dumps(s2))

# The real renderer, with no fake: it must either render or say UNRENDERED with
# a reason and exit 3. It must never report a commission it did not make.
with tempfile.TemporaryDirectory() as tmp:
    cache = Path(tmp) / "generated"
    jobs_file = Path(tmp) / "image-jobs.json"
    broken = to_motion_job(dict(DEMAND, entry="motion/src/does-not-exist.ts"), PROPS)
    jobs_file.write_text(json.dumps({
        "schema": "image-jobs-v2",
        "jobs": [{"job_hash": job_hash(broken), "job": broken,
                  "demands": [DEMAND]}],
    }), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(COMMISSIONER), "--jobs", str(jobs_file),
         "--cache", str(cache), "--json"],
        capture_output=True, text=True, cwd=str(WEB_BUILDER),
        env={k: v for k, v in os.environ.items()
             if k != "MEDIA_COMMISSION_FAKE_PROVIDER"})
    test("an unrenderable motion job exits 3 (NOT_MEASURED), not 0",
         r.returncode == 3, "rc=%d %s" % (r.returncode, r.stdout[-300:]))
    test("...and names the reason rather than reporting a commission",
         "UNRENDERED" in r.stdout and "unrendered\": 1" in r.stdout,
         r.stdout[-300:])
    test("...and wrote nothing to the cache",
         not cache.is_dir() or not list(cache.glob("*")))


print(f"\n  RESULTS: {PASS} passed, {FAIL} failed, {SKIP} skipped\n")
sys.exit(1 if FAIL else 0)

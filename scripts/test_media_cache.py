#!/usr/bin/env python3
"""The build commissions nothing, pays for nothing twice, and paints in the
palette the design compiler actually emitted.

Three defects this file exists to hold shut, each of which has already shipped
once in this repo in some form:

1. **`to_job_v1` had no production caller.** It was invoked only from its own
   test, so `image-jobs.json` carried raw gap rows — untyped, unvalidated,
   unhashed, and unable to reach `services/image-pipeline` at all. A lowering
   nothing calls is a lowering that does not exist.

2. **The brand came from the wrong layer.** The acceptance job R3b wrote asked
   for `#00d18f / #0b0f14` — a dark green ground, which is the *crawled* colour
   of the SOURCE site. The compiled design system for this build is a white
   ground with a `#004e89` accent (`site-spec.json.style`, `design_source:
   "benchmark"`, and it is what `globals.css` emits). Generating against the
   crawl produces art that fights the page it is placed on — the same failure
   shape as the invisible accent, one layer further out. The brand MUST come
   from the compiled style, and an uncompiled style must refuse rather than
   guess.

3. **The build could call a provider inline.** It must not, ever. Generation is
   out of band; the build reads cache and reports a miss as a named empty slot.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.image_jobs import (                                    # noqa: E402
    to_job_v1, job_hash, brand_from_style, lower_gaps, UncompiledStyle,
)

HERE = Path(__file__).parent
WEB_BUILDER = HERE.parent

#: The compiled style, copied verbatim out of the real build artifact
#: `output/cape-crypto/site-spec.json` -> `style`. Copied rather than read so
#: the pin survives the next rebuild: this test asserts what the design
#: compiler emits, and a test that reads its own subject cannot fail.
COMPILED_STYLE = {
    "design_source": "benchmark",
    "benchmark": {"market": "enterprise-stablecoin-payments"},
    "palette": {
        "bg_primary": "#ffffff",
        "bg_secondary": "#f1f7ff",
        "surface": "#f0f3f5",
        "text_primary": "#242d35",
        "text_muted": "#465869",
        "accent": "#004e89",
        "on_accent": "#ffffff",
        "border": "#dee3e8",
        "surface_inverse": "#242d35",
    },
}

#: What the CRAWL of capecrypto.com produced, and what a job must never be
#: generated against. Kept here as a named negative so the assertion below
#: reads as "not this" rather than as an arbitrary hex.
CRAWLED_PALETTE = {"accent": "#00d18f", "bg_primary": "#0b0f14",
                   "text_primary": "#f5f7fa"}

HERO_GAP = {
    "section_uid": "4f64a50d32d2", "archetype": "HERO", "variant": "centered",
    "slot": "backdrop_url", "intent": "texture", "aspect": "16:9",
    "role": "decorative", "reason": "design demand, no source",
}
ABOUT_GAP = {
    "section_uid": "495085a4ec69", "archetype": "ABOUT",
    "variant": "editorial-split", "slot": "image_url", "intent": "scene",
    "aspect": "4:5", "role": "load-bearing", "reason": "design demand, no source",
}

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print("  ✓ %s" % name)
    else:
        FAIL += 1
        print("  ✗ %s" % name)
        if detail:
            print("      %s" % detail)


# ── 1. The brand is the COMPILED design system ─────────────────────────────
print("\n1. The palette a job is generated against is the one the page renders")

brand = brand_from_style(COMPILED_STYLE, name="Cape Crypto")

test("the compiled accent is the job's accent",
     brand["accent"] == "#004e89", str(brand))
test("the ground is the compiled ground, not the crawl's near-black",
     brand["background"] == "#ffffff", str(brand))
test("the crawled palette appears nowhere in the brand",
     not any(v in json.dumps(brand).lower() for v in CRAWLED_PALETTE.values()),
     json.dumps(brand))

job = to_job_v1(HERO_GAP, brand)
test("and it reaches the job the provider is handed",
     "#004e89" in job["output"]["colors"], str(job["output"]["colors"]))
test("the crawled green never reaches a job",
     "#00d18f" not in json.dumps(job).lower())

# The specific regression: the brand dict must not be assembled from
# extraction data. Feeding the crawl in must produce a DIFFERENT hash, so a
# build that regressed to the crawl cannot silently reuse the correct cache
# entry and pass unnoticed.
crawled_brand = brand_from_style(
    {"design_source": "crawl", "palette": CRAWLED_PALETTE}, name="Cape Crypto")
test("a crawl-sourced brand keys a different cache entry (the regression is "
     "visible, not silent)",
     job_hash(to_job_v1(HERO_GAP, crawled_brand)) != job_hash(job))

# ── 2. An unmeasured style refuses; it does not guess ──────────────────────
print("\n2. No design authority means no commission — never a default palette")

for label, style in (("no style at all", {}),
                     ("a style with no design_source", {"palette": {"accent": "#111111"}}),
                     ("design_source present but null", {"design_source": None,
                                                         "palette": {"accent": "#111111"}})):
    try:
        brand_from_style(style, name="X")
        test("%s refuses" % label, False, "returned a brand instead of raising")
    except UncompiledStyle:
        test("%s refuses" % label, True)

try:
    brand_from_style({"design_source": "benchmark", "palette": {}}, name="X")
    test("a compiled style with an empty palette refuses", False)
except UncompiledStyle:
    test("a compiled style with an empty palette refuses", True)

# ── 3. Six demands, two pictures ───────────────────────────────────────────
print("\n3. The same request from five sections is one picture and one charge")

demand = [dict(HERO_GAP, section_uid="uid%d" % i) for i in range(5)] + [ABOUT_GAP]
lowered = lower_gaps(demand, brand)

test("six demand rows collapse to two distinct cache keys",
     len(lowered["jobs"]) == 2,
     "got %d: %s" % (len(lowered["jobs"]),
                     [j["job_hash"] for j in lowered["jobs"]]))
test("every demand row is still accounted for, none dropped",
     sum(len(j["demands"]) for j in lowered["jobs"]) == 6)
test("the five identical HERO asks share one entry",
     max(len(j["demands"]) for j in lowered["jobs"]) == 5)
test("each entry carries a validated job-v1 spec, not a gap row",
     all(j["job"].get("schema_version") == "job-v1" for j in lowered["jobs"]))
test("and the hash is the job's own content hash",
     all(j["job_hash"] == job_hash(j["job"]) for j in lowered["jobs"]))
test("lowering is order-independent — the same set produces the same keys",
     [j["job_hash"] for j in lower_gaps(list(reversed(demand)), brand)["jobs"]]
     != [] and
     sorted(j["job_hash"] for j in lower_gaps(list(reversed(demand)), brand)["jobs"])
     == sorted(j["job_hash"] for j in lowered["jobs"]))

# A gap that must never be generated is REPORTED, not silently dropped.
refused = lower_gaps([dict(HERO_GAP, intent="product")], brand)
test("a claim-bearing gap produces no job and a recorded refusal",
     refused["jobs"] == [] and len(refused["refused"]) == 1
     and "product" in refused["refused"][0]["reason"],
     json.dumps(refused))

# A failed-fetch gap carries no art intent — it is a retryable fetch, not a
# commission. It must be carried through as unlowerable with its reason, never
# quietly turned into a generation.
fetch_gap = {"section_uid": "u", "archetype": "HERO", "variant": "centered",
             "slot": "image", "reason": "no extracted source"}
un = lower_gaps([fetch_gap], brand)
test("a failed fetch is not commissioned — it is reported as unlowerable",
     un["jobs"] == [] and len(un["unlowered"]) == 1, json.dumps(un))

# ── 4. Cache hit is free; cache miss is a named empty slot ─────────────────
print("\n4. A cached hash is never regenerated; a miss never blocks the build")

sys.path.insert(0, str(HERE))
from lib.media_cache import resolve_cached, cache_path      # noqa: E402

import tempfile                                             # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    cache = Path(tmp)
    h = lowered["jobs"][0]["job_hash"]
    test("a miss returns None rather than a placeholder",
         resolve_cached(cache, h) is None)
    p = cache_path(cache, h, "png")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    hit = resolve_cached(cache, h)
    test("a hit returns the cached file, keyed only by the hash",
         hit is not None and hit.name.startswith(h), str(hit))
    test("the cache path is exactly <hash>.<ext>, so two builds agree",
         re.fullmatch(r"[0-9a-f]{16}\.png", p.name) is not None, p.name)

# ── 5. The build itself never calls a provider ─────────────────────────────
print("\n5. Generation is out of band — grep the build path and prove it")

BUILD_PATH = [WEB_BUILDER / "scripts" / "orchestrate.py",
              WEB_BUILDER / "scripts" / "lib" / "image_jobs.py",
              WEB_BUILDER / "scripts" / "lib" / "media_cache.py",
              WEB_BUILDER / "scripts" / "lib" / "asset_resolver.py"]

#: A provider call in the build path, in any of the forms this repo could
#: reach one: the CLI, the pipeline runner, or the MCP tool names.
PROVIDER_CALL = re.compile(
    r'(subprocess\.[a-z_]+\(\s*\[?\s*["\']higgsfield|'
    r'run_job(?:\.py)?["\']|'
    r'generate_image|higgsfield\.generate|api\.higgsfield)')

offenders = []
for f in BUILD_PATH:
    if not f.exists():
        continue
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        code = line.split("#", 1)[0]
        if PROVIDER_CALL.search(code):
            offenders.append("%s:%d: %s" % (f.name, i, line.strip()[:90]))
test("no provider call anywhere in the build path", not offenders,
     "\n      ".join(offenders))

# The commissioner is the ONLY thing allowed to spend, and it must be
# out-of-band: not importable from, or invoked by, orchestrate.py.
# Parsed, not grepped. The build's docstrings NAME the commissioner (they must
# — a reader has to know where generation happens), and a substring search
# cannot tell documentation from a call. The AST can: this walks every import
# and every call target and asserts the commissioner appears in neither.
import ast                                                   # noqa: E402

orch_src = (WEB_BUILDER / "scripts" / "orchestrate.py").read_text(encoding="utf-8")
tree = ast.parse(orch_src)
executable_refs = []
for node in ast.walk(tree):
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        mods = [getattr(node, "module", "") or ""] + [n.name for n in node.names]
        if any("commission" in (m or "") for m in mods):
            executable_refs.append("import at line %d" % node.lineno)
    elif isinstance(node, ast.Call):
        # Any literal argument naming the commissioner — i.e. a subprocess
        # invocation of it — counts as invoking it.
        for arg in ast.walk(node):
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                    and "commission-media" in arg.value:
                executable_refs.append("call at line %d" % node.lineno)
                break
test("orchestrate.py does not import or invoke the commissioner",
     not executable_refs, "; ".join(executable_refs))

commissioner = WEB_BUILDER / "scripts" / "quality" / "commission-media.py"
test("the commissioner exists as a separate, hand-run entry point",
     commissioner.exists(), str(commissioner))

# ── 6. --dry-run estimates and spends nothing ──────────────────────────────
print("\n6. --dry-run costs the set without touching a credit")

if commissioner.exists():
    with tempfile.TemporaryDirectory() as tmp:
        jobs_file = Path(tmp) / "image-jobs.json"
        jobs_file.write_text(json.dumps(lowered), encoding="utf-8")
        env = dict(os.environ, MEDIA_COMMISSION_FAKE_PROVIDER="1")
        r = subprocess.run(
            [sys.executable, str(commissioner), "--jobs", str(jobs_file),
             "--cache", str(Path(tmp) / "cache"), "--dry-run", "--json"],
            capture_output=True, text=True, env=env)
        ok = r.returncode == 0
        payload = {}
        if ok:
            try:
                payload = json.loads(r.stdout.strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError):
                ok = False
        test("--dry-run exits clean and reports a per-job estimate", ok,
             (r.stderr or r.stdout)[-500:])
        test("it reports how many jobs would be generated",
             payload.get("would_generate") == 2, json.dumps(payload)[:300])
        test("and it wrote nothing into the cache",
             not (Path(tmp) / "cache").exists()
             or not list((Path(tmp) / "cache").glob("*")))


# ── 7. A cached hash is never regenerated ──────────────────────────────────
# The property that makes this a cache and not a folder of pictures. Asserted
# by running the commissioner FOR REAL (fake provider) against a pre-populated
# cache and demanding zero provider calls.
print("\n7. A pre-populated cache costs nothing to rebuild against")

if commissioner.exists():
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp) / "cache"
        cache.mkdir()
        for entry in lowered["jobs"]:
            cache_path(cache, entry["job_hash"]).write_bytes(
                b"\x89PNG\r\n\x1a\n" + b"0" * 64)
        jobs_file = Path(tmp) / "image-jobs.json"
        jobs_file.write_text(json.dumps(lowered), encoding="utf-8")
        env = dict(os.environ, MEDIA_COMMISSION_FAKE_PROVIDER="1")
        r = subprocess.run(
            [sys.executable, str(commissioner), "--jobs", str(jobs_file),
             "--cache", str(cache), "--json"],
            capture_output=True, text=True, env=env)
        payload = {}
        try:
            payload = json.loads(r.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            pass
        test("every job is a cache hit and nothing is generated",
             payload.get("cached") == 2 and payload.get("generated") == 0,
             json.dumps(payload)[:300] + (r.stderr or "")[-300:])

    # A hash the file disagrees with must stop the run, not key the cache on a
    # lie — an edited job spec with a stale hash would generate the new picture
    # and file it under the old one's name forever.
    with tempfile.TemporaryDirectory() as tmp:
        bad = json.loads(json.dumps(lowered))
        bad["jobs"][0]["job_hash"] = "0" * 16
        jobs_file = Path(tmp) / "image-jobs.json"
        jobs_file.write_text(json.dumps(bad), encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(commissioner), "--jobs", str(jobs_file),
             "--cache", str(Path(tmp) / "c")],
            capture_output=True, text=True,
            env=dict(os.environ, MEDIA_COMMISSION_FAKE_PROVIDER="1"))
        test("a spec whose recorded hash does not match its content is refused",
             r.returncode != 0 and "hash mismatch" in (r.stdout + r.stderr))

# ── 8. Placement fills the slot that asked, and nothing else ───────────────
print("\n8. A cached picture reaches the component that demanded it")

from lib.media_cache import place_slot                       # noqa: E402

TSX = ('export default function Hero({\n'
       '  headline = "Buy and sell crypto",\n'
       '  backdropUrl = "",\n'
       '  imageAlt = "",\n'
       '}) {\n  return null;\n}\n')

out, placed = place_slot(TSX, "backdrop_url", "/images/generated/abc123.png")
test("the declared slot is filled", placed and
     'backdropUrl = "/images/generated/abc123.png"' in out, out)
test("no other empty prop is touched", out.count('= ""') == 1, out)
test("a slot whose prop is absent reports unplaced rather than corrupting the "
     "component",
     place_slot(TSX, "bg_image_url", "/x.png") == (TSX, False))
test("a repeater slot is never placed by string rewrite",
     place_slot(TSX, "members[].image_url", "/x.png") == (TSX, False))
filled = TSX.replace('backdropUrl = ""', 'backdropUrl = "/images/real.png"')
test("a slot that already carries a source is left alone",
     place_slot(filled, "backdrop_url", "/x.png") == (filled, False))


# ── 9. The prompt has to describe the picture the slot actually needs ──────
# Read before spending, and two things in it were wrong: it opened
# "Non-representational {intent} artwork" — a contradiction for `scene`, which
# is representational by definition — and it closed by asking for "a quiet
# backdrop behind text" for EVERY slot, including the load-bearing ABOUT
# image that is the subject of its own frame. A prompt that asks for the wrong
# picture is not cheaper than no prompt; it costs the same and wastes the
# credit.
print("\n9. Intent and role reach the prompt, not just the metadata")

hero = to_job_v1(HERO_GAP, brand)          # texture / decorative
about = to_job_v1(ABOUT_GAP, brand)        # scene   / load-bearing


def resolved(j):
    """The prompt as the pipeline will resolve it — subject plus the two
    output fields the compiler folds in."""
    fields = dict(j["subject"])
    fields.update({k: j["output"].get(k, "") for k in ("composition", "background")})
    return j["spec"]["prompt_template"].format(**fields)


hero_p, about_p = resolved(hero), resolved(about)

test("a scene is not described as non-representational",
     "non-representational" not in about_p.lower(), about_p)
test("a texture still is",
     "non-representational" in hero_p.lower(), hero_p)
test("the declared 4:5 portrait is not asked for as a 'wide' shot",
     "wide" not in about_p.lower() and about["output"]["aspect_ratio"] == "4:5",
     about_p)
test("a decorative slot is told to recede",
     "recede" in hero_p, hero_p)
test("a load-bearing slot is told to hold attention, not to recede",
     "recede" not in about_p and "hold attention" in about_p, about_p)
test("both still carry the claim boundary in the prompt itself",
     all("no data of any kind" in p for p in (hero_p, about_p)))
test("every placeholder resolves — none survives into the prompt",
     "{" not in hero_p and "{" not in about_p, hero_p + " || " + about_p)

# The colour hint is ORDERED, and the order is what recraft leans on. The first
# HERO backdrop was handed accent-first and came back as saturated navy against
# pure white — a checkerboard at maximum contrast, behind a headline.
test("a decorative slot leads with the ground, not the accent",
     hero["output"]["colors"][0] == brand["background"],
     str(hero["output"]["colors"]))
test("a decorative slot carries no dark role at all",
     brand["foreground"] not in hero["output"]["colors"]
     and brand["surface_inverse"] not in hero["output"]["colors"],
     str(hero["output"]["colors"]))
test("but the accent is still present, so moving it still invalidates the "
     "cached picture",
     brand["accent"] in hero["output"]["colors"]
     and job_hash(to_job_v1(HERO_GAP, dict(brand, accent="#123456")))
     != job_hash(hero))
test("a load-bearing slot gets the full palette, accent first",
     about["output"]["colors"][0] == brand["accent"]
     and brand["foreground"] in about["output"]["colors"],
     str(about["output"]["colors"]))
# The original phrasing — "tiles without a visible seam" — was an instruction
# to draw tiles wearing the costume of an instruction not to. Every mention of
# a pattern word must now be negated, and the phrase that bought the
# checkerboard must be gone outright.
_PATTERN_WORDS = ("tile", "tiles", "grid", "checkerboard", "mosaic", "cells")
test("the phrase that bought a checkerboard is gone",
     "without a visible seam" not in hero_p, hero_p)
test("every pattern word in the texture prompt is negated",
     all(("no " + w) in hero_p.lower()
         for w in _PATTERN_WORDS if w in hero_p.lower()),
     hero_p)


# ── 10. No template renders a local the filler will claim ──────────────────
# The defect this caught, found only when something finally COMPILED the
# output: `HERO/centered.tsx` declared `{backdrop_url}` and rendered a local
# named `backdrop`. `slot_contract._is_slot()` treats a token sharing its first
# underscore-segment with a declared slot as content — deliberately, so
# `{subtotal_value}` fills beside a declared `{subtotal_label}` — so `{backdrop}`
# was filled with the empty string. `<Image src={backdrop} .../>` became
# `<Image src= .../>`: a parse error in all five heroes on this site, and the
# identical latent bug sat in `CTA/dark-band.tsx`.
#
# Every gate the build runs passed while this was true, because none of them
# parses the emitted JSX. This one is cheap and total: a local the filler would
# claim is a defect whether or not the slot happens to be filled today.
print("\n10. A template's own locals are not mistaken for content slots")

sys.path.insert(0, str(WEB_BUILDER / "scripts"))
from lib.slot_contract import (                                # noqa: E402
    declared_slots, strip_comments, _is_slot, NUMBERED_RE)

TEMPLATES = sorted((WEB_BUILDER / "section-templates").rglob("*.tsx"))
_LOCAL_RE = re.compile(r'\b(?:const|let|var)\s+([a-z][A-Za-z0-9_]*)\s*=')
_BRACED_RE = re.compile(r'\{([a-z][a-z_0-9]*)\}')

collisions = []
for tpl in TEMPLATES:
    code = tpl.read_text(encoding="utf-8")
    body = strip_comments(code)
    declared = declared_slots(code)
    locals_here = set(_LOCAL_RE.findall(body))
    for token in set(_BRACED_RE.findall(body)):
        if token not in locals_here:
            continue
        if _is_slot(token, declared, NUMBERED_RE.match(token), not declared):
            collisions.append("%s: local `%s` is filled as a content slot"
                              % (tpl.relative_to(WEB_BUILDER), token))

test("no template renders a local the slot filler would substitute away",
     not collisions,
     "\n      ".join(collisions) or "")
test("the scan actually looked at the library", len(TEMPLATES) >= 14,
     "%d template(s)" % len(TEMPLATES))


# Mutation check. A scan that reports zero on a clean library is
# indistinguishable from a scan that reports zero on everything, so run it
# against the code as it actually shipped and require a hit.
def _scan(code):
    body = strip_comments(code)
    declared = declared_slots(code)
    locals_here = set(_LOCAL_RE.findall(body))
    return [t for t in set(_BRACED_RE.findall(body))
            if t in locals_here
            and _is_slot(t, declared, NUMBERED_RE.match(t), not declared)]


BROKEN = ('// Tokens: {headline} {backdrop_url}\n'
          'export default function H({ backdropUrl = "{backdrop_url}" }) {\n'
          '  const backdrop = backdropUrl ? backdropUrl : null;\n'
          '  return backdrop ? <Image src={backdrop} alt="" /> : null;\n}\n')
FIXED = BROKEN.replace("backdrop ", "backdropSrc ").replace(
    "{backdrop}", "{backdropSrc}").replace("? backdrop", "? backdropSrc")

test("the scan flags the shape that shipped", _scan(BROKEN) == ["backdrop"],
     str(_scan(BROKEN)))
test("...and clears the camelCase fix", _scan(FIXED) == [], str(_scan(FIXED)))

print("\n  RESULTS: %d passed, %d failed\n" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)

#!/usr/bin/env python3
"""The design ASKS for imagery — and refuses to ask for a claim.

`image-jobs.json` was `[]` on every build ever run, while the site carried five
images across twenty-one sections. Not because the wiring was missing: `gaps()`
fired only on `origin == "unresolved"`, a slot the source HAD and we failed to
fetch. A slot the design calls for and the source never had produced silence.

These tests run against the REAL section templates on disk, not only synthetic
fixtures — the declaration is worthless if the files that ship do not carry it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.section_artifact import SectionArtifact
from lib.asset_resolver import (
    art_declarations, art_declaration_errors, art_demand, art_refusals,
    claim_bearing_reason, gaps, stamp_section_uid,
)

TEMPLATES = Path(__file__).resolve().parents[1] / "section-templates"

PASS = 0
FAIL = 0


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


def artifact(tsx, archetype="HERO", variant="centered", provenance=None,
             assets=None, uid="uid1"):
    return SectionArtifact(
        tsx=tsx, archetype=archetype, variant=variant, section_uid=uid,
        intensity="moderate", origin="local_template",
        provenance=list(provenance or []), assets=list(assets or []),
        animation=None,
    )


def template(rel):
    return (TEMPLATES / rel).read_text(encoding="utf-8")


# ── 1. A declared slot with no source becomes a job ────────────────────────
print("\n1. Demand-side jobs")

a = artifact(template("HERO/centered.tsx"), "HERO", "centered")
g = gaps(a)
test("a declared art slot with no source becomes a job, not an empty",
     len(g) == 1, str(g))
test("its reason distinguishes demand from a failed fetch",
     g and g[0]["reason"] == "design demand, no source", str(g))
test("the declared intent rides along to the job",
     g and g[0]["intent"] == "texture", str(g))
test("so does the aspect the template asked for",
     g and g[0]["aspect"] == "16:9", str(g))
test("the job names the section that demanded it",
     g and g[0]["section_uid"] == "uid1", str(g))

# ── 2. A slot the source filled produces no job ────────────────────────────
print("\n2. Sourced slots stay silent")

sourced = artifact(
    template("HERO/centered.tsx"), "HERO", "centered",
    provenance=[{"section_uid": "uid1", "slot": "backdrop_url",
                 "value": "/images/harbour-1a2b3c.webp", "source": "harvested"}],
)
test("a slot the source filled produces no job", art_demand(sourced) == [],
     str(art_demand(sourced)))

empty_row = artifact(
    template("HERO/centered.tsx"), "HERO", "centered",
    provenance=[{"section_uid": "uid1", "slot": "backdrop_url", "value": "",
                 "source": "empty", "reason": "no-harvest-supply"}],
)
test("an EMPTY provenance row is a demand, not a resolution",
     len(art_demand(empty_row)) == 1, str(art_demand(empty_row)))

# A repeater slot is declared `logos[].src` and recorded `logos[1].src`.
repeater_sourced = artifact(
    template("LOGO-BAR/scrolling-marquee.tsx"), "LOGO-BAR", "scrolling-marquee",
    provenance=[{"slot": "logos[1].src", "value": "/images/x.svg", "source": "harvested"}],
)
test("a repeater declaration matches its indexed provenance rows",
     art_demand(repeater_sourced) == [], str(art_demand(repeater_sourced)))

# ── 3. Intent is declared, never inferred from the archetype ───────────────
print("\n3. Intent is declared, not inferred")

intents = {}
for rel in ("HERO/centered.tsx", "HERO/full-bleed-overlay.tsx", "HERO/split-image.tsx"):
    decls = art_declarations(template(rel))
    intents[rel] = [d["intent"] for d in decls]

test("three HERO variants do not share one intent — the archetype cannot imply it",
     len(set(tuple(v) for v in intents.values())) == 3, str(intents))
test("HERO | centered deliberately demands only a texture",
     intents["HERO/centered.tsx"] == ["texture"], str(intents))
test("HERO | split-image demands an abstract, load-bearing image",
     art_declarations(template("HERO/split-image.tsx"))[0]["role"] == "load-bearing")

# Same archetype word, opposite demand: an artifact whose tsx declares nothing
# emits nothing, however HERO-shaped it is.
bare = artifact("export default function X() {\n  return <section />;\n}", "HERO", "invented")
test("an archetype with no declaration demands nothing", art_demand(bare) == [],
     str(art_demand(bare)))

# ── 4. The boundary: no job for a claim-bearing depiction ──────────────────
print("\n4. Claim-bearing depictions are refused in the emitter")

team = artifact(template("TEAM/headshot-grid-square.tsx"), "TEAM",
                "headshot-grid-square")
test("TEAM headshots are never commissioned", art_demand(team) == [],
     str(art_demand(team)))
r = art_refusals(team)
test("and the refusal is RECORDED, not silent", len(r) == 1, str(r))
test("with a reason naming the people rule",
     r and "people" in r[0]["reason"], str(r))
test("a refused slot never reaches gaps()", gaps(team) == [], str(gaps(team)))

logos = artifact(template("LOGO-BAR/scrolling-marquee.tsx"), "LOGO-BAR",
                 "scrolling-marquee")
test("a third party's mark is never commissioned", art_demand(logos) == [])
test("and its refusal is recorded", len(art_refusals(logos)) == 1)

REFUSED = [
    ({"slot": "app_screenshot", "intent": "scene"}, "interface"),
    ({"slot": "dashboard_view", "intent": "abstract"}, "interface"),
    ({"slot": "fsca_certificate", "intent": "diagram"}, "credential"),
    ({"slot": "compliance_seal", "intent": "abstract"}, "credential"),
    ({"slot": "returns_chart", "intent": "diagram"}, "performance"),
    ({"slot": "portfolio_value", "intent": "abstract"}, "performance"),
    ({"slot": "customer_photo", "intent": "scene"}, "people"),
    ({"slot": "founder_portrait", "intent": "scene"}, "people"),
    ({"slot": "hero_art", "intent": "product"}, "product"),
]
for decl, marker in REFUSED:
    reason = claim_bearing_reason(decl)
    test(f"refused: {decl['slot']} / {decl['intent']}",
         reason is not None and marker in reason, str(reason))

ALLOWED = [
    {"slot": "backdrop_url", "intent": "texture"},
    {"slot": "image_url", "intent": "abstract"},
    {"slot": "bg_image_url", "intent": "scene"},
]
for decl in ALLOWED:
    test(f"allowed: {decl['slot']} / {decl['intent']}",
         claim_bearing_reason(decl) is None, str(claim_bearing_reason(decl)))

test("the archetype is evidence for REFUSING even when the slot name is bland",
     claim_bearing_reason({"slot": "member_image", "intent": "scene"}, "TEAM grid")
     is not None)

# ── 5. Malformed declarations are dropped and reported, never guessed ──────
print("\n5. A half-read declaration commissions nothing")

bad = """
// Art: intent=texture aspect=16:9 role=decorative
// Art: slot=x intent=hallucination role=decorative
// Art: slot=y intent=texture
// Art: slot=z intent=texture aspect=1:1 role=decorative
"""
test("only the well-formed declaration survives", len(art_declarations(bad)) == 1,
     str(art_declarations(bad)))
test("the three malformed ones are reported, not silently dropped",
     len(art_declaration_errors(bad)) == 3, str(art_declaration_errors(bad)))
test("`// Art: none` is an explicit absence, not an error",
     art_declarations("// Art: none — the words are the subject") == []
     and art_declaration_errors("// Art: none — the words are the subject") == [])

# ── 6. Both directions still reach gaps() ──────────────────────────────────
print("\n6. Unresolved fetches and design demand are different things")

both = artifact(
    template("ABOUT/editorial-split.tsx"), "ABOUT", "editorial-split",
    assets=[{"slot": "image", "src": "https://x/y.png", "origin": "unresolved",
             "bytes": 0}],
)
reasons = sorted(j["reason"] for j in gaps(both))
test("a failed fetch and a design demand are both emitted, distinctly",
     reasons == ["design demand, no source", "no extracted source"], str(reasons))

# ── 7. Every shipped template carries a declaration ────────────────────────
print("\n7. The corpus")

tsx_files = sorted(TEMPLATES.rglob("*.tsx"))
undeclared = [p.relative_to(TEMPLATES).as_posix() for p in tsx_files
              if "// Art:" not in p.read_text(encoding="utf-8")]
test(f"all {len(tsx_files)} templates carry an `// Art:` line (demand or none)",
     not undeclared, str(undeclared))

errors = {p.relative_to(TEMPLATES).as_posix(): art_declaration_errors(p.read_text(encoding="utf-8"))
          for p in tsx_files}
errors = {k: v for k, v in errors.items() if v}
test("no template's declaration is malformed", not errors, str(errors))

# ── 8. data-section-uid ────────────────────────────────────────────────────
print("\n8. Findings can name the artifact that produced them")

for rel in [p.relative_to(TEMPLATES).as_posix() for p in tsx_files]:
    art = artifact(template(rel), uid="abc123")
    stamp_section_uid(art)
    test(f"{rel} carries data-section-uid on its outer element",
         'data-section-uid="abc123"' in art.tsx,
         art.tsx[art.tsx.find("return"):][:120])

guarded = artifact(
    'export default function X() {\n'
    '  if (!headline) return null;\n'
    '  return (\n    <section className="w-full">hi</section>\n  );\n}',
    uid="g1")
stamp_section_uid(guarded)
test("a `return null;` guard is skipped, not stamped",
     '<section data-section-uid="g1"' in guarded.tsx, guarded.tsx)

stamp_section_uid(guarded)
test("stamping is idempotent", guarded.tsx.count("data-section-uid") == 1,
     guarded.tsx)

nojsx = artifact("const x = 1;\n", uid="n1")
before = nojsx.tsx
stamp_section_uid(nojsx)
test("a file with no default export is left untouched", nojsx.tsx == before)

commented = artifact(
    '// return <section> in the docs\n'
    'export default function X() {\n  return <section>hi</section>;\n}', uid="c1")
stamp_section_uid(commented)
test("a `return <section>` inside a COMMENT is not mistaken for the element",
     commented.tsx.count('data-section-uid="c1"') == 1
     and commented.tsx.startswith("// return <section> in the docs"),
     commented.tsx)


# ── Idempotency ────────────────────────────────────────────────────────────
#
# This is where this codebase has burned itself before. `animation-coverage.
# json` ACCUMULATED and doubled on a repeat run. `stage_resolve_assets`'s own
# comments record why re-resolution corrupts the tally: an "unresolved" slot
# keeps its remote src in the tsx, so a rescan re-matches and re-appends it,
# while a resolved slot's src is now a local path that matches nothing and
# silently drops out of the count.
#
# `art_demand()` is a NEW appender on that same loop, and it runs OUTSIDE the
# `if not a.assets` guard — `gaps()` is called on every artifact on every run.
# A demand emitter that appends on each pass silently inflates a spend
# estimate, which is worse than emitting nothing: an empty list is visibly
# wrong, an inflated one is not.
#
# The loop below is stage_resolve_assets's, reduced to the two calls it makes
# and the guard it makes them behind, so the property is pinned here rather
# than only observed once on a build.
print("\nIdempotency: resolving twice must not move a single byte")

import json as _json  # noqa: E402
import tempfile  # noqa: E402

from lib.asset_resolver import resolve_assets  # noqa: E402

_WITH_ART = (TEMPLATES / "HERO" / "centered.tsx").read_text(encoding="utf-8")
_NO_ART = (TEMPLATES / "FAQ" / "accordion.tsx").read_text(encoding="utf-8")


def _resolve_pass(artifacts, public_dir):
    """One pass of stage_resolve_assets over a set of artifacts."""
    counts = {"total": 0, "extracted": 0, "generated": 0, "unresolved": 0}
    jobs = []
    for a in artifacts:
        if not a.assets:  # the stage's one true "not yet resolved" signal
            resolve_assets(a, {}, public_dir, section_index=a.section_index,
                           download_fn=lambda *_a, **_k: False)
        for asset in a.assets:
            counts["total"] += 1
            counts[asset["origin"]] = counts.get(asset["origin"], 0) + 1
        jobs.extend(gaps(a))
    return _json.dumps(jobs, indent=2), _json.dumps(counts, indent=2)


with tempfile.TemporaryDirectory() as _tmp:
    _public = Path(_tmp)
    _arts = [
        # Two sections making the SAME declaration — the shape that would
        # double first if anything appended per pass.
        artifact(_WITH_ART, "HERO", "centered", uid="idem-a"),
        artifact(_WITH_ART, "HERO", "centered", uid="idem-b"),
        # A section with no art demand at all: `assets` stays empty, so the
        # guard does NOT hold and `resolve_assets` genuinely re-runs on it.
        # That is the path that re-stamps the uid and rescans the tsx.
        artifact(_NO_ART, "FAQ", "accordion", uid="idem-c"),
        # A slot the source had and the fetch failed — the ORIGINAL gap
        # reason, which must not double either.
        artifact(_NO_ART, "FAQ", "accordion", uid="idem-d",
                 assets=[{"slot": "image", "origin": "unresolved", "src": ""}]),
    ]
    _runs = [_resolve_pass(_arts, _public) for _ in range(3)]

    test("image-jobs.json is byte-identical across three resolutions",
         _runs[0][0] == _runs[1][0] == _runs[2][0],
         "run1=%d chars run2=%d chars run3=%d chars"
         % tuple(len(r[0]) for r in _runs))
    test("asset-coverage.json is byte-identical across three resolutions",
         _runs[0][1] == _runs[1][1] == _runs[2][1],
         " | ".join(r[1].replace("\n", " ") for r in _runs))

    _jobs = _json.loads(_runs[2][0])
    test("no job is duplicated by re-running",
         len(_jobs) == len({(j["section_uid"], j["slot"], j["reason"])
                            for j in _jobs}),
         _runs[2][0])
    test("the two same-declaration sections still yield two distinct demands",
         len([j for j in _jobs if j.get("intent")]) == 2,
         _runs[2][0])
    test("a re-resolved artifact carries exactly one uid stamp",
         _arts[2].tsx.count('data-section-uid="idem-c"') == 1,
         str(_arts[2].tsx.count("data-section-uid")))

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)

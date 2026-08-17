#!/usr/bin/env python3
"""Invariants for `lib.route_plan.plan_route` — the transform a developer does in
their head, written down.

The fixtures below are REAL artifacts, not sketches:
  - harvest        output/cape-crypto/site-spec.json           (buildPages output)
  - findings       aurelix-uiux-audit/.../capecrypto-source-20260814-full/
                   audit_result.yaml  (YAML, not JSON — there is no report.json)
  - omissions      output/cape-crypto/omitted-sections.json
                   output/cape-crypto/classification-loss.json
  - declaration    the cape-crypto phase-0 rows, inlined verbatim from
                   docs/census/2026-08-17-phase0-declarations.md §2 and a live
                   load_tenant_context("cape-crypto") on 2026-08-17. Inlined so
                   the suite needs neither Supabase nor the network.
  - design         benchmarks/enterprise-payments-bvnk.json

Run: python3 scripts/test_route_plan.py     (exit 0 = green)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.route_plan import (  # noqa: E402
    ArtIntentUndeclared,
    plan_json,
    plan_route,
)

HERE = Path(__file__).resolve().parent
WEB_BUILDER = HERE.parent
REPO = WEB_BUILDER.parent

SITE_SPEC = WEB_BUILDER / "output" / "cape-crypto" / "site-spec.json"
OMITTED = WEB_BUILDER / "output" / "cape-crypto" / "omitted-sections.json"
LOSS = WEB_BUILDER / "output" / "cape-crypto" / "classification-loss.json"
BENCHMARK = WEB_BUILDER / "benchmarks" / "enterprise-payments-bvnk.json"
AUDIT = (
    REPO
    / "aurelix-uiux-audit"
    / "artifacts"
    / "ui-ux-audit"
    / "standalone"
    / "capecrypto-source-20260814-full"
    / "audit_result.yaml"
)

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print("  ✓ %s" % name)
    else:
        FAIL += 1
        print("  ✗ %s %s" % (name, detail))


# ── The cape-crypto declaration, verbatim (86 fields; the 8 this module reads) ──

CAPE_DECL = {
    "slug": "cape-crypto",
    "load_status": "ok",
    "phase0_field_values": {
        "product_list": [
            "Spot exchange (order book)",
            "Quick Buy / Quick Sell",
            "Bitcoin Lightning send/receive",
            "Cape Crypto Wealth — managed crypto for FSPs and advisors "
            "(DCA, automated buying, portfolio management)",
            "Merchant Services — crypto-as-a-service rails for fintechs and banks",
            "Developer REST API v2 (accounts, funding, trading, market data, "
            "withdrawals, webhooks)",
            "iOS and Android apps",
        ],
        "content_pillars": [
            "South African crypto regulation and exchange-control policy",
            "Bitcoin macro and price context for a ZAR-denominated audience",
            "Stablecoins and cross-border payment rails in Africa",
            "Blockchain applied to South African public-sector and institutional problems",
            "AI x crypto and emerging technology",
        ],
        "licenses": [
            "FSP No. 53746 — authorised Financial Services Provider "
            "(FSCA, South Africa)"
        ],
        "regulatory_body": "Financial Sector Conduct Authority (FSCA), South Africa",
        "revenue_streams": [
            "Order-book trading fees (0.07% taker, maker rebate)",
            "Quick Buy/Sell margin at 0.6%",
            "Withdrawal fees",
            "Wealth platform revenue from FSP/advisor channel",
            "Merchant Services / API infrastructure revenue",
        ],
        "integrations": [
            "Zendesk (support + fee schedule)",
            "Google Sign-In",
            "Apple Sign-In",
            "Google Analytics 4",
            "Cloudflare",
            "SA bank EFT / RTC rails",
            "Bitcoin Lightning Network",
        ],
        "team": "Cape Town, South Africa — Cape Crypto commits publicly to "
                "remaining Cape Town based",
        "description": "Licensed South African cryptocurrency exchange "
                       "(FSP No. 53746) offering ZAR on/off-ramp and spot trading.",
    },
}

EMPTY_DECL = {"slug": "nobody", "load_status": "ok", "phase0_field_values": {}}

# A minimal design that declares art. The ratified bvnk benchmark declares none
# (see the real-artifact section below) — art demand is declaration-driven, so a
# benchmark that declares no art slots must produce no art demand, not a guess.
DESIGN_WITH_ART = {
    "palette_roles": {"accent": "#004e89"},
    "art_slots": {
        "HERO": [{"slot": "hero_art", "intent": "abstract", "aspect": "16:9"}],
        "FEATURES": [{"slot": "feature_art", "intent": "diagram", "aspect": "4:3"}],
    },
}


def harvest_page(route, sections, page_id="p"):
    """A site-spec-shaped single-page harvest."""
    return {
        "pages": [
            {
                "page_id": page_id,
                "route": route,
                "source_url": "https://capecrypto.com" + ("" if route == "/" else route),
                "sections": sections,
            }
        ]
    }


def block(archetype, variant, uid, images=None, **extra):
    b = {
        "index": extra.pop("index", 0),
        "archetype": archetype,
        "variant": variant,
        "section_uid": uid,
        "content": extra.pop("content", {"headings": ["h"], "body_text": [], "ctas": []}),
        "images": images or [],
    }
    b.update(extra)
    return b


def finding(rule_id, page, state="FAIL", evidence=None, layer="L1_strategic_ux"):
    return {
        "rule_id": rule_id,
        "state": state,
        "layer": layer,
        "severity": "medium",
        "issue": "issue text for %s" % rule_id,
        "recommended_fix": "fix",
        "affected_pages": [page],
        "prevalence": 1.0,
        "evidence": evidence if evidence is not None else [{"selector": None}],
    }


NO_OMISSIONS = {}


# ══ 1. Precedence: harvested > phase0 > omitted ══════════════════════════════
print("\n1. Precedence")

_h = harvest_page(
    "/merchants",
    [block("HERO", "centered", "h1"), block("FEATURES", "icon-grid", "f1", index=1)],
)
p = plan_route("/merchants", _h, [], NO_OMISSIONS, CAPE_DECL, {})
feats = [s for s in p["sections"] if s["archetype"] == "FEATURES"]
test("harvested FEATURES is not duplicated by declared products", len(feats) == 1)
test("and it stays harvested-sourced", feats and feats[0]["source"] == "harvested")
test(
    "the un-composed declaration is recorded, not silently dropped",
    any(o.get("field_key") == "product_list" for o in p["omitted"]),
)

_h2 = harvest_page("/merchants", [block("HERO", "centered", "h1")])
p2 = plan_route("/merchants", _h2, [], NO_OMISSIONS, CAPE_DECL, {})
feats2 = [s for s in p2["sections"] if s["archetype"] == "FEATURES"]
test("source silent + declaration covers it -> a phase0 section", len(feats2) == 1)
test("marked source=phase0", feats2 and feats2[0]["source"] == "phase0")
test(
    "content_ref names the declared field, not a guess",
    feats2 and feats2[0]["content_ref"] == "product_list",
)

p3 = plan_route("/merchants", _h2, [], NO_OMISSIONS, EMPTY_DECL, {})
test(
    "neither source nor declaration -> no FEATURES section, never padded",
    not [s for s in p3["sections"] if s["archetype"] == "FEATURES"],
)
test(
    "and the omission carries a reason",
    all(o.get("reason") for o in p3["omitted"]) and p3["omitted"],
)

# ══ 2. Every section carries a reason ════════════════════════════════════════
print("\n2. Explainability")
test(
    "every planned section has a non-empty reason",
    all(s.get("reason") for s in p2["sections"]),
    [s for s in p2["sections"] if not s.get("reason")],
)
test(
    "every section has a section_uid to hang demand off",
    all(s.get("section_uid") for s in p2["sections"]),
)

# ══ 3. Findings: actioned, or unactioned with a reason ═══════════════════════
print("\n3. Findings accounting")

FS = [
    finding("h1_presence", "https://capecrypto.com/merchants"),
    finding("missing_archetype:TRUST-BADGES", "https://capecrypto.com/merchants"),
    finding("missing_archetype:SIGNUP-FORM", "https://capecrypto.com/merchants"),
    finding("page_title_quality", "https://capecrypto.com/merchants", state="PASS"),
    finding("focus_visible_styles", "https://capecrypto.com/merchants",
            state="NOT_MEASURED"),
    finding("h1_presence", "https://capecrypto.com/wealth"),  # off-route
    finding("dna_heading_weight", "https://capecrypto.com",
            evidence=[{"selector": None, "page_url": "https://capecrypto.com"}]),
]
p4 = plan_route("/merchants", _h2, FS, NO_OMISSIONS, CAPE_DECL, {})
acc = {a["finding_id"] for a in p4["actioned"]} | {u["finding_id"] for u in p4["unactioned"]}
test(
    "no finding is silently dropped (off-route ones excluded by route, dna by kind)",
    len(acc) == 6,
    sorted(acc),
)
test("every unactioned entry carries a reason", all(u.get("reason") for u in p4["unactioned"]))
test("every actioned entry names its effect", all(a.get("effect") for a in p4["actioned"]))
test(
    "a page-level finding with no section identity is not guessed at",
    any(
        u["finding_id"].startswith("h1_presence")
        and u["reason"] == "no section identity"
        for u in p4["unactioned"]
    ),
    [u for u in p4["unactioned"]],
)
test(
    "a NOT_MEASURED finding does not read as actioned",
    any("NOT_MEASURED" in u["reason"] for u in p4["unactioned"]),
)
test(
    "dna_* is a site-level aggregate, never routed to a section",
    any(
        u["finding_id"].startswith("dna_")
        and "site-level" in u["reason"]
        for u in p4["unactioned"]
    ),
)
test(
    "an off-route finding is not in this route's plan at all",
    not any(u["finding_id"].startswith("h1_presence@/wealth") for u in p4["unactioned"]),
)

# missing_archetype closes a loop: declared licenses answer the demand.
tb = [s for s in p4["sections"] if s["archetype"] == "TRUST-BADGES"]
test("missing_archetype:TRUST-BADGES + declared licenses -> a section", len(tb) == 1)
test("and it is phase0-sourced", tb and tb[0]["source"] == "phase0")
test(
    "and the finding is actioned, naming the section",
    any(
        a["finding_id"].startswith("missing_archetype:TRUST-BADGES")
        and tb[0]["section_uid"] in a["effect"]
        for a in p4["actioned"]
    ),
    p4["actioned"],
)
test(
    "missing_archetype:SIGNUP-FORM with nothing declared is unactioned, not invented",
    any(
        u["finding_id"].startswith("missing_archetype:SIGNUP-FORM")
        and "declar" in u["reason"]
        for u in p4["unactioned"]
    )
    and not [s for s in p4["sections"] if s["archetype"] == "SIGNUP-FORM"],
)

# ══ 4. Section identity: bind what you can bind ══════════════════════════════
print("\n4. Section binding")

AXE = finding(
    "axe:color-contrast",
    "https://capecrypto.com/merchants",
    layer="L5_accessibility",
    evidence=[{"source": "axe_core", "selector": ".lp-feature:nth-child(1) > .lp-feature__text"}],
)
p5 = plan_route("/merchants", _h2, [AXE], NO_OMISSIONS, CAPE_DECL, {})
test(
    "an axe DOM path with no section to bind to stays unactioned",
    any(u["reason"] == "no section identity" for u in p5["unactioned"]),
)

_h3 = harvest_page(
    "/merchants",
    [
        block("HERO", "centered", "h1"),
        block("FEATURES", "icon-grid", "f9", index=1, root_class="lp-feature"),
    ],
)
p6 = plan_route("/merchants", _h3, [AXE], NO_OMISSIONS, CAPE_DECL, {})
test(
    "a harvested section that declares its root class IS bindable",
    any(a["finding_id"].startswith("axe:color-contrast") for a in p6["actioned"]),
    p6["unactioned"],
)
test(
    "and the binding produces copy demand against that section",
    any(c["section_uid"] == "f9" for c in p6["copy_demand"]),
    p6["copy_demand"],
)

# ══ 5. Omissions and classification loss are demand signals ══════════════════
print("\n5. Omissions / loss")

OMIT = {
    "omitted_sections": {
        "omitted": [
            {
                "archetype": "TRUST-BADGES",
                "variant": "icon-strip",
                "page": "sections/merchants",
                "cause": "no_sourced_content",
                "reason": "template resolved but the harvest filled no slot",
            }
        ]
    },
    "classification_loss": {
        "pages": {
            "merchants": {
                "blocks": [
                    {
                        "section_uid": "h1",
                        "archetype": "HERO",
                        "items_lost": 2,
                        "items_lost_detail": [
                            {"heading": "Get it on Google Play"},
                            {"heading": "Download on the App Store"},
                        ],
                    }
                ]
            }
        }
    },
}
p7 = plan_route("/merchants", _h2, [], OMIT, CAPE_DECL, {}, page_id="merchants")
test(
    "a prior omission for lack of sourced content is a demand the declaration answers",
    any(
        s["archetype"] == "TRUST-BADGES" and s["source"] == "phase0"
        for s in p7["sections"]
    ),
    [(s["archetype"], s["source"]) for s in p7["sections"]],
)
test(
    "content lost by the previous build becomes copy demand, not silence",
    any(
        c["section_uid"] == "h1" and "Google Play" in c["reason"]
        for c in p7["copy_demand"]
    ),
    p7["copy_demand"],
)

# ══ 6. Art demand is declared, never inferred from the archetype ═════════════
print("\n6. Art demand")

p8 = plan_route("/merchants", _h2, [], NO_OMISSIONS, CAPE_DECL, DESIGN_WITH_ART)
hero_art = [a for a in p8["art_demand"] if a["slot"] == "hero_art"]
test("a declared art slot the source cannot fill becomes demand", len(hero_art) == 1)
test("carrying the declared intent", hero_art and hero_art[0]["intent"] == "abstract")
test("carrying the declared aspect", hero_art and hero_art[0]["aspect"] == "16:9")
test("and a reason", hero_art and hero_art[0]["reason"])

_h4 = harvest_page(
    "/merchants",
    [block("HERO", "centered", "h1", images=[{"src": "https://x/y.png", "alt": "a"}])],
)
p9 = plan_route("/merchants", _h4, [], NO_OMISSIONS, EMPTY_DECL, DESIGN_WITH_ART)
test(
    "a slot the source filled produces no job",
    not [a for a in p9["art_demand"] if a["slot"] == "hero_art"],
    p9["art_demand"],
)

p10 = plan_route("/merchants", _h2, [], NO_OMISSIONS, CAPE_DECL, {})
test(
    "a design that declares no art slots produces no art demand (no inference)",
    p10["art_demand"] == [],
    p10["art_demand"],
)

bad_design = {"art_slots": {"HERO": [{"slot": "s", "intent": "staff_photo", "aspect": "1:1"}]}}
raised = False
try:
    plan_route("/merchants", _h2, [], NO_OMISSIONS, CAPE_DECL, bad_design)
except ArtIntentUndeclared:
    raised = True
test("a claim-bearing art intent is refused at the emitter", raised)

# ══ 7. Copy demand for composed sections ═════════════════════════════════════
print("\n7. Copy demand")
test(
    "a phase0 section demands phrasing, and names the field it must trace to",
    any(
        c["section_uid"] == feats2[0]["section_uid"] and c["field_key"] == "product_list"
        for c in p2["copy_demand"]
    ),
    p2["copy_demand"],
)
test("every copy demand carries a reason", all(c.get("reason") for c in p2["copy_demand"]))

# ══ 8. Determinism ═══════════════════════════════════════════════════════════
print("\n8. Determinism")
a = plan_json(plan_route("/merchants", _h, FS, OMIT, CAPE_DECL, DESIGN_WITH_ART))
b = plan_json(plan_route("/merchants", _h, FS, OMIT, CAPE_DECL, DESIGN_WITH_ART))
test("same inputs -> byte-identical JSON", a == b)

env = dict(os.environ)
env["PYTHONHASHSEED"] = "12345"
probe = (
    "import sys,json;sys.path.insert(0,%r);"
    "from lib.route_plan import plan_route, plan_json;"
    "d=json.load(open(%r));"
    "print(plan_json(plan_route('/merchants', d['h'], d['f'], d['o'], d['decl'], d['des'])))"
    % (str(HERE), str(HERE / ".route_plan_probe.json"))
)
(HERE / ".route_plan_probe.json").write_text(
    json.dumps({"h": _h, "f": FS, "o": OMIT, "decl": CAPE_DECL, "des": DESIGN_WITH_ART})
)
try:
    out = subprocess.run(
        [sys.executable, "-c", probe], env=env, capture_output=True, text=True, cwd=str(HERE)
    )
    test(
        "stable under a different PYTHONHASHSEED",
        out.returncode == 0 and out.stdout.strip() == a,
        out.stderr[-400:] or "stdout differs",
    )
finally:
    (HERE / ".route_plan_probe.json").unlink(missing_ok=True)

test("no wall-clock leaks into the plan", "generated_at" not in a and "timestamp" not in a)

# ══ 9. The real artifacts ════════════════════════════════════════════════════
print("\n9. Real cape-crypto artifacts")

missing = [str(p) for p in (SITE_SPEC, OMITTED, LOSS, BENCHMARK, AUDIT) if not p.exists()]
if missing:
    print("  ! skipped — absent fixtures: %s" % missing)
else:
    import yaml  # noqa: E402

    site_spec = json.loads(SITE_SPEC.read_text())
    omissions = {
        "omitted_sections": json.loads(OMITTED.read_text()),
        "classification_loss": json.loads(LOSS.read_text()),
    }
    audit = yaml.safe_load(AUDIT.read_text())
    design = json.loads(BENCHMARK.read_text())
    routes = [pg["route"] for pg in site_spec["pages"]]
    test("all five cape-crypto routes are present in the harvest", len(routes) == 5, routes)

    plans = {
        r: plan_route(r, site_spec, audit, omissions, CAPE_DECL, design) for r in routes
    }
    test(
        "every section of every route carries a reason",
        all(s.get("reason") for p in plans.values() for s in p["sections"]),
    )
    test(
        "phase0 provenance appears — the thing that has never happened in a build",
        any(s["source"] == "phase0" for p in plans.values() for s in p["sections"]),
    )
    test(
        "no route loses sections relative to its harvest",
        all(
            len(plans[pg["route"]]["sections"]) >= len(pg["sections"])
            for pg in site_spec["pages"]
        ),
    )
    test(
        "the three-section routes gain sections",
        all(
            len(plans[r]["sections"]) > 5
            for r in ("/merchants", "/developers")
        ),
        {r: len(plans[r]["sections"]) for r in routes},
    )
    test(
        "every finding on every route is accounted for",
        all(
            len({a["finding_id"] for a in p["actioned"]}
                | {u["finding_id"] for u in p["unactioned"]})
            == len(p["actioned"]) + len(p["unactioned"])
            for p in plans.values()
        ),
    )
    test(
        "the ratified benchmark declares no art slots, so no art is invented",
        all(p["art_demand"] == [] for p in plans.values()),
    )


print("\n%d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)

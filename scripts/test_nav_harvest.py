#!/usr/bin/env python3
"""Nav is sourced or empty. The fallback tables are a regulatory liability.

Fixtures below mirror the REAL site-spec.json shape (verified against
~/Developer/GitHub/tenants/cape-crypto/builds/task4-verify/cape-crypto/site-spec.json),
not the flat "nav_links"/"footer_links" shape originally assumed in the task
brief: nav lives at page["nav"]["links"] with "label"/"href" keys, and
footer links live inside FOOTER-archetype sections' content.items[*].ctas.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.nav_harvest import derive_nav, derive_footer

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


PAGES = [
    {
        "route": "/",
        "title": "Home",
        "nav": {"links": [
            {"label": "Wealth Management", "href": "/wealth"},
            {"label": "Merchant Services", "href": "/merchants"},
            {"label": "Developers", "href": "/developers"},
        ]},
        "sections": [
            {
                "archetype": "FOOTER",
                "content": {"items": [
                    {"heading": "Overview", "ctas": [
                        {"text": "About", "href": "/about"},
                        {"text": "Terms", "href": "/terms"},
                    ]},
                    {"heading": "Product", "ctas": [
                        {"text": "Fees", "href": "/fees"},
                    ]},
                ]},
            },
        ],
    },
    {
        "route": "/about",
        "title": "About",
        "nav": {"links": [
            {"label": "Wealth Management", "href": "/wealth"},
            {"label": "About", "href": "/about"},
        ]},
        "sections": [],
    },
]

FABRICATED = {"Shop", "New Arrivals", "Contact", "Our Story", "What We Do", "Process"}

# ── derive_nav ──────────────────────────────────────────────────────────
nav = derive_nav(PAGES)
nav_labels = [n["label"] for n in nav]

test("real nav labels are used", "Wealth Management" in nav_labels, str(nav_labels))
test("nav labels come from page['nav']['links'], not a top-level 'nav_links' key",
     set(nav_labels) == {"Wealth Management", "Merchant Services", "Developers", "About"},
     str(nav_labels))
test("no fabricated labels survive in nav",
     not (FABRICATED & set(nav_labels)), str(nav_labels))
test("nav links are deduplicated", len(nav_labels) == len(set(nav_labels)), str(nav_labels))
test("nav hrefs pass through unchanged (sourced, not remapped)",
     {n["href"] for n in nav if n["label"] == "Wealth Management"} == {"/wealth"})
test("empty harvest yields empty nav", derive_nav([]) == [])
test("page with no nav key yields empty nav (never a fallback table)",
     derive_nav([{"route": "/", "title": "X", "sections": []}]) == [])

# ── derive_footer ───────────────────────────────────────────────────────
footer = derive_footer(PAGES)
footer_labels = [f["label"] for f in footer]

test("real footer labels come from FOOTER-archetype section ctas",
     set(footer_labels) == {"About", "Terms", "Fees"}, str(footer_labels))
test("no fabricated labels survive in footer",
     not (FABRICATED & set(footer_labels)), str(footer_labels))
test("footer links are deduplicated", len(footer_labels) == len(set(footer_labels)))
test("empty harvest yields empty footer", derive_footer([]) == [])

# When no page carries a FOOTER section, the sourced fallback is the route
# list — not a canned table.
route_only_pages = [
    {"route": "/", "title": "Home", "sections": []},
    {"route": "/about", "title": "About", "sections": []},
]
route_footer = derive_footer(route_only_pages)
test("no FOOTER section falls back to the harvested route list",
     route_footer == [{"label": "About", "href": "/about"}], str(route_footer))
test("route-list fallback excludes the home route",
     all(f["href"] != "/" for f in route_footer), str(route_footer))

# ── Proof against the real build, not just a hand-written fixture ────────
# A test that only exercises a small hand-authored dict can pass while
# missing a real-world key mismatch (the brief's original "nav_links"
# assumption would have passed its own trivial tests while silently
# returning [] against real data). Run derive_nav/derive_footer against the
# actual Cape Crypto site-spec.json when present, and require real content
# to come through non-empty and free of the fabricated strings.
REAL_SPEC = Path(
    os.path.expanduser(
        "~/Developer/GitHub/tenants/cape-crypto/builds/task4-verify/cape-crypto/site-spec.json"
    )
)
if REAL_SPEC.exists():
    real_spec = json.loads(REAL_SPEC.read_text(encoding="utf-8"))
    real_pages = real_spec.get("pages") or []
    real_nav = derive_nav(real_pages)
    real_nav_labels = {n["label"] for n in real_nav}
    real_footer = derive_footer(real_pages)
    real_footer_labels = {f["label"] for f in real_footer}

    test("real Cape Crypto harvest yields non-empty nav", len(real_nav) > 0, str(real_nav_labels))
    test("real Cape Crypto nav carries the actual site nav (Wealth Management)",
         "Wealth Management" in real_nav_labels, str(real_nav_labels))
    test("real Cape Crypto nav carries no fabricated label",
         not (FABRICATED & real_nav_labels), str(real_nav_labels))
    test("real Cape Crypto harvest yields non-empty footer", len(real_footer) > 0, str(real_footer_labels))
    test("real Cape Crypto footer carries no fabricated label",
         not (FABRICATED & real_footer_labels), str(real_footer_labels))
else:
    print(f"  (skipped real-build assertions: {REAL_SPEC} not found on this machine)")

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)

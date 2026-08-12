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

# ── Security: harvested labels/hrefs are untrusted input ─────────────────
# The harvest crawls an arbitrary third-party site. A label with an
# apostrophe is ordinary content (Cape Crypto's own copy has some); a label
# engineered to break out of a quoted JS string literal is code injection;
# an href using the javascript:/data: scheme rendered into a live <Link>
# is exploitable XSS against real site visitors. All three must be handled
# at the lib/nav_harvest.py trust boundary, and the orchestrate.py template
# builders must never quote-wrap raw harvest content into generated source.

APOSTROPHE_PAGES = [
    {"route": "/", "title": "Home", "nav": {"links": [
        {"label": "What's New", "href": "/whats-new"},
    ]}, "sections": []},
]
apostrophe_nav = derive_nav(APOSTROPHE_PAGES)
test("a label with an apostrophe survives derive_nav intact",
     apostrophe_nav == [{"label": "What's New", "href": "/whats-new"}],
     str(apostrophe_nav))

INJECTION_PAGES = [
    {"route": "/", "title": "Home", "nav": {"links": [
        {"label": "', evil()//", "href": "/x"},
    ]}, "sections": []},
]
rejected_injection: list = []
injection_nav = derive_nav(INJECTION_PAGES, rejected=rejected_injection)
test("an injection-shaped label is not silently rewritten (still present as data)",
     injection_nav == [{"label": "', evil()//", "href": "/x"}], str(injection_nav))

JS_UNSAFE_PAGES = [
    {"route": "/", "title": "Home", "nav": {"links": [
        {"label": "JS Attack", "href": "javascript:alert(1)"},
    ]}, "sections": []},
]
rejected_js: list = []
js_nav = derive_nav(JS_UNSAFE_PAGES, rejected=rejected_js)
test("an href of javascript:alert(1) is dropped, not emitted",
     js_nav == [], str(js_nav))
test("the dropped javascript: href is counted as rejected",
     len(rejected_js) == 1 and rejected_js[0]["href"] == "javascript:alert(1)",
     str(rejected_js))

DATA_UNSAFE_PAGES = [
    {"route": "/", "title": "Home", "nav": {"links": [
        {"label": "Data Attack", "href": "data:text/html,<script>alert(1)</script>"},
    ]}, "sections": []},
]
rejected_data: list = []
data_nav = derive_nav(DATA_UNSAFE_PAGES, rejected=rejected_data)
test("a data: href is dropped, not emitted", data_nav == [], str(data_nav))
test("the dropped data: href is counted as rejected", len(rejected_data) == 1, str(rejected_data))

ORDINARY_HREF_PAGES = [
    {"route": "/", "title": "Home", "nav": {"links": [
        {"label": "Relative", "href": "/collections"},
        {"label": "Fragment", "href": "#faq"},
        {"label": "Secure", "href": "https://example.com/x"},
        {"label": "Insecure", "href": "http://example.com/x"},
        {"label": "Mail", "href": "mailto:hello@example.com"},
    ]}, "sections": []},
]
ordinary_nav = derive_nav(ORDINARY_HREF_PAGES)
test("ordinary relative, fragment, https, http, and mailto hrefs all pass through unchanged",
     {n["href"] for n in ordinary_nav} == {
         "/collections", "#faq", "https://example.com/x", "http://example.com/x", "mailto:hello@example.com",
     },
     str(ordinary_nav))

CONTROL_CHAR_PAGES = [
    {"route": "/", "title": "Home", "nav": {"links": [
        {"label": "Bad\x00Label", "href": "/x"},
        {"label": "Newline\nLabel", "href": "/y"},
    ]}, "sections": []},
]
control_nav = derive_nav(CONTROL_CHAR_PAGES)
test("labels containing control characters/newlines are dropped",
     control_nav == [], str(control_nav))

# Footer goes through the same _dedupe boundary — one targeted check that
# it isn't a separate, unguarded code path.
FOOTER_JS_UNSAFE_PAGES = [
    {"route": "/", "title": "Home", "sections": [
        {"archetype": "FOOTER", "content": {"items": [
            {"heading": "Legal", "ctas": [{"text": "Attack", "href": "javascript:alert(1)"}]},
        ]}},
    ]},
]
footer_js = derive_footer(FOOTER_JS_UNSAFE_PAGES)
test("derive_footer also drops javascript: hrefs (same boundary, not a separate gap)",
     footer_js == [], str(footer_js))

# ── Security: the orchestrate.py template builders serialize, not quote-wrap ──
# Prove the fix at the render site, not just at the derivation boundary —
# a correct derive_nav feeding a quote-wrapping template builder would still
# ship a broken/exploitable Navigation.tsx.
sys.path.insert(0, str(Path(__file__).parent))
import orchestrate as _O  # noqa: E402

_apostrophe_component = _O._build_nav_template(
    "test-project", harvested_nav=[{"label": "What's New", "href": "/whats-new"}]
)
test("_build_nav_template renders an apostrophe label as valid JSON-escaped JS, not a broken string",
     "\"What's New\"" in _apostrophe_component or "'What\\'s New'" not in _apostrophe_component,
     "generated component does not contain an unescaped-quote break")
test("_build_nav_template never emits a raw unescaped ' inside the label value for an apostrophe label",
     "label: 'What's New'" not in _apostrophe_component,
     "would indicate quote-wrapping, not json.dumps")

_injection_component = _O._build_nav_template(
    "test-project", harvested_nav=[{"label": "', evil()//", "href": "/x"}]
)
test("_build_nav_template cannot produce executable injected code from a hostile label",
     "evil()" not in _injection_component.replace(json.dumps("', evil()//"), ""),
     "the only occurrence of evil() must be inside a JSON-escaped string literal")
# Concretely: the injected text must appear ONLY as the JSON-escaped form,
# never as a bare `', evil()//` that would close the object literal.
test("the hostile label appears only json.dumps-escaped in the generated component",
     json.dumps("', evil()//") in _injection_component
     and "label: '', evil()//'" not in _injection_component,
     "raw quote-wrapped injection string must not appear")

_footer_apostrophe_component = _O._build_footer_template(
    "test-project", harvested_footer=[{"label": "Kund'innen", "href": "/x"}]
)
test("_build_footer_template also serializes apostrophe labels safely",
     json.dumps("Kund'innen") in _footer_apostrophe_component,
     "footer template must json.dumps labels too")

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)

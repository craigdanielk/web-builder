#!/usr/bin/env python3
"""A nav link to the site you are replacing sends away every visitor you win.

Harvested hrefs are absolute URLs on the SOURCE host. Left alone, every nav
click on the generated site leaks traffic back to the site it replaces — worse,
for anything client-facing, than the fabricated nav that was removed.

The mapping is DERIVED, not invented: the manifest's built routes are already
on disk, so matching a harvested path against them is a join. The rules:

  path matches a built route  -> rewrite to the local route
  no match                    -> leave absolute and COUNT it
  different host              -> leave absolute and COUNT it (never assume a
                                 third-party path maps onto our routes)
  never                       -> fabricate a route absent from the manifest

Query and fragment survive a rewrite; dropping them silently loses meaning the
source page carried.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.nav_harvest import localise_hrefs, source_host_from_pages

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


ROUTES = ["/", "/wealth", "/merchants", "/developers", "/about", "/blog"]
HOST = "capecrypto.com"


def L(label, href):
    return {"label": label, "href": href}


def run(links, routes=ROUTES, host=HOST):
    unmapped = []
    out = localise_hrefs(links, routes, source_host=host, unmapped=unmapped)
    return out, unmapped


# ── the core join ────────────────────────────────────────────────────────
out, un = run([L("Wealth", "https://capecrypto.com/wealth")])
test("absolute source URL matching a built route becomes local",
     out[0]["href"] == "/wealth", str(out))
test("a mapped link is not counted as unmapped", un == [], str(un))

out, _ = run([L("Home", "https://capecrypto.com/")])
test("bare origin maps to /", out[0]["href"] == "/", str(out))

out, _ = run([L("Home", "https://capecrypto.com")])
test("origin with no path maps to /", out[0]["href"] == "/", str(out))

out, _ = run([L("About", "https://capecrypto.com/about/")])
test("trailing slash still matches the built route",
     out[0]["href"] == "/about", str(out))

out, _ = run([L("Wealth", "https://www.capecrypto.com/wealth")])
test("www variant of the source host is the same host",
     out[0]["href"] == "/wealth", str(out))

# ── refusals: counted, never invented ────────────────────────────────────
out, un = run([L("Careers", "https://capecrypto.com/careers")])
test("source path with NO built route stays absolute",
     out[0]["href"] == "https://capecrypto.com/careers", str(out))
test("...and is counted as unmapped", len(un) == 1, str(un))
test("...with a reason naming the missing route",
     un and un[0].get("reason") == "no_matching_route", str(un))

out, un = run([L("Docs", "https://docs.other.com/about")])
test("a DIFFERENT host is never rewritten even when its path matches a route",
     out[0]["href"] == "https://docs.other.com/about", str(out))
test("...and is counted with an external-host reason",
     un and un[0].get("reason") == "external_host", str(un))

# ── things that must pass through untouched ──────────────────────────────
out, un = run([L("Support", "/support"), L("Mail", "mailto:a@b.com"),
               L("Top", "#top"), L("Tel", "tel:+27211234567")])
test("relative hrefs are untouched", out[0]["href"] == "/support", str(out))
test("mailto untouched", out[1]["href"] == "mailto:a@b.com", str(out))
test("fragment untouched", out[2]["href"] == "#top", str(out))
test("tel untouched", out[3]["href"] == "tel:+27211234567", str(out))
test("none of the pass-through forms are counted as unmapped",
     un == [], str(un))

# ── query and fragment survive the rewrite ───────────────────────────────
out, _ = run([L("Blog", "https://capecrypto.com/blog?tag=btc#latest")])
test("query and fragment survive a rewrite",
     out[0]["href"] == "/blog?tag=btc#latest", str(out))

# ── no route may be invented ─────────────────────────────────────────────
out, un = run([L("Ghost", "https://capecrypto.com/wealth/deep/nested")])
test("a deeper path is NOT collapsed onto a shorter built route",
     out[0]["href"] == "https://capecrypto.com/wealth/deep/nested", str(out))
test("...and is counted", len(un) == 1, str(un))

out, un = run([L("Anything", "https://capecrypto.com/wealth")], routes=[])
test("with NO built routes nothing is ever rewritten",
     out[0]["href"] == "https://capecrypto.com/wealth", str(out))
test("...and everything absolute is counted", len(un) == 1, str(un))

# ── labels are carried through unchanged ─────────────────────────────────
out, _ = run([L("What's New", "https://capecrypto.com/blog")])
test("apostrophe label survives localisation untouched",
     out[0]["label"] == "What's New", str(out))

# ── the function must not mutate its input ───────────────────────────────
src = [L("Wealth", "https://capecrypto.com/wealth")]
run(src)
test("input links are not mutated in place",
     src[0]["href"] == "https://capecrypto.com/wealth", str(src))

# ── unknown source host: cannot claim any absolute URL is ours ───────────
out, un = run([L("Wealth", "https://capecrypto.com/wealth")], host=None)
test("with no known source host, absolute URLs are left alone",
     out[0]["href"] == "https://capecrypto.com/wealth", str(out))
test("...and counted rather than silently kept",
     len(un) == 1, str(un))

# ── resolving the source host from the harvest itself ────────────────────
# The regression this guards: `localise_hrefs` was correct and its 25 tests
# passed, yet the built cape-crypto site shipped 8/8 nav links absolute. The
# caller could not ANSWER which host was ours. A captures build's site-spec has
# `source_url: ""` at the top level (build-site-spec.js has no extraction data
# to read it from) and no --from-url, so the host had to come from the pages.
# The page shapes below are copied from output/cape-crypto/site-spec.json.
CAPE_PAGES = [
    {"page_id": "homepage", "route": "/", "source_url": "https://capecrypto.com"},
    {"page_id": "wealth", "route": "/wealth", "source_url": "https://capecrypto.com/wealth"},
    {"page_id": "merchants", "route": "/merchants", "source_url": "https://capecrypto.com/merchants"},
    {"page_id": "developers", "route": "/developers", "source_url": "https://capecrypto.com/developers"},
    {"page_id": "about", "route": "/about", "source_url": "https://capecrypto.com/about"},
]

test("the source host is read off the harvested pages",
     source_host_from_pages(CAPE_PAGES) == "capecrypto.com",
     repr(source_host_from_pages(CAPE_PAGES)))

test("a www page URL resolves to the same bare host",
     source_host_from_pages([{"source_url": "https://www.capecrypto.com/wealth"}])
     == "capecrypto.com")

test("www and bare pages in one bundle are NOT a disagreement",
     source_host_from_pages([{"source_url": "https://www.capecrypto.com"},
                             {"source_url": "https://capecrypto.com/about"}])
     == "capecrypto.com")

test("two genuinely different hosts resolve to None, never a majority pick",
     source_host_from_pages([{"source_url": "https://capecrypto.com"},
                             {"source_url": "https://capecrypto.com/about"},
                             {"source_url": "https://elsewhere.com/x"}]) is None)

test("no pages resolves to None", source_host_from_pages([]) is None)
test("pages with no source_url resolve to None",
     source_host_from_pages([{"page_id": "homepage", "route": "/"}]) is None)
test("an empty-string source_url is not a host",
     source_host_from_pages([{"source_url": ""}]) is None)

# ── the exact failing shapes, end to end ─────────────────────────────────
# Every href below is verbatim from output/cape-crypto/link-mapping.json, where
# all 8 were recorded `unknown_source_host` and left absolute. Note the trailing
# slashes and the three genuinely different capecrypto SUBDOMAINS, which must
# stay external — `support.` is not `capecrypto.com`.
REAL_NAV = [
    L("Wealth Management", "https://capecrypto.com/wealth/"),
    L("Merchant Services", "https://capecrypto.com/merchants/"),
    L("Developers", "https://capecrypto.com/developers/"),
    L("About", "https://capecrypto.com/about/"),
    L("Support", "https://support.capecrypto.com/hc/en-za"),
    L("Fees", "https://support.capecrypto.com/hc/en-za/articles/360015121638-Fee-schedule"),
    L("Sign in", "https://trade.capecrypto.com/signin"),
    L("Sign up", "https://trade.capecrypto.com/signup"),
]
BUILT = ["/", "/wealth", "/merchants", "/developers", "/about"]

_host = source_host_from_pages(CAPE_PAGES)
_un: list = []
_out = localise_hrefs(REAL_NAV, BUILT, source_host=_host, unmapped=_un)
_local = [l["href"] for l in _out if l["href"].startswith("/")]

test("the real 8-link cape-crypto nav yields 4 root-relative hrefs",
     _local == ["/wealth", "/merchants", "/developers", "/about"], str(_local))
test("...and the other 4 stay absolute", len(_un) == 4, str(_un))
test("...counted as external hosts, not as an unknown source host",
     all(u["reason"] == "external_host" for u in _un), str(_un))
test("no emitted nav href points at the source site's own pages",
     not any(h["href"].startswith("https://capecrypto.com/") for h in _out), str(_out))

# The footer's /blog/ link: capecrypto.com, trailing slash, but /blog was NOT
# built in this 5-route build. It must stay absolute and be counted as a missing
# route — not fabricated into a /blog the site does not serve.
_un2: list = []
_out2 = localise_hrefs([L("Blog", "https://capecrypto.com/blog/")], BUILT,
                       source_host=_host, unmapped=_un2)
test("a source path with no built route stays absolute even once the host IS known",
     _out2[0]["href"] == "https://capecrypto.com/blog/", str(_out2))
test("...and is counted as a missing route",
     _un2 and _un2[0]["reason"] == "no_matching_route", str(_un2))

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)

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
from lib.nav_harvest import localise_hrefs

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

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)

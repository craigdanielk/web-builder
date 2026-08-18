#!/usr/bin/env python3
"""
VERIFY GATE D: Post-deploy — store is live and reachable.
- When --url is provided: GET deployed URL, /collections/<handle>, /products/<handle>; assert 200.
- Without --url: nothing was reached: NOT_MEASURED (exit 3), never PASS.
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

WEB_BUILDER_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.capability import describe  # noqa: E402

# Exit codes: 0 PASS - 1 FAIL - 3 NOT_MEASURED. NOT_MEASURED is not PASS.
NOT_MEASURED = 3

# What this gate is, in its own words. Compiled into the capability register by
# `scripts/capability_register.py`; see that file for why it lives here.
CAPABILITY = {
    "id": "aurelix.gate.verify-d",
    "name": "Gate D — the deployed store answers 200",
    "kind": "gate",
    "invocation": "python3 scripts/verify_gate_d.py --url <deployed-url> "
                  "[--collection-handle <h>] [--product-handle <h>]",
    "preconditions": [
        "a deployed, publicly reachable URL, passed as --url or set in GATE_D_URL",
        "outbound network access from this machine",
        "for the default check to be meaningful, a Shopify-shaped store: the collection "
        "handle defaults to `kaffee`, a leftover from one tenant",
    ],
    "inputs": ["--url (or $GATE_D_URL)", "--collection-handle", "--product-handle"],
    "outputs": [],
    "outcome": "whether the deployed site's home, one collection route and optionally one "
               "product route each return HTTP 200",
    "exit_contract": {
        0: "PASS — every requested route returned 200",
        1: "FAIL — at least one route returned something other than 200, or the request errored",
        3: "NOT_MEASURED — no --url and no GATE_D_URL, so no store was ever reached. This "
           "branch used to assert that the web-builder's OWN cart.ts and CartDrawer.tsx "
           "exist on disk and print PASS — file existence standing in for a live store",
    },
    "measures": [
        "the HTTP status of GET <url>/",
        "the HTTP status of GET <url>/collections/<collection-handle>",
        "the HTTP status of GET <url>/products/<product-handle>, only when --product-handle is given",
    ],
    "cannot_see": [
        "a store it never reached — with no --url it measures nothing and returns 3; a chain "
        "that reads 3 as a pass has verified nothing about the deployment",
        "anything below the status line: a 200 that renders an error page, an empty page or "
        "the previous deployment's content passes here. It never reads the body",
        "whether the URL it was handed is the deployment this build produced — it is given a "
        "URL, not a deployment id, so a stale or unrelated site passes",
        "any route beyond the three it constructs; a non-commerce site has no /collections/kaffee "
        "and fails on a hardcoded default rather than on a real defect",
        "client-rendered failures, JS errors, auth walls and redirects — urlopen follows "
        "redirects and reports the final code as if it were the requested route's",
    ],
    "reachable_from": [
        "run_pipeline.py:671 (stage_gate_d — only when a deploy URL was resolved)",
        "scripts/test_gate_outcomes.py:29",
        "standalone CLI",
    ],
    "cost": "seconds; three HTTP GETs at a 15s default timeout. Requires a live deployment",
}


def check_url(url: str, timeout: int = 15) -> tuple[int, str]:
    """Return (status_code, error_message). status_code 200 means OK."""
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Aurelix-GateD/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return (resp.getcode(), "")
    except urllib.error.HTTPError as e:
        return (e.code, f"HTTP {e.code}")
    except urllib.error.URLError as e:
        return (-1, str(e.reason) if getattr(e, "reason", None) else str(e))
    except Exception as e:
        return (-1, str(e))


def main() -> int:
    if describe(CAPABILITY):
        return 0
    parser = argparse.ArgumentParser(description="VERIFY GATE D: post-deploy URL checks or pre-deploy cart check")
    parser.add_argument("--url", type=str, default=os.environ.get("GATE_D_URL"), help="Deployed store URL (e.g. https://example.vercel.app)")
    parser.add_argument("--collection-handle", type=str, default="kaffee", help="Collection handle to check (e.g. /collections/<handle>)")
    parser.add_argument("--product-handle", type=str, default=None, help="Product handle to check (e.g. /products/<handle>). If omitted, only / and collection are checked.")
    parser.add_argument("--timeout", type=int, default=15, help="Request timeout in seconds")
    args = parser.parse_args()

    if args.url:
        base = args.url.rstrip("/")
        routes = [(base + "/", "home")]
        routes.append((base + "/collections/" + args.collection_handle, f"collections/{args.collection_handle}"))
        if args.product_handle:
            routes.append((base + "/products/" + args.product_handle, f"products/{args.product_handle}"))
        errors = []
        for url, label in routes:
            code, err = check_url(url, timeout=args.timeout)
            if code != 200:
                errors.append(f"Gate D failed: {label} returned {code or err}")
        if errors:
            for e in errors:
                print(e, file=sys.stderr)
            return 1
        print("VERIFY GATE D: PASS (deployed URL)")
        for _, label in routes:
            print(f"  200 {label}")
        return 0

    # No URL: the store was never reached, so liveness was not measured. The old
    # behaviour here checked that the web-builder's own cart.ts and
    # CartDrawer.tsx files exist on disk and reported PASS — file existence
    # standing in for "the deployed store is live".
    print(
        "VERIFY GATE D: NOT_MEASURED - no deployed store was reached; "
        "pass --url <deployed> (or set GATE_D_URL)"
    )
    return NOT_MEASURED


if __name__ == "__main__":
    sys.exit(main())

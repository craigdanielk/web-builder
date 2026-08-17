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

# Exit codes: 0 PASS - 1 FAIL - 3 NOT_MEASURED. NOT_MEASURED is not PASS.
NOT_MEASURED = 3


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

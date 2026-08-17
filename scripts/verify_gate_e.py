#!/usr/bin/env python3
"""
VERIFY GATE E: Store ready for handoff — redirects and nav links.
- When --url: fetch home, discover internal links (simple href parse), request sample; fail on 404.
- When --redirect-map: check that legacy URLs redirect to expected target (301/302).
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urljoin, urlparse

WEB_BUILDER_ROOT = Path(__file__).resolve().parent.parent

# Exit codes: 0 PASS - 1 FAIL - 3 NOT_MEASURED. NOT_MEASURED is not PASS.
NOT_MEASURED = 3


def fetch(url: str, timeout: int = 15, follow_redirect: bool = True) -> tuple[int, str, str]:
    """Return (status_code, final_url, body). Follows redirects by default."""
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Aurelix-GateE/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return (resp.getcode(), resp.geturl(), body)
    except urllib.error.HTTPError as e:
        return (e.code, e.geturl(), "")
    except urllib.error.URLError as e:
        return (-1, url, str(e.reason) if getattr(e, "reason", None) else str(e))
    except Exception as e:
        return (-1, url, str(e))


def extract_internal_links(base_url: str, html: str, max_links: int = 20) -> list[str]:
    """Return list of absolute URLs for same-origin links (path only or same host)."""
    base = base_url.rstrip("/") + "/"
    parsed_base = urlparse(base)
    host = parsed_base.netloc
    links: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r'href\s*=\s*["\']([^"\']+)["\']', html, re.I):
        href = m.group(1).strip().split("#")[0].split("?")[0]
        if not href or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        full = urljoin(base, href)
        p = urlparse(full)
        if p.netloc and p.netloc != host:
            continue
        path = p.path.rstrip("/") or "/"
        key = (p.netloc or host, path)
        if key not in seen and len(links) < max_links:
            seen.add(key)
            links.append(full)
    return links


def main() -> int:
    parser = argparse.ArgumentParser(description="VERIFY GATE E: redirects and nav links")
    parser.add_argument("--url", type=str, default=os.environ.get("GATE_E_URL"), help="Deployed store URL")
    parser.add_argument("--redirect-map", type=Path, default=None, help="CSV: from_path,to_path[,status]. Skip if not provided.")
    parser.add_argument("--max-links", type=int, default=15, help="Max internal links to check from home page")
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()

    errors = []
    # Set the moment a real check runs. Without it, "no errors" means only
    # "no checks", and reporting that as PASS is the failure this gate had.
    measured = False

    if args.redirect_map and args.redirect_map.exists():
        base = (args.url or "").rstrip("/")
        if not base:
            errors.append("Gate E: --url required when using --redirect-map")
        else:
            with open(args.redirect_map, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            for row in rows[:20]:
                from_path = (row.get("from_path") or row.get("from") or "").strip().lstrip("/")
                to_path = (row.get("to_path") or row.get("to") or row.get("target") or "").strip()
                if not from_path or not to_path:
                    continue
                url = base + "/" + from_path
                measured = True
                code, final_url, _ = fetch(url, timeout=args.timeout)
                if code not in (200, 301, 302):
                    errors.append(f"Redirect check failed: {from_path} -> {code}")
                elif code in (301, 302) and to_path not in final_url and to_path not in (final_url or ""):
                    errors.append(f"Redirect target mismatch: {from_path} expected {to_path}, got {final_url}")

    if args.url:
        base = args.url.rstrip("/")
        measured = True
        code, final_url, body = fetch(base + "/", timeout=args.timeout)
        if code != 200:
            errors.append(f"Gate E failed: home returned {code}")
        else:
            links = extract_internal_links(base, body, max_links=args.max_links)
            for link in links:
                c, _, _ = fetch(link, timeout=args.timeout)
                if c not in (200, 301, 302):
                    errors.append(f"Broken link: {link} returned {c}")
                if len(errors) >= 5:
                    break

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1

    if not measured:
        # Covers both "no inputs at all" and "--redirect-map given but the file
        # does not exist" — the latter previously fell through and printed PASS.
        if args.redirect_map and not args.redirect_map.exists():
            reason = f"redirect map {args.redirect_map} does not exist and no --url was given"
        else:
            reason = "no deployed store was reached; pass --url <deployed> (or set GATE_E_URL)"
        print(f"VERIFY GATE E: NOT_MEASURED - {reason}")
        return NOT_MEASURED

    print("VERIFY GATE E: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

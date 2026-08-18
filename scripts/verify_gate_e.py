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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.capability import describe  # noqa: E402

# Exit codes: 0 PASS - 1 FAIL - 3 NOT_MEASURED. NOT_MEASURED is not PASS.
NOT_MEASURED = 3

# What this gate is, in its own words. Compiled into the capability register by
# `scripts/capability_register.py`; see that file for why it lives here.
CAPABILITY = {
    "id": "aurelix.gate.verify-e",
    "name": "Gate E — internal links resolve and declared redirects land",
    "kind": "gate",
    "invocation": "python3 scripts/verify_gate_e.py --url <deployed-url> "
                  "[--redirect-map <csv>] [--max-links <n>]",
    "preconditions": [
        "a deployed, publicly reachable URL, passed as --url or set in GATE_E_URL",
        "outbound network access from this machine",
        "for the redirect lane: a CSV with from_path/to_path (or from/to/target) columns, "
        "AND a --url — a redirect map on its own is a FAIL, not a measurement",
    ],
    "inputs": ["--url (or $GATE_E_URL)", "--redirect-map CSV", "--max-links", "--timeout"],
    "outputs": [],
    "outcome": "whether the deployed home page's internal links resolve, and whether each "
               "declared legacy path still redirects to its declared target",
    "exit_contract": {
        0: "PASS — at least one real check ran and every check passed",
        1: "FAIL — a link returned something outside 200/301/302, a redirect target did not "
           "match, or --redirect-map was given without --url",
        3: "NOT_MEASURED — nothing was checked. Covers both 'no inputs at all' and "
           "'--redirect-map points at a file that does not exist'; the latter previously "
           "fell through to PASS on an empty error list",
    },
    "measures": [
        "HTTP status of the home page",
        "HTTP status of up to --max-links (default 15) same-origin hrefs parsed out of the "
        "home page's HTML by regex",
        "for the first 20 rows of a redirect map: the status of <base>/<from_path> and whether "
        "to_path appears as a substring of the final URL",
    ],
    "cannot_see": [
        "anything when it reached nothing — no --url and no existing redirect map means the "
        "`measured` flag stays False and it returns 3. 'No errors' there means 'no checks'",
        "links that are not literal href attributes in the home page's served HTML: "
        "client-rendered nav, JS routing, links on any page other than the home page",
        "more than 20 redirect rows and more than 5 errors — both are hard slices, so a "
        "larger map is partially measured while the verdict reads whole",
        "whether a redirect landed on the RIGHT page: the target test is a substring match "
        "against the final URL, so to_path '/a' matches a redirect to '/another-thing'",
        "a 200 that is really a soft-404 or an error page — it reads status codes, never bodies "
        "(and 301/302 are accepted as healthy for a link)",
        "whether the redirect map it was handed describes this site at all",
    ],
    "reachable_from": [
        "run_pipeline.py:692 (stage_gate_e — passes only --url; the redirect lane is "
        "unreachable from the chain)",
        "scripts/test_gate_outcomes.py:30",
        "standalone CLI",
    ],
    "cost": "seconds to a minute: 1 + up to 15 sequential HTTP GETs at a 15s default timeout, "
            "plus up to 20 redirect probes. Requires a live deployment",
}


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
    if describe(CAPABILITY):
        return 0
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

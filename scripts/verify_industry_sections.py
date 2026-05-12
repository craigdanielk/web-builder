#!/usr/bin/env python3
"""
Verify industry → page section resolution (Supabase RPC + CSV virtual fallback).

Run from repo root or web-builder:
  cd web-builder && python3 scripts/verify_industry_sections.py --industry ecommerce --page-type homepage
  python3 scripts/verify_industry_sections.py --strict --industry artisan-food

Exit 1 if --strict and no sections from any source, or if --require-supabase and RPC returns empty.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# scripts/ -> web-builder root for lib imports
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lib.supabase_client import (  # noqa: E402
    get_industry_metadata,
    get_section_sequence_sources,
    is_supabase_configured,
)
from lib.virtual_db import get_virtual_section_sequence  # noqa: E402


def _resolve_source(rows_rpc: list, rows_virt: list) -> str:
    if rows_rpc:
        return "supabase_rpc(get_page_sections)"
    if rows_virt:
        return "virtual_csv(aurelix_section_preset_database.csv)"
    return "none"


def main() -> int:
    p = argparse.ArgumentParser(description="Verify industry section sequences")
    p.add_argument(
        "--industry",
        action="append",
        dest="industries",
        metavar="HANDLE",
        help="Industry handle (repeatable), e.g. ecommerce, artisan-food",
    )
    p.add_argument("--page-type", default="homepage", help="Page type passed to get_page_sections")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Fail if both Supabase and virtual sources return zero sections",
    )
    p.add_argument(
        "--require-supabase",
        action="store_true",
        help="Fail if Supabase is configured but RPC returns no rows (ignores virtual fallback for pass/fail)",
    )
    p.add_argument("--json", action="store_true", help="Print one JSON object per line")
    args = p.parse_args()

    industries = args.industries or ["ecommerce", "sporting-goods", "artisan-food"]
    sb_ok = is_supabase_configured()
    report = []
    failed = False

    for industry in industries:
        if sb_ok:
            rows_rpc, rows_v = get_section_sequence_sources(industry, args.page_type)
        else:
            rows_rpc, rows_v = [], get_virtual_section_sequence(industry, args.page_type)
        effective = rows_rpc if rows_rpc else rows_v
        src = _resolve_source(rows_rpc, rows_v)
        meta = get_industry_metadata(industry) if sb_ok and get_industry_metadata else {}

        row = {
            "industry": industry,
            "page_type": args.page_type,
            "supabase_configured": sb_ok,
            "rpc_section_count": len(rows_rpc),
            "virtual_section_count": len(rows_v),
            "effective_source": src,
            "effective_count": len(effective),
            "archetypes_rpc": [r.get("archetype") for r in rows_rpc[:12]],
            "archetypes_effective": [r.get("archetype") for r in effective[:12]],
            "industry_metadata_keys": list(meta.keys()) if isinstance(meta, dict) else [],
        }
        report.append(row)

        if args.strict and row["effective_count"] == 0:
            failed = True
        if args.require_supabase and sb_ok and len(rows_rpc) == 0:
            failed = True

        if not args.json:
            print(
                f"{industry}/{args.page_type}: source={src} count={row['effective_count']} "
                f"(rpc={len(rows_rpc)} virtual={len(rows_v)})"
            )

    if args.json:
        print(json.dumps({"items": report, "failed": failed}, indent=2))

    if failed:
        print(
            "FAIL: strict or require-supabase conditions not met. "
            "Check SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY, RPC get_page_sections, and CSV path in lib/virtual_db.py.",
            file=sys.stderr,
        )
        return 1
    if not args.json:
        print("VERIFY industry sections: PASS")
    return 0


if __name__ == "__main__":
    # Load Aurelix_AG root .env if present (parent of web-builder)
    root_env = Path(__file__).resolve().parents[2] / ".env"
    if root_env.exists():
        for line in root_env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v

    sys.exit(main())

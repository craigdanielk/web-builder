#!/usr/bin/env python3
"""Export `section_presets` to a tracked file, and fail when the two diverge.

WHY THIS EXISTS
`section_presets` is the only design-authority store in this system whose
artefact exists *solely* in a database. Measured 2026-08-18:

    live rows                                     995
    in-repo seeder CSV (aurelix_section_preset_database.csv)
                                          842 data rows
    rows whose updated_at != created_at              0

So the nearest thing to a version-controlled copy is 153 rows stale, and no row
has ever been revised since insertion. A store nobody can diff is not a library
entry — you cannot review a change to it, revert one, or prove what it held on
the day a site was built.

This script exports the table and verifies the export against the table. It is
READ-ONLY against Supabase: there is no write, migrate or reseed path here, by
design. Reconciling the stale seeder is an operator decision; *recording* the
divergence is this script's whole job.

FORMAT — CSV, and why
The row is 12 flat scalar columns with no nesting, which is exactly the shape
CSV represents without ceremony. One row per line means a changed preset is a
one-line diff in git rather than a re-indented block; there is no key ordering
to go unstable the way it can in JSON; and the existing seeder already reads a
CSV of this table, so the format is the one the repo already speaks. JSONL
would repeat all 12 keys on all 995 lines for no gain.

WHAT IS EXPORTED, AND WHAT IS NOT
Exported: the nine columns that carry the sequencing decision.
Excluded: `id`, `created_at`, `updated_at`. Those are database bookkeeping, not
library content — and the timestamps in particular would make the file churn on
every reseed while saying nothing about what the store decided. Their loss is
recorded in the meta file so the omission is declared rather than silent.

Rows are sorted by the full natural key, which was measured unique across all
995 rows, so the ordering is total and the file is byte-reproducible.

USAGE
    python3 scripts/export_section_presets.py export
    python3 scripts/export_section_presets.py verify          # offline
    python3 scripts/export_section_presets.py verify --live   # vs Supabase

EXIT CODES (repo convention)
    0  PASS          1  FAIL          3  NOT_MEASURED
`verify --live` returns 3 — never 0 — when Supabase is unconfigured or
unreachable. An unverifiable export is not a verified one.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EXPORT_PATH = ROOT / "supabase" / "exports" / "section_presets.csv"
META_PATH = ROOT / "supabase" / "exports" / "section_presets.meta.json"

TABLE = "section_presets"
SCHEMA = "aurelix.store_export.v1"

# The nine columns carrying the sequencing decision, in export order.
COLUMNS = [
    "industry",
    "page_type",
    "position",
    "component_type",
    "section_archetype",
    "section_variant",
    "priority",
    "content_direction",
    "template_path",
]

# Measured unique over all 995 rows on 2026-08-18, so this is a total order.
# (industry, page_type, position) alone is NOT unique — 945 distinct — which is
# why component_type, archetype and variant are part of the key.
SORT_KEY = [
    "industry",
    "page_type",
    "position",
    "component_type",
    "section_archetype",
    "section_variant",
]

EXCLUDED_COLUMNS = ["id", "created_at", "updated_at"]

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NOT_MEASURED = 3


class NotMeasured(Exception):
    """Supabase could not be reached, so nothing was compared."""


# ─── Supabase (read-only) ─────────────────────────────────────────


def _fetch_live_rows() -> list[dict[str, Any]]:
    """Every row of section_presets, paged. Raises NotMeasured on any failure.

    Deliberately GET-only. Nothing in this module writes to Supabase.
    """
    url_base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url_base or not key:
        raise NotMeasured(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY absent from the "
            "environment — source web-builder/.env"
        )

    import ssl

    ctx = ssl.create_default_context()
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    rows: list[dict[str, Any]] = []
    offset = 0
    page = 1000
    while True:
        url = (
            f"{url_base}/rest/v1/{TABLE}"
            f"?select=*&order=id.asc&offset={offset}&limit={page}"
        )
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=60)
            batch = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
            raise NotMeasured(f"{TABLE} unreachable: {exc}") from exc
        if not isinstance(batch, list):
            raise NotMeasured(f"{TABLE} returned {type(batch).__name__}, not a list")
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return rows


# ─── Rendering ────────────────────────────────────────────────────


def project(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Reduce raw rows to the exported columns, as strings, sorted."""
    out = []
    for r in rows:
        out.append({c: "" if r.get(c) is None else str(r.get(c)) for c in COLUMNS})
    return sort_rows(out)


def sort_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Total order on SORT_KEY. `position` sorts numerically, not as a string,
    so 10 follows 9 rather than 1."""

    def key(r: dict[str, str]):
        return tuple(
            int(r[c]) if c == "position" and str(r[c]).lstrip("-").isdigit() else r[c]
            for c in SORT_KEY
        )

    return sorted(rows, key=key)


def render_csv(rows: list[dict[str, str]]) -> str:
    """Deterministic CSV text: LF line endings, fixed column order, no BOM."""
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_export() -> tuple[list[dict[str, str]], str]:
    """Parsed rows and the raw text of the tracked export."""
    text = EXPORT_PATH.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames != COLUMNS:
        raise ValueError(
            f"export header {reader.fieldnames} != expected {COLUMNS}"
        )
    return [dict(r) for r in reader], text


# ─── Commands ─────────────────────────────────────────────────────


def cmd_export(_args) -> int:
    rows = project(_fetch_live_rows())
    text = render_csv(rows)
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_PATH.write_text(text, encoding="utf-8")

    meta = {
        "schema": SCHEMA,
        "table": TABLE,
        "source": "supabase",
        "row_count": len(rows),
        "columns": COLUMNS,
        "excluded_columns": EXCLUDED_COLUMNS,
        "excluded_reason": (
            "database bookkeeping, not library content; the timestamps would "
            "churn the file on every reseed without recording a decision"
        ),
        "sort_key": SORT_KEY,
        "content_sha256": content_hash(text),
        "verify": "python3 scripts/export_section_presets.py verify --live",
    }
    META_PATH.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(f"exported {len(rows)} rows -> {EXPORT_PATH.relative_to(ROOT)}")
    print(f"sha256 {meta['content_sha256']}")
    return EXIT_OK


def verify_offline() -> tuple[bool, list[str]]:
    """The export is internally consistent with its own meta file.

    Catches a hand-edited CSV, a re-sorted CSV, a dropped row, and a meta file
    that was updated without re-exporting.
    """
    problems: list[str] = []
    if not EXPORT_PATH.exists():
        return False, [f"export missing: {EXPORT_PATH}"]
    if not META_PATH.exists():
        return False, [f"meta missing: {META_PATH}"]

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    try:
        rows, text = read_export()
    except ValueError as exc:
        return False, [str(exc)]

    if len(rows) != meta.get("row_count"):
        problems.append(
            f"row count: export has {len(rows)}, meta says {meta.get('row_count')}"
        )
    actual = content_hash(text)
    if actual != meta.get("content_sha256"):
        problems.append(
            f"content hash: export is {actual}, meta says {meta.get('content_sha256')}"
        )
    if meta.get("columns") != COLUMNS:
        problems.append(f"meta columns {meta.get('columns')} != code columns {COLUMNS}")
    if rows != sort_rows(list(rows)):
        problems.append(f"export is not sorted by {SORT_KEY}")

    keys = [tuple(r[c] for c in SORT_KEY) for r in rows]
    if len(set(keys)) != len(keys):
        problems.append(
            f"sort key is not unique over the export "
            f"({len(keys) - len(set(keys))} duplicate rows)"
        )
    return not problems, problems


def verify_live() -> tuple[bool, list[str]]:
    """The export still equals the table. Raises NotMeasured if it cannot look."""
    live = project(_fetch_live_rows())
    live_text = render_csv(live)
    rows, text = read_export()

    problems: list[str] = []
    if len(live) != len(rows):
        problems.append(
            f"row count diverged: live {len(live)}, export {len(rows)} "
            f"(delta {len(live) - len(rows):+d})"
        )
    if content_hash(live_text) != content_hash(text):
        problems.append(
            f"content diverged: live sha256 {content_hash(live_text)}, "
            f"export sha256 {content_hash(text)}"
        )
        live_keys = {tuple(r[c] for c in SORT_KEY) for r in live}
        export_keys = {tuple(r[c] for c in SORT_KEY) for r in rows}
        only_live = sorted(live_keys - export_keys)
        only_export = sorted(export_keys - live_keys)
        for k in only_live[:10]:
            problems.append(f"  in table, not in export: {k}")
        for k in only_export[:10]:
            problems.append(f"  in export, not in table: {k}")
    return not problems, problems


def cmd_verify(args) -> int:
    ok, problems = verify_offline()
    if not ok:
        print(f"VERIFY {TABLE} export: FAIL")
        for p in problems:
            print(f"  {p}")
        return EXIT_FAILED
    print(f"VERIFY {TABLE} export (offline): PASS — self-consistent")

    if not args.live:
        # Not a pass for the live table: we did not look at it.
        print(f"VERIFY {TABLE} vs table: NOT_MEASURED (pass --live to compare)")
        return EXIT_OK

    try:
        ok, problems = verify_live()
    except NotMeasured as exc:
        print(f"VERIFY {TABLE} vs table: NOT_MEASURED — {exc}")
        return EXIT_NOT_MEASURED
    if not ok:
        print(f"VERIFY {TABLE} vs table: FAIL")
        for p in problems:
            print(f"  {p}")
        print("  re-run `export` if the table is right, or revert the table")
        return EXIT_FAILED
    print(f"VERIFY {TABLE} vs table: PASS — export equals the live table")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("export", help="fetch the live table and write the export")
    v = sub.add_parser("verify", help="check the export against itself and the table")
    v.add_argument(
        "--live",
        action="store_true",
        help="also compare against Supabase (NOT_MEASURED if unreachable)",
    )
    args = parser.parse_args(argv)
    return {"export": cmd_export, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())

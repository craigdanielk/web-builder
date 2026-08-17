#!/usr/bin/env python3
"""Regenerate section-templates/manifest.json from disk + Supabase.

The manifest had been hand-maintained and drifted: generated 2026-02-13, it
claimed 26 archetypes / 76 variants / 13 templates while
`section_archetypes` holds 74 rows and 14 local .tsx files exist on disk.
`validate_integration.py:248` meanwhile asserts 25 archetypes / 72 variants,
so all three numbers disagreed with each other.

Two sources, and the distinction is the point:
  - a local `section-templates/<ARCHETYPE>/<variant>.tsx` is resolved FIRST
    by check_template_exists() (supabase_client.py:182)
  - a Supabase `section_archetypes` row with has_template=true is the
    fallback

`resolution` records which one a variant actually gets, so the manifest
answers "where does this template come from" rather than only "does one
exist".

Requires the Supabase env: `cd web-builder && set -a && . ./.env && set +a`.
There is no root .env; sourcing one fails silently and points SUPABASE_URL
at a project where section_archetypes is empty.

Run from web-builder/:
    python3 scripts/build_section_template_manifest.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.supabase_client import _get  # noqa: E402

WEB_BUILDER = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = WEB_BUILDER / "section-templates"
MANIFEST = TEMPLATES_DIR / "manifest.json"


def local_templates() -> dict[str, dict[str, Path]]:
    """{ARCHETYPE: {variant: path}} for every .tsx on disk."""
    found: dict[str, dict[str, Path]] = {}
    for path in sorted(TEMPLATES_DIR.rglob("*.tsx")):
        archetype = path.parent.name
        found.setdefault(archetype, {})[path.stem] = path
    return found


def db_variants() -> list[dict]:
    rows = _get("section_archetypes", "select=archetype,variant,has_template&limit=1000")
    if not rows:
        raise SystemExit(
            "section_archetypes returned 0 rows — SUPABASE_URL is almost certainly "
            "pointing at the wrong project. Run: cd web-builder && set -a && . ./.env && set +a"
        )
    return rows


def main() -> int:
    on_disk = local_templates()
    rows = db_variants()

    archetypes: dict[str, dict] = {}
    for row in rows:
        archetypes.setdefault(row["archetype"], {"variants": {}})
        archetypes[row["archetype"]]["variants"][row["variant"]] = bool(row.get("has_template"))

    # A local file for a variant the DB does not know about is still a real
    # template the resolver will use — record it rather than drop it.
    for archetype, variants in on_disk.items():
        archetypes.setdefault(archetype, {"variants": {}})
        for variant in variants:
            archetypes[archetype]["variants"].setdefault(variant, False)

    out_archetypes: dict[str, dict] = {}
    counts = {"local": 0, "db": 0, "none": 0}
    for archetype in sorted(archetypes):
        entries = []
        for variant in sorted(archetypes[archetype]["variants"]):
            has_db = archetypes[archetype]["variants"][variant]
            local_path = on_disk.get(archetype, {}).get(variant)
            if local_path is not None:
                resolution = "local"
                template_path = str(local_path.relative_to(WEB_BUILDER))
            elif has_db:
                resolution = "db"
                template_path = "db:section_archetypes.code_template"
            else:
                resolution = "none"
                template_path = None
            counts[resolution] += 1
            entries.append({
                "name": variant,
                "resolution": resolution,
                "has_template": resolution != "none",
                "template_path": template_path,
                "db_has_template": has_db,
                "local_file": local_path.name if local_path else None,
            })
        out_archetypes[archetype] = {
            "directory": f"section-templates/{archetype}/",
            "variants": entries,
        }

    manifest = {
        "version": "2.0.0",
        "generated": date.today().isoformat(),
        "generated_by": "scripts/build_section_template_manifest.py",
        "sources": {
            "local": "section-templates/<ARCHETYPE>/<variant>.tsx (resolved first)",
            "db": "Supabase section_archetypes.code_template where has_template = true",
        },
        "total_archetypes": len(out_archetypes),
        "total_variants": sum(counts.values()),
        "templates_available": counts["local"] + counts["db"],
        "templates_local": counts["local"],
        "templates_db_only": counts["db"],
        "variants_without_template": counts["none"],
        "archetypes": out_archetypes,
    }

    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST.relative_to(WEB_BUILDER)}")
    print(f"  archetypes {manifest['total_archetypes']}  variants {manifest['total_variants']}")
    print(f"  local {counts['local']}  db-only {counts['db']}  no template {counts['none']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

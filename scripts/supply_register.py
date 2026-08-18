#!/usr/bin/env python3
"""Record demand the template library cannot supply, instead of gap-filling it.

WHY THIS EXISTS
`omitted-sections.json` already records the sections a *build* could not emit.
Nothing records the sections the *library* cannot emit for anybody. Measured
2026-08-18:

    distinct (archetype, variant) demanded by section_presets   99
    distinct (archetype, variant) supplied                      76
    demanded but not supplied                                   27
    supplied but never demanded                                  2

27% of the registry's demand has no template row of any kind behind it. Today
that shortfall is invisible until a build trips over one pair at a time, and
the pressure at that moment is to invent something — which is exactly the
failure this repo keeps closing. Demand without supply is counted here, named,
and attributed to the pages that asked for it.

SOURCES — both version-controlled, so the register is re-derivable offline

    demand   supabase/exports/section_presets.csv       (the tracked export)
    supply   section-templates/manifest.json            (local .tsx ∪ DB rows)

Measured: taking supply from the manifest and from a live read of
`section_archetypes` produce the *identical* 27, so the offline path costs no
accuracy. The manifest is the better source anyway — it is the union a build
can actually resolve from, and it is in git. The two pairs the manifest adds
over the database (`CURRENCY-MAP/interactive`, `TRUST-BADGES/icon-strip`) are
not demanded by any preset, so they cannot change the missing set.

CAUSE VOCABULARY — shared with omitted-sections.json, deliberately

    archetype_absent        no entry for this archetype at all
    variant_not_in_library  the archetype exists; this variant does not

The second is the same string `omitted-sections.json` already uses, so the two
registers read as one vocabulary rather than two dialects.

USAGE
    python3 scripts/supply_register.py                       # to stdout
    python3 scripts/supply_register.py -o supply-register.json
    python3 scripts/supply_register.py --build-dir output/<project> -o …

`--build-dir` is read-only. It annotates which missing pairs a given build
actually demanded, and adds a `build` block naming the routes that asked.

EXIT CODES
    0  register written          1  a source was missing or malformed
Emitting a register is not a verdict — a non-empty register is the honest
state of the library, not a build failure.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEMAND_PATH = ROOT / "supabase" / "exports" / "section_presets.csv"
SUPPLY_PATH = ROOT / "section-templates" / "manifest.json"

SCHEMA = "aurelix.supply_register.v1"

CAUSE_ARCHETYPE_ABSENT = "archetype_absent"
CAUSE_VARIANT_MISSING = "variant_not_in_library"


class SourceMissing(Exception):
    """A register cannot be derived, so none is emitted. Never an empty one —
    an empty register reads as 'the library is complete'."""


# ─── Sources ──────────────────────────────────────────────────────


def load_demand(path: Path = DEMAND_PATH) -> list[dict[str, str]]:
    """Every (industry, page_type, position) demand row, from the tracked export."""
    if not path.exists():
        raise SourceMissing(
            f"demand source missing: {path}. Run "
            "`python3 scripts/export_section_presets.py export` first."
        )
    with path.open(encoding="utf-8", newline="") as fh:
        rows = [dict(r) for r in csv.DictReader(fh)]
    if not rows:
        raise SourceMissing(f"demand source empty: {path}")
    required = {"industry", "page_type", "position", "section_archetype",
                "section_variant", "priority"}
    missing_cols = required - set(rows[0])
    if missing_cols:
        raise SourceMissing(f"demand source lacks columns {sorted(missing_cols)}")
    return rows


def load_supply(path: Path = SUPPLY_PATH) -> dict[str, set[str]]:
    """archetype -> set of supplied variants, from the tracked manifest."""
    if not path.exists():
        raise SourceMissing(f"supply source missing: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    archetypes = manifest.get("archetypes")
    if not isinstance(archetypes, dict) or not archetypes:
        raise SourceMissing(f"supply source has no archetypes: {path}")
    out: dict[str, set[str]] = {}
    for name, entry in archetypes.items():
        out[name] = {v["name"] for v in entry.get("variants", []) if v.get("name")}
    return out


# ─── The register ─────────────────────────────────────────────────


def build_register(
    demand_rows: list[dict[str, str]],
    supply: dict[str, set[str]],
    build_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    supplied_pairs = {(a, v) for a, vs in supply.items() for v in vs}

    # Every demand row, grouped by the pair it asks for.
    by_pair: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for r in demand_rows:
        by_pair[(r["section_archetype"], r["section_variant"])].append(r)

    demanded_pairs = set(by_pair)
    missing_pairs = sorted(demanded_pairs - supplied_pairs)

    records = []
    for archetype, variant in missing_pairs:
        rows = by_pair[(archetype, variant)]
        available = sorted(supply.get(archetype, ()))
        cause = CAUSE_VARIANT_MISSING if archetype in supply else CAUSE_ARCHETYPE_ABSENT
        demanded_by = sorted(
            {(r["industry"], r["page_type"]) for r in rows}
        )
        records.append({
            "archetype": archetype,
            "variant": variant,
            "cause": cause,
            "reason": (
                "no template of any variant for this archetype; demand is unsourceable"
                if cause == CAUSE_ARCHETYPE_ABSENT
                else "archetype present in the library but not this variant"
            ),
            "variant_requested": variant,
            "variants_available": available,
            "demand_rows": len(rows),
            "page_types": sorted({r["page_type"] for r in rows}),
            "industries": sorted({r["industry"] for r in rows}),
            "priorities": sorted({r["priority"] for r in rows}),
            "demanded_by": [{"industry": i, "page_type": p} for i, p in demanded_by],
        })

    by_cause: dict[str, int] = defaultdict(int)
    for rec in records:
        by_cause[rec["cause"]] += 1

    unsatisfiable_rows = sum(rec["demand_rows"] for rec in records)

    register: dict[str, Any] = {
        "schema": SCHEMA,
        "sources": {
            "demand": str(DEMAND_PATH.relative_to(ROOT)),
            "supply": str(SUPPLY_PATH.relative_to(ROOT)),
        },
        "summary": {
            "demanded_pairs": len(demanded_pairs),
            "supplied_pairs": len(supplied_pairs),
            "missing": len(records),
            "by_cause": dict(sorted(by_cause.items())),
            "archetypes_absent": sorted(
                {r["archetype"] for r in records if r["cause"] == CAUSE_ARCHETYPE_ABSENT}
            ),
            "supplied_never_demanded": sorted(
                f"{a}/{v}" for a, v in (supplied_pairs - demanded_pairs)
            ),
            "demand_rows_total": len(demand_rows),
            "demand_rows_unsatisfiable": unsatisfiable_rows,
        },
        "missing": records,
    }

    if build_manifest is not None:
        register["build"] = _build_block(build_manifest, supplied_pairs, records)

    assert_balanced(register)
    return register


def _build_block(
    manifest: dict[str, Any],
    supplied_pairs: set[tuple[str, str]],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """What one build actually demanded, and which of its asks had no supply."""
    routes: dict[tuple[str, str], list[str]] = defaultdict(list)
    for page in manifest.get("pages", []):
        label = page.get("route") or page.get("id") or "?"
        for sec in page.get("sections", []):
            routes[(sec.get("archetype", ""), sec.get("variant", ""))].append(label)

    unsupplied = sorted(set(routes) - supplied_pairs)
    missing_index = {(r["archetype"], r["variant"]): r for r in records}

    # Annotate the registry-wide records this build actually tripped over.
    for pair in unsupplied:
        rec = missing_index.get(pair)
        if rec is not None:
            rec["demanded_by_build_routes"] = sorted(set(routes[pair]))

    return {
        "project": manifest.get("project"),
        "industry": manifest.get("industry"),
        "pages": len(manifest.get("pages", [])),
        "pairs_demanded": len(routes),
        "pairs_unsupplied": len(unsupplied),
        "unsupplied": [
            {
                "archetype": a,
                "variant": v,
                "routes": sorted(set(routes[(a, v)])),
                "in_registry_demand": (a, v) in missing_index,
            }
            for a, v in unsupplied
        ],
    }


def assert_balanced(register: dict[str, Any]) -> None:
    """The summary must agree with its own records.

    This is the guard against the failure the register exists to prevent: a
    pair quietly dropped from `missing` while the headline count still reads
    like the library is 27 short. Counts that do not balance are a broken
    register, not a smaller problem.
    """
    s = register["summary"]
    records = register["missing"]

    if s["missing"] != len(records):
        raise AssertionError(
            f"summary.missing {s['missing']} != {len(records)} records"
        )
    cause_total = sum(s["by_cause"].values())
    if cause_total != s["missing"]:
        raise AssertionError(
            f"by_cause sums to {cause_total}, summary.missing is {s['missing']}"
        )
    row_total = sum(r["demand_rows"] for r in records)
    if row_total != s["demand_rows_unsatisfiable"]:
        raise AssertionError(
            f"demand_rows across records sums to {row_total}, summary says "
            f"{s['demand_rows_unsatisfiable']}"
        )
    if s["missing"] > s["demanded_pairs"]:
        raise AssertionError("more pairs missing than demanded")

    absent = {r["archetype"] for r in records if r["cause"] == CAUSE_ARCHETYPE_ABSENT}
    if sorted(absent) != s["archetypes_absent"]:
        raise AssertionError(
            f"archetypes_absent {s['archetypes_absent']} != {sorted(absent)} from records"
        )
    for rec in records:
        if rec["cause"] == CAUSE_ARCHETYPE_ABSENT and rec["variants_available"]:
            raise AssertionError(
                f"{rec['archetype']}/{rec['variant']} claims the archetype is absent "
                f"but lists variants {rec['variants_available']}"
            )
        if rec["cause"] == CAUSE_VARIANT_MISSING and not rec["variants_available"]:
            raise AssertionError(
                f"{rec['archetype']}/{rec['variant']} claims the archetype is present "
                "but lists no available variant"
            )
        if rec["demand_rows"] < 1:
            raise AssertionError(f"{rec['archetype']}/{rec['variant']} demanded by 0 rows")


# ─── Emission ─────────────────────────────────────────────────────


def emit_supply_register(
    out_path: Path,
    build_manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Write the register beside a build's other registers. Used by the wire
    patch in orchestrate.py; safe to call from anywhere."""
    manifest = None
    if build_manifest_path is not None and build_manifest_path.exists():
        manifest = json.loads(build_manifest_path.read_text(encoding="utf-8"))
    register = build_register(load_demand(), load_supply(), manifest)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(register, indent=2) + "\n", encoding="utf-8")
    return register


def _print_summary(reg: dict[str, Any]) -> None:
    s = reg["summary"]
    print(
        f"supply register: {s['missing']} of {s['demanded_pairs']} demanded pairs "
        f"have no template ({s['demand_rows_unsatisfiable']} of "
        f"{s['demand_rows_total']} demand rows unsatisfiable)"
    )
    for cause, n in s["by_cause"].items():
        print(f"  {cause}: {n}")
    for rec in reg["missing"]:
        pages = ",".join(rec["page_types"])
        print(
            f"  {rec['archetype']}/{rec['variant']:<18} "
            f"{rec['demand_rows']:>3} rows  {len(rec['industries'])} industries  [{pages}]"
        )
    if "build" in reg:
        b = reg["build"]
        print(
            f"build {b['project']}: {b['pairs_unsupplied']} of {b['pairs_demanded']} "
            f"demanded pairs unsupplied"
        )
        for u in b["unsupplied"]:
            print(f"  {u['archetype']}/{u['variant']} <- {', '.join(u['routes'])}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-o", "--output", type=Path, help="write the register here")
    ap.add_argument(
        "--build-dir",
        type=Path,
        help="a build output dir; annotates which missing pairs it demanded (read-only)",
    )
    args = ap.parse_args(argv)

    manifest_path = None
    if args.build_dir:
        manifest_path = args.build_dir / "site-manifest.json"
        if not manifest_path.exists():
            print(f"no site-manifest.json under {args.build_dir}", file=sys.stderr)
            return 1
    try:
        manifest = json.loads(manifest_path.read_text()) if manifest_path else None
        register = build_register(load_demand(), load_supply(), manifest)
    except SourceMissing as exc:
        print(f"supply register NOT_MEASURED: {exc}", file=sys.stderr)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(register, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(json.dumps(register, indent=2))
        return 0
    _print_summary(register)
    return 0


if __name__ == "__main__":
    sys.exit(main())

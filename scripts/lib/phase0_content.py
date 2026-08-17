"""Phase-0 declarations, read as CONTENT — Tasks C1 and C2.

`VALID_SOURCES = {"harvested", "phase0", "empty"}` has been in
`section_artifact.py` since the contract was written, and a census over the last
real cape-crypto build returns 119 `harvested`, 23 `empty` and **zero**
`phase0`. Meanwhile cape-crypto declares 7 products and 5 content pillars across
86 phase-0 fields, and `/merchants` and `/developers` are three sections long.
Those two facts have never met. This module is the connector.

THE CONTENT RULE, RESTATED — NOT WIDENED
────────────────────────────────────────
"Sourced or empty, never invented." A phase-0 field is *sourced*: an operator
collected it from the tenant, it lives in a row with a `field_key`, and every
slot composed from it names that key. That is why `phase0` is a legal source
value. Composing a fact the tenant did **not** declare is invention and stays
forbidden — nothing here defaults, pads, or infers. An undeclared field yields
`[]`, and `[]` yields no section.

PRECEDENCE — harvested > phase0 > omitted
─────────────────────────────────────────
If the source page already says it, the harvest wins: composing over it would
tell the visitor the same thing twice, once in the tenant's own published words
and once in an operator's intake note. If the source is silent and the
declaration covers it, compose. If neither, omit with a recorded reason.

NOT_MEASURED ≠ NOTHING DECLARED
───────────────────────────────
`load_tenant_context` never raises — every read goes through `_safe_get`, which
degrades to `[]`. So an unreachable Supabase, a dropped table and a genuinely
empty tenant all arrive here as the same empty dict. `declared_content` refuses
with `DeclarationNotMeasured` when `load_status` says the read never happened,
for the same reason `declared_platforms` does: a database outage must never be
recorded as "this tenant declared nothing".
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

try:  # pragma: no cover - import shape depends on how the package is loaded
    from .tenant_context import _str_list
except ImportError:  # fallback when imported as a top-level module
    from tenant_context import _str_list  # type: ignore


class DeclarationNotMeasured(RuntimeError):
    """The tenant context never loaded, so nothing is known about what was declared.

    Deliberately NOT the same as "declared nothing". The sibling of
    `PlatformNotMeasured` in `tenant_context`, and it exists for the same
    reason: absence produced by a failed read says nothing about the tenant.
    """


#: The phase-0 field behind each declared-content group. One field per group,
#: named here once, so a provenance row can point at the exact row an operator
#: filled in. Nothing is derived from a second field as a "fallback" — a
#: fallback is an inference wearing a default's clothes.
DECLARED_FIELDS = {
    "products": "product_list",
    "pillars": "content_pillars",
    "positioning": "competitive_positioning",
    "proof": "licenses",
}

#: Load statuses that mean the phase-0 rows were never actually read.
_UNMEASURED_STATUSES = ("unconfigured", "unreachable")

#: Separators an operator uses inside one declared list entry to write
#: "Name — what it is". Splitting on them is normalisation of declared text,
#: not authoring: both halves are the tenant's own words and the full entry is
#: preserved verbatim in `value`.
_TITLE_BODY_SPLIT = re.compile(r"\s+[—–]\s+|\s+-\s+")


def _refuse_if_unmeasured(tenant_context: dict | None) -> None:
    """Raise `DeclarationNotMeasured` when the context never loaded.

    A context with no `load_status` key is a caller supplying values directly
    (a literal dict, a fixture, a CLI override). That is data in hand, not a
    failed load, so it is treated as read — the same rule `_unmeasured` uses in
    `tenant_context`, and it is what makes `{"phase0_field_values": {}}` mean
    "read, and empty".
    """
    if not tenant_context:
        raise DeclarationNotMeasured(
            "NOT_MEASURED: no tenant context was loaded, so nothing was read "
            "about what this tenant declares. This is not 'declared nothing' — "
            "nothing was asked. Pass --tenant <slug>."
        )
    status = tenant_context.get("load_status")
    if status in _UNMEASURED_STATUSES:
        slug = (tenant_context.get("slug")
                or tenant_context.get("coordinate") or "<unknown tenant>")
        reasons = tenant_context.get("load_errors") or []
        raise DeclarationNotMeasured(
            f"NOT_MEASURED: tenant '{slug}' context load_status={status!r}, so "
            "the phase-0 declarations were never read. Absence here says "
            "nothing about what the tenant declared — do not compose from it, "
            "and do not record it as undeclared.\n"
            + ("\n".join(f"  {r}" for r in reasons) if reasons else "  (no reason recorded)")
        )


def _indexed(values: list[str], field: str) -> list[dict[str, Any]]:
    """Declared list entries as `{value, field_key, title, body}` records.

    `field_key` is `product_list[3]` — the field AND the position inside it, so
    a provenance row names the exact declared entry a slot came from rather
    than the field it happened to live in.
    """
    out: list[dict[str, Any]] = []
    for i, value in enumerate(values):
        title, _, body = _split_title_body(value)
        out.append({
            "value": value,
            "field_key": f"{field}[{i}]",
            "title": title,
            "body": body,
        })
    return out


def _split_title_body(value: str) -> tuple[str, str, str]:
    """`"Name — what it is"` → (name, "", "what it is"); no separator → (value, "", "").

    The middle element is unused padding kept so the caller reads as a triple;
    see `_indexed`. Only the FIRST separator splits, so a description
    containing its own dash stays intact.
    """
    parts = _TITLE_BODY_SPLIT.split(value, maxsplit=1)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return (parts[0].strip(), "", parts[1].strip())
    return (value.strip(), "", "")


def declared_content(tenant_context: dict | None) -> dict[str, Any]:
    """What the tenant DECLARED that the build can compose from.

    Returns::

        {"products": [{value, field_key, title, body}, ...],
         "pillars":  [{value, field_key, title, body}, ...],
         "positioning": str | None,
         "proof":    [{value, field_key, title, body}, ...]}

    An undeclared field is `[]` / `None` — absent, never an empty string and
    never a placeholder. An unmeasurable context raises
    `DeclarationNotMeasured` rather than returning the same empty shape.
    """
    _refuse_if_unmeasured(tenant_context)
    values = (tenant_context or {}).get("phase0_field_values") or {}

    positioning_raw = values.get(DECLARED_FIELDS["positioning"])
    positioning = (positioning_raw.strip()
                   if isinstance(positioning_raw, str) and positioning_raw.strip()
                   else None)

    return {
        "products": _indexed(_str_list(values.get(DECLARED_FIELDS["products"])),
                             DECLARED_FIELDS["products"]),
        "pillars": _indexed(_str_list(values.get(DECLARED_FIELDS["pillars"])),
                            DECLARED_FIELDS["pillars"]),
        "positioning": positioning,
        "proof": _indexed(_str_list(values.get(DECLARED_FIELDS["proof"])),
                          DECLARED_FIELDS["proof"]),
    }


# ─── C2: the composer ─────────────────────────────────────────────

#: Which archetype each declared group composes into. FEATURES is the only
#: archetype in the local library whose template is a title+body repeater, and
#: both groups are exactly that shape. Both mapping to it is deliberate: the
#: page-level precedence rule below lets at most one composed section claim an
#: archetype, so a page never gets two identical card grids.
_GROUP_ARCHETYPE = {
    "products": "FEATURES",
    "pillars": "FEATURES",
}

#: Order the groups are considered in. Products before pillars: a product list
#: is what a visitor on a thin `/merchants` page came for; pillars are
#: editorial topics and are the weaker claim on the same slot.
_GROUP_ORDER = ("products", "pillars")

#: Fallback variant when the registry declares no variant for the archetype.
#: `FEATURES/icon-grid` is the local template — resolvable with no Supabase.
_FALLBACK_VARIANT = {"FEATURES": "icon-grid"}


def field_key_for_slot(slot: str, base_field: str) -> str:
    """The declared field a composed slot traces to.

    Slot names carry their 1-based item index in two spellings — `features[3]
    .title` (array slots) and `feature_3_title` (flat numbered slots) — and
    both must resolve, or a provenance row names the field without naming the
    entry, which is most of the point. A section-level slot with no index
    traces to the field itself. This is the only place the slot→declaration
    join is expressed; `fill_slots` calls it when stamping a composed section.
    """
    match = re.search(r"\[(\d+)\]", slot) or re.search(r"_(\d+)(?:_|$)", slot)
    if match:
        return f"{base_field}[{int(match.group(1)) - 1}]"
    return base_field


def compose_declared_sections(
    declared: dict[str, Any] | None,
    covered_archetypes: set,
    *,
    variant_for_archetype: dict | None = None,
    page_id: str = "",
) -> tuple[list[dict], list[dict]]:
    """Sections composed from declared facts the page's harvest does not cover.

    `covered_archetypes` is the set of CANONICAL archetypes the page's harvest
    already carries — canonicalised by the caller, because the alias table
    lives in `orchestrate.py` and importing it here would be circular.

    Returns `(sections, omissions)`. Every omission carries a machine-readable
    reason, because "no section appeared" and "no section was possible" are
    different facts and a build that cannot tell them apart is the failure mode
    this whole codebase is being dug out of.

    Never pads: an undeclared group composes nothing and says why.
    """
    declared = declared or {}
    variant_for_archetype = variant_for_archetype or {}
    sections: list[dict] = []
    omissions: list[dict] = []
    claimed: set = set(covered_archetypes or set())

    for group in _GROUP_ORDER:
        items = declared.get(group) or []
        archetype = _GROUP_ARCHETYPE[group]
        field = DECLARED_FIELDS[group]
        if not items:
            omissions.append({
                "group": group, "field_key": field, "archetype": archetype,
                "reason": "not_declared",
                "detail": f"tenant declares no {field}; nothing to compose",
            })
            continue
        if archetype in covered_archetypes:
            # harvested > phase0. The source page already says this in the
            # tenant's own published words.
            omissions.append({
                "group": group, "field_key": field, "archetype": archetype,
                "reason": "harvested_covers",
                "detail": f"the page harvest already carries a {archetype} block",
            })
            continue
        if archetype in claimed:
            omissions.append({
                "group": group, "field_key": field, "archetype": archetype,
                "reason": "archetype_already_composed",
                "detail": f"{archetype} was composed from a higher-precedence declaration",
            })
            continue

        sections.append(_compose_section(group, archetype, field, items,
                                         variant_for_archetype, page_id))
        claimed.add(archetype)

    return sections, omissions


def _compose_section(
    group: str, archetype: str, field: str, items: list[dict],
    variant_for_archetype: dict, page_id: str = "",
) -> dict:
    """One composed section dict, shaped exactly like a harvested one.

    `content` uses the GROUPED shape (`items[]` + `item_count`) that
    `fill_slots` already understands, so a composed section fills its template
    through the same join as a harvested one — no second code path, and array
    arity comes from the declaration rather than from a template's hardcoded
    card count.

    `section_headings` / `section_body_text` are deliberately EMPTY. A section
    heading is not a declared fact; inventing "What we offer" here is exactly
    the fabrication this module exists to avoid. The slot stays empty and is
    counted as empty. C3 is where declared facts become phrased copy.

    No `index` key: a composed section has no extraction-crawl index, and
    filling that gap with a list position fabricates a crawl coordinate that
    can collide with a real section's (see `_normalize_reconciled_section`).
    """
    return {
        "archetype": archetype,
        # A composed section needs a DURABLE uid for the same reason a
        # harvested one does: `_emit_section_artifact` keeps only the
        # provenance rows whose `section_uid` matches the artifact's, and a
        # section with neither `section_uid` nor a crawl `index` falls back to
        # a list position that differs between the fill call and the emit call
        # — so every phase0 row was filtered out of the artifact it belonged
        # to. Derived from page + archetype + field, so it is stable run to run
        # (determinism) and distinct per page.
        "section_uid": "p0" + hashlib.sha1(
            f"{page_id}|{archetype}|{field}".encode("utf-8")
        ).hexdigest()[:10],
        "variant": (variant_for_archetype.get(archetype)
                    or _FALLBACK_VARIANT.get(archetype) or ""),
        "content_direction": "",
        "content": {
            "items": [{"heading": it["title"], "body": it["body"]} for it in items],
            "item_count": len(items),
            "section_headings": [],
            "section_body_text": [],
            "ctas": [],
        },
        "_phase0_composed": True,
        "_phase0_group": group,
        "_phase0_field": field,
        # The provenance of the composed CONTENT, independent of which template
        # variant later resolves and which of its slots get filled. Every row
        # is `phase0` and every row names its declared entry.
        "_phase0_provenance": [
            {"source": "phase0", "field_key": it["field_key"], "value": it["value"]}
            for it in items
        ],
    }

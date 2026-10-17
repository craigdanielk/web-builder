"""Emit a canonical ProjectContract + ``semanticSectionId <-> section_uid`` map.

This establishes COEXISTENCE between two identities, without conflating them:

  * ``semanticSectionId`` = ``projectId:pageSlug:sectionKey`` — STABLE, survives
    copy, implementation, variant, layout and rebuild changes. This is the
    Project Contract's semantic identity.
  * ``section_uid`` = ``sha1(page|archetype|variant|first-text)`` — build/artifact
    identity, revision-scoped.

This module does NOT migrate asset / motion / image / provenance jobs away from
``section_uid`` (those are correctly revision-scoped), and it does NOT retrofit
historical builds (existing ``section_uid`` values and existing CMS data are
left untouched). It emits a NEW artifact alongside the existing ones.

Stdlib only, deterministic. Imported both as ``lib.project_contract_emit`` and
as a sibling of ``orchestrate.py``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from . import slot_contract
except ImportError:  # pragma: no cover - direct-script import path
    import slot_contract  # type: ignore


# Ratified archetype -> SectionTypeId mappings ONLY. Anything not here is
# "requires adjudication" and is emitted with semanticType=None + unratified.
ARCHETYPE_TO_SECTION_TYPE = {
    "HERO": "HERO",
    "NAV": "HEADER",
    "FOOTER": "FOOTER",
    "CTA": "CTA",
    "FAQ": "FAQ",
    "FEATURES": "FEATURE",
    "PRODUCT-SHOWCASE": "PRODUCT_SHOWCASE",
    "VIDEO": "MEDIA",
    "CONTENT": "TEXT_BLOCK",
    "LEGAL-BODY": "TEXT_BLOCK",
}

# Page slug -> PageTypeId for the slugs the greenfield build emits with a known
# canonical page type. Content/blog pages fall back to CUSTOM; anything else is
# left as None + a page_type_unratified flag (never invented).
PAGE_TYPE_BY_SLUG = {
    "homepage": "HOME",
    "about": "ABOUT",
    "contact": "CONTACT",
    "collection": "COLLECTION",
    "product-detail": "PRODUCT_DETAIL",
    "legal": "LEGAL",
}
CONTENT_PAGE_SLUGS = {"content-page", "blog-index"}

_PROP_RE = re.compile(r"^\s*(\w+)\??:\s*([\w\[\]]+);", re.M)
_ARRAY_T_RE = re.compile(r"^(\w+)\[\]$")


def _slugify(value: str) -> str:
    """lowercase, non-alnum -> '-', collapse runs, strip. Never empty."""
    out = [ch if ch.isalnum() else "-" for ch in value.lower()]
    s = re.sub(r"-+", "-", "".join(out)).strip("-")
    return s or "section"


def stable_section_key(section_type: str, occurrences: dict) -> str:
    """A stable, deterministic section key.

    The key depends ONLY on ``(section_type, ordinal-within-page)`` — never on
    first-text, variant, implementation, or file topology. The first occurrence
    of a base returns the base slug; each subsequent occurrence within a page
    returns ``base-2``, ``base-3``, ... via the caller-supplied counter.
    """
    base = _slugify(section_type)
    n = occurrences.get(base, 0) + 1
    occurrences[base] = n
    return base if n == 1 else f"{base}-{n}"


def _iface_body(tsx: str, name: str) -> str | None:
    # Simpler/more permissive than rails_emit's `\n\}` form: matches both
    # single-line and multi-line interface bodies (up to the first `}`).
    m = re.search(r"(?:interface|type)\s+" + re.escape(name) + r"\s*=?\s*\{(.*?)\}", tsx, re.S)
    return m.group(1) if m else None


def _props(tsx: str) -> list:
    """[(prop_name, ts_type), ...] from the component's Props interface, or []."""
    m = re.search(r"interface\s+(\w*Props)\s*\{", tsx)
    if not m:
        return []
    body = _iface_body(tsx, m.group(1))
    if body is None:
        return []
    return _PROP_RE.findall(body)


def _editable(tsx: str) -> bool:
    """'cms-structured' iff the section declares a Props interface with at least
    one string or array prop — the same rule rails_emit.derive_section_fields
    uses to decide a section has editable fields."""
    return any(t == "string" or _ARRAY_T_RE.match(t) for _p, t in _props(tsx))


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _derive_fields(tsx: str) -> list:
    """Minimal, honest CanonicalFieldType buckets from slot_contract.infer_type.

    Only cleanly-derivable mappings are emitted; anything ambiguous is omitted
    (an empty list) rather than guessed.
    """
    fields: list[str] = []
    for prop, _t in _props(tsx):
        kind = slot_contract.infer_type(_snake(prop))
        if kind in ("text-short", "text-long"):
            p = prop.lower()
            if "headline" in p or "title" in p or p.endswith("heading"):
                fields.append("headline")
            elif "subheadline" in p or "lead" in p or "subtitle" in p:
                fields.append("lead")
        elif kind == "image":
            fields.append("media")
        elif kind == "cta":
            fields.append("cta")
    return list(dict.fromkeys(fields))


def _load_section_index(section_artifacts_dir: Path) -> dict:
    """{page_id: [{section_uid, archetype, variant, tsx, section_index}]}.

    Mirrors rails_emit.load_section_index: reads every
    ``section-artifacts/<page_id>/NN-<name>.json``, skipping malformed entries
    and entries with no section_uid.
    """
    index: dict[str, list[dict]] = {}
    if not section_artifacts_dir.is_dir():
        return index
    for page_dir in sorted(p for p in section_artifacts_dir.iterdir() if p.is_dir()):
        entries: list[dict] = []
        for art_path in sorted(page_dir.glob("*.json")):
            try:
                art = json.loads(art_path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            uid = str(art.get("section_uid") or "").strip()
            if not uid:
                continue
            entries.append({
                "section_uid": uid,
                "section_key": str(art.get("section_key") or "").strip(),
                "archetype": (art.get("archetype") or ""),
                "variant": (art.get("variant") or ""),
                "tsx": (art.get("tsx") or ""),
                "section_index": art.get("section_index", 0),
            })
        if entries:
            index[page_dir.name] = entries
    return index


def _page_type(slug: str) -> tuple:
    """(page_type_id_or_None, page_type_unratified: bool)."""
    if slug in PAGE_TYPE_BY_SLUG:
        return PAGE_TYPE_BY_SLUG[slug], False
    if slug in CONTENT_PAGE_SLUGS:
        return "CUSTOM", False
    return None, True


def _label(slug: str) -> str:
    return " ".join(w.capitalize() for w in re.split(r"[-_]+", slug) if w)


def emit_project_contract(
    section_artifacts_dir,
    rails_emission_path,
    output_path,
    project_id: str,
    name: str,
) -> dict:
    section_artifacts_dir = Path(section_artifacts_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rails: dict = {}
    if rails_emission_path is not None:
        rp = Path(rails_emission_path)
        if rp.is_file():
            try:
                rails = json.loads(rp.read_text())
            except (OSError, json.JSONDecodeError):
                rails = {}
    # Read for parity with rails_emit. `editable_pages` is intentionally NOT
    # used to filter: a ProjectContract binds ALL pages (code-owned and
    # cms-structured), not only the ones with a Puck editor.
    editable_pages = rails.get("editable_pages") or []
    tenant = rails.get("tenant")
    if not name and tenant:
        name = str(tenant)

    index = _load_section_index(section_artifacts_dir)

    pages: list[dict] = []
    id_map: dict[str, dict] = {}
    for page_id in sorted(index):
        page_type, page_type_unratified = _page_type(page_id)
        occurrences: dict[str, int] = {}
        sections: list[dict] = []
        for entry in index[page_id]:
            explicit_key = entry.get("section_key")
            archetype = entry["archetype"]
            archetype_upper = (archetype or "").upper()
            semantic_type = ARCHETYPE_TO_SECTION_TYPE.get(archetype_upper)
            provisional_type = semantic_type is None
            
            if explicit_key:
                key = explicit_key
                provisional_key = False
            else:
                base = semantic_type if semantic_type else _slugify(archetype_upper or "custom")
                key = stable_section_key(base, occurrences)
                # Any generated key using occurrences is subject to ordinal drift
                provisional_key = True
                
            section = {
                "key": key,
                "canonicalType": semantic_type,
                "semanticType": semantic_type,
                "validationStatus": "valid" if semantic_type else "unratified",
                "archetype": archetype,
                "variant": entry["variant"],
                "editability": "cms-structured" if _editable(entry["tsx"]) else "code-owned",
                "fields": _derive_fields(entry["tsx"]),
                "section_uid": entry["section_uid"],
            }
            if provisional_key or provisional_type:
                section["key_provisional"] = True
            sections.append(section)
            id_map[f"{project_id}:{page_id}:{key}"] = {
                "section_uid": entry["section_uid"],
                "archetype": archetype,
                "variant": entry["variant"],
            }
        page = {
            "slug": page_id,
            "route": "/" if page_id == "homepage" else f"/{page_id}",
            "label": _label(page_id),
            "type": page_type,
            "sections": sections,
        }
        if page_type_unratified:
            page["page_type_unratified"] = True
        pages.append(page)

    contract = {
        "projectId": project_id,
        "name": name,
        "pages": pages,
    }

    output_path.write_text(json.dumps(contract, indent=2) + "\n")
    map_path = output_path.parent / "semantic-section-id-map.json"
    map_path.write_text(json.dumps(id_map, indent=2) + "\n")

    return contract

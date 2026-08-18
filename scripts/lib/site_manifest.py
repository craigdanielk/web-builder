"""
Site Manifest — Layer 6 Multi-Page App Generation

Defines the JSON structure that describes every page in a generated site.
Single source of truth for scaffold, sections, assembly, and deploy stages.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Default pages when no architecture file is provided
DEFAULT_PAGES = [
    {
        "id": "homepage",
        "route": "/",
        "app_path": "src/app/page.tsx",
        "page_type": "homepage",
        "title": "Home",
        "dynamic": False,
    },
    {
        "id": "collection-template",
        "route": "/collections/[handle]",
        "app_path": "src/app/collections/[handle]/page.tsx",
        "page_type": "collection",
        "title": "Collection",
        "dynamic": True,
    },
    {
        "id": "product-template",
        "route": "/products/[handle]",
        "app_path": "src/app/products/[handle]/page.tsx",
        "page_type": "product",
        "title": "Product",
        "dynamic": True,
    },
    {
        "id": "content-template",
        "route": "/pages/[handle]",
        "app_path": "src/app/pages/[handle]/page.tsx",
        "page_type": "about",
        "title": "Content Page",
        "dynamic": True,
    },
    {
        "id": "not-found",
        "route": "/not-found",
        "app_path": "src/app/not-found.tsx",
        "page_type": "landing",
        "title": "404",
        "dynamic": False,
    },
]


def get_default_shared_components(
    nav_variant: str = "sticky-transparent",
    footer_variant: str = "four-column",
) -> Dict[str, Dict[str, str]]:
    """Return default shared_components dict for manifest."""
    return {
        "navigation": {"archetype": "NAV", "variant": nav_variant},
        "footer": {"archetype": "FOOTER", "variant": footer_variant},
    }


# Commerce page-types that must render as dynamic [handle] routes with Layer-7
# Storefront wiring. Any other page-type from the industry registry is treated as
# a static marketing/funnel route (e.g. fintech: pricing, signup, kyc, checkout).
_COMMERCE_PAGE_TYPES = {"collection", "product"}
_COMMERCE_ROUTE = {
    "collection": ("collection-template", "/collections/[handle]", "src/app/collections/[handle]/page.tsx", "Collection"),
    "product": ("product-template", "/products/[handle]", "src/app/products/[handle]/page.tsx", "Product"),
}


def _page_entry_for_type(page_type: str) -> Dict[str, Any]:
    """Map an industry page_type to a manifest page entry.

    homepage → "/"; commerce types → dynamic [handle] routes (Layer 7); every
    other page_type → a static funnel/marketing route at /{page_type}."""
    if page_type == "homepage":
        return {"id": "homepage", "route": "/", "app_path": "src/app/page.tsx",
                "page_type": "homepage", "title": "Home", "dynamic": False}
    if page_type in _COMMERCE_ROUTE:
        pid, route, app_path, title = _COMMERCE_ROUTE[page_type]
        return {"id": pid, "route": route, "app_path": app_path,
                "page_type": page_type, "title": title, "dynamic": True}
    # Static marketing/funnel page (pricing, signup, kyc, account, checkout, legal, …)
    title = page_type.replace("-", " ").replace("_", " ").title()
    return {"id": f"{page_type}-page", "route": f"/{page_type}",
            "app_path": f"src/app/{page_type}/page.tsx",
            "page_type": page_type, "title": title, "dynamic": False}


def _pages_from_page_types(page_types) -> list:
    """Build manifest pages from an ordered list of industry page_types.
    homepage is forced first; a not-found page is always appended."""
    seen, ordered = set(), []
    for pt in (["homepage"] + list(page_types or [])):
        if pt and pt not in seen:
            seen.add(pt)
            ordered.append(pt)
    pages = [_page_entry_for_type(pt) for pt in ordered]
    pages.append({"id": "not-found", "route": "/not-found",
                  "app_path": "src/app/not-found.tsx", "page_type": "landing",
                  "title": "404", "dynamic": False})
    return pages


def generate_site_manifest(
    project: str,
    industry: str,
    output_dir: Path,
    industry_metadata: Optional[dict] = None,
    architecture_path: Optional[Path] = None,
    write_file: bool = True,
    page_types: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Generate a site manifest for multi-page generation.

    Page source, in priority order:
      1. architecture_path (e.g. from Calculator) — reads route structure from it.
      2. page_types — the industry's real page-types from the registry (e.g.
         fintech: homepage, pricing, signup, kyc, account, checkout, legal). Each
         becomes a page: homepage at "/", commerce types as dynamic [handle]
         routes, everything else a static funnel route at /{page_type}.
      3. DEFAULT_PAGES — the generic 5-page e-commerce fallback.

    industry_metadata: optional dict from get_industry_metadata(industry) with
        default_nav_variant, default_footer_variant. If None, uses defaults.

    Returns the manifest dict. If write_file is True, writes to output_dir/site-manifest.json.
    """
    nav_variant = "sticky-transparent"
    footer_variant = "four-column"
    if industry_metadata:
        nav_variant = industry_metadata.get("default_nav_variant") or nav_variant
        footer_variant = industry_metadata.get("default_footer_variant") or footer_variant

    if architecture_path and architecture_path.exists():
        try:
            arch = json.loads(architecture_path.read_text(encoding="utf-8"))
            if not industry or industry == "ecommerce":
                industry = arch.get("industry") or "ecommerce"
        except (OSError, json.JSONDecodeError):
            pass

    if page_types:
        pages = _pages_from_page_types(page_types)
    else:
        pages = [dict(p) for p in DEFAULT_PAGES]
    shared_components = get_default_shared_components(nav_variant, footer_variant)

    manifest = {
        "project": project,
        "industry": industry,
        "shared_components": shared_components,
        "pages": pages,
    }

    if write_file:
        out_path = output_dir / "site-manifest.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest


# ── The sequencing key, and the two vocabularies that meet at it ────────────
#
# THE DECISION (2026-08-18, gap 8 of the library-absorption census)
# `industry` is the sequencing key. `market` is the key of the REFERENCE.
# They are different axes and are not unified:
#
#   * `section_presets` — the only sequence store that exists — is keyed
#     (industry, page_type, position): 995 rows, 29 industries, 14 page types.
#   * `benchmarks/*.json` carry NO sequence field at all, and `market` is
#     declared in no phase-0 row of either live tenant; it arrives only as the
#     `--benchmark` flag. Keying sequences by market would mean a new store
#     with one populated entry (only enterprise-stablecoin-payments has a
#     corpus) and an invented corpus-slug -> page_type map.
#
# The market axis feeds the industry store as EVIDENCE — a measured reference
# sequence can revise registry rows — but it does not resolve them.
#
# THE MISMATCH THIS CONSTANT EXISTS TO CLOSE
# The harvest and manifest builders speak an 8-value page_type vocabulary
# (`html-page-harvest.js:659-674`, `build_site_manifest.PAGE_TYPE_DEFINITIONS`)
# and the registry speaks a different 14-value one. Four values overlap;
# three DO NOT, and a non-overlapping value cannot match a registry row on any
# industry — so the lookup silently returns 0 and the build falls through to a
# uniform hand-authored sequence. Measured 2026-08-18: cape-crypto resolves to
# industry `fintech`, and its three `content` pages queried `page_type=content`
# against a table whose only content key is `content-page`.
#
# `content` is also `build_site_manifest.harvested_pages_to_manifest_pages`'s
# DEFAULT for a page whose type could not be classified, so the silent miss is
# the normal path for any unclassified route.
REGISTRY_PAGE_TYPES = frozenset({
    "homepage", "product-detail", "collection", "content-page", "about",
    "contact", "blog-index", "shared", "pricing", "signup", "checkout",
    "kyc", "account", "legal",
})

#: manifest/harvest vocabulary -> registry vocabulary. Identity entries are
#: written out rather than implied: an entry here is a claim that the two
#: vocabularies mean the same thing by that word, and that claim should be
#: reviewable.
_PAGE_TYPE_TO_REGISTRY = {
    "homepage": "homepage",
    "about": "about",
    "contact": "contact",
    "collection": "collection",
    "content": "content-page",
    "product": "product-detail",
    "blog": "blog-index",
}


def registry_page_type(page_type: Optional[str]) -> Dict[str, Any]:
    """Translate a manifest page_type into the registry's vocabulary.

    Returns ``{"handle": str | None, "status": str, "source": str}``:

      ``mapped``       — translated across the vocabularies (`content` -> `content-page`)
      ``identity``     — the same word in both vocabularies
      ``registry_only``— already a registry value the manifest side never emits
      ``unmapped``     — NOT_MEASURED: no registry key for this page type, so a
                         lookup would be a guaranteed 0-row query reported as
                         "this industry has no sequence for this page"

    A page type this function cannot map is NEVER silently passed through to
    the query: an unmatchable key and a genuinely empty sequence are different
    facts and must not arrive at the caller looking identical.
    """
    raw = (page_type or "").strip().lower()
    if not raw:
        return {"handle": None, "status": "unmapped", "source": "empty"}
    mapped = _PAGE_TYPE_TO_REGISTRY.get(raw)
    if mapped:
        return {
            "handle": mapped,
            "status": "identity" if mapped == raw else "mapped",
            "source": "page_type_vocabulary",
        }
    if raw in REGISTRY_PAGE_TYPES:
        return {"handle": raw, "status": "registry_only", "source": "registry_vocabulary"}
    return {"handle": None, "status": "unmapped", "source": "no_registry_key"}


# ── Declared sequences in a preset, per page type ───────────────────────────
#
# WHY A PRESET CARRIES SEQUENCES AT ALL
# When the registry has no row for (industry, page_type) the build falls back
# to a fenced block in `skills/presets/<name>.md`. That is a DECLARED operator
# source and is legitimate; what was not legitimate is that there was exactly
# ONE block and it was applied to every page. Measured on cape-crypto
# (2026-08-18): five pages, five different page types, one identical 8-section
# sequence, and 19 of 21 omissions reasoned `registry_gap_fill_no_source` —
# sections demanded on a page whose source has no such block.
#
# `## Default Section Sequence` stays exactly as it was. A preset may now also
# declare `## Section Sequence — <page_type>` blocks, which win for that page
# type. Nothing is inferred: a page type with no block of its own falls back to
# the default, and that fallback is RECORDED as the source rather than being
# indistinguishable from a declared per-page choice.
_SEQ_DEFAULT_HEADING = re.compile(r"^##\s+Default Section Sequence\s*$", re.I)
_SEQ_PAGE_HEADING = re.compile(
    r"^##\s+Section Sequence\s*[-—–:]\s*(?P<page_type>[\w][\w-]*)\s*$", re.I
)
_SEQ_LINE = re.compile(r"\d+\.\s+([\w][\w-]*)\s*\|\s*([\w][\w-]*)(?:\s*\|\s*(.+))?")

#: the key under which the un-page-typed block is returned
SEQUENCE_DEFAULT_KEY = "default"


def _sequence_from_lines(lines: List[str]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for line in lines:
        match = _SEQ_LINE.match(line.strip().replace("**", ""))
        if match:
            result.append({
                "position": len(result) + 1,
                "archetype": match.group(1).strip(),
                "variant": match.group(2).strip(),
                "content_direction": (match.group(3) or "").strip(),
                "priority": "required",
            })
    return result


def parse_sequence_blocks(markdown: str) -> Dict[str, List[Dict[str, Any]]]:
    """Every declared section sequence in a preset, keyed by page type.

    ``{"default": [...], "homepage": [...], "about": [...]}`` — the default key
    is ``SEQUENCE_DEFAULT_KEY``. A heading with no fenced block, or a fenced
    block with no parsable lines, yields no key at all: an empty declared
    sequence and an absent one are the same fact here (nothing was declared),
    and inventing an empty list would let a caller report "declared: 0 sections"
    as though the operator had asked for a blank page.
    """
    blocks: Dict[str, List[Dict[str, Any]]] = {}
    key: Optional[str] = None
    in_fence = False
    seen_fence = False
    buffer: List[str] = []

    def flush():
        nonlocal key, buffer, seen_fence, in_fence
        if key and buffer:
            parsed = _sequence_from_lines(buffer)
            if parsed:
                blocks[key] = parsed
        key, buffer, seen_fence, in_fence = None, [], False, False

    for line in (markdown or "").split("\n"):
        stripped = line.strip()
        if not in_fence and (stripped.startswith("## ") or stripped.startswith("# ")):
            flush()
            if _SEQ_DEFAULT_HEADING.match(stripped):
                key = SEQUENCE_DEFAULT_KEY
            else:
                page_match = _SEQ_PAGE_HEADING.match(stripped)
                if page_match:
                    key = page_match.group("page_type").strip().lower()
            continue
        if key is None:
            continue
        if stripped.startswith("```"):
            if not seen_fence:
                seen_fence = True
                in_fence = True
                continue
            flush()
            continue
        if in_fence:
            buffer.append(line)

    flush()
    return blocks


def resolve_preset_sequence(
    blocks: Dict[str, List[Dict[str, Any]]],
    page_type: Optional[str],
) -> Dict[str, Any]:
    """Pick the declared sequence for one page type, and say which one it is.

    Returns ``{"sections": [...], "source": str, "status": str}`` with status
    ``page_type`` (a block declared for this page type), ``default`` (the
    preset's single default block), or ``none`` (nothing declared — an empty
    list AND a status that says so, never a silent empty page).
    """
    key = (page_type or "").strip().lower()
    if key and key in blocks:
        return {"sections": blocks[key], "source": f"#{key}", "status": "page_type"}
    if SEQUENCE_DEFAULT_KEY in blocks:
        return {
            "sections": blocks[SEQUENCE_DEFAULT_KEY],
            "source": f"#{SEQUENCE_DEFAULT_KEY}",
            "status": "default",
        }
    return {"sections": [], "source": None, "status": "none"}


def load_site_manifest(path: Union[Path, str]) -> Dict[str, Any]:
    """Load a site manifest from a JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Site manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def filter_nav_footer_from_sections(sections: List[dict]) -> List[dict]:
    """Remove NAV and FOOTER from a section sequence (they become shared components)."""
    return [
        s for s in sections
        if (s.get("archetype") or "").upper() not in ("NAV", "FOOTER")
    ]

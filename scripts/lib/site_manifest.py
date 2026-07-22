"""
Site Manifest — Layer 6 Multi-Page App Generation

Defines the JSON structure that describes every page in a generated site.
Single source of truth for scaffold, sections, assembly, and deploy stages.
"""

import json
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

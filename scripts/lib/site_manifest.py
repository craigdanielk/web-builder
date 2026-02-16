"""
Site Manifest — Layer 6 Multi-Page App Generation

Defines the JSON structure that describes every page in a generated site.
Single source of truth for scaffold, sections, assembly, and deploy stages.
"""

import json
from pathlib import Path
from typing import Any

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
) -> dict[str, dict[str, str]]:
    """Return default shared_components dict for manifest."""
    return {
        "navigation": {"archetype": "NAV", "variant": nav_variant},
        "footer": {"archetype": "FOOTER", "variant": footer_variant},
    }


def generate_site_manifest(
    project: str,
    industry: str,
    output_dir: Path,
    industry_metadata: dict | None = None,
    architecture_path: Path | None = None,
    write_file: bool = True,
) -> dict[str, Any]:
    """
    Generate a site manifest for multi-page generation.

    If architecture_path is provided (e.g. from Calculator), reads route structure from it.
    Otherwise uses default pages: homepage, collection, product, content, not-found.

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


def load_site_manifest(path: Path | str) -> dict[str, Any]:
    """Load a site manifest from a JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Site manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def filter_nav_footer_from_sections(sections: list[dict]) -> list[dict]:
    """Remove NAV and FOOTER from a section sequence (they become shared components)."""
    return [
        s for s in sections
        if (s.get("archetype") or "").upper() not in ("NAV", "FOOTER")
    ]

#!/usr/bin/env python3
"""
Site Manifest Builder — Layer 6 Multi-Page App Generation

Converts an enumerated page list (from sitemap crawling or manual input) into a
valid site-manifest.json consumable by the multipage pipeline. Reconciles discovered
pages with required page-types per industry.

Usage:
    python scripts/build_site_manifest.py --project my-project --industry artisan-food \\
        --pages homepage,about,contact --output output/my-project/site-manifest.json

    # Or read pages from a file (one page type per line)
    python scripts/build_site_manifest.py --project my-project --industry ecommerce \\
        --pages-file pages.txt --output output/my-project/site-manifest.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add scripts/lib to path for imports
sys.path.insert(0, str(Path(__file__).parent / "lib"))

try:
    import site_manifest
    from supabase_client import get_all_page_sections, get_industry_metadata
except ImportError:
    print("Error: Required modules not found. Ensure you're running from the web-builder root.")
    sys.exit(1)


# Page type definitions with their route patterns and dynamic flags
PAGE_TYPE_DEFINITIONS = {
    "homepage": {
        "id": "homepage",
        "route": "/",
        "app_path": "src/app/page.tsx",
        "page_type": "homepage",
        "title": "Home",
        "dynamic": False,
    },
    "about": {
        "id": "about",
        "route": "/about",
        "app_path": "src/app/about/page.tsx",
        "page_type": "about",
        "title": "About",
        "dynamic": False,
    },
    "contact": {
        "id": "contact",
        "route": "/contact",
        "app_path": "src/app/contact/page.tsx",
        "page_type": "contact",
        "title": "Contact",
        "dynamic": False,
    },
    "collection": {
        "id": "collection-template",
        "route": "/collections/[handle]",
        "app_path": "src/app/collections/[handle]/page.tsx",
        "page_type": "collection",
        "title": "Collection",
        "dynamic": True,
    },
    "product": {
        "id": "product-template",
        "route": "/products/[handle]",
        "app_path": "src/app/products/[handle]/page.tsx",
        "page_type": "product",
        "title": "Product",
        "dynamic": True,
    },
    "blog": {
        "id": "blog-template",
        "route": "/blog/[handle]",
        "app_path": "src/app/blog/[handle]/page.tsx",
        "page_type": "blog",
        "title": "Blog Post",
        "dynamic": True,
    },
    "blog-index": {
        "id": "blog-index",
        "route": "/blog",
        "app_path": "src/app/blog/page.tsx",
        "page_type": "blog",
        "title": "Blog",
        "dynamic": False,
    },
    "content": {
        "id": "content-template",
        "route": "/pages/[handle]",
        "app_path": "src/app/pages/[handle]/page.tsx",
        "page_type": "about",
        "title": "Content Page",
        "dynamic": True,
    },
    "not-found": {
        "id": "not-found",
        "route": "/not-found",
        "app_path": "src/app/not-found.tsx",
        "page_type": "landing",
        "title": "404",
        "dynamic": False,
    },
}


def get_required_page_types(industry: str) -> set[str]:
    """
    Get required page types for an industry from the database.

    Returns a set of page_type strings (e.g., {'homepage', 'about', 'contact'}).
    If database is unavailable, returns a sensible default.
    """
    try:
        all_sections = get_all_page_sections(industry)
        if all_sections:
            return set(all_sections.keys())
    except Exception as e:
        print(f"Warning: Could not fetch required page types from database: {e}")

    # Fallback to sensible defaults
    return {"homepage"}


def reconcile_pages(
    discovered_pages: list[str],
    required_pages: set[str],
    industry: str,
) -> list[str]:
    """
    Reconcile discovered pages with required page types per industry.

    Strategy:
    1. Always include discovered pages (user-specified)
    2. Add missing required pages
    3. Always include not-found page

    Returns a deduplicated, ordered list of page types.
    """
    # Start with discovered pages (preserve order)
    reconciled = list(dict.fromkeys(discovered_pages))  # Remove duplicates, preserve order

    # Add missing required pages
    for required in required_pages:
        if required not in reconciled:
            reconciled.append(required)

    # Always include not-found page (if not already present)
    if "not-found" not in reconciled:
        reconciled.append("not-found")

    return reconciled


def pages_to_manifest_pages(page_types: List[str]) -> List[Dict[str, Any]]:
    """
    Convert a list of page type strings to manifest page entries.

    Each page entry includes: id, route, app_path, page_type, title, dynamic
    """
    manifest_pages = []
    for page_type in page_types:
        # Normalize page type key (handle aliases)
        normalized_key = page_type.lower().replace("-", "_").replace(" ", "_")

        # Try exact match first, then fallback to closest match
        if page_type in PAGE_TYPE_DEFINITIONS:
            page_def = PAGE_TYPE_DEFINITIONS[page_type]
        elif normalized_key in PAGE_TYPE_DEFINITIONS:
            page_def = PAGE_TYPE_DEFINITIONS[normalized_key]
        else:
            # Fallback: create a basic definition for unknown page types
            page_def = {
                "id": page_type.lower().replace(" ", "-"),
                "route": f"/{page_type.lower().replace(' ', '-')}",
                "app_path": f"src/app/{page_type.lower().replace(' ', '-')}/page.tsx",
                "page_type": "about",  # Default to generic page type
                "title": page_type.replace("-", " ").title(),
                "dynamic": False,
            }

        manifest_pages.append(dict(page_def))

    return manifest_pages


def build_site_manifest(
    project: str,
    industry: str,
    pages: List[str],
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Build a complete site manifest from an enumerated page list.

    Args:
        project: Project name
        industry: Industry handle (e.g., 'artisan-food', 'ecommerce')
        pages: List of page type strings (e.g., ['homepage', 'about', 'contact'])
        output_path: Optional path to write the manifest JSON

    Returns:
        Complete manifest dictionary ready for consumption by the multipage pipeline
    """
    print(f"\n🏗️  Building site manifest for '{project}' in '{industry}' industry...")
    print(f"   Discovered pages: {', '.join(pages)}")

    # Get required page types for this industry
    required_pages = get_required_page_types(industry)
    print(f"   Required pages: {', '.join(sorted(required_pages))}")

    # Reconcile pages (add missing required pages, remove duplicates)
    reconciled_pages = reconcile_pages(pages, required_pages, industry)
    print(f"   Reconciled pages: {', '.join(reconciled_pages)}")

    # Convert page types to manifest page entries
    manifest_pages = pages_to_manifest_pages(reconciled_pages)

    # Get industry metadata for shared components
    industry_metadata = None
    try:
        industry_metadata = get_industry_metadata(industry)
    except Exception as e:
        print(f"   Warning: Could not fetch industry metadata: {e}")

    # Build shared components
    nav_variant = "sticky-transparent"
    footer_variant = "four-column"
    if industry_metadata:
        nav_variant = industry_metadata.get("default_nav_variant") or nav_variant
        footer_variant = industry_metadata.get("default_footer_variant") or footer_variant

    shared_components = site_manifest.get_default_shared_components(nav_variant, footer_variant)

    # Assemble complete manifest
    manifest = {
        "project": project,
        "industry": industry,
        "shared_components": shared_components,
        "pages": manifest_pages,
    }

    # Write to file if output path provided
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\n✅ Site manifest written to: {output_path}")
        print(f"   Total pages: {len(manifest_pages)}")

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Build a site-manifest.json from an enumerated page list",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple usage with comma-separated pages
  python scripts/build_site_manifest.py --project my-site --industry artisan-food \\
      --pages homepage,about,contact

  # Read pages from a file
  python scripts/build_site_manifest.py --project my-site --industry ecommerce \\
      --pages-file pages.txt --output output/my-site/site-manifest.json

  # Use default pages for industry
  python scripts/build_site_manifest.py --project my-site --industry construction-trades \\
      --use-default-pages
        """,
    )
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--industry", required=True, help="Industry handle (e.g., artisan-food, ecommerce)")
    parser.add_argument(
        "--pages",
        help="Comma-separated list of page types (e.g., homepage,about,contact)",
    )
    parser.add_argument(
        "--pages-file",
        type=Path,
        help="Path to file containing page types (one per line)",
    )
    parser.add_argument(
        "--use-default-pages",
        action="store_true",
        help="Use default pages for the industry instead of specifying manually",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for site-manifest.json (default: output/{project}/site-manifest.json)",
    )

    args = parser.parse_args()

    # Determine page list
    if args.use_default_pages:
        # Use required pages from industry as defaults
        pages = list(get_required_page_types(args.industry))
        if not pages:
            pages = ["homepage"]
    elif args.pages_file:
        # Read pages from file
        if not args.pages_file.exists():
            print(f"Error: Pages file not found: {args.pages_file}")
            sys.exit(1)
        pages = [line.strip() for line in args.pages_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    elif args.pages:
        # Parse comma-separated pages
        pages = [p.strip() for p in args.pages.split(",") if p.strip()]
    else:
        print("Error: Must specify --pages, --pages-file, or --use-default-pages")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = Path("output") / args.project / "site-manifest.json"

    # Build the manifest
    try:
        manifest = build_site_manifest(
            project=args.project,
            industry=args.industry,
            pages=pages,
            output_path=output_path,
        )
        print(f"\n📊 Manifest summary:")
        print(f"   Project: {manifest['project']}")
        print(f"   Industry: {manifest['industry']}")
        print(f"   Pages: {len(manifest['pages'])}")
        print(f"   Shared components: {list(manifest['shared_components'].keys())}")
    except Exception as e:
        print(f"\n❌ Error building manifest: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

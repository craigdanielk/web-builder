#!/usr/bin/env python3
"""
Site Manifest Builder — Layer 6 Multi-Page App Generation

Converts an enumerated page list (from sitemap crawling or manual input) OR a set
of already-harvested page objects (from a copy-harvest ``site-spec.json``) into a
valid site-manifest.json consumable by the multipage pipeline
(``orchestrate.py`` ``if site_manifest:`` path — ``stage_scaffold_multipage`` /
``stage_sections_multipage`` / ``stage_assemble_multipage``).

Every emitted manifest page carries ``id``, ``route``, ``page_type`` and
``sections``; the manifest carries a top-level ``industry``. Harvested pages use
the keys ``page_id`` / ``page_type`` / ``nav`` / ``sections``; this builder maps
that shape → the consumable shape (``page_id`` → ``id``, derives ``route`` and
``app_path`` from the page id, carries ``page_type`` and ``sections`` verbatim,
and stamps the top-level ``industry``).

DETERMINISTIC / IDEMPOTENT: the same input pages always produce a byte-identical
manifest. There are no timestamps, no random ids, and no set-ordering: required
page types are folded in via a sorted iteration and harvested pages are mapped
1:1 in their given order, so re-running is safe and yields identical output.

Usage:
    # Enumerated page-type list
    python scripts/build_site_manifest.py --project my-project --industry artisan-food \\
        --pages homepage,about,contact --output output/my-project/site-manifest.json

    # Read page types from a file (one page type per line)
    python scripts/build_site_manifest.py --project my-project --industry ecommerce \\
        --pages-file pages.txt --output output/my-project/site-manifest.json

    # Harvested pages from a copy-harvest site-spec.json (maps pages[] 1:1)
    python scripts/build_site_manifest.py --project my-project --industry fintech \\
        --site-spec /path/to/copy-harvest/site-spec.json \\
        --output output/my-project/site-manifest.json
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
    exact: bool = False,
) -> list[str]:
    """
    Reconcile discovered pages with required page types per industry.

    Strategy:
    1. Always include discovered pages (user-specified)
    2. Add missing required pages
    3. Always include not-found page

    When ``exact`` is True, steps 2 and 3 are skipped: the caller's enumerated
    page list is treated as the complete site. This matters for sites whose
    real route set is known (e.g. from a crawl) — silently folding in
    industry-required page types would emit routes the source site does not
    have, which on a regulated/financial site means shipping pages that can
    only be filled with invented content.

    Returns a deduplicated, ordered list of page types.
    """
    # Start with discovered pages (preserve order)
    reconciled = list(dict.fromkeys(discovered_pages))  # Remove duplicates, preserve order

    if exact:
        return reconciled

    # Add missing required pages.
    # IMPORTANT: iterate a *sorted* list, not the raw set — set iteration order
    # over strings is salted per-process (PYTHONHASHSEED) and would make the
    # emitted manifest nondeterministic across runs. sorted() guarantees the
    # same page ordering every time (idempotency).
    for required in sorted(required_pages):
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


def _route_for_page_id(page_id: str) -> str:
    """Derive a static route from a harvested page id. Deterministic."""
    if page_id in ("homepage", "home", "index", ""):
        return "/"
    return "/" + page_id.strip("/")


def _app_path_for_page_id(page_id: str) -> str:
    """Derive the Next.js app-router file path from a harvested page id. Deterministic."""
    if page_id in ("homepage", "home", "index", ""):
        return "src/app/page.tsx"
    return f"src/app/{page_id.strip('/')}/page.tsx"


def harvested_pages_to_manifest_pages(harvested: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Map already-harvested page objects (from a copy-harvest site-spec.json) to
    multipage-consumable manifest page entries.

    Input page shape (harvested):  {page_id, page_type, nav, sections, source_url, ...}
    Output page shape (consumed):  {id, route, app_path, page_type, title, dynamic, sections, nav}

    The mapping is a pure 1:1 transform preserving input order — no reconciliation,
    no not-found injection — so N harvested pages produce exactly N manifest pages.
    Deterministic: identical input list → identical output list.
    """
    manifest_pages: List[Dict[str, Any]] = []
    for page in harvested:
        page_id = str(page.get("page_id") or page.get("id") or "").strip()
        if not page_id:
            # Skip anonymous pages rather than emit an id-less entry the
            # consumer can't route. Deterministic (order-preserving).
            continue
        page_type = page.get("page_type") or "content"
        title = "Home" if page_id in ("homepage", "home", "index") else page_id.replace("-", " ").replace("_", " ").title()
        entry: Dict[str, Any] = {
            "id": page_id,
            "route": _route_for_page_id(page_id),
            "app_path": _app_path_for_page_id(page_id),
            "page_type": page_type,
            "title": title,
            "dynamic": False,
            "sections": list(page.get("sections") or []),
        }
        # Carry nav through when present (consumer ignores it if unused).
        if page.get("nav") is not None:
            entry["nav"] = page.get("nav")
        manifest_pages.append(entry)
    return manifest_pages


def build_site_manifest(
    project: str,
    industry: str,
    pages: Optional[List[str]] = None,
    output_path: Optional[Path] = None,
    harvested_pages: Optional[List[Dict[str, Any]]] = None,
    exact_pages: bool = False,
) -> Dict[str, Any]:
    """
    Build a complete site manifest from an enumerated page list OR from a set of
    already-harvested page objects.

    Args:
        project: Project name
        industry: Industry handle (e.g., 'artisan-food', 'ecommerce', 'fintech')
        pages: List of page type strings (e.g., ['homepage', 'about', 'contact']).
            Used only when harvested_pages is not provided.
        output_path: Optional path to write the manifest JSON
        harvested_pages: Optional list of harvested page objects (from a copy-harvest
            site-spec.json pages[]). When provided, they are mapped 1:1 to manifest
            pages (no reconciliation / not-found injection) and `pages` is ignored.

    Returns:
        Complete manifest dictionary ready for consumption by the multipage pipeline.
        Deterministic: same inputs → byte-identical manifest.
    """
    print(f"\n🏗️  Building site manifest for '{project}' in '{industry}' industry...")

    if harvested_pages is not None:
        # Harvested mode — map the copy-harvest pages[] 1:1 (order preserved).
        print(f"   Harvested pages: {len(harvested_pages)}")
        manifest_pages = harvested_pages_to_manifest_pages(harvested_pages)
        print(f"   Mapped pages: {', '.join(p['id'] for p in manifest_pages)}")
    else:
        pages = pages or []
        print(f"   Discovered pages: {', '.join(pages)}")

        # Get required page types for this industry
        required_pages = set() if exact_pages else get_required_page_types(industry)
        if exact_pages:
            print("   Exact mode: industry-required pages and not-found NOT folded in")
        else:
            print(f"   Required pages: {', '.join(sorted(required_pages))}")

        # Reconcile pages (add missing required pages, remove duplicates)
        reconciled_pages = reconcile_pages(pages, required_pages, industry, exact=exact_pages)
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
        "--site-spec",
        type=Path,
        help="Path to a copy-harvest site-spec.json — maps its pages[] 1:1 into the manifest "
        "(page_id→id, derives route, carries page_type/sections). Overrides --pages*.",
    )
    parser.add_argument(
        "--exact-pages",
        action="store_true",
        help="Emit exactly the pages given by --pages/--pages-file. Skips folding in "
        "industry-required page types and the not-found page. Use when the site's real "
        "route set is already known (e.g. from a crawl).",
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
    harvested_pages = None
    pages: List[str] = []
    if args.site_spec:
        # Harvested mode — read pages[] from a copy-harvest site-spec.json
        if not args.site_spec.exists():
            print(f"Error: site-spec not found: {args.site_spec}")
            sys.exit(1)
        try:
            spec = json.loads(args.site_spec.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Error: could not parse site-spec JSON: {e}")
            sys.exit(1)
        harvested_pages = spec.get("pages")
        if not isinstance(harvested_pages, list) or not harvested_pages:
            print(f"Error: site-spec has no non-empty 'pages' array: {args.site_spec}")
            sys.exit(1)
    elif args.use_default_pages:
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
        print("Error: Must specify --site-spec, --pages, --pages-file, or --use-default-pages")
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
            harvested_pages=harvested_pages,
            exact_pages=args.exact_pages,
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

#!/usr/bin/env python3
"""
Transform Templates — Add typed prop interfaces to Supabase code_template entries.

Queries the section_archetypes table for commerce-related templates (NAV, FOOTER,
PRODUCT-SHOWCASE, PRICING) and injects optional typed prop interfaces with fallback
to hardcoded defaults.

Usage:
    python scripts/transform_templates.py                    # Apply all archetypes
    python scripts/transform_templates.py --dry-run          # Preview without writing
    python scripts/transform_templates.py --archetype NAV    # Target specific archetype
    python scripts/transform_templates.py --archetype NAV --archetype FOOTER
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import urllib.parse
from typing import Any

# Reuse the existing Supabase client infrastructure
from lib.supabase_client import (
    SUPABASE_KEY,
    SUPABASE_URL,
    _get,
    _HEADERS,
    _SSL_CTX,
)
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("transform_templates")

# ─── Prop Interfaces ─────────────────────────────────────────────

NAV_INTERFACE = """\
interface NavProps {
  menu?: { title: string; url: string }[];
  logo?: string;
  shopName?: string;
}"""

FOOTER_INTERFACE = """\
interface FooterProps {
  menu?: { title: string; url: string; children?: { title: string; url: string }[] }[];
  shopName?: string;
}"""

PRODUCT_SHOWCASE_INTERFACE = """\
interface ProductShowcaseProps {
  products?: { title: string; handle: string; priceRange: { minVariantPrice: { amount: string } }; images: { edges: { node: { url: string; altText: string | null } }[] } }[];
  heading?: string;
  subheading?: string;
}"""

PRICING_INTERFACE = """\
interface PricingProps {
  variants?: { id: string; title: string; price: { amount: string; currencyCode: string } }[];
  productTitle?: string;
  productDescription?: string;
}"""

ARCHETYPE_CONFIG: dict[str, dict[str, Any]] = {
    "NAV": {
        "interface": NAV_INTERFACE,
        "props_type": "NavProps",
        "transforms": [
            {
                "pattern": r"(const\s+(?:items|menuItems|navItems|links|navLinks)\s*(?::\s*[^=]+)?\s*=\s*)(\[[\s\S]*?\])(;?)",
                "field": "menu",
                "wrap": lambda match, field: (
                    f"const {field}Default = {match.group(2)};\n"
                    f"{match.group(1)}props?.{field}?.length ? props.{field} : {field}Default{match.group(3)}"
                ),
            },
        ],
    },
    "FOOTER": {
        "interface": FOOTER_INTERFACE,
        "props_type": "FooterProps",
        "transforms": [
            {
                "pattern": r"(const\s+(?:columns|footerLinks|sections|footerSections|links)\s*(?::\s*[^=]+)?\s*=\s*)(\[[\s\S]*?\])(;?)",
                "field": "menu",
                "wrap": lambda match, field: (
                    f"const {field}Default = {match.group(2)};\n"
                    f"{match.group(1)}props?.{field}?.length ? props.{field} : {field}Default{match.group(3)}"
                ),
            },
        ],
    },
    "PRODUCT-SHOWCASE": {
        "interface": PRODUCT_SHOWCASE_INTERFACE,
        "props_type": "ProductShowcaseProps",
        "transforms": [
            {
                "pattern": r"(const\s+(?:products|items|featuredProducts)\s*(?::\s*[^=]+)?\s*=\s*)(\[[\s\S]*?\])(;?)",
                "field": "products",
                "wrap": lambda match, field: (
                    f"const {field}Default = {match.group(2)};\n"
                    f"{match.group(1)}props?.{field}?.length ? props.{field} : {field}Default{match.group(3)}"
                ),
            },
        ],
    },
    "PRICING": {
        "interface": PRICING_INTERFACE,
        "props_type": "PricingProps",
        "transforms": [
            {
                "pattern": r"(const\s+(?:variants|plans|tiers|pricingPlans|pricingTiers)\s*(?::\s*[^=]+)?\s*=\s*)(\[[\s\S]*?\])(;?)",
                "field": "variants",
                "wrap": lambda match, field: (
                    f"const {field}Default = {match.group(2)};\n"
                    f"{match.group(1)}props?.{field}?.length ? props.{field} : {field}Default{match.group(3)}"
                ),
            },
        ],
    },
}

VALID_ARCHETYPES = list(ARCHETYPE_CONFIG.keys())


# ─── Supabase Helpers ─────────────────────────────────────────────

def _patch(table: str, match_params: str, data: dict) -> int:
    """PATCH (update) rows in Supabase REST API matching the filter params."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_params}"
    body = json.dumps(data).encode("utf-8")
    headers = dict(_HEADERS)
    headers["Prefer"] = "return=minimal"
    req = urllib.request.Request(url, data=body, method="PATCH", headers=headers)
    resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=15)
    return resp.status


def fetch_templates(archetypes: list[str]) -> list[dict]:
    """Fetch code_template rows for the given archetypes."""
    # Supabase REST uses `in.(val1,val2)` syntax for IN filters
    archetype_filter = ",".join(archetypes)
    params = "&".join([
        f"archetype=in.({urllib.parse.quote(archetype_filter)})",
        "has_template=eq.true",
        "select=archetype,variant,code_template",
    ])
    rows = _get("section_archetypes", params)
    return [r for r in rows if r.get("code_template")]


# ─── Transform Logic ──────────────────────────────────────────────

def validate_brackets(code: str) -> bool:
    """Validate that brackets are balanced in the transformed code."""
    stack: list[str] = []
    pairs = {")": "(", "]": "[", "}": "{"}
    in_string = False
    string_char = ""
    escape_next = False

    for ch in code:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if in_string:
            if ch == string_char:
                in_string = False
            continue
        if ch in ("'", '"', "`"):
            in_string = True
            string_char = ch
            continue
        if ch in ("(", "[", "{"):
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.pop()

    return len(stack) == 0


def inject_interface(code: str, interface_text: str) -> str:
    """Inject the interface declaration after 'use client' or at the top of the component."""
    # Skip if interface already present
    interface_name = re.search(r"interface\s+(\w+)", interface_text)
    if interface_name and interface_name.group(1) in code:
        return code

    # Insert after "use client" directive if present
    use_client_match = re.search(r'^["\']use client["\'];?\s*\n', code, re.MULTILINE)
    if use_client_match:
        insert_pos = use_client_match.end()
        return code[:insert_pos] + "\n" + interface_text + "\n\n" + code[insert_pos:]

    # Insert after imports block
    last_import = None
    for m in re.finditer(r"^import\s+.*?;\s*$", code, re.MULTILINE):
        last_import = m
    if last_import:
        insert_pos = last_import.end()
        return code[:insert_pos] + "\n\n" + interface_text + "\n\n" + code[insert_pos:]

    # Fallback: insert at top
    return interface_text + "\n\n" + code


def inject_props_param(code: str, props_type: str) -> str:
    """Add typed props parameter to the component function signature."""
    # Match: export default function ComponentName() or function ComponentName()
    # Also match arrow functions: const ComponentName = () =>
    patterns = [
        # export default function Name() {
        (r"(export\s+default\s+function\s+\w+\s*)\(\s*\)", rf"\1(props: {props_type})"),
        # function Name() {
        (r"(function\s+\w+\s*)\(\s*\)", rf"\1(props: {props_type})"),
        # const Name = () =>
        (r"(const\s+\w+\s*=\s*)\(\s*\)\s*=>", rf"\1(props: {props_type}) =>"),
        # export default function Name({ existing }) — skip if already has params
    ]

    for pat, repl in patterns:
        new_code, count = re.subn(pat, repl, code, count=1)
        if count > 0:
            return new_code

    return code


def apply_array_transforms(code: str, transforms: list[dict]) -> str:
    """Wrap hardcoded arrays with prop fallback pattern."""
    for transform in transforms:
        pattern = transform["pattern"]
        field = transform["field"]
        wrap_fn = transform["wrap"]

        match = re.search(pattern, code)
        if match:
            replacement = wrap_fn(match, field)
            code = code[:match.start()] + replacement + code[match.end():]
            log.info(f"    Wrapped array with props?.{field} fallback")

    return code


def transform_template(archetype: str, variant: str, code: str) -> tuple[str, bool]:
    """
    Apply the mechanical transform for a given archetype.
    Returns (transformed_code, was_modified).
    """
    config = ARCHETYPE_CONFIG.get(archetype)
    if not config:
        log.warning(f"  No config for archetype {archetype}")
        return code, False

    original = code

    # 1. Inject interface
    code = inject_interface(code, config["interface"])

    # 2. Inject props parameter
    code = inject_props_param(code, config["props_type"])

    # 3. Apply array transforms (wrap hardcoded arrays with prop fallback)
    code = apply_array_transforms(code, config["transforms"])

    modified = code != original

    # 4. Validate bracket balance
    if modified and not validate_brackets(code):
        log.error(f"  BRACKET IMBALANCE after transform — reverting {archetype}/{variant}")
        return original, False

    return code, modified


# ─── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Add typed prop interfaces to Supabase code_template entries for commerce sections."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to Supabase",
    )
    parser.add_argument(
        "--archetype",
        action="append",
        choices=VALID_ARCHETYPES,
        help="Target specific archetype(s). Can be repeated. Default: all commerce archetypes.",
    )
    args = parser.parse_args()

    target_archetypes = args.archetype or VALID_ARCHETYPES

    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        sys.exit(1)

    log.info(f"Targeting archetypes: {', '.join(target_archetypes)}")
    log.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE — will write to Supabase'}")

    # Fetch templates
    log.info("Fetching templates from Supabase...")
    templates = fetch_templates(target_archetypes)
    log.info(f"Found {len(templates)} templates with code")

    if not templates:
        log.info("No templates to transform. Done.")
        return

    modified_count = 0
    skipped_count = 0
    error_count = 0

    for row in templates:
        archetype = row["archetype"]
        variant = row["variant"]
        code = row["code_template"]

        log.info(f"Processing {archetype}/{variant}...")

        transformed, was_modified = transform_template(archetype, variant, code)

        if not was_modified:
            log.info(f"  No changes needed (already has interface or no matching arrays)")
            skipped_count += 1
            continue

        if args.dry_run:
            log.info(f"  [DRY RUN] Would update {archetype}/{variant}")
            # Print first 20 lines of diff context
            original_lines = code.splitlines()[:5]
            new_lines = transformed.splitlines()[:10]
            log.info(f"  --- Original (first 5 lines):")
            for line in original_lines:
                log.info(f"    {line}")
            log.info(f"  +++ Transformed (first 10 lines):")
            for line in new_lines:
                log.info(f"    {line}")
            modified_count += 1
        else:
            try:
                match_params = "&".join([
                    f"archetype=eq.{urllib.parse.quote(archetype)}",
                    f"variant=eq.{urllib.parse.quote(variant)}",
                ])
                _patch("section_archetypes", match_params, {"code_template": transformed})
                log.info(f"  Updated {archetype}/{variant} in Supabase")
                modified_count += 1
            except Exception as e:
                log.error(f"  Failed to update {archetype}/{variant}: {e}")
                error_count += 1

    log.info("")
    log.info("─── Summary ───")
    log.info(f"  Templates found:    {len(templates)}")
    log.info(f"  Modified:           {modified_count}")
    log.info(f"  Skipped (no-op):    {skipped_count}")
    if error_count:
        log.info(f"  Errors:             {error_count}")
    log.info(f"  Mode:               {'DRY RUN' if args.dry_run else 'LIVE'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Compile motion props from declared phase-0 content + compiled design tokens.

This is the demand side of the motion contract, prototyped. It reads the same
two sources a section template reads — the tenant's declaration and the
compiled token set — and emits a props file that a Remotion composition
renders. Nothing here invents content: every string in `items` carries the
`field_key` it was declared under, so provenance survives into the motion job.

Claim safety (FSP No. 53746): only non-numeric declared product names are
emitted. Any declared value containing a digit is dropped and counted, never
rewritten — see `dropped_claim_bearing`.

Usage:
    python3 tools/build_props.py cape-crypto
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

MOTION_DIR = Path(__file__).resolve().parent.parent
WEB_BUILDER = MOTION_DIR.parent

# Token names read out of the compiled globals.css. Keeping this list explicit
# means an unrecognised token is absent from the props, not silently defaulted.
TOKEN_KEYS = (
    "background",
    "surface",
    "foreground",
    "muted",
    "accent",
    "on-accent",
    "border",
    "surface-inverse",
    "font-heading",
    "font-body",
    "heading-weight",
    "body-weight",
    "radius-card",
    "radius-button",
    "card-pad",
    "block-gap",
)


class TokensNotMeasured(RuntimeError):
    """The compiled token set could not be read. Not the same as 'no tokens'."""


class DeclarationNotMeasured(RuntimeError):
    """The tenant context could not be loaded. Not the same as 'declared nothing'."""


def read_tokens(globals_css: Path) -> dict:
    if not globals_css.is_file():
        raise TokensNotMeasured(
            "no compiled globals.css at %s — motion cannot claim to read the "
            "same tokens as the page when the page has not been compiled" % globals_css
        )
    text = globals_css.read_text(encoding="utf-8")
    root = re.search(r":root\s*\{(.*?)\}", text, re.S)
    if not root:
        raise TokensNotMeasured("globals.css has no :root block: %s" % globals_css)
    declared = dict(re.findall(r"--([a-z0-9-]+)\s*:\s*([^;]+);", root.group(1)))
    tokens = {}
    for key in TOKEN_KEYS:
        if key in declared:
            tokens[key] = declared[key].strip()
    missing = [k for k in TOKEN_KEYS if k not in tokens]
    return {"tokens": tokens, "tokens_missing": missing}


def _has_digit(value: str) -> bool:
    return bool(re.search(r"\d", value))


def declared_items(ctx: dict, field_key: str) -> tuple:
    """Return (items, dropped) for one declared list field."""
    values = (ctx.get("phase0_field_values") or {}).get(field_key)
    if not isinstance(values, list):
        return [], []
    items, dropped = [], []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        # An em-dash separates a declared product name from its gloss; the
        # name is what a motion card can hold legibly.
        name = value.split("—")[0].strip().rstrip(",")
        if _has_digit(name):
            dropped.append({"value": name, "reason": "contains a numeral"})
            continue
        items.append({"value": name, "field_key": field_key, "source": "phase0"})
    return items, dropped


def build(slug: str) -> dict:
    sys.path.insert(0, str(WEB_BUILDER / "scripts"))
    from lib.tenant_context import load_tenant_context  # noqa: E402

    ctx = load_tenant_context(slug)
    # load_tenant_context never raises; an unreachable Supabase must not read
    # as "this tenant declared nothing".
    if not ctx.get("available") or ctx.get("load_status") not in (None, "ok", "loaded"):
        raise DeclarationNotMeasured(
            "tenant context for %s is load_status=%r available=%r — refusing to "
            "compose motion from a declaration that was not measured"
            % (slug, ctx.get("load_status"), ctx.get("available"))
        )

    items, dropped = declared_items(ctx, "product_list")
    if not items:
        raise DeclarationNotMeasured(
            "no usable declared products for %s; motion has nothing sourced to "
            "show and must not invent any" % slug
        )

    token_info = read_tokens(WEB_BUILDER / "output" / slug / "site" / "src" / "app" / "globals.css")
    brand = ctx.get("brand") or {}
    name = brand.get("name") or (ctx.get("phase0_field_values") or {}).get("legal_name") or slug

    return {
        "tenant": slug,
        "brandName": name,
        "eyebrow": "What we build",
        "items": items,
        "dropped_claim_bearing": dropped,
        "tokens": token_info["tokens"],
        "tokens_missing": token_info["tokens_missing"],
        "fps": 30,
        "width": 1280,
        "height": 720,
        "framesPerItem": 55,
        "introFrames": 60,
    }


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "cape-crypto"
    props = build(slug)
    out = MOTION_DIR / "props" / ("%s-product-rail.json" % slug)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(props, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote %s" % out)
    print("  items: %d  dropped(claim-bearing): %d  tokens: %d  missing: %s"
          % (len(props["items"]), len(props["dropped_claim_bearing"]),
             len(props["tokens"]), props["tokens_missing"] or "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

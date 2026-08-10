"""
Token Sanitizer — Content Token Sanitization Module

Resolves all remaining {token_name} placeholders in generated site files.
Handles two categories:

A. Structural tokens (resolved from build context):
   - {filter_1}, {filter_2}, {filter_3} -> collection filter labels
   - {page_handle} -> page handle from architecture or "index"
   - {collection_handle} -> collection handle or "all"
   - {product_handle} -> product handle or first available

B. Content tokens (need content generation):
   - {feature_1_title}, {stat_2_value}, {faq_1_question}, etc.
   - Replaced with sensible defaults from archetype-aware tables

Designed to run AFTER the orchestrate.py 8-phase sanitization as a safety net.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Same token pattern used by testing/audit_tokens.py
TOKEN_PATTERN = re.compile(r"\{[a-z][a-z0-9]*(?:_[a-z0-9]+)+\}")

# Tokens that are valid JS/TS code (not content placeholders).
# Mirrors the set in testing/audit_tokens.py but extended for sanitizer context.
FALSE_POSITIVE_TOKENS: set[str] = {
    "{children}", "{className}", "{props}", "{key}", "{value}", "{index}",
    "{item}", "{id}", "{src}", "{alt}", "{href}", "{title}", "{name}",
    "{type}", "{label}", "{error}", "{data}", "{style}", "{ref}", "{params}",
    "{handle}", "{product}", "{collection}", "{products}", "{collections}",
    "{images}", "{variants}", "{options}", "{selected}", "{open}", "{close}",
    "{toggle}", "{width}", "{height}", "{color}", "{size}", "{count}",
    "{total}", "{price}", "{quantity}", "{url}", "{path}", "{query}",
    "{result}", "{results}", "{loading}", "{message}", "{content}",
    "{description}", "{placeholder}", "{e}", "{i}", "{j}", "{k}", "{n}",
    "{x}", "{y}", "{menu}", "{logo}", "{line}", "{qty}", "{container}",
    "{cart}", "{items}", "{theme}", "{state}", "{set}", "{show}", "{hide}",
    "{active}", "{disabled}", "{checked}", "{visible}", "{text}", "{icon}",
    "{image}", "{link}", "{links}", "{section}", "{sections}", "{page}",
    "{pages}", "{nav}", "{footer}", "{header}", "{body}", "{variant}",
    "{option}", "{node}", "{edge}", "{edges}", "{cursor}", "{amount}",
    "{format}", "{locale}", "{slug}", "{status}", "{shop}", "{store}",
    "{config}", "{env}", "{event}", "{target}", "{current}", "{prev}",
    "{next}", "{first}", "{last}", "{min}", "{max}", "{step}", "{cols}",
    "{rows}", "{gap}", "{span}", "{offset}", "{length}", "{idx}", "{arr}",
    "{obj}", "{str}", "{num}", "{val}", "{el}", "{cb}", "{fn}", "{err}",
    "{res}", "{req}", "{ctx}", "{msg}", "{args}", "{rest}", "{map}",
    "{list}", "{acc}", "{tab}", "{row}", "{col}", "{cell}", "{tag}",
    "{tags}", "{category}", "{categories}", "{group}", "{groups}",
    "{field}", "{fields}", "{form}", "{input}", "{output}", "{file}",
    "{dir}", "{base}", "{root}", "{prefix}", "{suffix}",
}

# Context patterns where tokens are valid code, not content
IGNORE_CONTEXTS = [
    re.compile(r"\$\{"),       # JS template literal: ${...}
    re.compile(r"var\(--"),    # CSS variable: var(--)
]

# Structural token defaults — resolved from context or hardcoded defaults
STRUCTURAL_DEFAULTS: dict[str, str] = {
    "page_handle": "index",
    "collection_handle": "all",
    "product_handle": "product",
    "store_domain": "store.myshopify.com",
    "storefront_token": "",
    "admin_token": "",
    "shop_name": "Store",
    "shop_domain": "store.myshopify.com",
}

# Content token defaults by archetype prefix, with numbered variety
CONTENT_DEFAULTS: dict[str, dict[str, str]] = {
    "filter": {"label": "All", "text": "All", "title": "All"},
    "feature": {"icon": "Star", "title": "Feature", "description": "Designed to help you achieve more.", "label": "Feature"},
    "testimonial": {"quote": "An exceptional experience.", "author": "Happy Customer", "role": "Verified Buyer", "rating": "5"},
    "stat": {"value": "99%", "label": "Satisfaction", "suffix": "+", "description": "Trusted by thousands."},
    "faq": {"question": "How can we help?", "answer": "We are here to support you."},
    "badge": {"icon": "Shield", "label": "Certified", "sublabel": "Quality guaranteed"},
    "product": {"name": "Product", "price": "$0.00", "tag": "New", "image": "/placeholder.svg"},
    "step": {"title": "Step", "description": "Follow these simple steps.", "icon": "ArrowRight"},
    "benefit": {"title": "Benefit", "description": "Experience the difference.", "icon": "Check"},
    "nav": {"label": "Shop", "url": "/collections", "href": "/collections"},
    "social": {"url": "#", "label": "Social", "icon": "Globe"},
    "card": {"title": "Card", "description": "Discover something new.", "image": "/placeholder.svg"},
    "team": {"name": "Team Member", "role": "Specialist", "image": "/placeholder.svg"},
    "cta": {"text": "Shop Now", "url": "/collections", "label": "Shop Now"},
    "link": {"label": "Link", "url": "#", "text": "Link"},
    "logo": {"src": "/placeholder.svg", "alt": "Partner", "name": "Partner"},
    "service": {"title": "Service", "description": "Professional service.", "icon": "Briefcase"},
    "value": {"title": "Our Value", "description": "What drives us forward.", "icon": "Heart"},
    "section": {"title": "Discover More", "subtitle": "Learn more about what we offer"},
    "hero": {"title": "Welcome", "subtitle": "Discover our collection", "description": "Premium quality."},
    "column": {"title": "Column", "name": "Column"},
    "col": {"title": "Shop", "name": "Shop"},
    "row": {"feature": "Included", "label": "Feature"},
    "breadcrumb": {"label": "Home", "url": "/"},
    "item": {"title": "Item", "description": "Quality assured.", "icon": "Package"},
    "pricing": {"name": "Plan", "price": "$0", "description": "Everything you need.", "feature": "Included"},
    "category": {"name": "Category", "image": "/placeholder.svg", "url": "#"},
}

NUMBERED_VARIETY: dict[str, list[dict[str, str]]] = {
    "filter": [
        {"label": "New Arrivals", "text": "New Arrivals", "title": "New Arrivals"},
        {"label": "Best Sellers", "text": "Best Sellers", "title": "Best Sellers"},
        {"label": "On Sale", "text": "On Sale", "title": "On Sale"},
    ],
    "feature": [
        {"title": "Free Shipping", "description": "Complimentary delivery on all orders over $50.", "icon": "Truck"},
        {"title": "Quality Guarantee", "description": "Every product meets our highest standards.", "icon": "ShieldCheck"},
        {"title": "24/7 Support", "description": "Our team is always available to help.", "icon": "Headphones"},
        {"title": "Easy Returns", "description": "Hassle-free 30-day returns.", "icon": "RefreshCw"},
    ],
    "stat": [
        {"value": "10K", "label": "Happy Customers", "suffix": "+"},
        {"value": "500", "label": "Products", "suffix": "+"},
        {"value": "99%", "label": "Satisfaction", "suffix": ""},
        {"value": "24/7", "label": "Support", "suffix": ""},
    ],
    "faq": [
        {"question": "What is your shipping policy?", "answer": "Free standard shipping on orders over $50."},
        {"question": "How do I return an item?", "answer": "Returns accepted within 30 days."},
        {"question": "Do you ship internationally?", "answer": "Yes, we ship to over 50 countries."},
    ],
    "testimonial": [
        {"quote": "Quality exceeded my expectations.", "author": "Sarah M.", "role": "Verified Buyer"},
        {"quote": "Incredible customer service!", "author": "James L.", "role": "Verified Buyer"},
        {"quote": "Best online shopping experience.", "author": "Emily R.", "role": "Verified Buyer"},
    ],
    "nav": [
        {"label": "Shop", "url": "/collections", "href": "/collections"},
        {"label": "About", "url": "/pages/about", "href": "/pages/about"},
        {"label": "Contact", "url": "/pages/contact", "href": "/pages/contact"},
    ],
}


def _resolve_token(token_inner: str, context: dict | None = None) -> str | None:
    """Resolve a token name (without braces) to a replacement value.

    Args:
        token_inner: The token name without braces, e.g. "filter_1" or "page_handle"
        context: Optional dict with collection_handles, product_handles, page_handles, etc.

    Returns:
        Replacement string, or None if token should not be replaced.
    """
    context = context or {}

    # 1. Check structural defaults, with context override
    if token_inner in STRUCTURAL_DEFAULTS:
        # Try context first
        if token_inner in context:
            return context[token_inner]
        return STRUCTURAL_DEFAULTS[token_inner]

    # 2a. Bare numbered tokens: prefix_N (e.g., filter_1, filter_2)
    m_bare = re.match(r'^([a-z]+)_(\d+)$', token_inner)
    if m_bare:
        prefix, num_str = m_bare.group(1), m_bare.group(2)
        num = int(num_str)
        # Try per-number variety, using "label" as the default field
        variety = NUMBERED_VARIETY.get(prefix)
        if variety and (num - 1) < len(variety):
            return variety[num - 1].get("label", variety[num - 1].get("title", variety[num - 1].get("text", f"{prefix.title()} {num_str}")))
        # Fall back to base defaults
        defaults = CONTENT_DEFAULTS.get(prefix, {})
        default_val = defaults.get("label", defaults.get("title", defaults.get("text", f"{prefix.title()} {num_str}")))
        return default_val

    # 2b. Numbered tokens with field: prefix_N_field
    m = re.match(r'^([a-z]+)_(\d+)(?:_(\d+))?_(.+)$', token_inner)
    if m:
        prefix, num_str, _sub, field = m.group(1), m.group(2), m.group(3), m.group(4)
        num = int(num_str)
        # Try per-number variety
        variety = NUMBERED_VARIETY.get(prefix)
        if variety and (num - 1) < len(variety) and field in variety[num - 1]:
            return variety[num - 1][field]
        # Fall back to base defaults
        defaults = CONTENT_DEFAULTS.get(prefix, {})
        if field in defaults:
            val = defaults[field]
            if field in ("title", "name", "label") and val == prefix.title():
                return f"{val} {num_str}"
            return val
        # See the note below: never humanize a token name into visible copy.
        return None

    # 3. Non-numbered: prefix_field
    m2 = re.match(r'^([a-z]+)_(.+)$', token_inner)
    if m2:
        prefix, field = m2.group(1), m2.group(2)
        # Check context
        ctx_key = f"{prefix}_{field}"
        if ctx_key in context:
            return context[ctx_key]
        defaults = CONTENT_DEFAULTS.get(prefix, {})
        if field in defaults:
            return defaults[field]
        # No humanize fallback: turning `primary_cta_text` into "Primary Cta
        # Text" renders a variable name as page copy. Unresolvable means
        # unresolvable — the caller records it and leaves the slot empty.
        return None

    return None


def sanitize_tokens(code: str, context: dict | None = None) -> tuple[str, list[dict]]:
    """Sanitize all content placeholder tokens in generated code.

    Args:
        code: Source code string to sanitize.
        context: Optional dict with build context (collection_handles, product_handles, etc.)

    Returns:
        Tuple of (sanitized_code, list of replacement records).
        Each record: {"token": str, "replacement": str, "line": int}
    """
    replacements: list[dict] = []
    lines = code.splitlines(keepends=True)
    result_lines: list[str] = []

    for line_num, line in enumerate(lines, 1):
        # Skip lines with template literals or CSS variables
        if any(p.search(line) for p in IGNORE_CONTEXTS):
            result_lines.append(line)
            continue

        new_line = line
        for match in reversed(list(TOKEN_PATTERN.finditer(line))):
            token = match.group()
            if token in FALSE_POSITIVE_TOKENS:
                continue

            # Check if inside TypeScript type annotation
            before = line[:match.start()].rstrip()
            if before.endswith(":") or before.endswith("<") or before.endswith("extends"):
                continue

            token_inner = token[1:-1]  # strip { }
            replacement = _resolve_token(token_inner, context)
            if replacement is None:
                # Last resort: humanize the token name
                replacement = token_inner.replace("_", " ").title()

            # Determine quoting based on surrounding context
            start, end = match.start(), match.end()
            char_before = line[start - 1] if start > 0 else ""
            char_after = line[end] if end < len(line) else ""

            if char_before in ('"', "'") and char_after in ('"', "'"):
                # Already inside quotes: replace bare
                final = replacement
            elif char_before == '"' or char_after == '"':
                final = replacement
            elif char_before == "'" or char_after == "'":
                final = replacement
            else:
                # Not inside quotes: wrap in double quotes
                final = f'"{replacement}"'

            new_line = new_line[:match.start()] + final + new_line[match.end():]
            replacements.append({
                "token": token,
                "replacement": replacement,
                "line": line_num,
            })

        result_lines.append(new_line)

    return "".join(result_lines), replacements


def sanitize_file(filepath: Path, context: dict | None = None) -> list[dict]:
    """Sanitize tokens in a single file in-place.

    Args:
        filepath: Path to the file to sanitize.
        context: Optional build context dict.

    Returns:
        List of replacement records for this file.
    """
    try:
        original = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    sanitized, replacements = sanitize_tokens(original, context)

    if replacements:
        filepath.write_text(sanitized, encoding="utf-8")
        for r in replacements:
            logger.warning(
                "Sanitized %s in %s:%d -> %s",
                r["token"], filepath.name, r["line"], r["replacement"],
            )

    return replacements


def sanitize_directory(
    site_dir: str | Path,
    context: dict | None = None,
    extensions: tuple[str, ...] = (".tsx", ".ts", ".jsx", ".js"),
) -> dict:
    """Sanitize all token placeholders in a site directory.

    Args:
        site_dir: Path to the generated site directory.
        context: Optional build context (collection handles, page handles, etc.)
        extensions: File extensions to scan.

    Returns:
        Summary dict: {"files_sanitized": int, "total_replacements": int, "details": list}
    """
    site_path = Path(site_dir)
    if not site_path.exists():
        return {"files_sanitized": 0, "total_replacements": 0, "details": []}

    all_replacements: list[dict] = []
    files_sanitized = 0

    for ext in extensions:
        for filepath in site_path.rglob(f"*{ext}"):
            rel = str(filepath.relative_to(site_path))
            if any(part in rel for part in ("node_modules", ".next", "__pycache__")):
                continue

            replacements = sanitize_file(filepath, context)
            if replacements:
                files_sanitized += 1
                for r in replacements:
                    all_replacements.append({**r, "file": rel})

    return {
        "files_sanitized": files_sanitized,
        "total_replacements": len(all_replacements),
        "details": all_replacements,
    }


def sanitize_comment_tokens(code: str) -> str:
    """Handle tokens that appear inside comments (like JSDoc or code comments).

    Tokens in comments are documentation, not rendered content.
    Replace them with descriptive text to avoid false audit positives.
    """
    lines = code.splitlines(keepends=True)
    result: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("*") or stripped.startswith("//") or stripped.startswith("/**") or stripped.startswith("/*"):
            # In a comment: replace token-like patterns with descriptive text
            def _comment_replace(m: re.Match) -> str:
                token = m.group()[1:-1]
                return f"<{token.replace('_', ' ')}>"
            new_line = TOKEN_PATTERN.sub(_comment_replace, line)
            # Only replace multi-word tokens that look like content placeholders
            result.append(new_line)
        else:
            result.append(line)
    return "".join(result)

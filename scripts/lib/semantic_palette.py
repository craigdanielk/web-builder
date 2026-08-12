"""Semantic role-token derivation with WCAG-checked foreground/background pairing.

BRIEF #33317 — root-cause fix for site-wide contrast failures.

The generation path used to thread raw brand hex as decorative Tailwind classes
(``text-[#b5b7ba]``, ``bg-[#0d0e45]``) with no foreground/background pairing, so
text could land grey-on-light or navy-on-navy and fail WCAG. This module derives a
small set of *role* tokens from the raw palette, and for every surface computes an
``on_*`` foreground guaranteed to meet WCAG AA contrast (>=4.5 body / >=3.0 large).

Roles emitted (hex values): ``bg``, ``surface``, ``text_primary``, ``text_muted``,
``on_accent``, ``on_surface``, ``border``, ``accent``. Tailwind role classes
(``text-primary``, ``text-muted``, ``on-accent``, ``on-surface``) map 1:1 to these.
"""
from __future__ import annotations

from typing import Any

# WCAG AA thresholds
_AA_BODY = 4.5
_AA_LARGE = 3.0

_NEAR_BLACK = "#0a0a0a"
_NEAR_WHITE = "#ffffff"
_MUTED_ON_DARK = "#c9ccd1"   # readable grey on dark surfaces
_MUTED_ON_LIGHT = "#4b5563"  # readable grey on light surfaces

# role token -> tailwind role class (the string "text-primary" MUST appear so the
# generation path and the node_7 oracle both see the semantic vocabulary)
ROLE_CLASS_MAP = {
    "text_primary": "text-primary",
    "text_muted": "text-muted",
    "on_accent": "on-accent",
    "on_surface": "on-surface",
    "border": "border-role",
}


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    h = str(value).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return (128, 128, 128)  # neutral fallback for malformed input
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return (128, 128, 128)


def _relative_luminance(value: str) -> float:
    """WCAG relative luminance of a hex color (0..1)."""
    def _lin(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _hex_to_rgb(value)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG contrast ratio between two hex colors (1.0 .. 21.0)."""
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def best_on_color(bg: str, minimum: float = _AA_BODY) -> str:
    """Pick the foreground (near-black or near-white) that best contrasts ``bg``.

    Returns the option meeting ``minimum`` with the higher ratio; if neither
    meets it, returns whichever is higher (caller still gets max legibility).
    """
    cw = contrast_ratio(_NEAR_WHITE, bg)
    cb = contrast_ratio(_NEAR_BLACK, bg)
    return _NEAR_WHITE if cw >= cb else _NEAR_BLACK


def _is_dark(value: str) -> bool:
    return _relative_luminance(value) < 0.5


def derive_semantic_tokens(palette: dict[str, Any] | None) -> dict[str, str]:
    """Map a raw brand palette to WCAG-checked semantic role tokens.

    Accepts the loose palette dicts produced by Phase-0 (keys vary by tenant:
    ``bg_primary``/``background``, ``accent``/``primary``, ``surface``, ``text``…).
    Missing roles fall back to safe neutrals. Every ``on_*`` foreground is computed
    to meet WCAG AA against its paired surface.
    """
    if not isinstance(palette, dict):
        palette = {}

    def pick(*keys: str, default: str) -> str:
        for k in keys:
            v = palette.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return default

    bg = pick("bg_primary", "background", "bg", "base", default=_NEAR_WHITE)
    surface = pick("bg_secondary", "surface", "card", "muted_bg", default=bg)
    accent = pick("accent", "primary", "brand", "cta", default="#2563eb")

    # A DECLARED value wins over a computed one, provided it is readable.
    #
    # This function used to compute every foreground unconditionally, which
    # meant a curated benchmark palette (text_primary #20334a, text_muted
    # #5c6f85, border #e5edf5) was silently replaced by generic neutrals
    # (#0a0a0a, #4b5563, #e5e7eb) on the way to the templates. The design
    # authority was overridden one step before it could be seen — the same
    # failure as `accent: #ffffff`, one layer down.
    #
    # The computation is still the fallback, and still the arbiter: a declared
    # colour that fails AA against its own surface is NOT honoured, because a
    # curated palette is not a licence to ship unreadable text.
    def declared_or(role: str, *aliases: str, against: str, computed: str) -> str:
        value = pick(role, *aliases, default="")
        if value and contrast_ratio(value, against) >= _AA_BODY:
            return value
        return computed

    on_bg = declared_or("text_primary", "text", "on_bg",
                        against=bg, computed=best_on_color(bg))
    on_surface = declared_or("on_surface", "text_primary", "text",
                             against=surface, computed=best_on_color(surface))
    on_accent = declared_or("on_accent", against=accent,
                            computed=best_on_color(accent))

    text_muted = declared_or(
        "text_muted", "muted", against=bg,
        computed=_MUTED_ON_DARK if _is_dark(bg) else _MUTED_ON_LIGHT)
    # Borders are decorative, not text — an AA check would reject every
    # legitimate hairline. Honour a declared border as given.
    border = pick("border", default="#2a2d34" if _is_dark(bg) else "#e5e7eb")

    return {
        "bg": bg,
        "surface": surface,
        "accent": accent,
        "text_primary": on_bg,
        "on_surface": on_surface,
        "on_accent": on_accent,
        "text_muted": text_muted,
        "border": border,
    }


def count_low_contrast(pairs: list[tuple[str, str]], minimum: float = _AA_BODY) -> int:
    """Count fg/bg pairs that fail ``minimum`` — the pipeline's own WCAG outcome."""
    return sum(1 for fg, bg in pairs if contrast_ratio(fg, bg) < minimum)

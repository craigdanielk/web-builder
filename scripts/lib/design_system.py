"""Compile a market benchmark into the build's design tokens.

WHY THIS EXISTS
---------------
`design-tokens.js` fills `site-spec.style` by averaging computed styles off the
CRAWLED SOURCE. For cape-crypto that produced `accent: #ffffff` — an accent that
cannot be seen — alongside Roboto and grey-on-white, and the whole build
faithfully reproduced a mediocre site. Aurelix is meant to be a builder, not a
cloner: the source supplies content, structure, assets and brand; a curated
benchmark supplies design.

This module is that inversion, and it is deliberately small. The benchmark holds
the design; the tenant holds identity; this puts them together and refuses when
they cannot be reconciled.

PRECEDENCE (not negotiable, or "brand overlay" grows to mean "tenant overrides
whatever it likes" and cloning returns through the side door)

    benchmark owns  type scale, weights, radii, rhythm, density, shadow depth,
                    motion, and the palette ROLES
    tenant owns     accent hex, logo, an owned typeface, content, routes

Two tenants in one market come out structurally identical and chromatically
distinct.

OPTIONALITY IS ASYMMETRIC — the load-bearing rule
-------------------------------------------------
Assertion-half keys (what `design_conformance.py` checks) are OPTIONAL: an
absent assertion means NOT_MEASURED, which is already safe.

Generation-half keys are REQUIRED AT LOAD. An absent generation key has no safe
meaning — the generator must emit *something*, and the only other source
available is the crawl. So an optional generation field is a silent field-level
fallback to crawled tokens: precisely the regression this module exists to
prevent, arriving through the schema instead of through the missing-benchmark
path. A benchmark missing any generation key is REJECTED, naming the keys.

This matters immediately rather than theoretically: the first benchmark of any
market is captured from references that will not exhibit every property, so
partial benchmarks are the normal early state.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: Generation-half contract. Every key required at load — see the module note.
REQUIRED_ROLES = (
    "bg_primary", "bg_secondary", "surface", "text_primary",
    "text_muted", "accent", "on_accent", "border",
)
REQUIRED_RHYTHM = ("section_py_px", "block_gap_px", "card_pad_px", "grid_px")
REQUIRED_TYPE_SCALE = ("ratio", "base_px", "heading_weight", "body_weight")

#: WCAG AA for body text. Below this the tenant's own brand colour is
#: unreadable against the benchmark's surfaces, which is a build failure and
#: not something to silently "fix" by darkening someone's brand.
MIN_CONTRAST = 4.5


class BenchmarkError(ValueError):
    """A benchmark that cannot be used. Never downgraded to a warning."""


def _srgb(channel: int) -> float:
    c = channel / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise BenchmarkError(f"not a hex colour: {hex_colour!r}")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _srgb(r) + 0.7152 * _srgb(g) + 0.0722 * _srgb(b)


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def load_benchmark(path: str | Path) -> dict[str, Any]:
    """Load and validate. Raises rather than returning something half-usable."""
    p = Path(path)
    if not p.exists():
        raise BenchmarkError(f"no benchmark at {p}")
    data = json.loads(p.read_text(encoding="utf-8"))

    meta = data.get("_meta") or {}
    if not meta.get("captured_from"):
        raise BenchmarkError(
            f"{p.name}: _meta.captured_from is required. A design rule with no "
            "measured source is an invented rule, which is fabrication in the "
            "same class as an invented statistic."
        )

    missing: list[str] = []
    roles = data.get("palette_roles") or {}
    missing += [f"palette_roles.{k}" for k in REQUIRED_ROLES if not roles.get(k)]
    rhythm = data.get("rhythm") or {}
    missing += [f"rhythm.{k}" for k in REQUIRED_RHYTHM if rhythm.get(k) is None]
    scale = data.get("type_scale") or {}
    missing += [f"type_scale.{k}" for k in REQUIRED_TYPE_SCALE
                if scale.get(k) is None]
    if not data.get("density"):
        missing.append("density")
    if not (data.get("motion") or {}).get("intensity"):
        missing.append("motion.intensity")

    if missing:
        raise BenchmarkError(
            f"{p.name}: generation-half keys missing: {', '.join(missing)}. "
            "These are required at load. An optional generation key is a "
            "field-level fallback to crawled source tokens — complete the "
            "capture instead."
        )
    return data


def compile_style(
    benchmark: dict[str, Any],
    brand_accent: str | None = None,
    brand_font: str | None = None,
) -> dict[str, Any]:
    """Benchmark + tenant identity -> the `site-spec.style` block.

    Returns a style dict carrying `design_source: "benchmark"` and, when a
    contrast substitution was needed, an `adjustments` list recording both
    ratios. A substitution draws ONLY on values already present in the
    benchmark's role palette: nothing is invented, and benchmark precedence
    holds because the replacement is benchmark-owned data.
    """
    roles = dict(benchmark["palette_roles"])
    roles.pop("_source", None)
    adjustments: list[dict] = []

    if brand_accent:
        roles["accent"] = brand_accent
        # `on_accent` must stay readable ON the tenant's colour. The tenant hex
        # is sacred; the benchmark's own palette is where a replacement comes
        # from. Failing outright over one colour pair, and forcing the
        # emergency override, would discard an entire benchmark to fix one
        # relationship.
        if contrast_ratio(roles["on_accent"], brand_accent) < MIN_CONTRAST:
            candidates = [
                (contrast_ratio(v, brand_accent), k, v)
                for k, v in roles.items()
                if isinstance(v, str) and v.startswith("#") and k != "accent"
            ]
            best = max(candidates, default=None)
            if best and best[0] >= MIN_CONTRAST:
                adjustments.append({
                    "role": "on_accent",
                    "from": roles["on_accent"],
                    "to": best[2],
                    "from_ratio": round(
                        contrast_ratio(roles["on_accent"], brand_accent), 2),
                    "to_ratio": round(best[0], 2),
                    "reason": "tenant accent failed 4.5:1 against benchmark on_accent",
                    "drawn_from": f"benchmark palette_roles.{best[1]}",
                })
                roles["on_accent"] = best[2]
            else:
                raise BenchmarkError(
                    f"tenant accent {brand_accent} reaches "
                    f"{best[0]:.2f}:1 at best against every colour in the "
                    f"benchmark palette; {MIN_CONTRAST}:1 is required. No value "
                    "may be invented to bridge this — ratify a benchmark whose "
                    "palette can carry this brand."
                )

    # Body text must be readable on both surfaces. This is the check that would
    # have caught `accent: #ffffff` on day one.
    # `surface` is included because it is where card body copy lands. Omitting
    # it let a measured dark palette ship `surface: #ffffff` alongside
    # `text_primary: #ffffff` — white on white, passing every other pair.
    for role, bg in (("text_primary", "bg_primary"),
                     ("text_muted", "bg_primary"),
                     ("text_primary", "bg_secondary"),
                     ("text_primary", "surface"),
                     ("text_muted", "surface")):
        ratio = contrast_ratio(roles[role], roles[bg])
        if ratio < MIN_CONTRAST:
            raise BenchmarkError(
                f"benchmark palette fails WCAG AA: {role} on {bg} is "
                f"{ratio:.2f}:1, below {MIN_CONTRAST}:1"
            )

    scale = benchmark["type_scale"]
    rhythm = benchmark["rhythm"]
    fonts = (benchmark.get("font_system") or {}).get("families") or ["Inter"]
    heading_family = brand_font or fonts[0]

    return {
        "design_source": "benchmark",
        "benchmark": {
            "market": (benchmark.get("_meta") or {}).get("market"),
            "captured_from": benchmark["_meta"]["captured_from"],
            "captured_at": (benchmark.get("_meta") or {}).get("captured_at"),
        },
        "palette": roles,
        "fonts": {
            "heading": {"extracted": heading_family,
                        "google_fallback": heading_family,
                        "weight": scale["heading_weight"]},
            "body": {"extracted": heading_family,
                     "google_fallback": heading_family,
                     "weight": scale["body_weight"]},
        },
        "type_scale": scale,
        "rhythm": rhythm,
        "spacing": {
            "section_padding": f"{rhythm['section_py_px']}px",
            "internal_gap": f"{rhythm['block_gap_px']}px",
            "scale": benchmark["density"],
        },
        "border_radius": {
            "button": f"{min((benchmark.get('cta_buttons') or {}).get('radius_px') or [8])}px",
            "card": f"{max((benchmark.get('card_system') or {}).get('radius_px') or [8])}px",
        },
        "shadow": {
            "max_layers": (benchmark.get("shadow_system") or {}).get("max_layers", 2),
        },
        "animation": {
            "engine": "framer-motion",
            "intensity": benchmark["motion"]["intensity"],
            "duration_ms": benchmark["motion"].get("duration_ms", 400),
            "libraries": [],
            "keyframes": [],
            "durations": [],
            "easings": [],
        },
        "density": benchmark["density"],
        "adjustments": adjustments,
    }

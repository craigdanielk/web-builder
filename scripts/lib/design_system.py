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
import re
from pathlib import Path
from typing import Any

from .font_match import match_font

#: Generation-half contract. Every key required at load — see the module note.
REQUIRED_ROLES = (
    "bg_primary", "bg_secondary", "surface", "text_primary",
    "text_muted", "accent", "on_accent", "border",
)
REQUIRED_RHYTHM = ("section_py_px", "block_gap_px", "card_pad_px", "grid_px")
REQUIRED_TYPE_SCALE = ("ratio", "base_px", "heading_weight", "body_weight")

#: Keys a tenant preset may override (operator decision 2026-10-21, THURIS).
#: Anything else stays benchmark-owned; an unlisted key is refused, not ignored.
#: `palette_light` is a second, complete role set for sections that opt into the
#: light tone — it never partially inherits the base set.
#: `heading_tiers_px` / `heading_tiers_min_px` declare the display sizes (desktop
#: ceiling / phone floor, largest first) instead of the benchmark's measured
#: tiers; `section_py_min_px` is the phone floor for section padding; `layout`
#: is the content measure (operator brief "Homepage Visual Refinement V1").
TENANT_OVERRIDABLE: dict[str, tuple[str, ...]] = {
    "palette_roles": REQUIRED_ROLES + ("surface_inverse",),
    "palette_light": REQUIRED_ROLES,
    "type_scale": REQUIRED_TYPE_SCALE + ("heading_tiers_px", "heading_tiers_min_px"),
    "rhythm": REQUIRED_RHYTHM + ("section_py_min_px",),
    "border_radius": ("button", "card"),
    "fonts": ("heading", "body"),
    "layout": ("max_width_px", "gutter_min_px", "gutter_max_px"),
}

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


#: web-builder/ — `_meta.corpus` is recorded repo-relative to it.
_WEB_BUILDER_ROOT = Path(__file__).resolve().parents[2]


def _walk_gsap_nodes(evidence: dict[str, Any]):
    """Every GSAP call in a page's evidence, including timeline steps."""
    for call in evidence.get("gsapCalls") or []:
        if not isinstance(call, dict):
            continue
        yield call
        for step in call.get("steps") or []:
            if isinstance(step, dict):
                yield step


def lower_motion_evidence(benchmark: dict[str, Any]) -> dict[str, Any]:
    """Lower the corpus's ALREADY-MEASURED animation evidence into the style.

    `compile_style` used to emit `libraries: [], keyframes: [], durations: [],
    easings: []` — four hardcoded empty lists. The corpus behind the benchmark
    carries all four, per page, and has since it was captured: `libraries[]`
    with confidence and `detectedVia`, `cssKeyframes[]` with bodies, and every
    intercepted GSAP call's `duration` and `ease`. The commissioner lowered
    `motion.intensity` and discarded the rest.

    This is a LOWERING, not a measurement. Nothing here computes a new fact,
    infers a rule, or invents a field the corpus does not carry — it copies
    what was measured, deduplicates it, and records which pages it came from.

    Three-state, like every other surface here:
      * a benchmark with no `_meta.corpus` -> the four keys are ABSENT and
        `evidence_source` says NOT_MEASURED and why. They are not emitted as
        empty lists, because an empty list reads as "measured, found none".
      * a corpus with no page extractions -> the same, naming the directory.
      * a corpus present -> the four keys, and the pages they were read from.

    Deterministic by construction: every collection is sorted on a total key,
    so the same corpus always produces byte-identical output.
    """
    corpus_rel = (benchmark.get("_meta") or {}).get("corpus")
    if not corpus_rel:
        return {
            "evidence_source": "NOT_MEASURED: benchmark declares no _meta.corpus, "
                               "so its animation evidence cannot be re-read"
        }

    corpus_dir = _WEB_BUILDER_ROOT / str(corpus_rel)
    pages = sorted(corpus_dir.glob("*/extraction.json"))
    if not pages:
        return {
            "evidence_source": f"NOT_MEASURED: no */extraction.json under {corpus_rel}"
        }

    libraries: dict[str, dict[str, Any]] = {}
    keyframes: dict[tuple[str, str], dict[str, Any]] = {}
    durations: dict[int, int] = {}
    easings: dict[str, int] = {}
    pages_read: list[str] = []

    for page_file in pages:
        page_id = page_file.parent.name
        try:
            evidence = (json.loads(page_file.read_text(encoding="utf-8"))
                        .get("animations") or {}).get("evidence") or {}
        except (OSError, json.JSONDecodeError):
            # A page that cannot be read is not evidence of an absent library.
            continue
        pages_read.append(page_id)

        for lib in evidence.get("libraries") or []:
            name = lib.get("name")
            if not name:
                continue
            entry = libraries.setdefault(
                name, {"name": name, "confidence": 0, "detected_via": set(), "pages": set()}
            )
            conf = lib.get("confidence")
            if isinstance(conf, (int, float)):
                entry["confidence"] = max(entry["confidence"], conf)
            if lib.get("detectedVia"):
                entry["detected_via"].add(lib["detectedVia"])
            entry["pages"].add(page_id)

        for kf in evidence.get("cssKeyframes") or []:
            name, body = kf.get("name"), kf.get("body")
            if not name or not body:
                continue
            entry = keyframes.setdefault((name, body), {"name": name, "body": body, "pages": set()})
            entry["pages"].add(page_id)

        for node in _walk_gsap_nodes(evidence):
            secs = node.get("duration")
            if isinstance(secs, (int, float)) and not isinstance(secs, bool):
                ms = int(round(secs * 1000))
                durations[ms] = durations.get(ms, 0) + 1
            ease = node.get("ease")
            if isinstance(ease, str) and ease:
                easings[ease] = easings.get(ease, 0) + 1

    return {
        "evidence_source": str(corpus_rel),
        "evidence_pages": sorted(pages_read),
        "libraries": [
            {
                "name": e["name"],
                "confidence": e["confidence"],
                "detected_via": sorted(e["detected_via"]),
                "pages": sorted(e["pages"]),
            }
            for e in sorted(libraries.values(), key=lambda x: x["name"])
        ],
        "keyframes": [
            {"name": e["name"], "body": e["body"], "pages": sorted(e["pages"])}
            for e in sorted(keyframes.values(), key=lambda x: (x["name"], x["body"]))
        ],
        # Recorded with counts, not averaged. An average of 300ms and 60000ms
        # (a 60-second marquee) is a number that describes nothing on the page.
        "durations": [{"ms": ms, "count": durations[ms]} for ms in sorted(durations)],
        # Emitted verbatim, INCLUDING `e.ease||` — a fragment of minified
        # source the extractor captured as an easing name. It is not filtered
        # here: hiding an extractor defect inside a lowering is how a measured
        # artefact becomes an invisible one. The fix belongs in
        # scripts/quality/lib/animation-detector.js.
        "easings": [
            {"name": name, "count": easings[name]}
            for name in sorted(easings, key=lambda n: (-easings[n], n))
        ],
    }


def heading_tiers(benchmark: dict[str, Any], count: int = 4) -> list[int]:
    """The reference's heading tiers, largest first: the `count` most-used
    measured heading sizes (ties to the larger size), else the `count` largest
    declared sizes. `[]` when the benchmark declares no sizes at all."""
    dist = (benchmark.get("_distributions") or {}).get("heading_sizes_px") or {}
    counts: dict[int, int] = {}
    for size, n in dist.items():
        try:
            counts[int(float(size))] = counts.get(int(float(size)), 0) + int(n)
        except (TypeError, ValueError):
            continue
    if counts:
        top = sorted(counts, key=lambda s: (counts[s], s), reverse=True)[:count]
        return sorted(top, reverse=True)
    ts = benchmark.get("type_system") or {}
    declared = ts.get("heading_sizes_px") or ts.get("scale_px") or []
    sizes = sorted({int(float(v)) for v in declared if isinstance(v, (int, float))}, reverse=True)
    return sizes[:count]


def compile_style(
    benchmark: dict[str, Any],
    brand_accent: str | None = None,
    brand_font: str | None = None,
    tenant_overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Benchmark + tenant identity -> the `site-spec.style` block.

    Returns a style dict carrying `design_source: "benchmark"` and, when a
    contrast substitution was needed, an `adjustments` list recording both
    ratios. A substitution draws ONLY on values already present in the
    benchmark's role palette: nothing is invented, and benchmark precedence
    holds because the replacement is benchmark-owned data.
    """
    _check_tenant_overrides(tenant_overrides)
    over = tenant_overrides or {}
    override_log: list[dict] = []
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

    roles = _apply_overrides(roles, over.get("palette_roles"), "palette_roles", override_log)
    _check_readable(roles, "benchmark palette")
    # A tenant-declared accent must carry its own CTA label. Checked only on
    # declared sets: measured benchmarks predate this rule.
    if {"accent", "on_accent"} & set(over.get("palette_roles") or {}):
        _check_label(roles, "tenant palette_roles")
    palette_light = None
    if "palette_light" in over:
        palette_light = dict(over["palette_light"])
        _check_readable(palette_light, "tenant palette_light")
        _check_label(palette_light, "tenant palette_light")

    scale = _apply_overrides(benchmark["type_scale"], over.get("type_scale"),
                             "type_scale", override_log)
    # Heading sizes are part of the scale: templates read these as --type-h1..h4
    # rather than naming display sizes the benchmark never measured.
    # A tenant-declared tier set wins; it is logged as an override above.
    tiers = heading_tiers(benchmark)
    if tiers and "heading_tiers_px" not in (over.get("type_scale") or {}):
        scale = {**scale, "heading_tiers_px": tiers}
    _check_tiers(scale)
    rhythm = _apply_overrides(benchmark["rhythm"], over.get("rhythm"), "rhythm", override_log)
    fonts = (benchmark.get("font_system") or {}).get("families") or ["Inter"]
    font_over = over.get("fonts") or {}
    if font_over.get("heading"):
        brand_font = font_over["heading"]

    # The measured family is usually the reference's proprietary face, which no
    # build can serve. Resolve it to something servable and RECORD the
    # substitution beside the contrast adjustments; emitting the measured name
    # unresolved produced `font-family: 'Capsule Sans Text', system-ui` and a
    # silent fallback, which is a site declaring a typeface it never loads.
    if brand_font:
        heading_family = brand_font
    else:
        heading_family = None
        for candidate in fonts:
            m = match_font(candidate)
            if m.served:
                heading_family = m.served
                if m.substituted:
                    adjustments.append({
                        "role": "font.heading",
                        "from": m.measured,
                        "to": m.served,
                        "reason": m.reason,
                        "confidence": m.confidence,
                        "drawn_from": "font_match.CATALOG",
                    })
                break
        if heading_family is None:
            raise BenchmarkError(
                f"no measured family in {fonts} resolves to a servable font. "
                "A benchmark may not declare a typeface the build cannot load "
                "— supply brand_font, or extend font_match.CATALOG with a "
                "ratified substitute."
            )

    body_family = font_over.get("body") or heading_family
    for role in ("heading", "body"):
        if font_over.get(role):
            override_log.append({"field": f"fonts.{role}", "value": font_over[role],
                                 "was": fonts[0] if fonts else None})
    radius = {
        "button": f"{min((benchmark.get('cta_buttons') or {}).get('radius_px') or [8])}px",
        "card": f"{max((benchmark.get('card_system') or {}).get('radius_px') or [8])}px",
    }
    radius = _apply_overrides(radius, over.get("border_radius"), "border_radius", override_log)
    layout = _apply_overrides({}, over.get("layout"), "layout", override_log)

    style = {
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
            "body": {"extracted": body_family,
                     "google_fallback": body_family,
                     "weight": scale["body_weight"]},
        },
        "type_scale": scale,
        "rhythm": rhythm,
        "spacing": {
            "section_padding": f"{rhythm['section_py_px']}px",
            "internal_gap": f"{rhythm['block_gap_px']}px",
            "scale": benchmark["density"],
        },
        "border_radius": radius,
        "shadow": {
            "max_layers": (benchmark.get("shadow_system") or {}).get("max_layers", 2),
        },
        "animation": {
            "engine": "framer-motion",
            "intensity": benchmark["motion"]["intensity"],
            "duration_ms": benchmark["motion"].get("duration_ms", 400),
            # libraries / keyframes / durations / easings — lowered from the
            # corpus when the benchmark declares one, ABSENT with a
            # NOT_MEASURED `evidence_source` when it does not. They were four
            # hardcoded empty lists until 2026-08-18.
            **lower_motion_evidence(benchmark),
        },
        "density": benchmark["density"],
        "adjustments": adjustments,
    }
    if tenant_overrides is not None:
        style["tenant_overrides"] = override_log
    if palette_light is not None:
        style["palette_light"] = palette_light
    if layout:
        style["layout"] = layout
    return style


def _check_tiers(scale: dict[str, Any]) -> None:
    """Declared tiers are px integers, largest first; a phone floor pairs 1:1
    with the ceiling and never exceeds it. A tier set that fails this would
    emit a clamp() whose floor is above its ceiling — CSS resolves that to
    the floor, silently inverting the operator's declaration."""
    top = scale.get("heading_tiers_px") or []
    floor = scale.get("heading_tiers_min_px")
    for name, tiers in (("heading_tiers_px", top), ("heading_tiers_min_px", floor or [])):
        if not all(isinstance(t, int) and t > 0 for t in tiers):
            raise BenchmarkError(f"type_scale.{name} must be positive px integers: {tiers}")
        if list(tiers) != sorted(tiers, reverse=True):
            raise BenchmarkError(f"type_scale.{name} must be largest first: {tiers}")
    if floor is not None:
        if len(floor) != len(top):
            raise BenchmarkError(
                f"type_scale.heading_tiers_min_px declares {len(floor)} tiers; "
                f"heading_tiers_px has {len(top)}")
        for lo, hi in zip(floor, top):
            if lo > hi:
                raise BenchmarkError(
                    f"type_scale.heading_tiers_min_px {lo}px exceeds its ceiling {hi}px")


def _check_tenant_overrides(overrides: dict[str, Any] | None) -> None:
    """Refuse any key outside TENANT_OVERRIDABLE, naming it."""
    if overrides is None:
        return
    if not isinstance(overrides, dict):
        raise BenchmarkError("tenant design overrides must be an object")
    for group, values in overrides.items():
        if group not in TENANT_OVERRIDABLE:
            raise BenchmarkError(
                f"tenant override group {group!r} is benchmark-owned; overridable: "
                f"{', '.join(TENANT_OVERRIDABLE)}")
        if not isinstance(values, dict):
            raise BenchmarkError(f"tenant override {group} must be an object")
        for key in values:
            if key not in TENANT_OVERRIDABLE[group]:
                raise BenchmarkError(
                    f"tenant override {group}.{key} is not overridable; allowed: "
                    f"{', '.join(TENANT_OVERRIDABLE[group])}")
    light = overrides.get("palette_light")
    if light is not None:
        missing = [r for r in REQUIRED_ROLES if r not in light]
        if missing:
            raise BenchmarkError(
                f"tenant palette_light must declare every role; missing {missing}")


def _apply_overrides(base: dict[str, Any], values: dict[str, Any] | None,
                     group: str, log: list[dict]) -> dict[str, Any]:
    out = dict(base)
    for key, value in (values or {}).items():
        log.append({"field": f"{group}.{key}", "value": value, "was": out.get(key)})
        out[key] = value
    return out


def _check_readable(roles: dict[str, Any], label: str) -> None:
    """Body text must be readable on every ground it lands on.

    This is the check that would have caught `accent: #ffffff` on day one.
    `surface` is included because it is where card body copy lands. Omitting
    it let a measured dark palette ship `surface: #ffffff` alongside
    `text_primary: #ffffff` — white on white, passing every other pair.
    """
    for role, bg in (("text_primary", "bg_primary"),
                     ("text_muted", "bg_primary"),
                     ("text_primary", "bg_secondary"),
                     ("text_primary", "surface"),
                     ("text_muted", "surface")):
        ratio = contrast_ratio(roles[role], roles[bg])
        if ratio < MIN_CONTRAST:
            raise BenchmarkError(
                f"{label} fails WCAG AA: {role} on {bg} is "
                f"{ratio:.2f}:1, below {MIN_CONTRAST}:1"
            )


def _check_label(roles: dict[str, Any], label: str) -> None:
    ratio = contrast_ratio(roles["on_accent"], roles["accent"])
    if ratio < MIN_CONTRAST:
        raise BenchmarkError(
            f"{label} fails WCAG AA: on_accent on accent is {ratio:.2f}:1, "
            f"below {MIN_CONTRAST}:1 — CTA labels would be unreadable")


_OVERRIDES_BLOCK = re.compile(
    r"^## Tenant Design Overrides\s*\n.*?```json\s*\n(.*?)```", re.DOTALL | re.MULTILINE)


def parse_tenant_design_overrides(markdown: str) -> dict[str, Any] | None:
    """The preset's `## Tenant Design Overrides` JSON block, or None when absent.

    A present-but-malformed block raises: an override the operator wrote and the
    build silently skipped would ship the benchmark value under their name.
    """
    match = _OVERRIDES_BLOCK.search(markdown or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise BenchmarkError(f"## Tenant Design Overrides is not valid JSON: {exc}") from exc
    _check_tenant_overrides(data)
    return data

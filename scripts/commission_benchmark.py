#!/usr/bin/env python3
"""Commission a market benchmark from a persisted capture corpus.

PATTERNS ONLY. Reads measured computed styles and emits distributions.
No markup, copy, asset, SVG or shader crosses this boundary — the output
carries numbers and role colours, each with a measured provenance string.

PROVENANCE OF THIS FILE
This is `scripts/compile_benchmark.py` (398 lines, added `731cd819`, deleted
`9805e275` fifteen minutes later) recovered from git and parameterised. The
census `docs/census/2026-08-17-benchmark-production.md` established that the
deleted walker still executes unmodified against today's extractor shape (§4)
and that the ratified BVNK benchmark is a walker-shaped file finished by hand
(§3). Five things were hardcoded in the original and are now parameters:

    market slug · captured_at · contributions · tenant accent ·
    the `"robinhood "` provenance prefix (now the reference host)

WHAT THIS COMMAND WILL NOT DO
Five fields in the benchmark schema are not measurable by any tool in this
repo (census §6.5). They are **absent** from the output and enumerated in
`_unmeasured` with the reason, never defaulted:

    density                      no code path can emit "spacious"; the walker's
                                 comfortable/compact is a two-value guess
    palette_roles.surface_inverse no extractor identifies a deliberately-dark
                                 section ground
    palette_roles.accent /        tenant identity by contract. Emitted ONLY when
    palette_roles.on_accent       --tenant-accent declares it, and then stamped
                                 as declared, never as measured
    font_system.families          measurement yields the reference's proprietary
                                 face; naming a *servable* face is an operator
                                 act. `measured_families` is emitted instead

Four of those five are required by `design_system.load_benchmark`. That is the
point: **a commissioned benchmark does not load until it is ratified.**
`ratified: false` is stamped on everything this command produces; ratification
is a separate, explicit act (Task B3).

USAGE
    python3 scripts/commission_benchmark.py <corpus-dir> \\
        --market <slug> --captured-at YYYY-MM-DD [--out <path>] \\
        [--reference-host <host>] [--tenant-accent '#004e89'] \\
        [--contribution block=url ...]

`<corpus-dir>` is what `scripts/quality/capture-benchmark-pages.js` writes:
`index.json` plus `<slug>/extraction.json` per page.

EXIT CODES
    0   a benchmark was written
    3   NOT_MEASURED — a refusal gate fired; nothing was written
    64  usage error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

TOOL = "commission_benchmark.py"
TOOL_VERSION = "1"
#: `scripts/quality/lib/extract-reference.js:41` — MAX_DOM_ELEMENTS. The cap
#: that bounds every count in `_meta.elements_measured`. Stated, not assumed:
#: `_meta.elements_measured` in the BVNK file reports 3888 for five pages,
#: which five 500-element captures cannot produce (census §3.5).
PER_PAGE_DOM_CAP = 500

#: A banding surface must be VISIBLY distinct from bg_primary. A luminance
#: epsilon is meaningless in the dark range (#000 vs #010101 passes it and
#: renders as no banding at all), so require a real contrast step.
#: The ratified BVNK benchmark's bg_secondary sits at 1.078 and would be
#: refused here. That is correct: this gate is not relaxed to reproduce a
#: hand-finished file (census §3.1, §6.7).
MIN_BANDING = 1.12
#: WCAG AA for body text.
MIN_TEXT_CONTRAST = 4.5
#: A `border` in this schema is a SEPARATOR — it sits close to its background.
MAX_SEPARATOR_CONTRAST = 4.5
#: A heading size must recur to be a deliberate step rather than a one-off.
STEP_MIN_USES = 2

EXIT_OK = 0
EXIT_NOT_MEASURED = 3
EXIT_USAGE = 64


class NotMeasured(Exception):
    """A refusal. The capture did not yield the measurement.

    Never downgraded to a default. Raised, surfaced, exit 3 — the caller
    widens the capture rather than inventing the value.
    """


# ── primitives (recovered verbatim from the deleted walker) ──────────────────
def px(v):
    if not v:
        return None
    m = re.match(r"^(-?[\d.]+)px$", str(v).strip())
    return float(m.group(1)) if m else None


def rgb_to_hex(v):
    if not v:
        return None
    m = re.match(r"rgba?\(([^)]+)\)", str(v))
    if not m:
        return None
    parts = [p.strip() for p in m.group(1).replace("/", " ").split(",")]
    if len(parts) < 3:
        return None
    try:
        r, g, b = (int(float(parts[i])) for i in range(3))
    except ValueError:
        return None
    if len(parts) >= 4:
        try:
            if float(parts[3]) < 0.9:
                return None  # translucent: not a role colour
        except ValueError:
            pass
    return f"#{r:02x}{g:02x}{b:02x}"


def _srgb(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(hexc):
    h = hexc.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _srgb(r) + 0.7152 * _srgb(g) + 0.0722 * _srgb(b)


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def pad_parts(v):
    """'96px 24px' -> (top/bottom, left/right) in px."""
    if not v:
        return None, None
    vals = [px(x) for x in str(v).split()]
    vals = [x for x in vals if x is not None]
    if not vals:
        return None, None
    if len(vals) == 1:
        return vals[0], vals[0]
    if len(vals) == 2:
        return vals[0], vals[1]
    if len(vals) == 4:
        return vals[0], vals[1]
    return vals[0], vals[-1]


def _ranked(counter: Counter) -> list[tuple[Any, int]]:
    """most_common with an explicit, total tie-break.

    `Counter.most_common` breaks ties by insertion order, which is stable for
    one process but couples the output to page iteration order. Determinism is
    a stated requirement of this command, so ties break on the value itself.
    """
    return sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0])))


def _distribution(counter: Counter) -> dict[str, int]:
    """A full measured distribution, ordered, as JSON-safe keys.

    Emitted so ratification can see what was silently picked over. The walker
    took `most_common(1)` for `rhythm.section_py_px` and `most_common(8)` for
    `type_system.heading_sizes_px`; both choices were overridden by hand in the
    ratified file (census §3.2, §2). The distribution makes the override
    visible rather than requiring an archaeologist.
    """
    return {str(k): n for k, n in _ranked(counter)}


# ── corpus ───────────────────────────────────────────────────────────────────
def load_corpus(corpus_dir: Path) -> dict[str, Any]:
    """Read `index.json` + every page's `extraction.json`.

    Pages are sorted by slug, not taken in index order: two corpora holding the
    same pages must compile to the same bytes.
    """
    index_path = corpus_dir / "index.json"
    if not index_path.exists():
        raise NotMeasured(
            f"no capture corpus at {corpus_dir}: {index_path} is missing. "
            "Run scripts/quality/capture-benchmark-pages.js first."
        )
    index = json.loads(index_path.read_text(encoding="utf-8"))
    pages = sorted((p for p in index if p.get("ok")),
                   key=lambda p: str(p.get("slug")))
    if not pages:
        raise NotMeasured(
            f"no successful captures in {index_path}: "
            f"{len(index)} page(s) recorded, 0 with ok=true."
        )

    dom: list[dict] = []
    text: list[dict] = []
    fonts: Counter = Counter()
    motion_profiles: list[dict] = []
    for p in pages:
        slug = p["slug"]
        d = json.loads((corpus_dir / slug / "extraction.json").read_text(
            encoding="utf-8"))
        for el in d.get("renderedDOM", []):
            el["_page"] = slug
            dom.append(el)
        for t in d.get("textContent", []):
            t["_page"] = slug
            text.append(t)
        for f in (d.get("assets") or {}).get("fonts") or []:
            name = f if isinstance(f, str) else (f.get("family") or f.get("name"))
            if name:
                fonts[name] += 1
        # The animation profile is `analyzeAnimationEvidence()`'s output, which
        # the capture step writes. See `motion_block` for why it is read rather
        # than re-derived.
        prof = (d.get("animations") or {}).get("profile")
        if isinstance(prof, dict) and prof.get("intensity"):
            motion_profiles.append({"page": slug, **prof})

    return {"pages": pages, "dom": dom, "text": text, "fonts": fonts,
            "motion_profiles": motion_profiles}


# ── palette ──────────────────────────────────────────────────────────────────
def palette_block(dom, text, host, tenant_accent):
    prov: dict[str, str] = {}
    dist: dict[str, Any] = {}
    unmeasured: list[dict] = []

    bgs, fgs = Counter(), Counter()
    for el in dom:
        s = el.get("styles") or {}
        r = el.get("rect") or {}
        area = (r.get("width") or 0) * (r.get("height") or 0)
        bg = rgb_to_hex(s.get("backgroundColor"))
        if bg and area > 0:
            bgs[bg] += 1
    for t in text:
        fg = rgb_to_hex((t.get("styles") or {}).get("color"))
        if fg:
            fgs[fg] += 1

    if not bgs or not fgs:
        raise NotMeasured(
            "palette unmeasurable: "
            f"{len(bgs)} opaque background colour(s) and {len(fgs)} text "
            "colour(s) measured. Widen the capture."
        )

    bg_primary = _ranked(bgs)[0][0]
    prov["bg_primary"] = (
        f"{host} most common opaque background, {bgs[bg_primary]} elements")

    # text roles: highest-count colours that clear AA on bg_primary
    readable = sorted(
        ((n, h) for h, n in fgs.items()
         if contrast(h, bg_primary) >= MIN_TEXT_CONTRAST),
        key=lambda nh: (-nh[0], nh[1]),
    )
    if not readable:
        # Refusal gate 2 (census §6.7). A benchmark whose measured type cannot
        # be read on its own measured ground is not a partial measurement, it
        # is a failed one.
        raise NotMeasured(
            f"no measured text colour clears {MIN_TEXT_CONTRAST}:1 on "
            f"{bg_primary}; {len(fgs)} text colour(s) measured. "
            "Widen the capture rather than darkening a measured colour."
        )
    text_primary = max(readable,
                       key=lambda nh: (contrast(nh[1], bg_primary), nh[0]))[1]
    prov["text_primary"] = (
        f"{host} text colour, {fgs[text_primary]} occurrences, "
        f"{contrast(text_primary, bg_primary):.2f}:1 on bg_primary")

    muted = [(n, h) for n, h in readable if h != text_primary]
    text_muted = muted[0][1] if muted else text_primary
    prov["text_muted"] = (
        f"{host} secondary text colour, {fgs[text_muted]} occurrences, "
        f"{contrast(text_muted, bg_primary):.2f}:1 on bg_primary")

    # surface: a background used on rounded elements (cards), which must carry
    # body text. A surface the body text cannot be read on is the white-on-white
    # failure, and `load_benchmark` does not check this pair.
    surface_c = Counter()
    for el in dom:
        s = el.get("styles") or {}
        raw = str(s.get("borderRadius") or "").split()
        rad = px(raw[0]) if raw else None
        if (rad or 0) >= 4:
            h = rgb_to_hex(s.get("backgroundColor"))
            if h:
                surface_c[h] += 1
    surface = None
    for hexc, n in _ranked(surface_c):
        if contrast(text_primary, hexc) >= MIN_TEXT_CONTRAST:
            surface = hexc
            prov["surface"] = (
                f"{host} background on radius>=4px elements, {n} elements, "
                f"{contrast(text_primary, hexc):.2f}:1 with text_primary")
            break

    # bg_secondary must satisfy BOTH constraints at once: readable body text AND
    # a visible step from bg_primary. Selecting on either alone reinstates the
    # invisible #010101 banding that MIN_BANDING exists to reject.
    bg_secondary = None
    for hexc, n in _ranked(bgs):
        if (hexc != bg_primary
                and contrast(hexc, bg_primary) >= MIN_BANDING
                and contrast(text_primary, hexc) >= MIN_TEXT_CONTRAST):
            bg_secondary = hexc
            prov["bg_secondary"] = (
                f"{host} banding background, {n} elements, "
                f"{contrast(hexc, bg_primary):.2f}:1 step from bg_primary, "
                f"{contrast(text_primary, hexc):.2f}:1 with text_primary")
            break
    if bg_secondary is None:
        # Refusal gate 1 (census §6.7). Recorded as a distribution so the
        # operator can see how close the capture came.
        near = [(h, round(contrast(h, bg_primary), 3))
                for h, _ in _ranked(bgs)[:10] if h != bg_primary]
        raise NotMeasured(
            "no captured background is both a visible step from "
            f"{bg_primary} (>={MIN_BANDING}:1) and readable with "
            f"{text_primary} (>={MIN_TEXT_CONTRAST}:1). Widen the capture "
            "rather than inventing a banding colour. "
            f"Measured steps from bg_primary: {near}"
        )

    if surface is None and contrast(text_primary, bg_secondary) >= MIN_TEXT_CONTRAST:
        surface = bg_secondary
        prov["surface"] = (
            f"no measured {host} card background carries text_primary; "
            "using measured bg_secondary")

    # border: measured borderColor on elements that actually draw a border.
    border_c = Counter()
    for el in dom:
        s = el.get("styles") or {}
        bw = px((str(s.get("borderWidth") or "").split() or [None])[0])
        raw_bc = str(s.get("borderColor") or "")
        h = rgb_to_hex(raw_bc.split(") ")[0] + ")") if "rgb" in raw_bc else None
        if bw and bw > 0 and h:
            border_c[h] += 1
    # The most-used measured border colour is often an emphasis outline (a neon
    # CTA ring): correct measurement, wrong role. Take the most-used measured
    # border that stays near bg_primary.
    separators = [(n, h) for h, n in border_c.items()
                  if contrast(h, bg_primary) <= MAX_SEPARATOR_CONTRAST]
    border = None
    if separators:
        n, border = max(separators, key=lambda nh: (nh[0], nh[1]))
        prov["border"] = (
            f"{host} measured borderColor on borderWidth>0, {n} elements, "
            f"{contrast(border, bg_primary):.2f}:1 from bg_primary "
            "(separator range)")
        emphasis = [h for h, _ in _ranked(border_c)
                    if contrast(h, bg_primary) > MAX_SEPARATOR_CONTRAST]
        if emphasis:
            prov["_border_emphasis_excluded"] = (
                f"{emphasis[0]} measured on {border_c[emphasis[0]]} elements is "
                "an emphasis outline, not a separator; excluded from the border "
                "role")
    else:
        unmeasured.append({
            "field": "palette_roles.border",
            "reason": "no measured border sits in separator range "
                      f"(<={MAX_SEPARATOR_CONTRAST}:1 from bg_primary)",
            "resolution": "widen the capture",
        })

    roles: dict[str, Any] = {
        "bg_primary": bg_primary,
        "bg_secondary": bg_secondary,
        "surface": surface,
        "text_primary": text_primary,
        "text_muted": text_muted,
    }
    if border:
        roles["border"] = border
    else:
        prov["border"] = "NOT_MEASURED — no measured border sits in separator range"

    # accent / on_accent are tenant identity by contract, never measured from a
    # reference (census §6.5). Declared or absent.
    if tenant_accent:
        white, black = contrast("#ffffff", tenant_accent), contrast("#000000", tenant_accent)
        on_accent = "#ffffff" if white >= black else "#000000"
        roles["accent"] = tenant_accent
        roles["on_accent"] = on_accent
        prov["accent"] = (
            f"DECLARED tenant identity {tenant_accent} via --tenant-accent — "
            "NOT measured from the reference")
        prov["on_accent"] = (
            f"derived for {contrast(on_accent, tenant_accent):.2f}:1 on the "
            "declared tenant accent")
    else:
        for field in ("palette_roles.accent", "palette_roles.on_accent"):
            unmeasured.append({
                "field": field,
                "reason": "tenant identity by contract; not measurable from a "
                          "reference and must not be",
                "resolution": "pass --tenant-accent, or declare at ratification",
            })

    unmeasured.append({
        "field": "palette_roles.surface_inverse",
        "reason": "no extractor in this repo identifies a deliberately-dark "
                  "section ground",
        "resolution": "declare at ratification",
    })

    dist["backgrounds"] = _distribution(bgs)
    dist["text_colours"] = _distribution(fgs)
    dist["rounded_element_backgrounds"] = _distribution(surface_c)
    dist["border_colours"] = _distribution(border_c)

    roles["_source"] = prov
    return roles, {"max_unique": len(bgs) + len(fgs)}, dist, unmeasured


# ── type ─────────────────────────────────────────────────────────────────────
def type_blocks(text, host):
    head_sizes, body_sizes = Counter(), Counter()
    head_w, body_w = Counter(), Counter()
    for t in text:
        s = t.get("styles") or {}
        fs, fw = px(s.get("fontSize")), s.get("fontWeight")
        if fs is None:
            continue
        if t.get("isHeading"):
            head_sizes[fs] += 1
            if fw:
                head_w[int(float(fw))] += 1
        else:
            body_sizes[fs] += 1
            if fw:
                body_w[int(float(fw))] += 1

    unmeasured: list[dict] = []
    base_px = int(_ranked(body_sizes)[0][0]) if body_sizes else None
    if base_px is None:
        unmeasured.append({
            "field": "type_scale.base_px",
            "reason": "no non-heading text node carried a fontSize",
            "resolution": "widen the capture",
        })
    ladder = sorted({s for s in list(head_sizes) + list(body_sizes) if s >= 10})

    # The scale ratio is a property of the HEADING ladder. Measuring it across
    # every adjacent size drags in the 12/13/14/15/16 body cluster and reports
    # ~1.12 for a page whose headings actually step 16->22->32->52->72.
    head_ladder = sorted({s for s, n in head_sizes.items()
                          if n >= STEP_MIN_USES and base_px and s >= base_px})
    ratios = [b / a for a, b in zip(head_ladder, head_ladder[1:])
              if a > 0 and 1.05 < b / a < 2.2]
    ratio = round(sorted(ratios)[len(ratios) // 2], 3) if ratios else None
    if ratio is None:
        unmeasured.append({
            "field": "type_scale.ratio",
            "reason": f"no adjacent heading step in {head_ladder} fell in "
                      "(1.05, 2.2)",
            "resolution": "widen the capture",
        })

    scale = {"ratio": ratio, "base_px": base_px,
             "heading_weight": _ranked(head_w)[0][0] if head_w else None,
             "body_weight": _ranked(body_w)[0][0] if body_w else None}
    for key in ("heading_weight", "body_weight"):
        if scale[key] is None:
            unmeasured.append({
                "field": f"type_scale.{key}",
                "reason": "no measured fontWeight on that text class",
                "resolution": "widen the capture",
            })

    # heading_sizes_px carries EVERY measured heading size, not most_common(8).
    # The walker's trim is what hid the 165px H1 outlier that was then dropped
    # by hand (census §2); the distribution beside it makes the judgement
    # available to ratification instead of pre-empting it.
    system = {
        "weights_used": sorted({int(w) for w in list(head_w) + list(body_w)}),
        "scale_px": [int(x) for x in ladder],
        "heading_sizes_px": sorted(int(s) for s in head_sizes),
        "_source": {
            "heading_sizes_px": (
                f"every distinct heading fontSize measured on {host}; see "
                "_distributions.heading_sizes_px for occurrence counts. No "
                "outlier is excluded here — exclusion is a ratification act."),
        },
    }
    dist = {"heading_sizes_px": _distribution(head_sizes),
            "body_sizes_px": _distribution(body_sizes),
            "heading_weights": _distribution(head_w),
            "body_weights": _distribution(body_w)}
    return scale, system, dist, unmeasured


# ── rhythm / radii / shadow ──────────────────────────────────────────────────
def rhythm_block(dom, host):
    sec_py, card_pad, gaps = Counter(), Counter(), Counter()
    for el in dom:
        s = el.get("styles") or {}
        r = el.get("rect") or {}
        tb, _lr = pad_parts(s.get("padding"))
        w = r.get("width") or 0
        if tb and tb >= 24 and w >= 1000:
            sec_py[int(tb)] += 1
        raw = str(s.get("borderRadius") or "").split()
        radius = px(raw[0]) if raw else None
        if tb and radius and radius >= 4 and 100 <= w < 1000:
            card_pad[int(tb)] += 1
        raw_gap = str(s.get("gap") or "").split()
        g = px(raw_gap[0]) if raw_gap else None
        if g and g >= 4:
            gaps[int(g)] += 1

    unmeasured: list[dict] = []
    section_py = _ranked(sec_py)[0][0] if sec_py else None
    card_p = _ranked(card_pad)[0][0] if card_pad else None
    block_gap = _ranked(gaps)[0][0] if gaps else None

    # The grid unit is the largest conventional unit that most measured
    # spacings are multiples of. A GCD over every observed value collapses to
    # 1-2 the moment one odd pixel appears, reporting a grid no designer used.
    spacings = [int(v) for v in list(sec_py) + list(card_pad) + list(gaps) if v]
    grid = None
    if spacings:
        for unit in (8, 4, 2):
            if sum(1 for v in spacings if v % unit == 0) / len(spacings) >= 0.75:
                grid = unit
                break

    rhythm = {"section_py_px": section_py, "block_gap_px": block_gap,
              "card_pad_px": card_p, "grid_px": grid}
    for key, why in (("section_py_px", "no element with padding>=24px and "
                                       "width>=1000px"),
                     ("block_gap_px", "no element with gap>=4px"),
                     ("card_pad_px", "no rounded element of width 100-1000px "
                                     "with padding"),
                     ("grid_px", "no conventional unit divides >=75% of "
                                 "measured spacings")):
        if rhythm[key] is None:
            unmeasured.append({"field": f"rhythm.{key}", "reason": why,
                               "resolution": "widen the capture"})

    ranked_sec = _ranked(sec_py)
    runner_up = ranked_sec[1] if len(ranked_sec) > 1 else None
    rhythm["_source"] = {
        "section_py_px": (
            f"modal full-width block padding on {host}: {section_py}px on "
            f"{sec_py[section_py] if section_py else 0} blocks"
            + (f"; runner-up {runner_up[0]}px on {runner_up[1]}. The modal "
               "value can be hero-specific top padding rather than the section "
               "default — see _distributions.section_py_px and decide at "
               "ratification." if runner_up else ".")),
    }
    dist = {"section_py_px": _distribution(sec_py),
            "card_pad_px": _distribution(card_pad),
            "block_gap_px": _distribution(gaps)}
    return rhythm, dist, unmeasured


def radii_shadow_blocks(dom, host):
    card_radii, btn_radii, shadow_layers = Counter(), Counter(), Counter()
    for el in dom:
        s = el.get("styles") or {}
        r = el.get("rect") or {}
        raw = str(s.get("borderRadius") or "").split()
        rad = px(raw[0]) if raw else None
        w, h = r.get("width") or 0, r.get("height") or 0
        if rad and rad > 0:
            if 100 <= w < 1000 and h > 80:
                card_radii[int(rad)] += 1
            elif 60 <= w < 400 and 28 <= h <= 72:
                btn_radii[int(rad)] += 1
        sh = s.get("boxShadow")
        if sh and sh != "none":
            shadow_layers[sh.count("rgb")] += 1

    card = {"radius_px": [r for r, _ in _ranked(card_radii)[:3]]}
    cta = {"radius_px": [r for r, _ in _ranked(btn_radii)[:3]]}
    shadow = {
        "max_layers": max(shadow_layers) if shadow_layers else 0,
        "observation": (
            f"{sum(shadow_layers.values())} shadowed elements measured on "
            f"{host}; layer counts {_distribution(shadow_layers)}"),
    }
    dist = {"card_radius_px": _distribution(card_radii),
            "cta_radius_px": _distribution(btn_radii),
            "shadow_layers": _distribution(shadow_layers)}
    return card, cta, shadow, dist


def font_block(text, corpus_fonts, host):
    """Emit `measured_families` only. `families` is a ratification act.

    Measurement yields the reference's proprietary face — Circular, Capsule
    Sans — which no build can serve. Naming a servable substitute is an
    operator decision, recorded as such in `902e166b`. Emitting a measured
    proprietary name as `families` produces a site declaring a typeface it
    never loads.
    """
    fams = Counter(corpus_fonts)
    for t in text:
        fam = (t.get("styles") or {}).get("fontFamily")
        if fam:
            fams[fam.split(",")[0].strip().strip('"\'')] += 1
    block = {
        "measured_families": [f for f, _ in _ranked(fams)[:3]],
        "_source": {
            "measured_families": (
                f"most-used first font-family on {host}; occurrence counts in "
                "_distributions.font_families"),
        },
    }
    unmeasured = [{
        "field": "font_system.families",
        "reason": "measurement yields the reference's proprietary face; naming "
                  "a servable face is an operator act",
        "resolution": "declare at ratification, or resolve measured_families "
                      "through scripts/lib/font_match.py and stamp the "
                      "substitution",
    }]
    return block, {"font_families": _distribution(fams)}, unmeasured


def motion_block(profiles):
    """Read the animation detector's verdict; never re-derive it.

    CORRECTION to census §6.6, measured 2026-08-17:
    `grep -n analyzeAnimationEvidence scripts/quality/lib/extract-reference.js`
    → 0 hits. `extract-reference.js:1071` sets `animations.evidence =
    rawAnimationEvidence`, i.e. `extractAnimationData()`'s RAW output — not the
    scored `{level, score, confidence}` the census expected to find there. The
    only caller of `analyzeAnimationEvidence()` outside the detector is
    `scripts/quality/url-to-preset.js:264`.

    The wire is therefore made in the capture step: `capture-benchmark-pages.js`
    calls `analyzeAnimationEvidence()` and writes its result to
    `animations.profile`. This function reads `intensity.{level,score,
    confidence}` out of that. The walker's CSS-duration histogram is NOT
    restored — it is a second, disagreeing measurement of the same property.

    `duration_ms` is absent: `analyzeAnimationEvidence()` returns no duration
    (its return shape is `{libraries, intensity, engine, cssAnimations,
    scrollAnimations, ...}`, `animation-detector.js:639`).
    """
    if not profiles:
        return None, [{
            "field": "motion.intensity",
            "reason": "no page in the corpus carried animations.profile; the "
                      "capture step did not run the animation detector",
            "resolution": "re-capture with scripts/quality/"
                          "capture-benchmark-pages.js",
        }, {
            "field": "motion.duration_ms",
            "reason": "analyzeAnimationEvidence() returns no duration",
            "resolution": "declare at ratification",
        }]

    # Highest-scoring page wins: motion intensity is a property of the site's
    # richest expression, and a corpus of five pages where one is a Lottie-and-
    # GSAP home page and four are text is an expressive site.
    best = max(profiles, key=lambda p: (
        float((p.get("intensity") or {}).get("score") or 0), str(p.get("page"))))
    inten = best.get("intensity") or {}
    libs = sorted({str(l.get("name")) for l in (best.get("libraries") or [])
                   if l.get("name")})
    block = {
        "intensity": inten.get("level"),
        "_source": {
            "intensity": (
                f"animation-detector.analyzeAnimationEvidence() scored "
                f"{inten.get('score')} '{inten.get('level')}' at "
                f"{inten.get('confidence')} confidence on page "
                f"'{best.get('page')}'; engine {best.get('engine')}; "
                f"libraries {libs or 'none'}"),
        },
        "evidence": {
            "score": inten.get("score"),
            "confidence": inten.get("confidence"),
            "engine": best.get("engine"),
            "libraries": libs,
            "scored_page": best.get("page"),
            "pages_profiled": len(profiles),
        },
    }
    unmeasured = [{
        "field": "motion.duration_ms",
        "reason": "analyzeAnimationEvidence() returns no duration; the "
                  "walker's CSS-duration histogram is a different, disagreeing "
                  "measurement and is not restored",
        "resolution": "declare at ratification",
    }]
    return block, unmeasured


# ── the command ──────────────────────────────────────────────────────────────
def commission(
    corpus_dir: Path,
    *,
    market: str,
    captured_at: str,
    reference_host: str | None = None,
    contributions: dict[str, str] | None = None,
    tenant_accent: str | None = None,
    corpus_ref: str | None = None,
) -> dict[str, Any]:
    """Corpus in, benchmark dict out. Raises `NotMeasured` on a refusal.

    `captured_at` is a required argument and never `datetime.now()`: the same
    corpus must compile to the same bytes on any day.
    """
    c = load_corpus(corpus_dir)
    pages, dom, text = c["pages"], c["dom"], c["text"]
    host = reference_host or _host_of(pages[0].get("url") or "")

    roles, palette, pal_dist, unmeasured = palette_block(
        dom, text, host, tenant_accent)
    scale, system, type_dist, u2 = type_blocks(text, host)
    rhythm, rhy_dist, u3 = rhythm_block(dom, host)
    card, cta, shadow, rad_dist = radii_shadow_blocks(dom, host)
    fonts, font_dist, u4 = font_block(text, c["fonts"], host)
    motion, u5 = motion_block(c["motion_profiles"])
    unmeasured = unmeasured + u2 + u3 + u4 + u5

    unmeasured.append({
        "field": "density",
        "reason": "no code path in this repo emits \"spacious\"; the walker's "
                  "comfortable/compact is a two-value guess over card_pad_px, "
                  "not a measurement",
        "resolution": "declare at ratification; the evidence is "
                      "_distributions.card_pad_px",
    })

    benchmark: dict[str, Any] = {
        "_meta": {
            "ratified": False,
            "market": market,
            "captured_from": [p["url"] for p in pages],
            "captured_at": captured_at,
            "method": "computed_style",
            "patterns_only": True,
            "note": (
                "PATTERNS ONLY. No markup, copy, asset, SVG or shader is lifted "
                "from the reference. Every number below is a count or a "
                "distribution over measured computed styles."),
            "ratification_note": (
                "ratified: false. Fields in _unmeasured are absent, not "
                "defaulted — four of them are required by "
                "design_system.load_benchmark, so this file does not load "
                "until an operator declares them. That is the gate, not a bug."),
            "tool": {"name": TOOL, "version": TOOL_VERSION,
                     "extractor": "scripts/quality/lib/extract-reference.js",
                     "capture_step": "scripts/quality/capture-benchmark-pages.js"},
            "reference_host": host,
            "corpus": corpus_ref or str(corpus_dir),
            "page_selection_rationale": {p["slug"]: p.get("why") for p in pages},
            "elements_measured": {
                "definition": (
                    "renderedDOM_elements and text_nodes are summed across "
                    "pages and counted separately; neither includes the other. "
                    "renderedDOM is capped per page by MAX_DOM_ELEMENTS in "
                    "extract-reference.js, so renderedDOM_elements <= pages * "
                    "per_page_dom_cap by construction."),
                "pages": len(pages),
                "renderedDOM_elements": len(dom),
                "text_nodes": len(text),
                "per_page_dom_cap": PER_PAGE_DOM_CAP,
            },
            "contributions": dict(sorted((contributions or {}).items())),
        },
        "palette_roles": roles,
        "type_scale": scale,
        "type_system": system,
        "rhythm": rhythm,
        "card_system": card,
        "cta_buttons": cta,
        "shadow_system": shadow,
        "palette": palette,
        "font_system": fonts,
    }
    if motion:
        benchmark["motion"] = motion
    benchmark["_unmeasured"] = sorted(unmeasured, key=lambda u: u["field"])
    benchmark["_distributions"] = {
        **pal_dist, **type_dist, **rhy_dist, **rad_dist, **font_dist}

    measured = _count_measured(benchmark)
    if measured == 0:
        raise NotMeasured(
            "zero measured fields; refusing to write a benchmark that measures "
            "nothing.")
    benchmark["_meta"]["measured_field_count"] = measured
    return benchmark


#: Every scalar the benchmark claims to have measured. `_count_measured`
#: backs the "a benchmark with zero measured fields refuses to write" rule.
_MEASURED_PATHS = (
    ("palette_roles", "bg_primary"), ("palette_roles", "bg_secondary"),
    ("palette_roles", "surface"), ("palette_roles", "text_primary"),
    ("palette_roles", "text_muted"), ("palette_roles", "border"),
    ("type_scale", "ratio"), ("type_scale", "base_px"),
    ("type_scale", "heading_weight"), ("type_scale", "body_weight"),
    ("rhythm", "section_py_px"), ("rhythm", "block_gap_px"),
    ("rhythm", "card_pad_px"), ("rhythm", "grid_px"),
    ("palette", "max_unique"),
)


def _count_measured(benchmark: dict[str, Any]) -> int:
    n = 0
    for block, key in _MEASURED_PATHS:
        if (benchmark.get(block) or {}).get(key) is not None:
            n += 1
    for block, key in (("type_system", "weights_used"),
                       ("type_system", "scale_px"),
                       ("card_system", "radius_px"),
                       ("cta_buttons", "radius_px"),
                       ("font_system", "measured_families")):
        if (benchmark.get(block) or {}).get(key):
            n += 1
    if (benchmark.get("motion") or {}).get("intensity"):
        n += 1
    return n


def _host_of(url: str) -> str:
    m = re.match(r"^[a-z]+://([^/]+)", url.strip(), re.I)
    return (m.group(1) if m else url.strip()) or "reference"


def _contribution(arg: str) -> tuple[str, str]:
    if "=" not in arg:
        raise argparse.ArgumentTypeError(
            f"--contribution takes block=url, got {arg!r}")
    block, url = arg.split("=", 1)
    return block.strip(), url.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog=TOOL,
        description="Compile a persisted capture corpus into an unratified "
                    "market benchmark.")
    ap.add_argument("corpus", type=Path,
                    help="capture corpus directory (index.json + "
                         "<slug>/extraction.json)")
    ap.add_argument("--market", required=True, help="market slug")
    ap.add_argument("--captured-at", required=True,
                    help="YYYY-MM-DD. Required, never derived from the clock: "
                         "the same corpus must compile to the same bytes.")
    ap.add_argument("--out", type=Path,
                    help="output path (default benchmarks/<market>.json)")
    ap.add_argument("--reference-host",
                    help="host used in provenance strings (default: derived "
                         "from the first captured URL)")
    ap.add_argument("--tenant-accent",
                    help="declared tenant accent hex. Absent => accent and "
                         "on_accent are absent, not defaulted.")
    ap.add_argument("--contribution", action="append", type=_contribution,
                    default=[], metavar="BLOCK=URL",
                    help="records which reference contributed which block; "
                         "repeatable")
    ap.add_argument("--print", action="store_true",
                    help="also print the benchmark to stdout")
    args = ap.parse_args(argv)

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.captured_at):
        print(f"{TOOL}: --captured-at must be YYYY-MM-DD, got "
              f"{args.captured_at!r}", file=sys.stderr)
        return EXIT_USAGE
    if args.tenant_accent and not re.match(r"^#[0-9a-fA-F]{6}$",
                                           args.tenant_accent):
        print(f"{TOOL}: --tenant-accent must be #rrggbb, got "
              f"{args.tenant_accent!r}", file=sys.stderr)
        return EXIT_USAGE

    root = Path(__file__).resolve().parent.parent
    out = args.out or (root / "benchmarks" / f"{args.market}.json")
    corpus = args.corpus.resolve()
    try:
        corpus_ref = str(corpus.relative_to(root))
    except ValueError:
        corpus_ref = str(corpus)

    try:
        benchmark = commission(
            corpus,
            market=args.market,
            captured_at=args.captured_at,
            reference_host=args.reference_host,
            contributions=dict(args.contribution),
            tenant_accent=args.tenant_accent,
            corpus_ref=corpus_ref,
        )
    except NotMeasured as exc:
        print(f"NOT_MEASURED: {exc}", file=sys.stderr)
        print(f"{TOOL}: nothing written.", file=sys.stderr)
        return EXIT_NOT_MEASURED

    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(benchmark, indent=2, sort_keys=False) + "\n"
    out.write_text(payload, encoding="utf-8")
    meta = benchmark["_meta"]
    print(f"{TOOL}: wrote {out}")
    print(f"  market            {meta['market']}   ratified: "
          f"{meta['ratified']}")
    print(f"  measured fields   {meta['measured_field_count']}")
    print(f"  unmeasured        {len(benchmark['_unmeasured'])} "
          f"({', '.join(u['field'] for u in benchmark['_unmeasured'])})")
    print(f"  corpus            {meta['corpus']}")
    if args.print:
        print(payload)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Compile Robinhood captures into a market benchmark.

PATTERNS ONLY. Reads measured computed styles and emits distributions.
No markup, copy, asset, SVG or shader crosses this boundary — the output
carries numbers and role colours, each with a measured provenance string.

Every emitted value must be traceable to a count over captured elements.
Where a value cannot be measured it is left absent so that
`design_system.load_benchmark` rejects the file by name, rather than
being bridged with an invented default.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

RH = Path(sys.argv[1])
OUT = Path(sys.argv[2])

# Cape Crypto tenant identity, measured from capecrypto.com in the prior
# capture (see benchmarks/crypto-exchange.json palette_roles._source).
# Carried forward because it is tenant identity, not reference structure.
TENANT_ACCENT = "#004e89"


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


def srgb(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(hexc):
    h = hexc.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b)


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


# ── load every page ──────────────────────────────────────────────────────────
index = json.loads((RH / "index.json").read_text())
pages = [p for p in index if p.get("ok")]
if not pages:
    sys.exit("no successful captures")

dom, text, assets_fonts = [], [], Counter()
for p in pages:
    d = json.loads((RH / p["slug"] / "extraction.json").read_text())
    for el in d.get("renderedDOM", []):
        el["_page"] = p["slug"]
        dom.append(el)
    for t in d.get("textContent", []):
        t["_page"] = p["slug"]
        text.append(t)
    for f in d.get("assets", {}).get("fonts", []) or []:
        name = f if isinstance(f, str) else (f.get("family") or f.get("name"))
        if name:
            assets_fonts[name] += 1

prov = {}


# ── palette ──────────────────────────────────────────────────────────────────
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
    sys.exit("palette unmeasurable: no opaque backgrounds or text colours")

bg_primary = bgs.most_common(1)[0][0]
prov["bg_primary"] = f"robinhood most common opaque background, {bgs[bg_primary]} elements"

# bg_secondary: a banding surface must be VISIBLY distinct from bg_primary.
# A luminance epsilon is meaningless in the dark range (#000 vs #010101 passes
# it and renders as no banding at all), so require a real contrast step.
MIN_BANDING = 1.12
bg_secondary = None
for hexc, n in bgs.most_common(30):
    if hexc == bg_primary:
        continue
    if contrast(hexc, bg_primary) >= MIN_BANDING:
        bg_secondary = hexc
        prov["bg_secondary"] = (
            f"robinhood banding background, {n} elements, "
            f"{contrast(hexc, bg_primary):.2f}:1 step from bg_primary")
        break

# surface: a background used on rounded elements (cards). Deferred until
# text_primary is known — a surface the body text cannot be read on is the
# white-on-white failure, and `load_benchmark` does not check this pair.
surface_c = Counter()
for el in dom:
    s = el.get("styles") or {}
    if (px((s.get("borderRadius") or "").split()[0]) or 0) >= 4:
        h = rgb_to_hex(s.get("backgroundColor"))
        if h:
            surface_c[h] += 1

# text roles: highest-count colours that clear AA on bg_primary
readable = [(n, h) for h, n in fgs.items() if contrast(h, bg_primary) >= 4.5]
readable.sort(reverse=True)
if not readable:
    sys.exit(f"no measured text colour clears 4.5:1 on {bg_primary}")
text_primary = max(readable, key=lambda x: (contrast(x[1], bg_primary), x[0]))[1]
prov["text_primary"] = (
    f"robinhood text colour, {fgs[text_primary]} occurrences, "
    f"{contrast(text_primary, bg_primary):.2f}:1 on bg_primary")

muted = [(n, h) for n, h in readable if h != text_primary]
text_muted = muted[0][1] if muted else text_primary
prov["text_muted"] = (
    f"robinhood secondary text colour, {fgs[text_muted]} occurrences, "
    f"{contrast(text_muted, bg_primary):.2f}:1 on bg_primary")

# surface must carry body text. Take the most-used rounded-element background
# that text_primary actually clears AA on; otherwise there is no measured card
# surface and the key is left absent so load_benchmark names it.
surface = None
for hexc, n in surface_c.most_common(30):
    if contrast(text_primary, hexc) >= 4.5:
        surface = hexc
        prov["surface"] = (
            f"robinhood background on radius>=4px elements, {n} elements, "
            f"{contrast(text_primary, hexc):.2f}:1 with text_primary")
        break
if surface is None and contrast(text_primary, bg_secondary) >= 4.5:
    surface = bg_secondary
    prov["surface"] = ("no measured card background carries text_primary; "
                       "using measured bg_secondary")

# border: measured borderColor on elements that actually draw a border.
border_c = Counter()
for el in dom:
    s = el.get("styles") or {}
    bw = px((str(s.get("borderWidth") or "").split() or [None])[0])
    h = rgb_to_hex((str(s.get("borderColor") or "").split(") ")[0] + ")")
                   if "rgb" in str(s.get("borderColor") or "") else None)
    if bw and bw > 0 and h:
        border_c[h] += 1
# A `border` in this schema is a SEPARATOR — it sits close to its background.
# The most-used measured border colour on this reference is the neon CTA
# outline (#ccff00), which is an emphasis treatment: correct measurement,
# wrong role. Take the most-used measured border that stays near bg_primary.
MAX_SEPARATOR_CONTRAST = 4.5
separators = [(n, h) for h, n in border_c.items()
              if contrast(h, bg_primary) <= MAX_SEPARATOR_CONTRAST]
if separators:
    n, border = max(separators)
    prov["border"] = (
        f"robinhood measured borderColor on borderWidth>0, {n} elements, "
        f"{contrast(border, bg_primary):.2f}:1 from bg_primary (separator range)")
    emphasis = [h for h, _ in border_c.most_common()
                if contrast(h, bg_primary) > MAX_SEPARATOR_CONTRAST]
    if emphasis:
        prov["_border_emphasis_excluded"] = (
            f"{emphasis[0]} measured on {border_c[emphasis[0]]} elements is an "
            "emphasis outline, not a separator; excluded from the border role")
else:
    border = None
    prov["border"] = "NOT_MEASURED — no measured border sits in separator range"

on_accent = "#ffffff" if contrast("#ffffff", TENANT_ACCENT) >= contrast("#000000", TENANT_ACCENT) else "#000000"
prov["accent"] = "capecrypto.com tenant identity rgb(0,78,137) — NOT from reference"
prov["on_accent"] = f"chosen for {contrast(on_accent, TENANT_ACCENT):.2f}:1 on tenant accent"

# bg_secondary must satisfy BOTH constraints at once: readable body text AND a
# visible step from bg_primary. Re-selecting on text contrast alone reinstates
# the invisible #010101 banding that the MIN_BANDING check just rejected.
if bg_secondary is None or contrast(text_primary, bg_secondary) < 4.5:
    bg_secondary = None
    for hexc, n in bgs.most_common(30):
        if (hexc != bg_primary
                and contrast(text_primary, hexc) >= 4.5
                and contrast(hexc, bg_primary) >= MIN_BANDING):
            bg_secondary = hexc
            prov["bg_secondary"] = (
                f"robinhood banding background, {n} elements, "
                f"{contrast(hexc, bg_primary):.2f}:1 step from bg_primary, "
                f"{contrast(text_primary, hexc):.2f}:1 with text_primary")
            break
if bg_secondary is None:
    sys.exit(
        "NOT_MEASURED: no captured background is both a visible step from "
        f"{bg_primary} (>={MIN_BANDING}:1) and readable with {text_primary}. "
        "Widen the capture rather than inventing a banding colour.")

palette_roles = {
    "bg_primary": bg_primary, "bg_secondary": bg_secondary, "surface": surface,
    "text_primary": text_primary, "text_muted": text_muted,
    "accent": TENANT_ACCENT, "on_accent": on_accent, "border": border,
    "_source": prov,
}

# ── type ─────────────────────────────────────────────────────────────────────
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

base_px = int(body_sizes.most_common(1)[0][0]) if body_sizes else None
ladder = sorted({s for s in list(head_sizes) + list(body_sizes) if s >= 10})

# The scale ratio is a property of the HEADING ladder. Measuring it across every
# adjacent size drags in the 12/13/14/15/16 body cluster and reports ~1.12 for a
# page whose headings actually step 16->22->32->52->72. Use heading sizes that
# appear often enough to be a deliberate step, walking up from base_px.
STEP_MIN_USES = 2
head_ladder = sorted({s for s, n in head_sizes.items()
                      if n >= STEP_MIN_USES and base_px and s >= base_px})
ratios = [b / a for a, b in zip(head_ladder, head_ladder[1:])
          if a > 0 and 1.05 < b / a < 2.2]
ratio = round(sorted(ratios)[len(ratios) // 2], 3) if ratios else None
heading_weight = head_w.most_common(1)[0][0] if head_w else None
body_weight = body_w.most_common(1)[0][0] if body_w else None

# ── rhythm ───────────────────────────────────────────────────────────────────
sec_py, card_pad, gaps = Counter(), Counter(), Counter()
for el in dom:
    s = el.get("styles") or {}
    r = el.get("rect") or {}
    tb, _lr = pad_parts(s.get("padding"))
    w, h = r.get("width") or 0, r.get("height") or 0
    if tb and tb >= 24 and w >= 1000:
        sec_py[int(tb)] += 1
    radius = px((s.get("borderRadius") or "").split()[0] if s.get("borderRadius") else None)
    if tb and radius and radius >= 4 and 100 <= w < 1000:
        card_pad[int(tb)] += 1
    g = px((s.get("gap") or "").split()[0] if s.get("gap") else None)
    if g and g >= 4:
        gaps[int(g)] += 1

section_py = sec_py.most_common(1)[0][0] if sec_py else None
card_p = card_pad.most_common(1)[0][0] if card_pad else None
block_gap = gaps.most_common(1)[0][0] if gaps else None
# The grid unit is the largest of the conventional units that most measured
# spacings are multiples of. A GCD over every observed value collapses to 1-2
# the moment a single odd pixel appears, which reports a grid no designer used.
spacings = [int(v) for v in list(sec_py) + list(card_pad) + list(gaps) if v]
grid = None
if spacings:
    for unit in (8, 4, 2):
        if sum(1 for v in spacings if v % unit == 0) / len(spacings) >= 0.75:
            grid = unit
            break

# ── radii / shadow / motion ──────────────────────────────────────────────────
card_radii, btn_radii, shadow_layers = Counter(), Counter(), Counter()
for el in dom:
    s = el.get("styles") or {}
    r = el.get("rect") or {}
    rad = px((s.get("borderRadius") or "").split()[0] if s.get("borderRadius") else None)
    w, h = r.get("width") or 0, r.get("height") or 0
    if rad and rad > 0:
        if 100 <= w < 1000 and h > 80:
            card_radii[int(rad)] += 1
        elif 60 <= w < 400 and 28 <= h <= 72:
            btn_radii[int(rad)] += 1
    sh = s.get("boxShadow")
    if sh and sh != "none":
        shadow_layers[sh.count("rgb")] += 1

for t in text:
    s = t.get("styles") or {}
    fam = s.get("fontFamily")
    if fam:
        assets_fonts[fam.split(",")[0].strip().strip('"\'')] += 1

durations = Counter()
for el in dom:
    s = el.get("styles") or {}
    for field in ("transition", "animationDuration"):
        for m in re.finditer(r"([\d.]+)(m?s)", str(s.get(field) or "")):
            ms = float(m.group(1)) * (1 if m.group(2) == "ms" else 1000)
            if 50 <= ms <= 2000:
                durations[int(round(ms / 50) * 50)] += 1

benchmark = {
    "_meta": {
        "market": "consumer-crypto-exchange",
        "captured_from": [p["url"] for p in pages],
        "captured_at": "2026-08-13",
        "method": "computed_style",
        "patterns_only": True,
        "note": ("PATTERNS ONLY. No markup, copy, asset, SVG or shader is "
                 "lifted from the reference. Every number below is a count or "
                 "a distribution over measured computed styles."),
        "page_selection_rationale": {p["slug"]: p["why"] for p in pages},
        "elements_measured": len(dom),
        "text_nodes_measured": len(text),
        "contributions": {
            "type_system": "https://robinhood.com",
            "card_system": "https://robinhood.com",
            "shadow_system": "https://robinhood.com",
            "rhythm": "https://robinhood.com",
            "palette_roles": ("https://robinhood.com (structural bg/surface/"
                              "border/text) + capecrypto.com (accent, tenant "
                              "identity)"),
        },
    },
    "palette_roles": palette_roles,
    "type_scale": {"ratio": ratio, "base_px": base_px,
                   "heading_weight": heading_weight, "body_weight": body_weight},
    "type_system": {
        "weights_used": sorted({int(w) for w in list(head_w) + list(body_w)}),
        "scale_px": [int(x) for x in ladder],
        "heading_sizes_px": [int(s) for s, _ in head_sizes.most_common(8)],
    },
    "rhythm": {"section_py_px": section_py, "block_gap_px": block_gap,
               "card_pad_px": card_p, "grid_px": grid},
    "card_system": {"radius_px": [r for r, _ in card_radii.most_common(3)]},
    "cta_buttons": {"radius_px": [r for r, _ in btn_radii.most_common(3)]},
    "shadow_system": {"max_layers": max(shadow_layers) if shadow_layers else 0,
                      "observation": f"{sum(shadow_layers.values())} shadowed elements measured"},
    "palette": {"max_unique": len(bgs) + len(fgs)},
    "font_system": {"families": [f for f, _ in assets_fonts.most_common(3)]},
    "density": "comfortable" if (card_p or 0) >= 24 else "compact",
    "motion": {"intensity": "subtle" if not durations else
               ("subtle" if max(durations, key=durations.get) <= 400 else "expressive"),
               "duration_ms": max(durations, key=durations.get) if durations else None},
}

OUT.write_text(json.dumps(benchmark, indent=2) + "\n", encoding="utf-8")
print(json.dumps(benchmark, indent=2))

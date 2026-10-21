# Preset: THURIS (tenant)

Tenant: THURIS — botanical fragrance house (Aweku Laboratories (Pty) Ltd, South Africa).
Lead market: UAE. Target: Shopify (headless, Vercel front end).

Sequence authority: tenant

> **Tenant preset.** Values come from the operator, not from a crawl — THURIS is a
> greenfield brand (`source_platform: none`). Authority, in order:
> `intake/thuris/RESOLVED-DECISIONS.md` (operator answers 2026-10-21) >
> `THURIS_Brand_CI_Guide_v1.0.pdf` > the planning-agent handoff YAML.
> The page copy is `intake/thuris/THURIS-launch-copy.md`, delivered to the
> build as an operator-authored capture (`intake/thuris/capture-bundle/`).

---

## Default Section Sequence

Mirrors the operator-authored source page. The harvest is the spine; this block
only governs gap-fill, and its job here is to stop the luxury-premium registry
from demanding VIDEO, GALLERY, TESTIMONIALS and NEWSLETTER, none of which a
pre-launch brand with no media, no proof and no email module can fill.

```
1. HERO                 | centered               (dark — Founding Collection)
2. ABOUT                | editorial-split        (light — the house / thesis)
3. PRODUCT-SHOWCASE     | featured-3             (dark — three essences + complete collection)
4. ABOUT                | editorial-split        (dark — Frankincense)
5. ABOUT                | editorial-split        (light — Neroli)
6. ABOUT                | editorial-split        (dark — Rose Geranium)
7. ABOUT                | editorial-split        (dark — The Ritual of Scent)
8. FEATURES             | spec-table             (light — provenance: species · origin)
9. ABOUT                | editorial-split        (light — the Founding Release)
10. HOW-IT-WORKS        | numbered-steps         (light — how pre-order works)
11. FAQ                 | accordion              (light)
12. CTA                 | dark-band              (dark — final reservation)
```

Held, not sequenced: **the vessel section** (bottle / closure / concealed dropper) —
`[HOLD: final supplier specification approved]`.

---

## Tenant Design Overrides

Operator decision 2026-10-21: THURIS's palette, type sizes, spacing, radius and
fonts override the `luxury-botanical-oils` benchmark (measured from Amouage +
Aesop: cream `#f7f4ef` ground, `#000000` text, 14px base, 100px sections). The
measured type ratio (1.143) and heading weight (400) are kept. Read by
`design_system.parse_tenant_design_overrides`; every value is recorded in
`site-spec.style.tenant_overrides` against the measured value it replaced.

```json
{
  "palette_roles": {
    "bg_primary": "#09070B", "bg_secondary": "#120D14", "surface": "#18111A",
    "text_primary": "#F4EEE4", "text_muted": "#A69A91", "border": "#312832",
    "accent": "#C1A36B", "on_accent": "#09070B", "surface_inverse": "#F4F0E8"
  },
  "palette_light": {
    "bg_primary": "#F4F0E8", "bg_secondary": "#E7DED2", "surface": "#FBF8F2",
    "text_primary": "#241F1B", "text_muted": "#736A61", "border": "#CFC5B8",
    "accent": "#241F1B", "on_accent": "#F4F0E8"
  },
  "type_scale": {"base_px": 17},
  "rhythm": {"section_py_px": 140, "block_gap_px": 64, "card_pad_px": 40},
  "border_radius": {"button": "0px", "card": "0px"},
  "fonts": {"heading": "Bodoni Moda", "body": "Inter"}
}
```

---

## Style Configuration

Two-mode system (operator replacement for CI Guide §04). **Dark Ceremonial is the
base** on a commerce page (60–70% of the composition); **Light Editorial** sections
opt in per section via `data-tone="light"` in the source.

```yaml
color_temperature: warm-nocturnal
palette:
  # Dark Ceremonial — base
  bg_primary: "#09070B"        # THURIS Black — never #000000
  bg_secondary: "#120D14"      # Nocturne
  surface: "#18111A"           # Black Violet
  text_primary: "#F4EEE4"      # Warm Ivory
  text_heading: "#F4EEE4"
  text_muted: "#A69A91"        # Ash
  border: "#312832"            # Violet Charcoal
  accent: "#C1A36B"            # Champagne Gold — logo detail, product names, rules, primary CTA
  on_accent: "#09070B"
  accent_hover: "#9A7748"      # Antique Brass
  accent_secondary: "#9A7748"  # Antique Brass
  accent_tertiary: "#291723"   # Smoked Violet — product world only
  surface_inverse: "#F4F0E8"   # Bone — the light editorial ground
light_editorial:
  bg_primary: "#F4F0E8"        # Bone
  bg_secondary: "#E7DED2"      # Parchment
  surface: "#FBF8F2"           # Ivory
  text_primary: "#241F1B"      # Charcoal
  text_muted: "#736A61"        # Stone
  border: "#CFC5B8"            # Warm Hairline
  accent: "#241F1B"            # Charcoal CTA fill on Bone (Brass on Bone is 3.62:1 — fails AA)
  on_accent: "#F4F0E8"         # Bone label — 15.4:1
  detail: "#9A7748"            # Antique Brass — hairlines, selected states, micro-detail only
rare_highlight: "#5A3145"      # Resin Plum — reflected colour only, never a fill

typography:
  pairing: didone-display + neo-grotesk-ui
  heading_font: Bodoni Moda
  heading_weight: 400          # 500 max — never bold Didone
  heading_weights: 400, 500    # fetched faces (RESOLVED-DECISIONS: Bodoni Moda 400/500)
  body_font: Inter
  body_weight: 400
  body_weights: 400, 500, 600  # fetched faces (RESOLVED-DECISIONS: Inter 400/500/600)
  scale_ratio: 1.333
  weight_distribution: hierarchy by size and space, not weight
  eyebrow: Inter 500, uppercase, letter-spacing 0.18–0.28em
  body_size: 16–18px, line-height 1.45–1.65
  nav_button_size: 11–13px, tracked

whitespace: airy
section_padding: 120–160px desktop / 56–72px mobile
internal_gap: generous
grid: 12-col desktop / 4-col mobile, max content width 1320px

border_radius: 0–2px
buttons: 48–52px tall, square; dark Champagne-filled on dark, Charcoal or Brass on Bone
cards: square, 1px hairline border, no shadow
inputs: square, 1px hairline

animation_engine: framer-motion
animation_intensity: subtle
entrance: fade + rise (opacity, small vertical translate)
hover: hairline / colour shift only — no lift, no scale
timing: 450–700ms, weighted ease-out; no spring, no bounce
smooth_scroll: false
section_overrides:
gsap_plugins:

visual_density: airy
image_treatment: light sections — natural directional light, limestone/travertine/plaster;
  dark sections — low-key cinematic, obsidian/smoked violet, champagne metal.
  No media supplied yet; every image slot stays empty and is recorded.
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: THURIS Black #09070B / Warm Ivory #F4EEE4 / Champagne #C1A36B · light: Bone #F4F0E8 / Charcoal #241F1B / Brass #9A7748
Type: Bodoni Moda 400 display + Inter 400/500 UI, ratio 1.333
Space: airy, 120–160px sections, 1320px max
Radius: 0–2px, 1px hairlines
Motion: subtle/framer-motion — entrance:fade-rise hover:hairline timing:450–700ms | none
Density: airy | Images: empty slots (none supplied)
═══════════════════════
```

---

## Content Direction

**Tone:** measured, sensory, precise, provenance-led. Short controlled sentences; no
exclamation marks; never call the product luxurious, premium or exclusive — show it.
**Hero copy pattern:** release name as display line, one-line idea, one factual line on the cap.
**CTA language:** "Reserve the Founding Collection" / "Reserve [essence]". Never "buy now".

---

## Photography / Visual Direction

- Light sections: warm directional natural light, hard-edged shadow, limestone, plaster,
  travertine, uncoated paper, brushed brass.
- Dark sections: low-key studio, rim light on glass and metal, obsidian and smoked violet.
- Never: spa, wellness, diffusers, towels, palms, faux-Arabic ornament, domes, desert
  cliché, water splashes, floating ingredients, fake seals, review stars.

---

## Known Pitfalls

- **Light sections on a dark base.** The token chain historically emitted one palette
  plus a single `--surface-inverse`; a Bone section inheriting Warm Ivory text renders
  invisible. Light sections need the `light_editorial` set re-declared, scoped.
- **Gold is not a background.** No metallic gradients, no large gold fields.
- **Logo is a temporary raster** (CI Guide crops, JPEG on bone, no transparency) until
  production vectors are approved. Do not re-typeset THURIS in Bodoni Moda as a stand-in.
- **Prohibited claims** — purity, therapeutic, origin beyond the declared country, usage.
  Every `[HOLD]` in the copy stays unrendered until its fact is supplied.

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-10-21 | Created from operator decisions + CI Guide v1.0 + handoff | thuris |

# Preset: Ecommerce

Industries: general ecommerce, online retail, product stores, demo stores.

---

## Default Section Sequence

```
1. NAV              | hamburger-only
2. HERO             | full-bleed-overlay
3. PRODUCT-SHOWCASE | hover-cards
4. ABOUT            | editorial-split
5. TESTIMONIALS     | single-featured
6. NEWSLETTER       | minimal
7. FOOTER           | minimal
```

**Optional sections (add based on brief):**
- ANNOUNCEMENT-BAR (if sale/launch) → insert before HERO
- GALLERY (if lookbook/content) → insert after PRODUCT-SHOWCASE

---

## Style Configuration

```yaml
color_temperature: neutral
palette:
  bg_primary: white
  bg_secondary: neutral-50
  bg_accent: neutral-100
  text_primary: neutral-900
  text_heading: neutral-950
  text_muted: neutral-400
  accent: neutral-900
  accent_hover: neutral-700
  border: neutral-200

typography:
  pairing: editorial
  heading_font: Cormorant Garamond
  heading_weight: 400
  body_font: Inter
  body_weight: 300
  scale_ratio: 1.414
  weight_distribution: uniform

whitespace: generous
section_padding: py-24
internal_gap: gap-10

border_radius: sharp
buttons: rounded-sm
cards: rounded-sm
inputs: rounded-sm

animation_intensity: subtle
entrance: fade-up
hover: slight-lift
timing: "0.5s ease-out"

visual_density: low
image_treatment: full-bleed
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: neutral — bg:white/neutral-50 text:neutral-900 accent:neutral-900 border:neutral-200
Type: editorial — heading:Cormorant Garamond,400 body:Inter,300 scale:1.414
Space: generous — sections:py-24 internal:gap-10
Radius: sharp — buttons:rounded-sm cards:rounded-sm inputs:rounded-sm
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.5s ease-out
Density: low | Images: full-bleed
═══════════════════════
```

---

## Content Direction

**Tone:** Clear, trustworthy, conversion-oriented. Focus on benefits and clarity.

**Hero:** One strong headline and supporting line. CTA to main collection or offer.

**CTA language:** Direct but not aggressive. "Shop the collection" / "View products" / "Get started."

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|----------------|
| 2026-02-17 | Initial preset for pipeline industry fallback | run_pipeline gate_c |

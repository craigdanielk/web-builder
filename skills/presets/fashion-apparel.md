# Preset: Fashion & Apparel

Industries: clothing brands, streetwear, luxury fashion, accessories, boutique retailers,
sustainable fashion, activewear.

---

## Default Section Sequence

```
1. NAV              | hamburger-only
2. HERO             | full-bleed-overlay
3. PRODUCT-SHOWCASE | hover-cards
4. ABOUT            | editorial-split
5. GALLERY          | masonry
6. TESTIMONIALS     | single-featured
7. BLOG-PREVIEW     | magazine
8. NEWSLETTER       | minimal
9. FOOTER           | minimal
```

**Optional sections (add based on brief):**
- ANNOUNCEMENT-BAR (if sale/launch/new drop) → insert before HERO
- LOGO-BAR (if press features) → insert after HERO
- VIDEO (if campaign content) → insert after ABOUT
- PRICING (if subscription model like rental/box) → insert after PRODUCT-SHOWCASE

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

**Tone:** Minimal, aspirational, understated. Third person or no pronoun. Short,
evocative fragments. Let imagery carry the narrative. Avoid "shop now" energy —
think editorial voice.

**Hero copy pattern:** Lead with the collection or seasonal concept, not the product.
"Autumn Essentials" not "Buy our new jackets." One line of copy maximum.

**CTA language:** Understated and non-aggressive. "Explore the collection" not
"Shop now." "Discover" not "Buy." "View lookbook" not "See products."

---

## Photography / Visual Direction

- Full-bleed editorial photography with strong art direction
- Models in environmental context (architecture, nature, urban)
- Desaturated, neutral color grading — avoid oversaturation
- Close-up fabric texture shots for detail sections
- Avoid catalog-style flat lays — everything should feel aspirational

---

## Known Pitfalls

- Black-on-white minimal can feel like every other fashion site. Differentiate
  through typography scale (the 1.414 ratio gives dramatic headings) and image
  curation quality.
- Editorial fonts at light weights (400) need careful line-height tuning. Set
  headings to leading-tight or leading-none to avoid floaty spacing.
- Full-bleed images need high-resolution source material. Low-res images
  destroy the premium feel instantly.
- Sharp radius combined with subtle animation can feel cold. Ensure hover
  states provide enough feedback (the slight-lift helps).

---

## Reference Sites

Study these for pattern validation (not copying):
- COS, Everlane, AllSaints, SSENSE, Arket
- Look for: hero image treatment, product grid density, typography sizing,
  whitespace between sections, mobile navigation patterns

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

# Preset: Artisan Food & Beverage

Industries: coffee roasters, bakeries, craft breweries, specialty food producers,
artisan chocolatiers, tea companies, small-batch distilleries, farm-to-table brands.

---

## Default Section Sequence

```
1. NAV              | sticky-transparent
2. HERO             | full-bleed-overlay
3. ABOUT            | editorial-split
4. PRODUCT-SHOWCASE | hover-cards
5. HOW-IT-WORKS     | horizontal-timeline
6. TESTIMONIALS     | single-featured
7. NEWSLETTER       | inline
8. FOOTER           | minimal
```

**Optional sections (add based on brief):**
- PRICING (if subscription model) → insert after PRODUCT-SHOWCASE
- STATS (if impressive numbers) → insert after ABOUT
- GALLERY (if strong visual content) → insert after TESTIMONIALS
- BLOG-PREVIEW (if content marketing) → insert before FOOTER

---

## Style Configuration

```yaml
color_temperature: warm-earth
palette:
  bg_primary: stone-50
  bg_secondary: white
  bg_accent: amber-50
  text_primary: stone-900
  text_heading: stone-950
  text_muted: stone-500
  accent: amber-700
  accent_hover: amber-800
  border: stone-200

typography:
  pairing: serif-sans
  heading_font: DM Serif Display
  heading_weight: 700
  body_font: DM Sans
  body_weight: 400
  scale_ratio: 1.333
  weight_distribution: heavy-light

whitespace: generous
section_padding: py-24
internal_gap: gap-8

border_radius: medium
buttons: rounded-lg
cards: rounded-xl
inputs: rounded-lg

animation_intensity: moderate
entrance: fade-up-stagger
hover: lift-shadow
timing: "0.6s ease-out"

visual_density: low
image_treatment: full-bleed
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: warm-earth — bg:stone-50/white text:stone-900 accent:amber-700 border:stone-200
Type: serif-sans — heading:DM Serif Display,700 body:DM Sans,400 scale:1.333
Space: generous — sections:py-24 internal:gap-8
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: moderate — entrance:fade-up-stagger hover:lift-shadow timing:0.6s ease-out
Density: low | Images: full-bleed
═══════════════════════
```

---

## Content Direction

**Tone:** Warm, confident, story-driven. First person plural ("we"). Short
sentences. Evocative sensory language for product descriptions. Avoid corporate
jargon. Let the craft speak.

**Hero copy pattern:** Lead with the origin or philosophy, not the product.
"Single origin, roasted in Zurich" not "Buy our coffee beans."

**About section:** Founding story or philosophy. Emphasize craft process,
sourcing relationships, or local roots. Use one striking image.

**Product descriptions:** Origin + flavor notes + roast level. Treat each
product as a character with a story.

**CTA language:** Warm and inviting, not aggressive. "Explore our roasts"
not "Buy now." "Join the community" not "Subscribe."

---

## Photography Direction

- Dark, moody, warm lighting for hero and product shots
- Close-up texture shots (beans, crema, roasting process)
- Human moments (barista pouring, farmer harvesting)
- Avoid stock-photo sterility — imperfection is authenticity
- Color grading should lean warm with rich shadows

---

## Known Pitfalls

- Don't over-brown the palette. The accent color (amber-700) needs to pop
  against the warm backgrounds. Ensure sufficient contrast.
- Serif fonts can feel stuffy if the weight is too heavy. Keep headings at
  700, never 900.
- "Generous whitespace" doesn't mean empty. Each section should feel
  intentional, not sparse.
- Full-bleed images need careful overlay treatment to maintain text readability.
  Use a gradient overlay (from-black/60 to-transparent), not a flat opacity.

---

## Reference Sites

Study these for pattern validation (not copying):
- Trade Coffee, Blue Bottle, Counter Culture, Intelligentsia
- Look for: section sequencing, typography choices, scroll behavior,
  image treatment, color ratios

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

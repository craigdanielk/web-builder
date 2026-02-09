# Preset: Home & Lifestyle

Industries: furniture brands, home decor, kitchenware, interior design, bedding/linens,
candles, home organization.

---

## Default Section Sequence

```
1. NAV              | sticky-transparent
2. HERO             | full-bleed-overlay
3. PRODUCT-SHOWCASE | category-grid
4. ABOUT            | values-grid
5. GALLERY          | masonry
6. FEATURES         | alternating-rows
7. TESTIMONIALS     | carousel
8. NEWSLETTER       | inline
9. FOOTER           | mega
```

**Optional sections (add based on brief):**
- BLOG-PREVIEW (if design inspiration content) → insert before NEWSLETTER
- HOW-IT-WORKS (if custom furniture/made-to-order process) → insert after ABOUT
- STATS (if sustainability metrics) → insert after ABOUT
- VIDEO (if brand story or craftsmanship content) → insert after ABOUT

---

## Style Configuration

```yaml
color_temperature: earth
palette:
  bg_primary: stone-50
  bg_secondary: white
  bg_accent: green-50
  text_primary: stone-800
  text_heading: stone-900
  text_muted: stone-400
  accent: emerald-700
  accent_hover: emerald-800
  border: stone-200

typography:
  pairing: serif-sans
  heading_font: Libre Baskerville
  heading_weight: 700
  body_font: Outfit
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

animation_intensity: subtle
entrance: fade-up
hover: slight-lift
timing: "0.5s ease-out"

visual_density: medium
image_treatment: contained
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: earth — bg:stone-50/white text:stone-800 accent:emerald-700 border:stone-200
Type: serif-sans — heading:Libre Baskerville,700 body:Outfit,400 scale:1.333
Space: generous — sections:py-24 internal:gap-8
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.5s ease-out
Density: medium | Images: contained
═══════════════════════
```

---

## Content Direction

**Tone:** Warm, considered, aspirational but accessible. Second person ("your home" /
"your space"). Evocative but not flowery. Focus on how products transform a space,
not specs.

**Hero copy pattern:** Lead with the lifestyle aspiration, not the product.
"Designed for how you actually live" not "Shop furniture." Set a mood, not a
transaction.

**CTA language:** Inviting and exploratory. "Explore the collection" not "Shop now."
"Find your style" not "Browse products." "See it in a room" not "View details."

---

## Photography / Visual Direction

- Products shown in styled room settings — never isolated on white
- Natural daylight, warm tones, soft shadows from windows
- Lived-in but curated — a book on the table, a blanket draped casually
- Overhead and three-quarter angle shots for tableware and accessories
- Color grading leans warm with natural greens and earthy neutrals

---

## Known Pitfalls

- Earth palettes can feel muddy. The green-50 accent background and emerald-700
  CTA provide necessary freshness — don't swap for more browns.
- Contained image treatment with rounded-xl needs consistent aspect ratios
  across product photography. Mixed ratios break the grid harmony.
- Category-grid product showcase needs clear visual hierarchy between categories.
  Don't let all categories look the same size and weight.
- Room-setting photography can distract from the product. Each image should
  have a clear focal piece even within the styled context.

---

## Reference Sites

Study these for pattern validation (not copying):
- HAY, Muji, West Elm, Schoolhouse Electric, Blu Dot
- Look for: room-setting photography, product-in-context, collection
  organization, lifestyle storytelling, color palette warmth

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

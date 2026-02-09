# Preset: Real Estate

Industries: residential real estate, commercial properties, luxury real estate,
property management, real estate agencies, vacation rentals, property developers.

---

## Default Section Sequence

```
1. NAV              | sticky-transparent
2. HERO             | full-bleed-overlay (stunning property photography)
3. STATS            | inline-bar (market data / key metrics)
4. PRODUCT-SHOWCASE | grid (property listings)
5. FEATURES         | alternating-rows (services / why choose us)
6. TESTIMONIALS     | single-featured
7. ABOUT            | editorial-split (agency story)
8. CONTACT          | info-plus-form (inquiry form)
9. CTA              | gradient-block
10. FOOTER          | mega
```

**Optional sections (add based on brief):**
- GALLERY (if portfolio of sold properties) → insert after PRODUCT-SHOWCASE
- VIDEO (if virtual tour or brand video) → insert after HERO
- BLOG-PREVIEW (if market insights content) → insert before CTA
- NEWSLETTER (if market updates email) → insert before FOOTER

---

## Style Configuration

```yaml
color_temperature: dark
palette:
  bg_primary: slate-950
  bg_secondary: slate-900
  bg_accent: amber-950
  text_primary: slate-100
  text_heading: white
  text_muted: slate-400
  accent: amber-500
  accent_hover: amber-400
  border: slate-800

typography:
  pairing: serif-sans
  heading_font: Playfair Display
  heading_weight: 700
  body_font: Inter
  body_weight: 400
  scale_ratio: 1.333
  weight_distribution: heavy-light

whitespace: moderate
section_padding: py-20
internal_gap: gap-6

border_radius: medium
buttons: rounded-lg
cards: rounded-xl
inputs: rounded-lg

animation_intensity: subtle
entrance: fade-up
hover: slight-lift
timing: "0.5s ease-out"

visual_density: medium
image_treatment: full-bleed
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: dark — bg:slate-950/slate-900 text:slate-100 accent:amber-500 border:slate-800
Type: serif-sans — heading:Playfair Display,700 body:Inter,400 scale:1.333
Space: moderate — sections:py-20 internal:gap-6
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.5s ease-out
Density: medium | Images: full-bleed
═══════════════════════
```

---

## Content Direction

**Tone:** Refined, aspirational, confident. Second or third person. Language
should evoke lifestyle, not just square footage. Precision matters — use
specific neighborhood names, property features, market data. Avoid clichés
like "dream home" or "your next chapter."

**Hero copy pattern:** Lead with location or lifestyle aspiration, supported by
a breathtaking property image. "Tribeca. Redefined." or "Where the Pacific
meets your doorstep." Not "Find your perfect home."

**Property listings:** Address, price, bed/bath/sqft, one distinguishing feature.
Grid layout with hover reveal for quick details. Every card must have a
high-quality hero image.

**Stats section:** Market metrics — average sale price, days on market, properties
sold, client satisfaction rate. Numbers build trust in this industry.

**CTA language:** Low-friction, high-intent. "Schedule a private showing" /
"Request a valuation" / "Explore listings" — never "Buy now."

---

## Photography / Visual Direction

- Architectural photography with dramatic lighting (golden hour, twilight shots)
- Wide-angle interiors emphasizing space, light, and materials
- Aerial/drone shots for luxury properties and developments
- Lifestyle context shots (neighborhood cafés, parks, city skylines)
- Dark, cinematic color grading to match the dark palette — rich shadows, warm highlights

---

## Known Pitfalls

- Dark palettes require extra attention to text contrast. Slate-100 on slate-950
  is sufficient, but slate-400 muted text on slate-900 secondary backgrounds
  needs testing. Bump to slate-300 if readability suffers.
- The serif heading font (Playfair Display) at 700 weight can feel heavy on
  smaller screens. Consider reducing to 600 or using a lighter optical size
  for mobile breakpoints.
- Property grid density is key — too few cards feels empty, too many feels like
  a marketplace. 6-9 properties per view is the sweet spot.
- Full-bleed imagery on dark backgrounds can look muddy if the photos aren't
  high quality. Insist on professional real estate photography or use overlay
  gradients to maintain consistency.

---

## Reference Sites

Study these for pattern validation (not copying):
- Compass, Sotheby's International Realty, Douglas Elliman, The Agency
- Look for: property card layouts, hero treatment, how dark palettes handle
  listing density, map integration patterns, CTA placement on listings

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

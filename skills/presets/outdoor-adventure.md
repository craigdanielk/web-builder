# Preset: Outdoor & Adventure Gear

Industries: camping gear, hiking equipment, surf brands, climbing gear, overlanding,
trail running, outdoor apparel, adventure travel gear.

---

## Default Section Sequence

```
1. NAV              | sticky-transparent
2. HERO             | video-background (epic landscape or action footage)
3. ABOUT            | values-grid (brand mission + sustainability story)
4. PRODUCT-SHOWCASE | category-grid
5. FEATURES         | alternating-rows
6. STATS            | counter-animation
7. TESTIMONIALS     | grid
8. GALLERY          | masonry
9. NEWSLETTER       | split
10. FOOTER          | mega
```

**Optional sections (add based on brief):**
- BLOG-PREVIEW (if content marketing / adventure stories) → insert before NEWSLETTER
- VIDEO (if brand film or product demo) → insert after ABOUT
- HOW-IT-WORKS (if technical product with setup) → insert after FEATURES
- LOGO-BAR (if stocked by notable retailers) → insert after HERO

---

## Style Configuration

```yaml
color_temperature: earth
palette:
  bg_primary: stone-100
  bg_secondary: white
  bg_accent: emerald-50
  text_primary: stone-900
  text_heading: stone-950
  text_muted: stone-500
  accent: emerald-700
  accent_hover: emerald-800
  border: stone-300

typography:
  pairing: display-clean
  heading_font: Clash Display
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

animation_intensity: moderate
entrance: fade-up-stagger
hover: lift-shadow
timing: "0.6s ease-out"

visual_density: medium
image_treatment: full-bleed
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: earth — bg:stone-100/white text:stone-900 accent:emerald-700 border:stone-300
Type: display-clean — heading:Clash Display,700 body:Inter,400 scale:1.333
Space: moderate — sections:py-20 internal:gap-6
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: moderate — entrance:fade-up-stagger hover:lift-shadow timing:0.6s ease-out
Density: medium | Images: full-bleed
═══════════════════════
```

---

## Content Direction

**Tone:** Bold, direct, aspirational. Second person ("you"). Short punchy
sentences that evoke movement and the outdoors. Let the landscape and the
gear speak — avoid corporate sustainability buzzwords. Authentic over polished.

**Hero copy pattern:** Lead with the experience, not the product. "Built for
the ridge, not the runway" not "Shop our new hiking jackets." The hero should
make you feel the cold air and hear the trail.

**About section:** Brand mission and sustainability commitment. Emphasize
materials sourcing, environmental impact, warranty/repair philosophy. Keep it
honest and specific — "recycled nylon from ocean waste" not "we care about
the planet."

**CTA language:** Action-oriented but not salesy. "Explore the range" /
"Find your gear" / "Gear up" — match the energy of the outdoors. Never
"Buy now" or "Shop today."

---

## Photography / Visual Direction

- Full-bleed landscape photography: mountain ridges, ocean breaks, desert trails at golden hour
- Action shots: real athletes in real conditions, motion blur acceptable
- Product shots in-situ: gear on a summit, pack against a rock face, boots on a muddy trail
- Earthy, slightly desaturated color grading — no oversaturated Instagram look
- Avoid studio-clean product shots as hero images; save those for product detail pages

---

## Known Pitfalls

- Green-on-stone can feel military if overused. Use emerald-700 as accent sparingly
  against the neutral backgrounds. Let the photography carry the color.
- Display fonts (Clash Display) can feel aggressive at large sizes. Keep headings
  confident but not shouty — size 700 weight, never 900.
- Video backgrounds must have a strong fallback image. If video loads slowly, the
  hero should still look complete with a static landscape frame.
- "Moderate" animation means purposeful movement, not constant motion. Outdoor
  brands should feel grounded, not bouncy.

---

## Reference Sites

Study these for pattern validation (not copying):
- Patagonia, REI, Yeti, Arc'teryx, Huckberry
- Look for: hero treatments, storytelling sequencing, product category navigation,
  sustainability section patterns, color use against landscape photography

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

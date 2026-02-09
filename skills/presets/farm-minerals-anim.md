# Preset: Agricultural Product Marketing

Industries: agricultural technology, sustainable farming products, eco-friendly fertilizers, farm supply innovation, agricultural biotechnology, precision agriculture solutions

---

## Default Section Sequence

```
1. HERO                 | full-bleed-overlay
2. FEATURES             | icon-grid
3. FEATURES             | icon-grid
4. FEATURES             | icon-grid
5. COMPARISON           | vs-table
6. FEATURES             | icon-grid
7. FOOTER               | mega
```

**Optional sections (add based on brief):**
- TESTIMONIALS (if social proof available) → insert after COMPARISON
- STATS (if performance data available) → insert after first FEATURES
- FAQ (if technical product) → insert before FOOTER

---

## Style Configuration

```yaml
color_temperature: warm-earth

palette:
  bg_primary: stone-50
  bg_secondary: white
  bg_accent: stone-200
  text_primary: gray-900
  text_heading: stone-900
  text_muted: stone-600
  accent: green-700
  accent_hover: green-800
  border: stone-300

typography:
  pairing: single-sans
  heading_font: Aeonik
  heading_weight: 600
  body_font: Aeonik
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: medium-contrast

whitespace: generous
section_padding: 6rem
internal_gap: 3rem

border_radius: pill
buttons: pill
cards: 3xl
inputs: full

animation_engine: gsap
animation_intensity: expressive
entrance: fade-up-stagger
hover: lift-glow
timing: 0.6s-ease-out
smooth_scroll: false
section_overrides: hero:lottie-hero features:scroll-reveal comparison:slide-compare

visual_density: airy
image_treatment: natural-rounded
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: warm-earth | stone-50/white/green-700
Type: Aeonik/Aeonik · 600/400 · 1.25 ratio
Space: generous (6rem/3rem)
Radius: pill (buttons) · 3xl (cards)
Motion: expressive/gsap — entrance:fade-up-stagger hover:lift-glow timing:0.6s-ease-out | hero:lottie-hero features:scroll-reveal comparison:slide-compare
Density: airy | Images: natural-rounded
═══════════════════════
```

---

## Content Direction

**Tone:** Scientific optimism, innovation-forward, environmentally conscious, outcome-focused

**Hero copy pattern:** Provocative question format leading to transformative solution statement. Opens with possibility-focused question ("How much could you grow...?") then pivots to product introduction with technical naming (CropTab™).

**CTA language:** Direct action verbs with minimal friction ("Just drop it"), emphasize simplicity and ease-of-use, avoid traditional sales language in favor of demonstration-focused phrases.

---

## Photography / Visual Direction

- Product macro photography showcasing microscopic innovation and technical precision
- Agricultural landscape imagery emphasizing sustainable outcomes (zero runoff, clean fields)
- Scientific visualization and particle/molecular-level animations via Lottie
- Natural earth tones with fresh green accents reflecting crop vitality
- Clean studio shots of product against minimal backgrounds
- Before/after comparison visuals demonstrating environmental impact
- Microscopic scale comparisons (smaller than plant cell) with visual proof
- Animation-heavy approach using GSAP and Lottie for technical storytelling

---

## Known Pitfalls

- Avoid over-technical jargon without visual support; this preset relies heavily on animation to explain complex concepts
- Don't skimp on Lottie/animation budget — the product differentiation depends on visual storytelling
- Comparison tables must be clear and data-driven; avoid marketing fluff in favor of measurable outcomes
- Ensure mobile optimization of complex animations doesn't degrade to static fallbacks without maintaining clarity
- Icon grids should maintain generous spacing to preserve "airy" density even with multiple feature sections
- Keep CTA language conversational despite technical product; maintain "just drop it" simplicity
- Pill radius on everything can feel dated if not balanced with generous whitespace and modern typography

---

## Reference Sites

- https://www.farmminerals.com/promo

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-xx | Preset created | farmminerals.com/promo |
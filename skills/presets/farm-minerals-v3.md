# Preset: Agricultural Technology / AgriTech Innovation

Industries: agricultural technology, farming solutions, precision agriculture, biotech products, sustainable farming, crop nutrition, agricultural innovation, farm input suppliers

---

## Default Section Sequence

```
1. HERO              | full-bleed-overlay
2. FEATURES          | icon-grid
3. FEATURES          | icon-grid
4. FEATURES          | icon-grid
5. FEATURES          | icon-grid
6. FEATURES          | icon-grid
7. COMPARISON        | vs-table
8. FEATURES          | icon-grid
9. FOOTER            | mega
```

**Optional sections (add based on brief):**
- TESTIMONIALS (if social proof needed) → insert after section 6
- STATS (if data-driven story) → insert after section 2
- CTA_BLOCK (if conversion focus) → insert before footer

---

## Style Configuration

```yaml
color_temperature: warm-earth

palette:
  bg_primary: stone-50
  bg_secondary: white
  bg_accent: stone-200
  text_primary: stone-900
  text_heading: stone-900
  text_muted: stone-600
  accent: lime-700
  accent_hover: lime-800
  border: stone-300

typography:
  pairing: single-font
  heading_font: Aeonik
  heading_weight: 600
  body_font: Aeonik
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: moderate-contrast

whitespace: generous
section_padding: xl
internal_gap: lg

border_radius: pill
buttons: pill
cards: xl
inputs: lg

animation_engine: gsap
animation_intensity: expressive
entrance: fade-up-stagger
hover: lift-subtle
timing: smooth-elastic
smooth_scroll: false
section_overrides: hero:parallax-overlay features:scroll-reveal comparison:slide-in

visual_density: spacious
image_treatment: natural-clean
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: warm-earth — stone-50/white/lime-700
Type: Aeonik (single-font) — 600/400 — 1.25 scale
Space: generous | xl/lg
Radius: pill — buttons:pill cards:xl
Motion: expressive/gsap — entrance:fade-up-stagger hover:lift-subtle timing:smooth-elastic | hero:parallax-overlay features:scroll-reveal comparison:slide-in
Density: spacious | Images: natural-clean
═══════════════════════
```

---

## Content Direction

**Tone:** Scientific-optimistic, innovation-forward, problem-solving, educational yet accessible. Emphasizes sustainability and measurable outcomes. Question-based engagement that challenges status quo.

**Hero copy pattern:** Start with provocative question highlighting potential ("How much could you grow — if nothing was wasted?"), followed by product introduction. Focus on transformative possibility rather than incremental improvement.

**CTA language:** Action-oriented but educational. Use phrases like "Discover how," "See the difference," "Learn more," "Get started." Avoid aggressive sales language — lean toward invitation to explore innovation.

---

## Photography / Visual Direction

- Macro photography of plant structures and cellular detail
- Clean product shots on neutral backgrounds (white or soft earth tones)
- Agricultural landscapes with focus on healthy crops
- Before/after comparisons showing results
- Scientific/microscopic imagery to emphasize nano-scale innovation
- Lottie animations for process explanation and micro-interactions
- Animated data visualizations showing efficiency improvements
- Green-dominant color palette in photography reflecting agricultural context
- High contrast between product and background for clarity
- Documentary-style authenticity mixed with product glamour shots

---

## Known Pitfalls

- Avoid overly technical jargon that alienates non-scientist farmers
- Don't over-promise results — maintain credibility with realistic claims
- Balance innovation messaging with practical application examples
- Ensure mobile experience handles large icon grid sections gracefully
- Watch for performance with multiple Lottie animations on scroll
- Comparison tables must remain readable on mobile (consider accordion variant)
- Large border radius values (864px) may need capping on smaller elements
- GSAP ScrollTrigger performance — batch animations to avoid jank
- Maintain accessibility with sufficient color contrast on earth-tone backgrounds

---

## Reference Sites

- https://farmminerals.com/promo (source)

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Initial preset created | farmminerals.com/promo |
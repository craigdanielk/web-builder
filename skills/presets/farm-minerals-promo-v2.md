# Preset: Agricultural Technology & Science

Industries: agricultural technology, farming products, scientific agriculture, sustainable farming solutions, crop nutrition, agtech B2B, environmental science products

---

## Default Section Sequence

```
1. HERO                 | full-bleed-overlay
2. FEATURES             | icon-grid
3. FEATURES             | icon-grid
4. FEATURES             | icon-grid
5. FEATURES             | icon-grid
6. FEATURES             | icon-grid
7. COMPARISON           | vs-table
8. FEATURES             | icon-grid
9. FOOTER               | mega
```

**Optional sections (add based on brief):**
- TESTIMONIAL (if social proof needed) → insert after position 6
- STATS (if data-driven messaging) → insert after position 2
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
  text_heading: gray-900
  text_muted: gray-600
  accent: lime-700
  accent_hover: lime-800
  border: stone-300

typography:
  pairing: single-family
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
cards: pill
inputs: pill

animation_engine: gsap
animation_intensity: expressive
entrance: fade-up-stagger
hover: lift-subtle
timing: 0.3s ease
smooth_scroll: false
section_overrides: hero:lottie-hero features:scroll-reveal comparison:fade-in

visual_density: open
image_treatment: natural-organic
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: warm-earth stone/lime
Type: Aeonik single-family | 1.25 scale
Space: generous/xl/lg
Radius: pill everywhere
Motion: expressive/gsap — entrance:fade-up-stagger hover:lift-subtle timing:0.3s | hero:lottie-hero features:scroll-reveal
Density: open | Images: natural-organic
═══════════════════════
```

---

## Content Direction

**Tone:** Scientific yet approachable, innovation-focused, sustainability-forward, confident and technical without jargon overload

**Hero copy pattern:** Question-led value proposition ("How much could you grow — if nothing was wasted?") followed by product name and differentiation statement

**CTA language:** Action-oriented with minimal friction ("Just drop it"), emphasizing simplicity and ease of adoption

---

## Photography / Visual Direction

- Macro photography of plants, soil, and agricultural environments
- Clean product shots showing scale and application
- Scientific visualization and microscopy imagery
- Earth tones with vibrant green accents from crops
- High contrast between product and natural backgrounds
- Use of Lottie animations for product demonstrations and technical explanations
- Iconography should be clean, minimal, and science-inspired
- Environmental responsibility should be visually evident

---

## Known Pitfalls

- Avoid overly technical language that alienates farmers without scientific backgrounds
- Balance innovation messaging with practical application benefits
- Don't oversell sustainability claims without backing with data
- Ensure animations enhance understanding rather than distract from technical content
- Icon grids can become repetitive — vary visual treatment across sections
- Comparison tables must clearly demonstrate value without appearing combative
- Pill radius may feel too rounded for highly technical audiences — test with target demographic

---

## Reference Sites

- https://www.farmminerals.com/promo (source)

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Initial preset creation | farmminerals.com/promo |
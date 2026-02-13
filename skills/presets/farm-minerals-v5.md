# Preset: Agricultural Technology

Industries: agricultural products, farming solutions, sustainable agriculture, crop nutrition, mineral supplements, farm technology

---

## Default Section Sequence

```
1. HERO                 | full-bleed-overlay
2. FEATURES             | alternating-rows
3. FEATURES             | icon-grid
4. FEATURES             | icon-grid
5. PRODUCT-SHOWCASE     | hover-cards
6. FEATURES             | icon-grid
7. COMPARISON           | vs-table
8. FEATURES             | icon-grid
9. FOOTER               | mega
```

**Optional sections (add based on brief):**
- TESTIMONIALS (if social proof needed) → insert after section 5
- FAQ (if technical product) → insert before FOOTER
- CTA (if conversion-focused) → insert after COMPARISON

---

## Style Configuration

```yaml
color_temperature: warm-earth
palette:
  bg_primary: orange-50
  bg_secondary: white
  bg_accent: orange-200
  text_primary: gray-800
  text_heading: gray-900
  text_muted: gray-600
  accent: lime-800
  accent_hover: lime-900
  accent_secondary: lime-600
  accent_tertiary: orange-100
  border: orange-200

section_accents:
  hero: lime-800
  features-1: lime-800
  features-2: lime-700
  features-3: lime-700

typography:
  pairing: single-family
  heading_font: Aeonik
  heading_weight: 700
  body_font: Aeonik
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: moderate

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
timing: 0.6s ease-out
smooth_scroll: true
section_overrides: hero:character-reveal features:scroll-fade product-showcase:hover-lift comparison:slide-in
gsap_plugins:
  - GSAP
  - ScrollTrigger
  - SplitText
  - Observer

visual_density: airy
image_treatment: natural-with-overlay
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: warm-earth (orange-50/white/lime-800) | Accents: primary:lime-800 secondary:lime-600 tertiary:orange-100
Type: Aeonik (single-family) | 1.25 scale | moderate weights
Space: generous/xl/lg
Radius: pill (864px)
Motion: expressive/gsap — entrance:fade-up-stagger hover:lift-subtle timing:0.6s ease-out | hero:character-reveal features:scroll-fade product-showcase:hover-lift comparison:slide-in
Density: airy | Images: natural-with-overlay
Plugins: GSAP, ScrollTrigger, SplitText, Observer
═══════════════════════
```

---

## Content Direction

**Tone:** Scientific yet accessible, innovation-focused, sustainability-conscious, benefit-driven with technical credibility

**Hero copy pattern:** Question-led impact statement ("How much could you grow — if nothing was wasted?") that positions the product as a paradigm shift rather than incremental improvement

**CTA language:** Action-oriented and simple ("Just drop it"), emphasizing ease of use and immediate application. Focuses on simplicity despite technological sophistication.

---

## Photography / Visual Direction

- Macro photography showing cellular-level detail and product integration
- Clean product shots against natural earth-tone backgrounds
- Agricultural field imagery with warm, golden-hour lighting
- Scientific visualization combined with organic textures
- High contrast between product detail and soft environmental contexts
- Animated Lottie illustrations for technical concepts (10 detected)
- Natural overlays that don't overpower product visibility

---

## Known Pitfalls

- Balance scientific credibility with accessibility — avoid over-technical jargon while maintaining authority
- Ensure agricultural imagery feels modern and tech-forward, not traditional/rustic
- Large border radius (864px) creates pill shapes — ensure content containers have adequate padding
- Multiple feature sections may feel repetitive — vary visual treatment and content depth
- Comparison tables in agriculture need to avoid appearing combative toward traditional methods
- GSAP SplitText animations on hero can impact CLS — implement proper loading states
- Warm earth tones can reduce contrast — ensure text legibility on orange-100 backgrounds
- Product showcase hover effects need clear affordance that items are interactive

---

## Reference Sites

- https://www.farmminerals.com/promo

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Initial preset creation | farmminerals.com/promo |
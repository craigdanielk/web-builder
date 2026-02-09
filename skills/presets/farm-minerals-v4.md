# Preset: Agricultural Technology

Industries: Agricultural products, mineral supplements, farming solutions, crop nutrition, sustainable agriculture, biotech farming products

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
- TESTIMONIALS (if social proof needed) → insert before COMPARISON
- FAQ (if product complexity high) → insert after COMPARISON
- CTA_BAND (if lead capture priority) → insert after section 6

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
  weight_distribution: moderate

whitespace: generous
section_padding: 5rem
internal_gap: 3rem

border_radius: pill
buttons: 864px
cards: 24px
inputs: 864px

animation_engine: gsap
animation_intensity: expressive
entrance: fade-slide
hover: lift-glow
timing: 0.6s cubic-bezier(0.4, 0, 0.2, 1)
smooth_scroll: false
section_overrides: hero:parallax-fade features:stagger-in comparison:reveal-rows

visual_density: airy
image_treatment: natural-blend
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: warm-earth (stone-50/white/lime-700)
Type: Aeonik/Aeonik • moderate weight • 1.25 scale
Space: generous (5rem/3rem)
Radius: pill (buttons:864px cards:24px)
Motion: expressive/gsap — entrance:fade-slide hover:lift-glow timing:0.6s cubic-bezier | hero:parallax-fade features:stagger-in comparison:reveal-rows
Density: airy | Images: natural-blend
═══════════════════════
```

---

## Content Direction

**Tone:** Scientific yet approachable, innovation-focused with environmental consciousness, direct benefit statements, question-driven engagement

**Hero copy pattern:** Provocative question format that challenges conventional thinking ("How much could you grow — if nothing was wasted?"), followed by product name lockup as visual anchor

**CTA language:** Action-focused and simple ("Just drop it"), emphasizing ease of use and immediacy, avoid technical jargon in primary CTAs

---

## Photography / Visual Direction

- Macro photography of crops, soil, and agricultural elements
- Scientific/microscopic imagery showing particle size and integration
- Clean product shots against neutral backgrounds
- Environmental scenes showcasing sustainable practices
- Split-screen or before/after comparison visuals
- Minimal color grading maintaining natural earth tones
- High contrast between product and background for clarity
- Iconography should be simple, nature-inspired line drawings

---

## Known Pitfalls

- Don't over-tech the language; farmers value clarity over scientific complexity
- Balance environmental messaging with practical ROI — avoid greenwashing tone
- Pill-shaped buttons with 864px radius require careful text sizing to avoid awkward spacing
- Multiple icon-grid sections can feel repetitive; vary icon styles or grid layouts
- Ensure comparison tables remain mobile-friendly with clear hierarchy
- Heavy GSAP animations may impact performance on rural/slower connections
- Warm earth palette needs sufficient contrast for accessibility; test text on stone-50 backgrounds
- Lottie animations (10 detected) should have fallback images for older devices

---

## Reference Sites

- https://farmminerals.com/promo

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2024 | Initial preset creation | farmminerals.com/promo |
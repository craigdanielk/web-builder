# Preset: Agricultural Technology

Industries: agricultural products, crop nutrition, farming solutions, mineral supplements, precision agriculture, sustainable farming, agrochemical alternatives

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
- PRICING (if product tiers exist) → insert after section 7
- FAQ (if technical product) → insert before FOOTER

---

## Style Configuration

```yaml
color_temperature: warm-earth
palette:
  bg_primary: orange-50
  bg_secondary: white
  bg_accent: orange-200
  text_primary: gray-800
  text_heading: black
  text_muted: lime-700
  accent: lime-800
  accent_hover: lime-900
  accent_secondary: orange-200
  accent_tertiary: lime-600
  border: orange-200

section_accents:
  section-0: lime-800
  section-1: lime-800
  section-2: lime-700
  section-3: lime-700

typography:
  pairing: single-family
  heading_font: Aeonik
  heading_weight: 700
  body_font: Aeonik
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: bold-headings

whitespace: generous
section_padding: 128px
internal_gap: 64px

border_radius: pill
buttons: pill
cards: pill
inputs: pill

animation_engine: gsap
animation_intensity: expressive
entrance: fade-up-stagger
hover: lift-subtle
timing: 0.6s ease-out
smooth_scroll: false
section_overrides: hero:character-reveal features:icon-morph product-showcase:hover-cards comparison:fade-in-sequence
gsap_plugins:
  - GSAP
  - ScrollTrigger
  - SplitText
  - Observer

visual_density: spacious
image_treatment: high-quality-photography
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: warm-earth (orange-50/white/lime-800) | Accents: primary:lime-800 secondary:orange-200 tertiary:lime-600
Type: Aeonik/Aeonik • 1.25 ratio • bold-headings
Space: generous (128/64)
Radius: pill
Motion: expressive/gsap — entrance:fade-up-stagger hover:lift-subtle timing:0.6s ease-out | hero:character-reveal features:icon-morph product-showcase:hover-cards comparison:fade-in-sequence
Density: spacious | Images: high-quality-photography
═══════════════════════
```

---

## Content Direction

**Tone:** Scientific confidence with accessible clarity. Technical innovation explained through benefit-driven narratives. Environmental responsibility as core value proposition.

**Hero copy pattern:** Question-driven hook that challenges conventional thinking → "How much could you grow — if nothing was wasted?" followed by product name as solution anchor.

**CTA language:** Action-focused but consultative. Avoid aggressive sales language. Use discovery-oriented phrases like "Explore the science," "See how it works," "Calculate your impact."

---

## Photography / Visual Direction

- Macro photography of crops, soil, and plant cells emphasizing microscopic precision
- Aerial/drone shots of farmland showing scale and environmental context
- Close-up product shots on natural, earthy surfaces (wood, stone, soil)
- Scientific imagery: microscopy, crystalline structures, cellular interaction
- Muted, desaturated color grading maintaining warm earth tones
- Avoid overly saturated greens; prefer natural, realistic agricultural colors
- Human elements minimal; focus on product efficacy and natural processes
- Clean white/cream backgrounds for product isolation shots
- Environmental storytelling through before/after field comparisons

---

## Known Pitfalls

- Avoid over-technical jargon without explanatory context; balance scientific credibility with farmer accessibility
- Don't default to bright green as primary accent — this brand uses muted lime/olive tones for sophistication
- Resist generic "green/eco" clichés; sustainability here is about efficiency and innovation, not just environmentalism
- Product photography must show scale and application context, not just isolated tablets
- Comparison tables should focus on environmental impact metrics, not just price
- Animation should enhance scientific storytelling (particle effects, cell integration visualization) not distract
- Footer must accommodate agricultural compliance, certifications, and technical resources
- Mobile experience critical for field usage — ensure readability in bright outdoor conditions

---

## Reference Sites

- https://www.farmminerals.com/promo

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Preset created from Farm Minerals CropTab promo page | farmminerals.com |
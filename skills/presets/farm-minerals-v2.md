# Preset: Agricultural Technology & Sustainable Products

Industries: agricultural technology, sustainable farming products, eco-friendly fertilizers, agricultural innovation, farm supply, green agriculture, precision farming solutions

---

## Default Section Sequence

```
1. HERO             | full-bleed-overlay
2. FEATURES         | icon-grid
3. FEATURES         | icon-grid
4. FEATURES         | icon-grid
5. FEATURES         | icon-grid
6. FEATURES         | icon-grid
7. COMPARISON       | vs-table
8. FEATURES         | icon-grid
9. FOOTER           | mega
```

**Optional sections (add based on brief):**
- STATS (if quantifiable impact data available) → insert after position 2
- TESTIMONIAL (if farmer/user testimonials provided) → insert before COMPARISON
- FAQ (if technical questions needed) → insert after COMPARISON

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
  accent: green-800
  accent_hover: green-900
  border: stone-300

typography:
  pairing: single-font
  heading_font: Aeonik
  heading_weight: 600
  body_font: Aeonik
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: balanced

whitespace: generous
section_padding: 7rem
internal_gap: 3rem

border_radius: pill
buttons: pill
cards: pill
inputs: pill

animation_engine: gsap
animation_intensity: expressive
entrance: fade-up-cascade
hover: lift-glow
timing: 0.3s, ease-out
smooth_scroll: false
section_overrides: hero:parallax-overlay features:scroll-fade comparison:slide-reveal

visual_density: spacious
image_treatment: natural-organic
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: warm-earth (stone-50/white/green-800)
Type: Aeonik/Aeonik • 1.25 ratio • balanced
Space: generous (7rem/3rem)
Radius: pill (buttons:pill cards:pill inputs:pill)
Motion: expressive/gsap — entrance:fade-up-cascade hover:lift-glow timing:0.3s,ease-out | hero:parallax-overlay features:scroll-fade comparison:slide-reveal
Density: spacious | Images: natural-organic
═══════════════════════
```

---

## Content Direction

**Tone:** Scientific confidence meets environmental optimism. Emphasize breakthrough innovation, precision, and sustainability. Use questions to provoke thinking ("How much could you grow — if nothing was wasted?"). Balance technical credibility with accessible language. Celebrate waste elimination and efficiency gains.

**Hero copy pattern:** Thought-provoking question headline followed by product name/trademark. Focus on potential and possibility rather than limitations. Use metrics and absolutes ("0 run-off", "Zero manufacturing emissions") to establish credibility.

**CTA language:** Direct, action-oriented, minimal friction. Avoid aggressive sales language. Prefer "Learn more", "Discover how", "Get started", "See the difference". Emphasize ease and simplicity ("Just drop it").

---

## Photography / Visual Direction

- Hero: Full-bleed imagery with overlay — vibrant crop fields, aerial farm views, or macro plant growth shots with warm natural lighting
- Product photography: Clean, isolated product shots on neutral backgrounds emphasizing small size and precision
- Lifestyle: Farmers interacting with product in real farm settings, candid and authentic
- Macro/microscopic imagery showing product integration at cellular level
- Sustainability visuals: pristine water, healthy soil, thriving ecosystems
- Color grading: Warm earth tones with rich greens, golden hour lighting preferred
- Avoid: Overly clinical/sterile laboratory settings, stock agriculture clichés
- Include: Lottie animations for process explanations, technical diagrams, comparison visuals

---

## Known Pitfalls

- Don't oversimplify the science — maintain credibility with technical audience while staying accessible
- Avoid greenwashing language; be specific about environmental claims
- Balance innovation messaging with practical application and ease of use
- Don't bury the comparison table — it's a key differentiator and should be prominent
- Ensure icon-grid features have sufficient whitespace; avoid visual clutter with too many technical details
- Product name trademark (™) should be consistently applied
- Multiple feature sections need visual variety — alternate layouts, alternate background colors
- Pill radius on everything can feel repetitive; consider selective application
- GSAP animations at "expressive" level may distract from content — ensure scroll-triggered animations enhance rather than dominate
- Warm earth palette can feel muddy; maintain sufficient contrast for accessibility

---

## Reference Sites

- https://farmminerals.com/promo

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Initial preset created | farmminerals.com/promo |
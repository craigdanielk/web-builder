# Preset: Health Tech Product

Industries: telehealth, digital health platform, wellness technology, health device, consumer health, sleep tech, wellness tracking

---

## Default Section Sequence

```
1. STATS                | counter-animation
2. FEATURES             | icon-grid
3. STATS                | counter-animation
4. FEATURES             | alternating-rows
5. FEATURES             | alternating-rows
6. FEATURES             | icon-grid
7. FEATURES             | alternating-rows
8. FEATURES             | icon-grid
9. STATS                | counter-animation
10. FEATURES             | alternating-rows
11. FOOTER               | mega
```

**Optional sections (add based on brief):**
- TESTIMONIAL (if social proof needed) → insert after section 6
- PRICING (if product tiers) → insert after section 9
- FAQ (if complexity high) → insert before FOOTER

---

## Style Configuration

```yaml
color_temperature: monochrome-light

palette:
  bg_primary: white
  bg_secondary: stone-50
  bg_accent: black
  text_primary: gray-800
  text_heading: black
  text_muted: gray-500
  accent: black
  accent_hover: gray-800
  border: gray-200

typography:
  pairing: custom-modern
  heading_font: HelveticaNowDisplayMedium
  heading_weight: 500
  body_font: HelveticaNowDisplayMedium
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: medium-headers

whitespace: generous
section_padding: xl
internal_gap: lg

border_radius: full
buttons: pill
cards: 3xl
inputs: 2xl

animation_engine: css
animation_intensity: subtle
entrance: fade-up
hover: lift-subtle
timing: 0.3s ease
smooth_scroll: false
section_overrides: stats:counter-animation

visual_density: spacious
image_treatment: clean-product
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: monochrome • bg:white text:black/gray-800 accent:black
Type: custom/custom • 500/400 • 1.25 scale
Space: generous/xl/lg
Radius: full (pill buttons, 3xl cards)
Motion: subtle/css — entrance:fade-up hover:lift-subtle timing:0.3s | stats:counter-animation
Density: spacious | Images: clean-product
═══════════════════════
```

---

## Content Direction

**Tone:** Minimal, scientific, wellness-focused. Direct statements about measurable impact. Product-first language that emphasizes technology and nature intersection.

**Hero copy pattern:** Single powerful word or short phrase as headline ("feelbetter"), followed by explanatory subheading about measurable plant-based impact on wellness metrics.

**CTA language:** Action-oriented but understated. Menu navigation focused. Primary CTAs likely product-focused ("get sofi", "learn more") rather than aggressive sales language.

---

## Photography / Visual Direction

- Clean product photography on pure white or black backgrounds
- High contrast, studio-quality shots of the physical device (pod)
- Minimal lifestyle imagery; focus on the technology itself
- Rounded edge containers for product images matching the border-radius system
- Black and white color variants prominently featured
- Macro/detail shots showing craftsmanship and materials
- Stark, uncluttered compositions with generous negative space

---

## Known Pitfalls

- The extreme minimalism requires excellent photography and copy to avoid feeling empty
- Monochrome palette needs careful attention to hierarchy through scale and weight alone
- Multiple stats sections may feel repetitive; vary presentation style
- Icon grids and alternating features need strong visual differentiation without color
- Product-only focus may need social proof integration for conversion
- Menu-driven navigation requires clear, intuitive structure for complex product information

---

## Reference Sites

- https://www.sofihealth.com/

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Initial preset created | sofihealth.com analysis |
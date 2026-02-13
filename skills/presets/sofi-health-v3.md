# Preset: Health Tech / Wellness Device

Industries: health technology, wellness devices, sleep technology, personal health monitoring, connected health products, botanical wellness, lifestyle health

---

## Default Section Sequence

```
1. HERO                 | full-bleed-overlay
2. STATS                | counter-animation
3. ABOUT                | editorial-split
4. STATS                | counter-animation
5. PRODUCT-SHOWCASE     | hover-cards
6. STATS                | counter-animation
7. BLOG-PREVIEW         | card-grid
8. FOOTER               | mega
```

**Optional sections (add based on brief):**
- TESTIMONIALS (if social proof needed) → insert after section 3
- FAQ (if product complexity high) → insert after section 5
- CTA-BANNER (if conversion focus) → insert before footer

---

## Style Configuration

```yaml
color_temperature: dark-neutral
palette:
  bg_primary: black
  bg_secondary: gray-950
  bg_accent: neutral-50
  text_primary: white
  text_heading: white
  text_muted: gray-400
  accent: white
  accent_hover: gray-200
  border: gray-800

typography:
  pairing: display-sans
  heading_font: HelveticaNowDisplayMedium
  heading_weight: 500
  body_font: HelveticaNowDisplayMedium
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: medium-contrast

whitespace: generous
section_padding: 8rem 2rem
internal_gap: 3rem

border_radius: full
buttons: 56px
cards: 49px
inputs: 20px

animation_engine: css
animation_intensity: subtle
entrance: fade-in
hover: lift-subtle
timing: 0.3s ease
smooth_scroll: false
section_overrides: stats:count-up
gsap_plugins:
  # none detected

visual_density: spacious
image_treatment: high-contrast-photography
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: dark-neutral (black/gray-950 + white text)
Type: display-sans (HelveticaNowDisplayMedium 500/400) 1.25
Space: generous (8rem/3rem)
Radius: full (56px buttons, 49px cards)
Motion: subtle/css — entrance:fade-in hover:lift-subtle timing:0.3s | stats:count-up
Density: spacious | Images: high-contrast-photography
═══════════════════════
```

---

## Content Direction

**Tone:** Minimal, scientific, and wellness-focused. Uses lowercase stylization for brand personality ("feelbetter", "sofi pod"). Emphasizes measurable impact and plant-based science with clean, direct language.

**Hero copy pattern:** Single-word emotional hook followed by scientific value proposition. Format: "[emotion]" → "sofi measures the impact of plants to improve the way we [benefit]"

**CTA language:** Action-oriented and exploratory ("open the menu"). Keep CTAs conversational and low-pressure, reflecting wellness industry approachability.

---

## Photography / Visual Direction

- High-contrast product photography on pure black backgrounds
- Clean, minimalist product shots emphasizing device design and portability
- Lifestyle imagery showing personal wellness contexts (sleep, relaxation)
- Strong use of negative space to create breathing room
- Monochromatic or near-monochromatic color grading
- Focus on tactile product details (materials, form factor)
- Avoid busy backgrounds; let products float in space

---

## Known Pitfalls

- The dark background is intentional brand identity — don't suggest lightening for "accessibility" without client request
- Counter animations on STATS sections are crucial for impact metrics; ensure they trigger properly in viewport
- Border radius should remain consistently rounded (full/pill style) across all UI elements
- Resist adding color accents; the monochrome palette is deliberate
- Product showcase cards need subtle hover states to maintain minimal aesthetic
- Typography should stay medium-weight; avoid bold treatments that feel too aggressive
- Footer mega structure handles extensive product/company information; keep organized with clear visual hierarchy

---

## Reference Sites

- https://www.sofihealth.com/

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Initial preset created | sofihealth.com analysis |
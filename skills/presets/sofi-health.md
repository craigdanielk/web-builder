# Preset: Health & Wellness Tech

Industries: health tech, wellness devices, smart health products, consumer medical devices, sleep technology, biometric tracking, connected health devices

---

## Default Section Sequence

```
1. STATS            | counter-animation
2. FEATURES         | icon-grid
3. STATS            | counter-animation
4. FEATURES         | alternating-rows
5. FEATURES         | alternating-rows
6. FEATURES         | icon-grid
7. FEATURES         | alternating-rows
8. FEATURES         | icon-grid
9. STATS            | counter-animation
10. FEATURES        | alternating-rows
11. FOOTER          | mega
```

**Optional sections (add based on brief):**
- TESTIMONIALS (if social proof needed) → insert after section 6
- PRICING (if product tiers exist) → insert after section 8
- FAQ (if product complexity warrants) → insert before FOOTER

---

## Style Configuration

```yaml
color_temperature: dark-neutral

palette:
  bg_primary: black
  bg_secondary: zinc-950
  bg_accent: zinc-100
  text_primary: white
  text_heading: white
  text_muted: zinc-400
  accent: white
  accent_hover: zinc-200
  border: zinc-800

typography:
  pairing: custom-sans/custom-sans
  heading_font: HelveticaNowDisplayMedium
  heading_weight: 500
  body_font: HelveticaNowDisplayMedium
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: narrow

whitespace: generous
section_padding: xl
internal_gap: lg

border_radius: pill
buttons: pill
cards: 3xl
inputs: pill

animation_engine: css
animation_intensity: subtle
entrance: fade-up
hover: subtle-lift
timing: 0.3s
smooth_scroll: false
section_overrides: stats:counter-animation

visual_density: spacious
image_treatment: high-contrast-photography
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: dark-neutral (black/zinc-950 bg, white text, minimal borders)
Type: HelveticaNowDisplayMedium · 500/400 · 1.25 ratio · narrow weight
Space: generous/xl/lg
Radius: pill (buttons) · 3xl (cards)
Motion: subtle/css — entrance:fade-up hover:subtle-lift timing:0.3s | stats:counter-animation
Density: spacious | Images: high-contrast-photography
═══════════════════════
```

---

## Content Direction

**Tone:** Calm, scientific, aspirational — emphasizes wellness outcomes and technology integration with nature. Clean, minimal language that balances technical innovation with organic solutions.

**Hero copy pattern:** Single word emotional payoff ("feelbetter") followed by scientific product description focusing on measurement and natural ingredients. Direct, benefits-first.

**CTA language:** Action-oriented modal controls ("close modal button", "accept all", "open the menu") — functional and clear rather than marketing-driven. Prioritizes user agency.

---

## Photography / Visual Direction

- High-contrast product photography on dark backgrounds
- Close-up detail shots emphasizing texture and craftsmanship
- Minimal lifestyle imagery — focus on device itself
- Clean white or black product colorways featured prominently
- Natural plant elements juxtaposed with technology
- Studio-lit, editorial quality with deep blacks and crisp whites
- Abstract organic shapes and botanical references
- Floating/isolated product shots with dramatic lighting

---

## Known Pitfalls

- Don't soften the contrast — this aesthetic requires stark black/white
- Avoid colorful accents — the monochrome palette is intentional
- Don't add gradient overlays — clean solid backgrounds only
- Keep copy minimal — resist the urge to over-explain
- Don't use typical health industry pastels or blues
- Avoid stock lifestyle photography — product-first approach works here
- Don't round corners inconsistently — pill buttons with large card radii
- Stats sections need counter animations — don't make them static

---

## Reference Sites

- https://www.sofihealth.com/

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Initial preset created | sofihealth.com analysis |
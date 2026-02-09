# Preset: Nike Golf (URL-Extracted)

Industries: Athletic apparel, sports equipment e-commerce, performance gear, branded athletic category pages

Source: Extracted from https://www.nike.com/ch/en/w/golf-23q9w via Playwright

---

## Default Section Sequence

```
1. NAV              | sticky-solid
2. HERO             | full-bleed-overlay
3. LOGO-BAR         | scrolling-marquee
4. PRODUCT-SHOWCASE | category-grid
5. FEATURES         | bento-grid
6. STATS            | counter-animation
7. PRODUCT-SHOWCASE | hover-cards
8. CTA              | split-with-image
9. NEWSLETTER       | inline
10. FOOTER          | mega
```

**Optional sections (add based on brief):**
- TESTIMONIALS (if athlete endorsements available) → insert after STATS
- FAQ (if product questions needed) → insert before CTA

---

## Style Configuration

```yaml
color_temperature: light-neutral

palette:
  bg_primary: white
  bg_secondary: gray-50
  bg_accent: gray-100
  text_primary: neutral-900
  text_heading: black
  text_muted: gray-500
  accent: black
  accent_hover: neutral-800
  border: gray-200

typography:
  pairing: geometric-sans
  heading_font: Inter
  heading_weight: 700
  body_font: Inter
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: medium-contrast
  note: "Nike uses proprietary Helvetica Now. Inter is the closest Google Font equivalent."

whitespace: spacious
section_padding: py-20
internal_gap: gap-8

border_radius: full
buttons: rounded-full
cards: rounded-3xl
inputs: rounded-full

animation_engine: gsap
animation_intensity: moderate
entrance: fade-up-stagger
hover: lift-subtle
timing: "0.4s ease-out"
smooth_scroll: false
section_overrides: hero:fade-in stats:count-up features:stagger-children

visual_density: airy
image_treatment: full-bleed
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: light-neutral — bg:white/gray-50 text:neutral-900 accent:black border:gray-200
Type: geometric-sans — heading:Inter,700 body:Inter,400 scale:1.250
Space: spacious — sections:py-20 internal:gap-8
Radius: full — buttons:rounded-full cards:rounded-3xl inputs:rounded-full
Motion: moderate/gsap — entrance:fade-up-stagger hover:lift-subtle timing:0.4s ease-out | hero:fade-in stats:count-up features:stagger-children
Density: airy | Images: full-bleed
═══════════════════════
```

---

## Content Direction

**Tone:** Confident, performance-focused, minimalist, empowering

**Hero copy pattern:** Direct category naming with product counts (e.g., "Golf(107)"). Minimal descriptive text, letting imagery convey the brand experience. Brief, impactful statements about data and personalization when needed.

**CTA language:** Action-oriented and decision-focused. Use directive language ("Accept All", "Confirm Choices", "Learn more about..."). CTAs are clear, concise commands rather than conversational invitations. Category labels double as navigation CTAs ("Brands").

---

## Photography / Visual Direction

- Full-bleed hero imagery showcasing athletes in action or product lifestyle contexts
- High-contrast photography with strong blacks and whites
- Clean product shots against minimal or solid backgrounds
- Athletic action photography emphasizing movement and performance
- Diverse representation of athletes across different sports and activities
- Imagery focuses on the product in use rather than studio isolation
- Overlay text should have sufficient contrast (white on dark imagery, black on light)
- Icon-based features use simple, geometric symbols aligned with the brand's minimal aesthetic

---

## Known Pitfalls

- Avoid cluttering the minimal aesthetic with excessive text or decorative elements
- Don't use soft or rounded typography that conflicts with the sharp, modern Helvetica system
- Resist adding warm color accents that break the cool, neutral palette
- Avoid small border radii that feel dated against the 24-30px rounded elements
- Don't over-animate; keep transitions subtle to maintain the premium, controlled feel
- Ensure sufficient color contrast when placing dark text on gray backgrounds
- Mega footers require careful hierarchy planning to avoid overwhelming users
- Cookie/privacy modals need clear visual priority without disrupting the brand experience
- Product grids should maintain generous whitespace to avoid feeling cramped

---

## Reference Sites

- https://www.nike.com/ch/en/w/golf-23q9w

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-09 | Initial preset extracted from URL via Playwright | Nike Golf CH |
| 2026-02-09 | Fixed palette (black→white bg), mapped fonts to Google Fonts (Inter) | Nike Golf CH |
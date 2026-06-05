# Preset: E-commerce Lifestyle Apparel

Industries: streetwear brands, athletic apparel, lifestyle clothing, urban fashion, fitness wear, DTC apparel brands

---

## Default Section Sequence

```
1. HERO                 | full-bleed-overlay
2. FEATURES             | icon-grid
3. PRODUCT-SHOWCASE     | hover-cards
4. LOGO-BAR             | scrolling-marquee
5. PRODUCT-SHOWCASE     | hover-cards
6. LOGO-BAR             | inline
7. CTA                  | centered
8. VIDEO                | full-width-embed
9. TEAM                 | grid-with-hover
10. STATS               | counter-animation
11. LOGO-BAR            | scrolling-marquee
12. FAQ                 | accordion
```

**Optional sections (add based on brief):**
- TESTIMONIALS (if social proof needed) → insert after section 5
- PRODUCT-GRID (if large inventory) → insert after section 3
- NEWSLETTER (if list building focus) → insert before FAQ

---

## Style Configuration

```yaml
color_temperature: dark-neutral
palette:
  bg_primary: black
  bg_secondary: gray-950
  bg_accent: yellow-400
  text_primary: white
  text_heading: white
  text_muted: gray-600
  accent: yellow-400
  accent_hover: yellow-300
  border: gray-800

typography:
  pairing: sans-display
  heading_font: Anton
  heading_weight: 400
  body_font: Inter
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: consistent

whitespace: compact
section_padding: 4rem
internal_gap: 2rem

border_radius: pill
buttons: 500px
cards: 10px
inputs: 4px

animation_engine: css
animation_intensity: expressive
entrance: fade-slide
hover: lift-glow
timing: 0.3s ease-in-out
smooth_scroll: false
section_overrides: stats:counter-animation logo-bar:scrolling-marquee team:grid-with-hover
gsap_plugins: []

visual_density: balanced
image_treatment: vibrant-overlay
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: black/gray-950 + yellow-400 accent on dark-neutral
Type: Anton/Inter sans-display 1.25 consistent
Space: compact 4rem/2rem
Radius: pill (buttons:500px cards:10px inputs:4px)
Motion: expressive/css — entrance:fade-slide hover:lift-glow timing:0.3s ease-in-out | stats:counter-animation logo-bar:scrolling-marquee team:grid-with-hover
Density: balanced | Images: vibrant-overlay
═══════════════════════
```

---

## Content Direction

**Tone:** Bold, energetic, street-confident. Short punchy statements with high contrast messaging. Emphasis on exclusivity and movement culture.

**Hero copy pattern:** Single powerful word or two-word phrase in oversized display type over immersive imagery. Examples: "HALL OF FAME" / "Joga Starz" / "Warehouse SALE"

**CTA language:** Action-forward with additive syntax. Use "ADD TO CART +" format with symbol reinforcement. Secondary CTAs use simple labels like "FAQ's" or "SUBMIT" in all caps.

---

## Photography / Visual Direction

- High-contrast lifestyle photography with deep blacks and vibrant colors
- Active lifestyle shots showing movement and urban environments
- Product photography on dark backgrounds with dramatic lighting
- Video content showcasing brand energy and product in action
- Team/ambassador photography with authentic street style aesthetic
- Hover states reveal additional product angles or context

---

## Known Pitfalls

- Yellow accent (#fff304) is extremely bright — ensure sufficient contrast on dark backgrounds and test accessibility
- Pill-radius buttons (500px) require careful padding balance to avoid awkward proportions on varying text lengths
- Scrolling marquee logos can cause motion sickness — provide pause-on-hover functionality
- Dark theme requires careful attention to form input visibility and focus states
- Anton display font at small sizes loses legibility — maintain minimum 24px for headings
- Counter animations on stats should respect prefers-reduced-motion
- Full-bleed video embeds need mobile optimization strategy to avoid bandwidth issues

---

## Reference Sites

- https://shopjoga.com

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Initial preset created | shopjoga.com analysis |
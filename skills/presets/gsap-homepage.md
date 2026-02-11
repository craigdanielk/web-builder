# Preset: Animation Platform / Developer Tools

Industries: Developer tools, JavaScript libraries, animation platforms, technical SaaS, creative coding tools, web development services

---

## Default Section Sequence

```
1. NAV              | sticky-transparent
2. HERO             | full-bleed-animated
3. FEATURES         | split-media (Why GSAP — value proposition)
4. FEATURES         | icon-grid (Animate Anything — capabilities demo)
5. FEATURES         | interactive-demo (Easing — visual curves demo)
6. PRODUCT-SHOWCASE | card-grid (GSAP Tools — Scroll, SVG, Text, UI)
7. TRUST-BADGES     | logo-cloud (Brands using GSAP)
8. GALLERY          | showcase-reel (Showcase — featured sites)
9. CTA              | centered (Get GSAP / Newsletter)
10. FOOTER          | mega
```

**Optional sections (add based on brief):**
- PRICING (if monetization model present) → insert before CTA
- TESTIMONIALS (if social proof needed) → insert after TRUST-BADGES

---

## Style Configuration

```yaml
color_temperature: dark-neutral

palette:
  bg_primary: black
  bg_secondary: stone-950
  bg_accent: amber-50
  text_primary: amber-50
  text_heading: amber-50
  text_muted: stone-500
  accent: orange-500
  accent_hover: orange-600
  border: stone-800

typography:
  pairing: single-family
  heading_font: Inter
  heading_weight: 700
  body_font: Inter
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: balanced

whitespace: generous
section_padding: 7rem
internal_gap: 3rem

border_radius: medium
buttons: 100px
cards: 8px
inputs: 8px

animation_engine: gsap
animation_intensity: expressive
entrance: fade-slide-up
hover: lift-glow
timing: cubic-bezier(0.645, 0.045, 0.355, 1)
smooth_scroll: true
section_overrides: hero:character-reveal features:stagger-in footer:none

visual_density: spacious
image_treatment: high-contrast
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: dark-neutral (black/stone-950/amber-50/orange-500)
Type: Inter 700/400 @ 1.25 scale
Space: generous (7rem/3rem)
Radius: medium (buttons:100px cards:8px)
Motion: expressive/gsap — entrance:fade-slide-up hover:lift-glow timing:cubic-bezier(0.645, 0.045, 0.355, 1) | hero:character-reveal features:stagger-in
Density: spacious | Images: high-contrast
═══════════════════════
```

---

## Content Direction

**Tone:** Professional, confident, technically authoritative. Direct language that speaks to experienced developers. Emphasis on performance, robustness, and professional-grade capabilities.

**Hero copy pattern:** Bold capability statement + technical credibility reinforcement. Format: "[Action Verb] + [Scope]" headline followed by "wildly robust" technical descriptor with profession-specific qualifier.

**CTA language:** Direct action verbs with technical context. "Tools", "Login/Create Account", "Sign In" — utilitarian and functional rather than persuasive. Assumes user intent and knowledge.

---

## Photography / Visual Direction

- Dark, sophisticated UI with high contrast
- Code-focused demonstrations and animated examples
- Abstract geometric patterns and grid systems
- Neon accent colors (purple, pink, orange) against dark backgrounds
- Minimal photography, maximum focus on animation demonstrations
- Terminal/IDE aesthetic influences
- Smooth gradient overlays and ambient lighting effects

---

## Known Pitfalls

- Animation intensity may overwhelm users on lower-end devices — provide reduced motion fallbacks
- Dark backgrounds require careful contrast management for accessibility compliance
- Multiple feature sections with icon-grid can feel repetitive — vary content density and visual hierarchy
- GSAP-heavy sites may have performance issues if not properly optimized — implement lazy loading for scroll-triggered animations
- Technical audience expects functional perfection — ensure all interactive elements are polished
- Pill-shaped buttons (100px radius) must maintain adequate padding for readability

---

## Reference Sites

- https://gsap.com/

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2024 | Initial preset created | gsap.com analysis |
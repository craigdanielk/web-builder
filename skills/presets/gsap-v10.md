# Preset: Animation Platform / Creative Developer Tools

Industries: animation software, developer tools, creative technology platforms, JavaScript libraries, web animation services, technical documentation sites

---

## Default Section Sequence

```
1. HERO                 | full-bleed-overlay
2. FEATURES             | icon-grid
3. FEATURES             | icon-grid
4. PRODUCT-SHOWCASE     | hover-cards
5. LOGO-BAR             | scrolling-marquee
6. GALLERY              | lightbox-grid
```

**Optional sections (add based on brief):**
- TESTIMONIALS (if user quotes available) → insert after FEATURES
- PRICING (if monetization model) → insert before LOGO-BAR
- HOW-IT-WORKS (if tutorial content) → insert after HERO

---

## Reference Sites

- https://gsap.com/

---

## Style Configuration

```yaml
color_temperature: dark-vibrant
palette:
  bg_primary: black
  bg_secondary: gray-950
  bg_accent: yellow-100
  text_primary: yellow-100
  text_heading: yellow-100
  text_muted: gray-500
  accent: orange-500
  accent_hover: orange-600
  accent_secondary: indigo-300
  accent_tertiary: cyan-600
  accent_quaternary: green-500
  accent_quinary: green-300
  border: gray-800

section_accents:
  section-3: fuchsia-200

typography:
  pairing: single-modern
  heading_font: Mori
  heading_weight: 700
  body_font: Mori
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: single-weight

whitespace: spacious
section_padding: 8rem
internal_gap: 3rem

border_radius: medium
buttons: 100px
cards: 8px
inputs: 8px

animation_engine: gsap
animation_intensity: expressive
entrance: stagger-fade-up
hover: lift-glow
timing: 0.6s ease-out
smooth_scroll: true
section_overrides:
  hero: character-reveal+morph-path
  features: icon-morph+flow-along-path
  product-showcase: flip-filter+draggable-slider
  gallery: flip-layout+observer-swipe
gsap_plugins:
  - GSAP
  - ScrollTrigger
  - ScrollSmoother
  - DrawSVG
  - MotionPath
  - CustomEase
  - SplitText
  - Flip
  - MorphSVG
  - Draggable
  - Observer

visual_density: breathable
image_treatment: high-contrast-overlay
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: dark-vibrant (black/gray-950/yellow-100) | Accents: orange:orange-500 indigo:indigo-300 cyan:cyan-600 green:green-500 lime:green-300
Type: Mori/Mori (single-modern) | Scale: 1.25 | Wt: single-weight
Space: spacious (8rem/3rem)
Radius: medium (buttons:100px cards:8px)
Motion: expressive/gsap — entrance:stagger-fade-up hover:lift-glow timing:0.6s ease-out | hero:character-reveal+morph-path features:icon-morph+flow-along-path product-showcase:flip-filter+draggable-slider gallery:flip-layout+observer-swipe
Density: breathable | Images: high-contrast-overlay
Plugins: GSAP ScrollTrigger ScrollSmoother DrawSVG MotionPath CustomEase SplitText Flip MorphSVG Draggable Observer
═══════════════════════
```

---

## Content Direction

**Tone:** technical-confident, developer-focused, bold and direct with professional energy. Emphasizes power, performance, and professional-grade capabilities.

**Hero copy pattern:** Direct value statement + technical credibility → "GSAP – A wildly robust JavaScript animation library built for professionals" / "Animate Anything" — leads with capability and authority, speaks to power users.

**CTA language:** Action-focused and utilitarian → "Sign In", "Login/Create Account", "Tools" — minimal friction, assumes user intent and technical literacy.

---

## Photography / Visual Direction

- High-contrast neon-on-dark aesthetic with vibrant accent colors (orange, purple, cyan, green)
- Code-centric and technical visualization — animated code snippets, interface mockups, performance graphs
- Dynamic motion showcases — abstract geometric animations, particle systems, fluid morphing shapes
- Minimal photography, maximum technical demonstration through interactive examples
- Glowing edges and vibrant borders to emphasize interactive elements
- Dark backgrounds to maximize contrast with bright accent colors and reduce eye strain for developers

---

## Known Pitfalls

- Avoid over-explaining basics — audience is technical and wants to see capabilities immediately
- Don't bury documentation or code examples — developers need immediate access to implementation details
- Multi-accent palette requires careful management — establish clear hierarchy to prevent visual chaos (primary orange, secondary purple for alternate CTAs)
- High animation intensity can impact performance if not optimized — essential for this industry but must be flawlessly smooth
- Dark theme requires careful contrast management for accessibility — ensure yellow-100 text maintains WCAG AA against black backgrounds
- Technical audiences are skeptical of marketing speak — prioritize demonstrations over claims
- Avoid generic stock imagery — every visual should demonstrate actual product capabilities

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Preset created from GSAP.com analysis | gsap.com |
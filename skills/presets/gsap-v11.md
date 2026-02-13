# Preset: Animation Platform / Developer Tools

Industries: animation software, developer tools, JavaScript libraries, creative technology platforms, technical SaaS

---

## Reference Sites
- https://gsap.com

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
- STATS (if showcasing usage metrics) → insert after HERO
- HOW-IT-WORKS (if explaining implementation) → insert after first FEATURES
- PRICING (if tiered product) → insert after PRODUCT-SHOWCASE
- CTA (if conversion focus) → insert before GALLERY

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
  accent_tertiary: cyan-500
  accent_quaternary: green-500
  border: gray-800

section_accents:
  features-3: fuchsia-200
  product-showcase: green-300

typography:
  pairing: single-family-geometric
  heading_font: Mori
  heading_weight: 700
  body_font: Mori
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: wide

whitespace: generous
section_padding: 7xl
internal_gap: 2xl

border_radius: medium
buttons: 100px
cards: 8px
inputs: 8px

animation_engine: gsap
animation_intensity: expressive
entrance: fade-up-cascade
hover: lift-glow
timing: 0.6s custom-ease
smooth_scroll: true
section_overrides:
  hero: character-reveal+orbit
  features: icon-morph+flow-along-path
  product-showcase: filter-grid+slider
  gallery: layout-transition+swipe
  stats: count-up
  how-it-works: path-progress

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

visual_density: spacious
image_treatment: dark-vignette
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: dark-vibrant (black/yellow-100) | Accents: primary:orange-500 secondary:indigo-300 tertiary:cyan-500 quaternary:green-500
Type: Mori/Mori (geometric, 1.25 ratio, wide weights)
Space: generous (7xl section, 2xl internal)
Radius: medium (buttons:pill cards:8px)
Motion: expressive/gsap — entrance:fade-up-cascade hover:lift-glow timing:0.6s custom-ease | hero:character-reveal+orbit features:icon-morph+flow-along-path product-showcase:filter-grid+slider gallery:layout-transition+swipe stats:count-up how-it-works:path-progress | smooth_scroll:true
Density: spacious | Images: dark-vignette
═══════════════════════
```

---

## Content Direction

**Tone:** Technical confidence with creative energy — bold declarative statements, minimal fluff, developer-focused clarity with enthusiastic edge

**Hero copy pattern:** Power statement + capability descriptor format
- Lead with action verb ("Animate Anything")
- Follow with authoritative descriptor emphasizing robustness and professional focus
- Example structure: "[Action Verb] [Universal Noun]" + "A wildly [quality] [technology type] built for [audience]"

**CTA language:** Direct action-oriented (Tools, Login/Create Account) — prioritize functionality over persuasion, use clear technical terminology

---

## Photography / Visual Direction

- Abstract colorful gradients and vibrant glowing shapes on dark backgrounds
- Code visualization and animation path demonstrations
- High-contrast neon accent colors (orange, purple, cyan, green) against pure black
- Animated UI elements and interface components as hero content
- Geometric shapes with motion blur and trail effects
- No photography — focus on digital illustration and animated graphics
- Liquid/fluid morphing shapes and particle effects
- Glowing outlines and luminescent accents

---

## Known Pitfalls

- Don't dilute the multi-accent strategy — this palette needs 4-5 distinct vibrant accents to match the energetic developer tool aesthetic
- Avoid reducing animation intensity — expressive motion is core to the brand identity (it's an animation platform)
- Don't substitute the geometric sans-serif — technical tools need geometric precision in typography
- Maintain generous whitespace despite dark background — prevent claustrophobic feeling
- Ensure sufficient contrast with yellow-100 text on black (meets WCAG AAA)
- Don't add photography where abstract graphics are specified — keep it digital/technical
- Section-specific accent colors are intentional — preserve the features-3 fuchsia and product-showcase green overrides
- Custom easing curves are brand-defining — don't default to CSS ease presets
- ScrollSmoother integration is critical — native scroll won't match the reference experience

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Preset created from gsap.com extraction | gsap.com design analysis |
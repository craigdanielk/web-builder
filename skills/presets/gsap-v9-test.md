# Preset: Animation Platform / Dev Tools

Industries: animation libraries, developer tools, SaaS platforms, creative software, JavaScript frameworks, technical documentation sites

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
- PRICING (if subscription model) → insert after section 4
- TESTIMONIALS (if customer logos present) → insert after section 5
- FAQ (if technical product) → insert after section 6

---

## Style Configuration

```yaml
color_temperature: dark-neutral
palette:
  bg_primary: black
  bg_secondary: gray-950
  bg_accent: yellow-50
  text_primary: yellow-50
  text_heading: yellow-50
  text_muted: gray-500
  accent: orange-500
  accent_hover: orange-600
  accent_secondary: indigo-300
  accent_tertiary: cyan-500
  border: gray-800

section_accents:
  section-3: fuchsia-200
  features-alt: green-400

typography:
  pairing: sans-serif
  heading_font: Mori
  heading_weight: 700
  body_font: Mori
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: 400/700

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
hover: scale-lift
timing: 0.6s cubic-bezier(0.32, 0, 0.355, 1)
smooth_scroll: false
section_overrides: hero:character-reveal features:stagger-in showcase:hover-cards marquee:infinite-scroll

visual_density: spacious
image_treatment: crisp-screenshots
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: dark-neutral (black/gray-950 + yellow-50 text)
Type: Mori/Mori 400/700 @1.25
Space: generous (7rem/3rem)
Radius: medium (buttons:pill cards:8px)
Motion: expressive/gsap — entrance:fade-slide-up hover:scale-lift timing:0.6s cubic-bezier(0.32, 0, 0.355, 1) | hero:character-reveal features:stagger-in showcase:hover-cards marquee:infinite-scroll
Density: spacious | Images: crisp-screenshots
Accents: primary:orange-500 secondary:indigo-300 tertiary:cyan-500 green:green-400 pink:fuchsia-200
═══════════════════════
```

---

## Content Direction

**Tone:** Technical-confident, professional yet energetic, developer-focused with bold claims backed by capability

**Hero copy pattern:** Power statement headline (2-3 words) + descriptive subheading emphasizing performance and professional-grade capability. Example: "Animate Anything" → "A wildly robust JavaScript animation library built for professionals"

**CTA language:** Direct action verbs with account-gating emphasis. Primary: "Login/Create Account" | Secondary: "Tools" (product navigation). Uses benefit-focused prompts like "Why create an account?" to overcome friction.

---

## Photography / Visual Direction

- Crisp, high-contrast code demos and UI screenshots on dark backgrounds
- Vibrant multi-colored accent highlights (orange, indigo, cyan, green, pink) for emphasis and code syntax
- Animated demonstrations showing before/after states
- Abstract geometric patterns and gradient overlays
- Developer workspace aesthetics (terminal windows, code editors)
- Minimal photography; focus on interface and animation examples
- High-energy visual effects: glow effects, motion trails, neon accents

---

## Known Pitfalls

- Multi-accent system can feel chaotic if not carefully balanced — reserve bright colors (green, pink) for specific feature highlights
- Dark background with yellow text requires careful contrast management for accessibility
- GSAP-powered animations must have fallback states for users with reduced motion preferences
- Pill-shaped buttons (100px radius) may look odd at very small or very large sizes — set min/max widths
- Scrolling marquee can cause motion sickness — ensure pause-on-hover and respect prefers-reduced-motion
- Technical audience expects fast load times despite heavy animation — lazy load all GSAP features
- Dark theme requires careful form input styling for visibility

---

## Reference Sites

- https://gsap.com/

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2024 | Initial preset created | gsap.com analysis |
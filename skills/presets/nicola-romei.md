# Preset: Creative Portfolio / Digital Studio

Industries: Creative agencies, design studios, web designers, digital artists, freelance creatives, brand studios, interactive developers

---

## Default Section Sequence

```
1. HERO               | full-viewport-statement
2. ABOUT/INTRO        | text-image-split
3. WORK/PORTFOLIO     | grid-showcase
4. SERVICES           | icon-grid
5. TESTIMONIALS       | slider-minimal
6. CONTACT            | centered-form
7. FOOTER             | minimal-credits
```

**Optional sections (add based on brief):**
- STATS (if metrics/achievements emphasized) → insert after position 2
- CLIENTS (if brand showcase needed) → insert after position 3
- PROCESS (if methodology important) → insert after position 4

---

## Style Configuration

```yaml
color_temperature: dark-neutral

palette:
  bg_primary: black
  bg_secondary: gray-900
  bg_accent: stone-100
  text_primary: gray-50
  text_heading: white
  text_muted: stone-300
  accent: blue-600
  accent_hover: blue-700
  border: gray-800

typography:
  pairing: modern-grotesk
  heading_font: Host Grotesk
  heading_weight: 700
  body_font: Host Grotesk
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: minimal-contrast

whitespace: generous
section_padding: 8rem
internal_gap: 3rem

border_radius:
  buttons: sharp
  cards: sharp
  inputs: sharp

animation_engine: gsap
animation_intensity: expressive
entrance: character-reveal, fade-up-stagger
hover: lift-subtle, color-shift
timing: 0.6s cubic-bezier(0.4, 0, 0.2, 1)
smooth_scroll: true
section_overrides: hero:character-reveal work:parallax-scroll cta:magnetic-hover

visual_density: spacious
image_treatment: high-contrast-desaturated
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: Dark-neutral — black/gray-900 bg, white/gray-50 text, blue-600 accent
Type: Host Grotesk/Host Grotesk — 1.25 scale, minimal-contrast weights
Space: Generous — 8rem section, 3rem internal
Radius: Sharp — 0-4px all elements
Motion: expressive/gsap — entrance:character-reveal,fade-up-stagger hover:lift-subtle,color-shift timing:0.6s cubic-bezier(0.4,0,0.2,1) | hero:character-reveal work:parallax-scroll cta:magnetic-hover
Density: Spacious | Images: high-contrast-desaturated
═══════════════════════
```

---

## Content Direction

**Tone:** Confident, minimal, artistic. Statements over explanations. Brand-first language with studio credibility.

**Hero copy pattern:** Bold declarative statements. Product/service names styled as trademarks (e.g., "the artboard™"). Single-line impact phrases with typographic emphasis. Minimal supporting text.

**CTA language:** Direct, lowercase preferred. Simple verbs: "view work", "get in touch", "explore", "see more". No heavy sales language—assume interest.

---

## Photography / Visual Direction

- High-contrast black and white or desaturated imagery
- Full-bleed hero visuals with typographic overlays
- Portfolio pieces presented as crisp mockups against dark backgrounds
- Minimal photography; prioritize work samples and graphics
- Abstract textures or geometric patterns as accents
- Retro CRT/glitch effects as optional overlays
- Generous negative space around all imagery
- Grid-based layouts with asymmetric focal points

---

## Known Pitfalls

- Don't dilute the dark aesthetic with too many light sections—maintain visual weight
- Avoid cluttered portfolios; limit items per row and prioritize whitespace
- Character-reveal animations must be smooth; test font rendering at various sizes
- Custom fonts (Host Grotesk) require proper fallbacks; ensure loading strategy doesn't cause flash
- GSAP ScrollTrigger must be properly disposed on route changes to prevent memory leaks
- Magnetic hover effects need performance optimization on mobile—consider disable below tablet
- Three.js elements (if used) should be lazy-loaded and have low-power fallbacks
- Maintain accessibility with dark theme: ensure minimum 4.5:1 contrast ratios
- CRT/glitch effects should be subtle and respect prefers-reduced-motion

---

## Reference Sites

- https://www.nicolaromei.com/

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Preset created | nicolaromei.com analysis |
# Preset: Health & Wellness

Industries: wellness clinics, yoga studios, fitness studios, spas, meditation apps,
holistic health, nutritionists, mental health practices, retreat centers.

---

## Default Section Sequence

```
1. NAV              | sticky-transparent
2. HERO             | centered (serene, calming imagery)
3. ABOUT            | editorial-split (philosophy / approach)
4. HOW-IT-WORKS     | icon-steps (the journey / process)
5. FEATURES         | cards-with-hover (services or offerings)
6. TESTIMONIALS     | carousel
7. PRICING          | three-tier
8. CTA              | split-with-image
9. NEWSLETTER       | inline
10. FOOTER          | minimal
```

**Optional sections (add based on brief):**
- STATS (if strong outcome data) → insert after ABOUT
- GALLERY (if space/studio photography) → insert after FEATURES
- VIDEO (if guided session or brand video) → insert after HERO
- FAQ (if complex service tiers) → insert after PRICING
- BLOG-PREVIEW (if wellness content active) → insert before NEWSLETTER

---

## Style Configuration

```yaml
color_temperature: pastel
palette:
  bg_primary: green-50
  bg_secondary: white
  bg_accent: violet-50
  text_primary: stone-800
  text_heading: stone-900
  text_muted: stone-500
  accent: green-600
  accent_hover: green-700
  border: stone-200

typography:
  pairing: humanist
  heading_font: Open Sans
  heading_weight: 600
  body_font: Open Sans
  body_weight: 400
  scale_ratio: 1.333
  weight_distribution: medium-regular

whitespace: generous
section_padding: py-24
internal_gap: gap-8

border_radius: full
buttons: rounded-2xl
cards: rounded-3xl
inputs: rounded-xl

animation_intensity: subtle
entrance: fade-up
hover: slight-lift
timing: "0.5s ease-out"

visual_density: low
image_treatment: contained
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: pastel — bg:green-50/white text:stone-800 accent:green-600 border:stone-200
Type: humanist — heading:Open Sans,600 body:Open Sans,400 scale:1.333
Space: generous — sections:py-24 internal:gap-8
Radius: full — buttons:rounded-2xl cards:rounded-3xl inputs:rounded-xl
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.5s ease-out
Density: low | Images: contained
═══════════════════════
```

---

## Content Direction

**Tone:** Warm, calm, empathetic. Second person ("you" / "your journey"). Gentle
encouragement, never pushy. Language should feel like a caring practitioner —
reassuring, knowledgeable, unhurried. Avoid clinical coldness and Instagram
wellness clichés equally.

**Hero copy pattern:** Lead with the transformation or feeling, not the service.
"Find your stillness" or "Where healing begins" — not "Book a yoga class."
Pair with a serene image that evokes the end state (calm, balance, vitality).

**How-it-works (journey):** Frame as a gentle 3-4 step path. "Discover →
Experience → Transform" or "Consult → Design → Practice → Thrive." Each step
should feel inviting, not procedural.

**Pricing:** Name tiers after the experience, not a corporate ladder. "Essential,"
"Guided," "Immersive" — not "Basic," "Pro," "Enterprise."

**CTA language:** Inviting and gentle. "Begin your journey" / "Book a session" /
"Explore our offerings" — never aggressive urgency or countdown timers.

---

## Photography / Visual Direction

- Natural light, airy compositions with soft shadows
- Muted, warm color grading — never harsh or over-saturated
- Real people in genuine moments of practice (not posed stock models)
- Nature elements woven in: plants, water, natural textures, wood, stone
- Negative space in photos should echo the generous whitespace of the layout

---

## Known Pitfalls

- Pastel palettes can feel washed-out and lose hierarchy. The green-600 accent
  must carry enough weight to anchor CTAs and interactive elements against the
  soft green-50 background.
- "Full" border radius on everything can tip into childish if overused. Reserve
  rounded-3xl for cards only — buttons at rounded-2xl and inputs at rounded-xl
  maintain enough structure.
- Generous whitespace + low density can make the page feel empty on desktop.
  Ensure each section has enough substance (meaningful copy, quality imagery)
  to justify the space it occupies.
- Wellness is a trust-sensitive industry. Testimonials need real names and
  specifics — vague praise feels manufactured in this context.

---

## Reference Sites

Study these for pattern validation (not copying):
- Headspace, ClassPass, Equinox, WellSet, Calm
- Look for: color palette softness, typography warmth, how they maintain
  visual interest with low density, CTA gentleness, imagery authenticity

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

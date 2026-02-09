# Preset: Sports & Fitness

Industries: athletic equipment, fitness apparel, supplements, gym equipment, outdoor
sports gear, performance wear.

---

## Default Section Sequence

```
1. NAV              | sticky-solid
2. HERO             | video-background
3. STATS            | counter-animation
4. PRODUCT-SHOWCASE | grid
5. FEATURES         | bento-grid
6. HOW-IT-WORKS     | numbered-steps
7. TESTIMONIALS     | carousel
8. CTA              | gradient-block
9. FOOTER           | mega
```

**Optional sections (add based on brief):**
- LOGO-BAR (if athlete endorsements or partnerships) → insert after HERO
- COMPARISON (if competing against incumbents) → insert after FEATURES
- FAQ (if supplement/equipment questions) → insert before CTA
- APP-DOWNLOAD (if companion app) → insert before CTA

---

## Style Configuration

```yaml
color_temperature: dark
palette:
  bg_primary: gray-950
  bg_secondary: gray-900
  bg_accent: gray-800
  text_primary: gray-100
  text_heading: white
  text_muted: gray-400
  accent: lime-400
  accent_hover: lime-300
  border: gray-700

typography:
  pairing: geometric-sans
  heading_font: Space Grotesk
  heading_weight: 700
  body_font: Space Grotesk
  body_weight: 400
  scale_ratio: 1.250
  weight_distribution: heavy-light

whitespace: tight
section_padding: py-16
internal_gap: gap-6

border_radius: medium
buttons: rounded-lg
cards: rounded-xl
inputs: rounded-lg

animation_intensity: moderate
entrance: fade-up-stagger
hover: lift-shadow
timing: "0.4s ease-out"

visual_density: high
image_treatment: full-bleed
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: dark — bg:gray-950/gray-900 text:gray-100 accent:lime-400 border:gray-700
Type: geometric-sans — heading:Space Grotesk,700 body:Space Grotesk,400 scale:1.250
Space: tight — sections:py-16 internal:gap-6
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: moderate — entrance:fade-up-stagger hover:lift-shadow timing:0.4s ease-out
Density: high | Images: full-bleed
═══════════════════════
```

---

## Content Direction

**Tone:** Bold, direct, motivational without being cheesy. Second person imperative
("Push harder" / "Train smarter"). Short punchy sentences. Data-driven where
possible — percentages, metrics, results.

**Hero copy pattern:** Lead with a challenge or aspiration, backed by the product.
"Engineered for your next PR" or "No limits. No excuses." Action words, not
descriptions.

**CTA language:** Direct and energizing. "Start training" not "Learn more."
"Get yours" not "Shop now." "Join the movement" not "Sign up." Always imply
action and transformation.

---

## Photography / Visual Direction

- Action shots — mid-movement, high energy, sweat and intensity
- Dark environments with dramatic lighting — spotlight effects, rim light
- Bold color accents matching the lime-400 palette in clothing or equipment
- Athletes in real environments — gym, track, outdoors — never stock
- Motion blur and dynamic angles for energy — avoid static posed shots

---

## Known Pitfalls

- Neon accent (lime-400) on dark backgrounds is high-energy but can strain eyes
  if overused. Reserve for CTAs, key stats, and small highlights — not large
  text blocks.
- High density and tight whitespace can quickly become cluttered. Use the
  bento-grid structure to create visual variety within the density.
- Video backgrounds must load fast — compress aggressively and provide a strong
  poster frame. Slow-loading video kills the energy immediately.
- Counter-animation stats need real, impressive numbers. Generic stats
  ("1000+ customers") feel weak in the sports context. Use performance metrics
  like speed, weight, or percentage improvements.

---

## Reference Sites

Study these for pattern validation (not copying):
- Nike, Gymshark, Peloton, Whoop, Under Armour
- Look for: hero video treatment, stats presentation, product grid
  density, accent color usage, mobile animation performance

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

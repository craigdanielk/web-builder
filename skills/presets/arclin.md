# Preset: Industrial Materials & Manufacturing

Industries: building materials, industrial manufacturing, chemical products, material science, B2B manufacturing, specialty materials, sustainable materials

---

## Default Section Sequence

```
1. HERO                 | minimal-statement
2. PRODUCT-SHOWCASE     | hover-cards
3. STATS                | counter-animation
4. FEATURES             | icon-grid
5. FEATURES             | icon-grid
6. FEATURES             | icon-grid
7. CTA                  | full-width
8. FOOTER               | mega
```

**Optional sections (add based on brief):**
- TEAM (if highlighting community/partnership focus) → insert after STATS
- TESTIMONIALS (if showcasing industry partnerships) → insert before final CTA
- LOCATIONS (if multi-facility operation) → insert before FOOTER

---

## Style Configuration

```yaml
color_temperature: warm-earth-dark
palette:
  bg_primary: stone-50
  bg_secondary: white
  bg_accent: stone-950
  text_primary: stone-900
  text_heading: stone-950
  text_muted: stone-600
  accent: stone-800
  accent_hover: stone-950
  border: stone-200

typography:
  pairing: serif-heading-mono-body
  heading_font: Arclin Serif
  heading_weight: 400
  body_font: General Grotesque Mono
  body_weight: 400
  scale_ratio: 1.333
  weight_distribution: light-medium

whitespace: generous
section_padding: large
internal_gap: relaxed

border_radius:
buttons: sharp
cards: sharp
inputs: sharp

animation_engine: gsap
animation_intensity: expressive
entrance: fade-up-stagger
hover: lift-subtle
timing: 0.8s ease-out
smooth_scroll: false
section_overrides: stats:count-up product-showcase:hover-reveal

visual_density: airy
image_treatment: full-bleed-editorial
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: warm-earth-dark (stone-50→stone-950, serif+mono contrast)
Type: Arclin Serif/General Grotesque Mono • 1.333 scale • light-medium weights
Space: generous padding, relaxed gaps, airy density
Radius: sharp (0-4px all elements)
Motion: expressive/gsap — entrance:fade-up-stagger hover:lift-subtle timing:0.8s ease-out | stats:count-up product-showcase:hover-reveal
Density: airy | Images: full-bleed-editorial
═══════════════════════
```

---

## Content Direction

**Tone:** Sophisticated, forward-thinking, grounded in expertise. Emphasizes innovation, sustainability, and partnership. Professional yet approachable. Uses aspirational language balanced with practical benefits.

**Hero copy pattern:** Bold declarative statements about innovation and impact, followed by value propositions. Pattern: "[Action verb] with [quality descriptor] materials for [aspirational outcome]"

**CTA language:** Direct and benefit-focused. Uses imperative verbs: "Find," "Build," "Create," "Collaborate," "Bring to life." Focuses on exploration and partnership rather than hard selling.

---

## Photography / Visual Direction

- Full-bleed, high-quality product and application photography
- Close-up material textures showing detail and quality
- Environmental shots showing products in real-world applications
- Architectural and industrial settings highlighting scale and professionalism
- Warm, natural lighting with rich earth tones
- Mix of abstract material details and contextual usage scenes
- Human elements showing collaboration and craftsmanship
- Sophisticated composition with generous negative space

---

## Known Pitfalls

- Don't oversimplify the serif/mono font pairing—this creates sophisticated contrast essential to the brand
- Avoid adding border radius—sharp edges are intentional and reinforce industrial precision
- Keep animation purposeful and smooth; expressive doesn't mean chaotic
- Maintain generous whitespace—visual breathing room reinforces premium positioning
- Don't default to standard grid layouts—hover cards and staggered reveals are key differentiators
- Ensure counter animations on stats are smooth and start on scroll trigger
- Avoid overly technical jargon in copy—balance expertise with accessibility
- Don't lose the warmth in the dark earth tones—this differentiates from sterile industrial sites

---

## Reference Sites

- https://www.arclin.com/

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Initial preset created | arclin.com analysis |
# Preset: Health & Wellness Coaching

Industries: health coaching, wellness programs, preventive health, personalized medicine, health tech platforms, lifestyle optimization services

---

## Default Section Sequence

```
1. HERO             | full-bleed-overlay
2. PROCESS          | stepped-vertical
3. GOALS            | icon-grid
4. DIAGNOSTICS      | data-display
5. CTA              | centered-simple
```

**Optional sections (add based on brief):**
- TESTIMONIALS (if social proof needed) → insert after PROCESS
- PRICING (if tiered plans) → insert before final CTA
- FAQ (if complex methodology) → insert before final CTA

---

## Style Configuration

```yaml
color_temperature: cool-forest
palette:
  bg_primary: white
  bg_secondary: stone-50
  bg_accent: emerald-900
  text_primary: stone-900
  text_heading: stone-900
  text_muted: slate-500
  accent: emerald-800
  accent_hover: emerald-950
  border: stone-200

typography:
  pairing: serif-sans
  heading_font: Baskervville
  heading_weight: 400
  body_font: Figtree
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: light-headings

whitespace: generous
section_padding: 128px
internal_gap: 64px

border_radius: medium
buttons: 5px
cards: 20px
inputs: 10px

animation_engine: gsap
animation_intensity: expressive
entrance: fadeInUp, blockReveal, fadeInImg
hover: dsm-bob-float, dsm-pulse-grow, ripple-out
timing: 0.4s ease-in-out
smooth_scroll: false
section_overrides: hero:lottie-integration process:scroll-triggered-reveal goals:staggered-fade

visual_density: spacious
image_treatment: natural-rounded
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: cool-forest (emerald-900/800, stone-900, white, stone-50)
Type: Baskervville/Figtree · light-headings · 1.25 scale
Space: generous (128/64)
Radius: medium (5-20px)
Motion: expressive/gsap — entrance:fadeInUp+blockReveal hover:bob-float+pulse-grow timing:0.4s ease-in-out | hero:lottie process:scroll-reveal goals:stagger
Density: spacious | Images: natural-rounded
═══════════════════════
```

---

## Content Direction

**Tone:** Empowering, methodical, science-backed, calm confidence. Uses action-oriented language ("set your goals," "perform better") balanced with aspirational messaging ("small decisions, extraordinary outcomes").

**Hero copy pattern:** Branded philosophy statement as headline ("THE CASCAID EFFECT") + emotional promise as subhead (small → extraordinary transformation). Leads with process ownership.

**CTA language:** Exclusive/invitation-based ("Request Invitation" vs. "Sign Up") to create aspirational positioning and controlled access feel.

---

## Photography / Visual Direction

- Clean lifestyle imagery showing active, health-conscious individuals
- Data visualization and diagnostic graphics with clinical precision
- Use of natural lighting with cool-toned color grading to match forest palette
- Lottie animations for process flows and data visualization
- Mix of photography and iconography for goals/targets sections
- Maintain generous whitespace around imagery for breathing room

---

## Known Pitfalls

- Don't oversaturate the forest green palette — maintain white space dominance
- Serif headings need careful weight management to avoid appearing too heavy
- Balance clinical/data-driven content with warmth through typography and spacing
- Lottie animations must have fallback states for accessibility
- "Request Invitation" CTA may create friction if conversion is priority — test against standard CTAs
- GSAP ScrollTrigger requires careful performance optimization with extensive keyframes library
- Stepped process layout needs mobile-first consideration for vertical flow

---

## Reference Sites

- https://cascaidhealth.com/how-it-works/

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2024 | Initial preset creation | cascaidhealth.com analysis |
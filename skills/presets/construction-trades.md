# Preset: Construction & Trades

Industries: general contractors, architects, home builders, plumbing companies,
electrical contractors, landscapers, renovation specialists, home services.

---

## Default Section Sequence

```
1. NAV              | sticky-solid
2. HERO             | full-bleed-overlay (project photography)
3. PORTFOLIO        | filtered-grid (completed projects by category)
4. FEATURES         | icon-grid (services offered)
5. HOW-IT-WORKS     | numbered-steps (engagement process)
6. STATS            | counter-animation (projects, years, clients)
7. TESTIMONIALS     | grid
8. TRUST-BADGES     | certification-logos (licenses, insurance, awards)
9. CONTACT          | split-with-map
10. FOOTER          | minimal
```

**Optional sections (add based on brief):**
- ABOUT (if strong founder story or company history) → insert after HERO
- TEAM (if showcasing key personnel or crew) → insert after STATS
- FAQ (if common customer questions about process/pricing) → insert before CONTACT
- BLOG-PREVIEW (if publishing project case studies) → insert before CONTACT

---

## Style Configuration

```yaml
color_temperature: neutral
palette:
  bg_primary: gray-50
  bg_secondary: white
  bg_accent: slate-100
  text_primary: gray-900
  text_heading: gray-950
  text_muted: gray-500
  accent: orange-600
  accent_hover: orange-700
  border: gray-200

typography:
  pairing: geometric-sans
  heading_font: Space Grotesk
  heading_weight: 700
  body_font: Space Grotesk
  body_weight: 400
  scale_ratio: 1.250
  weight_distribution: heavy-light

whitespace: moderate
section_padding: py-16
internal_gap: gap-6

border_radius: sharp
buttons: rounded-sm
cards: rounded-sm
inputs: rounded-sm

animation_intensity: subtle
entrance: fade-up
hover: slight-lift
timing: "0.4s ease-out"

visual_density: medium
image_treatment: contained
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: neutral — bg:gray-50/white text:gray-900 accent:orange-600 border:gray-200
Type: geometric-sans — heading:Space Grotesk,700 body:Space Grotesk,400 scale:1.250
Space: moderate — sections:py-16 internal:gap-6
Radius: sharp — buttons:rounded-sm cards:rounded-sm inputs:rounded-sm
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.4s ease-out
Density: medium | Images: contained
═══════════════════════
```

---

## Content Direction

**Tone:** Direct, competent, no-nonsense. First person plural ("we build").
Short declarative sentences. Let the work speak — lead with project imagery,
support with credentials. Avoid superlatives; use specifics instead.

**Hero copy pattern:** Capability + track record. "Building Arizona's finest
homes since 1997" or "Commercial construction. On time. On budget." Keep it
factual and confident, not boastful.

**CTA language:** Practical and low-pressure. "Get a free estimate" not "Start
your project." "Request a consultation" not "Build your dream." Contractors'
clients want competence, not poetry.

**Industry-specific notes:** The PORTFOLIO section is the centerpiece. Every
project should have a strong hero image, project type tag, and brief scope
description. Filtered-grid lets visitors find relevant work (residential,
commercial, renovation). TRUST-BADGES with licenses, insurance, and awards
are non-negotiable — they close deals.

---

## Photography / Visual Direction

- High-quality project photography: completed builds, dramatic angles, clean compositions
- Before/during/after sequences where available (powerful social proof)
- Aerial/drone shots for large commercial or landscape projects
- Avoid generic hard-hat stock photos — use real jobsite or finished-project imagery
- Neutral color grading with natural contrast; don't over-stylize construction photos

---

## Known Pitfalls

- Orange accent on gray backgrounds can feel like a safety sign if overused.
  Reserve orange-600 for primary CTAs and key interactive elements only.
- Sharp border radius (rounded-sm) requires crisp, well-composed photography
  to avoid looking dated. Sloppy images in sharp containers look worse than
  in rounded ones.
- Construction sites have inherently messy imagery. Curate portfolio images
  ruthlessly — only show completed, professional-grade photography.
- The py-16 section padding is denser than other presets. Ensure sections
  don't feel cramped; use internal gap-6 consistently to maintain rhythm.

---

## Reference Sites

Study these for pattern validation (not copying):
- Bjarke Ingels Group (BIG), Turner Construction, Skanska, Layton Construction, Hensel Phelps
- Look for: portfolio grid treatment, project detail pages, how they balance
  visual impact with technical credibility (specs, certifications, process)

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

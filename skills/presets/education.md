# Preset: Education & Online Learning

Industries: online course platforms, coaching businesses, learning management,
bootcamps, tutoring services, professional development, educational institutions.

---

## Default Section Sequence

```
1. NAV              | sticky-solid
2. HERO             | split-image (course preview or instructor)
3. LOGO-BAR         | static-grid (partner institutions or press)
4. FEATURES         | bento-grid (curriculum / course catalog)
5. HOW-IT-WORKS     | numbered-steps (enrollment to outcome)
6. TESTIMONIALS     | grid (student outcomes)
7. STATS            | counter-animation (completion rates, student count)
8. PRICING          | three-tier with toggle
9. FAQ              | accordion
10. CTA             | centered
11. FOOTER          | mega
```

**Optional sections (add based on brief):**
- COMPARISON (if competing with alternatives) → insert after FEATURES
- VIDEO (if demo lesson or brand video) → insert after HERO
- BLOG-PREVIEW (if educational content marketing) → insert before CTA
- NEWSLETTER (if free resources funnel) → insert before FOOTER

---

## Style Configuration

```yaml
color_temperature: vibrant
palette:
  bg_primary: white
  bg_secondary: slate-50
  bg_accent: indigo-50
  text_primary: slate-900
  text_heading: slate-950
  text_muted: slate-500
  accent: indigo-600
  accent_hover: indigo-700
  border: slate-200

typography:
  pairing: geometric-sans
  heading_font: Space Grotesk
  heading_weight: 700
  body_font: Inter
  body_weight: 400
  scale_ratio: 1.250
  weight_distribution: heavy-light

whitespace: moderate
section_padding: py-20
internal_gap: gap-6

border_radius: medium
buttons: rounded-lg
cards: rounded-xl
inputs: rounded-lg

animation_intensity: moderate
entrance: fade-up-stagger
hover: lift-shadow
timing: "0.6s ease-out"

visual_density: medium
image_treatment: contained
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: vibrant — bg:white/slate-50 text:slate-900 accent:indigo-600 border:slate-200
Type: geometric-sans — heading:Space Grotesk,700 body:Inter,400 scale:1.250
Space: moderate — sections:py-20 internal:gap-6
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: moderate — entrance:fade-up-stagger hover:lift-shadow timing:0.6s ease-out
Density: medium | Images: contained
═══════════════════════
```

---

## Content Direction

**Tone:** Energizing, credible, outcome-focused. Second person ("you"). Direct
and clear — learners are evaluating, not browsing. Lead with the transformation
("become"), support with credibility (instructors, outcomes, data). Avoid
academic stuffiness and salesy hype equally.

**Hero copy pattern:** Transformation + specificity. "Master product design in
12 weeks" or "Learn from the operators who built it." Not "Welcome to our
platform." Include instructor photo or course preview mockup on the right.

**Features (curriculum):** Bento grid with mixed-size cards — larger cards for
flagship courses, smaller for supporting modules. Each card: course name,
duration, level indicator, and one outcome statement.

**Stats section:** Student count, completion rate, career outcomes, instructor
count. Use counter-animation — numbers should feel impressive and earned.

**Pricing:** Clear tier differentiation tied to access level. "Self-Paced" /
"Cohort" / "Mentored." Highlight the recommended tier. Monthly/annual toggle
if subscription model.

**CTA language:** Direct and motivating. "Start learning" / "Enroll now" /
"Join the next cohort" — always convey low barrier and high value.

---

## Photography / Visual Direction

- Course content previews in device mockups (laptop, tablet)
- Instructor headshots that feel approachable, not academic
- Student success moments — graduation, collaboration, achievement
- Abstract geometric illustrations for curriculum or feature sections
- Bright, well-lit imagery with vibrant accents matching the indigo palette

---

## Known Pitfalls

- The bento-grid FEATURES section is information-dense for education. Don't try
  to fit every course — curate 4-6 that represent the range, then link to a
  full catalog.
- Stats must be specific and credible. "10,000+ students" with a counter
  animation only works if the number is real. Vague stats destroy trust
  faster in education than any other industry.
- Three-tier pricing with toggle creates a complex decision matrix. Keep tier
  names self-explanatory and limit feature comparison to 5-7 differentiators.
- Education sites need clear progression signals. The HOW-IT-WORKS section
  should make the enrollment-to-outcome path feel simple, even if the
  learning journey is complex.

---

## Reference Sites

Study these for pattern validation (not copying):
- Coursera, Masterclass, Maven, Reforge, Notion Academy
- Look for: course card layouts, pricing tier structure, how they
  balance information density with clarity, social proof placement,
  hero treatment with course previews

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

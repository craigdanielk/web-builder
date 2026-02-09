# Preset: Creative Studios

Industries: design agencies, photography studios, video production, branding agencies,
creative consultancies, illustration studios, motion design studios.

---

## Default Section Sequence

```
1. NAV              | hamburger-only
2. HERO             | minimal-text (bold statement, maximum impact)
3. PORTFOLIO        | full-width-showcase
4. ABOUT            | editorial-split (philosophy / approach)
5. TEAM             | grid-with-hover (hover reveal cards)
6. TESTIMONIALS     | single-featured
7. VIDEO            | lightbox-trigger (showreel)
8. CTA              | centered
9. FOOTER           | minimal
```

**Optional sections (add based on brief):**
- BLOG-PREVIEW (if case study content) → insert before CTA
- CONTACT (if direct inquiry preferred) → replace CTA
- GALLERY (if additional visual work) → insert after PORTFOLIO
- STATS (if impressive project metrics) → insert after ABOUT

---

## Style Configuration

```yaml
color_temperature: neutral
palette:
  bg_primary: neutral-950
  bg_secondary: neutral-900
  bg_accent: neutral-800
  text_primary: neutral-100
  text_heading: white
  text_muted: neutral-400
  accent: rose-500
  accent_hover: rose-400
  border: neutral-800

typography:
  pairing: display-clean
  heading_font: Clash Display
  heading_weight: 700
  body_font: Inter
  body_weight: 400
  scale_ratio: 1.414
  weight_distribution: heavy-light

whitespace: generous
section_padding: py-24
internal_gap: gap-8

border_radius: sharp
buttons: rounded-sm
cards: rounded-sm
inputs: rounded-sm

animation_intensity: expressive
entrance: fade-up-scale
hover: morph-color
timing: "0.8s cubic-bezier(0.22, 1, 0.36, 1)"

visual_density: low
image_treatment: full-bleed
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: neutral — bg:neutral-950/neutral-900 text:neutral-100 accent:rose-500 border:neutral-800
Type: display-clean — heading:Clash Display,700 body:Inter,400 scale:1.414
Space: generous — sections:py-24 internal:gap-8
Radius: sharp — buttons:rounded-sm cards:rounded-sm inputs:rounded-sm
Motion: expressive — entrance:fade-up-scale hover:morph-color timing:0.8s cubic-bezier(0.22, 1, 0.36, 1)
Density: low | Images: full-bleed
═══════════════════════
```

---

## Content Direction

**Tone:** Confident, minimal, opinionated. First person plural ("we"). Short,
declarative sentences. Let the work speak — copy should frame, not explain.
Avoid self-congratulatory language. Studio voice should feel like the smartest
person in the room who doesn't need to prove it.

**Hero copy pattern:** One bold statement, maximum 6 words. "We make things
move." or "Design is how it works." No subline needed — the PORTFOLIO below
is the proof. The text IS the design.

**Portfolio section:** This is the centerpiece. Full-width showcase with project
name, client, and discipline overlaid. Each project should feel like a gallery
piece. Hover/click reveals case study detail.

**About section:** Philosophy, not history. "We believe..." not "Founded in
2015..." Keep it to 3-4 sentences. Pair with a studio culture image or
abstract visual.

**CTA language:** Understated invitation. "Let's talk" / "Start a project" /
"Say hello" — never "Get a quote" or "Request proposal."

---

## Photography / Visual Direction

- Portfolio work displayed at full-bleed with no borders or containers
- High-contrast imagery — deep blacks, bright highlights, strong composition
- Studio culture shots should feel candid, not staged
- Abstract textures and details for accent imagery (materials, screens, tools)
- No stock photography under any circumstances — every image must be original work or studio-shot

---

## Known Pitfalls

- Dark monochrome palettes with one accent color can feel monotonous across
  many sections. Vary the bg between neutral-950 and neutral-900, and use
  the rose-500 accent sparingly — it should be a punctuation mark, not a highlight.
- Display fonts (Clash Display) at large scale ratios (1.414) create dramatic
  headings but can overwhelm on mobile. Test heading sizes at 375px viewport
  and reduce scale if needed.
- Expressive animation is the studio's calling card but must feel intentional.
  Every animation should serve the content — parallax on portfolio images yes,
  bouncing buttons no.
- Sharp radius (rounded-sm) on a dark background reads brutalist. This is
  deliberate — but ensure it doesn't feel unfinished. Consistent application
  across ALL elements is critical.

---

## Reference Sites

Study these for pattern validation (not copying):
- Pentagram, Buck, ManvsMachine, Collins, Instrument
- Look for: portfolio presentation hierarchy, how minimal copy carries
  maximum impact, animation as brand expression, dark palette variation
  techniques, navigation treatment

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

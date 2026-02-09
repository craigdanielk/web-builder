# Preset: Nonprofits & Social Impact

Industries: charitable foundations, social causes, community organizations,
environmental nonprofits, advocacy groups, social enterprises, mutual aid organizations.

---

## Default Section Sequence

```
1. NAV              | sticky-solid
2. HERO             | centered (powerful human photography background)
3. STATS            | counter-animation (impact numbers — critical)
4. ABOUT            | values-grid (mission / vision / values)
5. HOW-IT-WORKS     | icon-steps (how donations create impact)
6. TESTIMONIALS     | grid (beneficiary stories)
7. GALLERY          | carousel (impact imagery)
8. CTA              | gradient-block (donate / volunteer)
9. NEWSLETTER       | split (stay informed / join movement)
10. FAQ             | accordion
11. FOOTER          | mega
```

**Optional sections (add based on brief):**
- TEAM (if leadership visibility matters) → insert after ABOUT
- BLOG-PREVIEW (if active content/reports) → insert before CTA
- VIDEO (if impact documentary or campaign film exists) → insert after STATS
- LOGO-BAR (if major partners or grant-makers) → insert after HERO

---

## Style Configuration

```yaml
color_temperature: vibrant
palette:
  bg_primary: white
  bg_secondary: teal-50
  bg_accent: amber-50
  text_primary: gray-900
  text_heading: gray-950
  text_muted: gray-500
  accent: teal-600
  accent_hover: teal-700
  border: gray-200

typography:
  pairing: humanist
  heading_font: Source Sans 3
  heading_weight: 700
  body_font: Source Sans 3
  body_weight: 400
  scale_ratio: 1.333
  weight_distribution: heavy-light

whitespace: moderate
section_padding: py-20
internal_gap: gap-6

border_radius: full
buttons: rounded-2xl
cards: rounded-3xl
inputs: rounded-xl

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
Palette: vibrant — bg:white/teal-50 text:gray-900 accent:teal-600 border:gray-200
Type: humanist — heading:Source Sans 3,700 body:Source Sans 3,400 scale:1.333
Space: moderate — sections:py-20 internal:gap-6
Radius: full — buttons:rounded-2xl cards:rounded-3xl inputs:rounded-xl
Motion: moderate — entrance:fade-up-stagger hover:lift-shadow timing:0.6s ease-out
Density: medium | Images: contained
═══════════════════════
```

---

## Content Direction

**Tone:** Urgent but hopeful. Second person ("you can make a difference") mixed
with first person plural ("together, we"). Short paragraphs. Lead with the
problem, pivot to hope, close with action. Never guilt-trip — inspire.

**Hero copy pattern:** Problem → hope → action. "1 in 4 children don't have
access to clean water. You can change that today." Always pair with a powerful
human photograph.

**CTA language:** Action-oriented and specific. "Donate $25 to feed a family"
not just "Donate." "Volunteer this weekend" not "Get involved." Quantify the
impact of the action wherever possible.

**Industry-specific notes:** The STATS section is the single most important
differentiator for nonprofits. Use animated counters with large, bold numbers.
Every stat should have a human label: "12,000 families fed" not "12,000 served."
Impact numbers build trust faster than any testimonial.

---

## Photography / Visual Direction

- Authentic, documentary-style human photography — real beneficiaries, real moments
- Warm color grading with natural light; avoid over-processed or stock-photo look
- Show faces, eye contact, and connection — empathy drives action
- Environmental context shots (the community, the landscape, the problem and solution)
- Avoid "poverty porn" or exploitative imagery — dignity and agency in every frame

---

## Known Pitfalls

- Vibrant accent colors on white backgrounds need careful contrast checking.
  Teal-600 on white meets WCAG AA, but verify all text-on-color combinations.
- The "full" border radius (rounded-2xl, rounded-3xl) can feel juvenile if
  overused. Reserve rounded-3xl for cards; keep structural elements more restrained.
- Nonprofits often have too much content. Resist the urge to add more sections.
  The sequence above is already 11 sections — trim before adding.
- Counter-animation stats are powerful but must use real, verifiable numbers.
  Inflated or vague metrics ("millions impacted") destroy trust instantly.

---

## Reference Sites

Study these for pattern validation (not copying):
- charity: water, The Nature Conservancy, Khan Academy, ACLU, DonorsChoose
- Look for: stat presentation, donation flow UX, hero photography treatment,
  how they balance urgency with hope, CTA placement frequency

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

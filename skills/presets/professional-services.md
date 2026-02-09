# Preset: Professional Services

Industries: consulting firms, law firms, accounting firms, management consulting,
HR agencies, financial advisory, business coaching, strategy consultancies.

---

## Default Section Sequence

```
1. NAV              | sticky-solid
2. HERO             | centered
3. LOGO-BAR         | static-grid
4. FEATURES         | icon-grid (service areas)
5. ABOUT            | values-grid
6. TEAM             | featured-leadership
7. STATS            | counter-animation
8. TESTIMONIALS     | grid
9. CTA              | centered
10. FOOTER          | mega
```

**Optional sections (add based on brief):**
- FAQ (if complex service offerings) → insert after TESTIMONIALS
- BLOG-PREVIEW (if thought leadership active) → insert before CTA
- CONTACT (if lead-gen is primary goal) → replace CTA
- NEWSLETTER (if content-driven funnel) → insert before FOOTER

---

## Style Configuration

```yaml
color_temperature: cool
palette:
  bg_primary: white
  bg_secondary: slate-50
  bg_accent: sky-50
  text_primary: slate-800
  text_heading: slate-950
  text_muted: slate-500
  accent: sky-700
  accent_hover: sky-800
  border: slate-200

typography:
  pairing: humanist
  heading_font: Source Sans 3
  heading_weight: 600
  body_font: Source Sans 3
  body_weight: 400
  scale_ratio: 1.250
  weight_distribution: medium-regular

whitespace: moderate
section_padding: py-20
internal_gap: gap-6

border_radius: medium
buttons: rounded-lg
cards: rounded-xl
inputs: rounded-lg

animation_intensity: subtle
entrance: fade-up
hover: slight-lift
timing: "0.5s ease-out"

visual_density: medium
image_treatment: contained
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: cool — bg:white/slate-50 text:slate-800 accent:sky-700 border:slate-200
Type: humanist — heading:Source Sans 3,600 body:Source Sans 3,400 scale:1.250
Space: moderate — sections:py-20 internal:gap-6
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.5s ease-out
Density: medium | Images: contained
═══════════════════════
```

---

## Content Direction

**Tone:** Authoritative but approachable. Third person or second person ("we
help you" / "our firm"). Measured, precise language. No buzzwords or hype.
Lead with outcomes and expertise. Understated confidence.

**Hero copy pattern:** Lead with the client's challenge, then position the firm
as the answer. "Navigating complexity with clarity" not "We are a consulting
firm." Keep it short — one headline, one subline, one CTA.

**Features (service areas):** Each service card: clear discipline name, 2-line
description of what the client gets (not what the firm does). Use icons that
feel professional, not playful.

**Team section:** Title, role, brief credential. Headshots should be
professional but not stiff. Leadership gets larger cards.

**CTA language:** Confident, not salesy. "Schedule a consultation" / "Discuss
your challenge" / "Get in touch" — always low-pressure.

---

## Photography / Visual Direction

- Professional headshots with neutral backgrounds, natural lighting
- Abstract architectural photography (lines, glass, structure) for hero/accents
- Clean office environments — avoid generic stock meeting rooms
- Subtle color grading leaning cool/desaturated for cohesion
- If no photography available, use geometric abstract patterns or text-only treatment

---

## Known Pitfalls

- Navy-and-white is the most generic professional services look. Differentiate
  through the sky-700 accent and strong typography hierarchy, not color alone.
- Humanist fonts feel corporate — which is correct here — but can tip into boring.
  Use weight contrast (600 headings vs 400 body) to maintain visual interest.
- The values-grid ABOUT section can easily become wall-of-text. Keep each value
  to a headline + 2 sentences maximum.
- Don't hide the team behind a "learn more" click. Professional services are
  people businesses — the TEAM section should be prominent and above-the-fold
  in the overall page flow.

---

## Reference Sites

Study these for pattern validation (not copying):
- McKinsey & Company, Bain & Company, Deloitte, Accenture, Cravath Swaine
- Look for: section density, typography hierarchy, trust signaling,
  how they balance authority with approachability, CTA placement

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

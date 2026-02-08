# Preset: SaaS / Tech Product

Industries: B2B software, developer tools, productivity apps, analytics platforms,
API products, cloud infrastructure, project management, CRM/marketing tools.

---

## Default Section Sequence

```
1. NAV              | sticky-solid
2. ANNOUNCEMENT-BAR | static (optional, for launches/promos)
3. HERO             | split-image (product screenshot or mockup)
4. LOGO-BAR         | scrolling-marquee
5. FEATURES         | bento-grid
6. HOW-IT-WORKS     | numbered-steps (3 steps)
7. TESTIMONIALS     | carousel
8. PRICING          | three-tier with toggle
9. FAQ              | accordion
10. CTA             | centered
11. FOOTER          | mega
```

**Optional sections (add based on brief):**
- COMPARISON (if competitive positioning matters) → insert after FEATURES
- STATS (if strong metrics) → insert after LOGO-BAR
- INTEGRATIONS (if ecosystem is a selling point) → insert after FEATURES
- BLOG-PREVIEW (if content marketing active) → insert before CTA

---

## Style Configuration

```yaml
color_temperature: cool
palette:
  bg_primary: white
  bg_secondary: slate-50
  bg_accent: blue-50
  text_primary: slate-900
  text_heading: slate-950
  text_muted: slate-500
  accent: blue-600
  accent_hover: blue-700
  border: slate-200

typography:
  pairing: geometric-sans
  heading_font: Inter
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

animation_intensity: subtle
entrance: fade-up
hover: slight-lift
timing: "0.5s ease-out"

visual_density: medium
image_treatment: contained
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: cool — bg:white/slate-50 text:slate-900 accent:blue-600 border:slate-200
Type: geometric-sans — heading:Inter,700 body:Inter,400 scale:1.250
Space: moderate — sections:py-20 internal:gap-6
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.5s ease-out
Density: medium | Images: contained
═══════════════════════
```

---

## Content Direction

**Tone:** Clear, confident, no fluff. Second person ("you"). Short paragraphs.
Lead with the problem, then the solution. Quantify benefits where possible.

**Hero copy pattern:** Problem → solution → CTA. "Stop wasting time on X.
[Product] does Y so you can Z."

**Features:** Benefit-led, not feature-led. Each feature card: benefit headline,
2-line description, supporting visual (screenshot, icon, or illustration).

**Pricing:** Clear tier names that signal the buyer (Starter, Pro, Enterprise).
Highlight the recommended tier. Include a brief FAQ below pricing.

**CTA language:** Direct but not pushy. "Start free" / "Get started" / "Try
[Product] free" — always mention free trial or no-commitment.

---

## Photography / Visual Direction

- Product screenshots in device frames (browser, phone, tablet)
- Clean mockups with subtle shadows on light backgrounds
- Abstract geometric illustrations for feature sections
- Avoid stock photos of people on laptops — use actual product imagery
- If no product screenshots exist, use abstract gradient/mesh backgrounds

---

## Known Pitfalls

- Blue-on-white is the most generic SaaS look. Differentiate through the
  accent color, typography choice, or a unique hero treatment.
- The bento grid features section is overused. If you use it, make the grid
  layout genuinely asymmetric and interesting, not just 6 equal cards.
- "Subtle" animation doesn't mean boring. The fade-up should feel smooth
  and intentional, not like a default.
- Three-tier pricing is expected. Stand out through clear value differentiation,
  not visual tricks.

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

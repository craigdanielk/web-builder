```markdown
# Preset: Crypto Exchange / Fintech (South Africa)

Industries: cryptocurrency exchange, bitcoin trading platform, fintech onramp, digital asset brokerage

---

## Default Section Sequence

```
1. HERO                 | split-image
2. TRUST-BADGES         | icon-strip
3. HOW-IT-WORKS         | numbered-steps
4. FEATURES             | icon-grid
5. LOGO-BAR             | scrolling-marquee
6. FAQ                  | accordion
```

**Optional sections (add based on brief):**
- PRICING (if fee comparison table needed) → insert after FEATURES
- TESTIMONIALS (if social proof available) → insert before FAQ
- STATS (if trading volume/user count data available) → insert after HERO

---

## Style Configuration

```yaml
color_temperature: cool-blue
palette:
  bg_primary: sky-800        # #20334a — page wrapper bg, dark navy
  bg_secondary: sky-700      # #004e89 — alt section bg
  bg_accent: white           # #ffffff — light/card sections
  text_primary: white        # on dark sections
  text_heading: white
  text_muted: blue-400       # #94a3b8
  accent: sky-700            # #004e89 — primary CTA
  accent_hover: sky-800      # #20334a
  border: sky-700

section_accents:
  hero: sky-700
  trust-badges: sky-800
  how-it-works: sky-800
  features: sky-800
  logo-bar: sky-700
  faq: sky-800

typography:
  pairing: single-font
  heading_font: Plus Jakarta Sans
  heading_weight: 700
  body_font: Plus Jakarta Sans
  body_weight: 400
  scale_ratio: 1.25
  weight_distribution: bold-heading-regular-body

whitespace: comfortable
section_padding: py-20
internal_gap: gap-6

border_radius: medium
buttons: rounded-full        # 25px outlier radius = pill CTAs
cards: rounded-xl            # 16px
inputs: rounded-lg           # 8px

animation_engine: css
animation_intensity: subtle
entrance: fade-up
hover: color-shift
timing: 0.2s ease-default
smooth_scroll: false
section_overrides: hero:fade-in steps:sequential-reveal
gsap_plugins: []
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: sky-800/sky-700 navy on white, single-accent
Type: Plus Jakarta Sans (heading+body)
Space: comfortable, py-20
Radius: medium (buttons pill, cards xl, inputs lg)
Motion: subtle/css — entrance:fade-up hover:color-shift timing:0.2s ease | hero:fade-in steps:sequential-reveal
Density: balanced | Images: split-image hero, icon-based feature grid
═══════════════════════
```

---

## Content Direction

**Tone:** Direct, trust-building, speed-focused. Short declarative headlines ("Buy Bitcoin within a minute") emphasizing simplicity and speed over crypto jargon. Local (South Africa) trust signals matter.

**Hero copy pattern:** [Action] + [Asset] + [Geo qualifier] — e.g. "Buy Bitcoin South Africa" / "Buy Bitcoin within a minute". Lead with speed/ease, not technical differentiation.

**CTA language:** Action-first, low-friction verbs implied by flow ("Sign Up" → "Deposit" → "Buy Bitcoin"). Keep CTAs short: "Get Started", "Buy Now", "Sign Up Free".

---

## Photography / Visual Direction

- Split-image hero: app/dashboard mockup or device screenshot paired with headline, not stock photography
- Icon-driven feature grid over photos (trust/speed/fee icons)
- Partner/exchange logos in scrolling marquee for credibility
- Numbered step icons for onboarding flow (Sign Up → Deposit → Buy)

---

## Known Pitfalls

- Dark navy (#20334a) page bg vs white section backgrounds detected — verify per-section bg before assuming full-dark theme; hero/nav likely dark, body content likely light
- No CTA button text was extracted — copy above is inferred from heading/flow tone, confirm exact wording with client before finalizing
- Animation confidence score was 0% — treat "subtle/css" as a safe default, not a confirmed signal; upgrade if brief calls for more premium motion

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-07-23 | Initial preset created from extraction | https://capecrypto.com |
```
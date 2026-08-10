# Preset: Fintech / Crypto Exchange

Industries: cryptocurrency exchange, bitcoin trading platform, cross-border
payments, fintech onramp, digital wallet, remittance, stablecoin issuer,
regulated money-services business

> **This preset is the STRUCTURAL SPINE — it is deliberately brand-free.**
> Every colour below is a role name or a neutral placeholder, never a tenant's
> hue. A tenant preset (`cape-crypto.md`, `xago.md`, …) or a tenant phase0
> palette capture overrides the `palette:` and `typography:` keys; the
> structure — type scale, weight pairing, shadow geometry, radius steps,
> spacing rhythm, grid, gradient stop ordering — is inherited unchanged.
> **A tenant's accent hex appearing in this file is a bug.**
>
> Derived from `tenants/xago/out/stripe-benchmark.json` (Stripe computed-style
> capture, 2026-07-23) and validated against the shipped Xago implementation
> (`tenants/xago/site`, Lighthouse 89-98). Dimension definitions and per-value
> provenance live in `skills/style-schema.md` §8-13.

---

## Default Section Sequence

```
1. HERO                 | gradient-split
2. LOGO-BAR             | scrolling-marquee
3. FEATURES             | icon-grid
4. HOW-IT-WORKS         | numbered-steps
5. STATS                | metric-row
6. TESTIMONIALS         | quote-cards
7. TRUST-BADGES         | icon-strip
8. FAQ                  | accordion
9. CTA                  | dark-band
```

**Optional sections (add based on brief):**
- PRICING (if a fee table or fee comparison exists) → insert after FEATURES
- COMPARISON (if positioned against incumbents) → insert after STATS
- CONTENT-GRID (if a coverage list exists — supported currencies, countries,
  assets) → insert after FEATURES, rendered as the 4-column coverage grid

**Rhythm rule (not a section list — see "What tokens cannot carry"):** the page
alternates light → hairline band → light → **dark band** → light → dark CTA.
Exactly two dark bands per page. Never two dark sections adjacent.

---

## Style Configuration

```yaml
color_temperature: cool-institutional
palette:
  bg_primary: PLACEHOLDER-lightest surface, near-white, tinted toward brand hue
  bg_secondary: PLACEHOLDER-pure white (cards sit on bg_primary)
  bg_accent: PLACEHOLDER-2 steps darker than bg_primary
  bg_dark: PLACEHOLDER-darkest brand colour, never pure black
  text_primary: PLACEHOLDER-neutral ink at ~32% lightness
  text_heading: PLACEHOLDER-darkest brand colour
  text_muted: PLACEHOLDER-neutral at ~60% lightness
  text_on_dark: PLACEHOLDER-~96% lightness
  text_muted_on_dark: PLACEHOLDER-~80% lightness
  accent: PLACEHOLDER-primary brand accent
  accent_hover: PLACEHOLDER-accent darkened ~10%
  accent_secondary: PLACEHOLDER-accent lightened ~15% (gradient stop 2)
  accent_tertiary: PLACEHOLDER-accent lightened ~35% (gradient stop 3)
  accent_alt: PLACEHOLDER-off-hue tension stop, 120-180deg from accent
  on_accent: PLACEHOLDER-contrast-safe label colour on accent fill
  border: PLACEHOLDER-neutral at ~92% lightness, same hue family as bg_primary
  border_on_dark: PLACEHOLDER-white at 8-14% alpha
  shadow_ink: PLACEHOLDER-rgb triplet, tint of bg_dark, never 0,0,0
  # Colour values MUST be written as rgb()/rgba(), never hex. parse_yaml_style_block()
  # in seed_supabase.py treats "#" as an inline-comment marker and truncates hex
  # values to an empty string. See style-schema.md "Structural Spine vs Brand Inputs".

typography:
  pairing: geometric-sans
  heading_font: PLACEHOLDER-tenant display face
  heading_weight: 400
  heading_tracking: -0.02em
  heading_leading: 1.08
  body_font: PLACEHOLDER-tenant text face
  body_weight: 400
  ui_label_weight: 600
  scale_ratio: 1.25
  scale_px: 56, 48, 32, 26, 22, 20, 18, 16, 14, 12, 11
  weight_distribution: light-display
  headline_treatment: two-tone
  headline_gradient_angle: 100deg

whitespace: generous
section_padding: py-20 md:py-28 lg:py-32
internal_gap: gap-8
container: max-w-6xl px-6 lg:px-8
band_padding: py-10 md:py-14

border_radius: squarish
buttons: rounded-md
cards: rounded-lg
inputs: rounded-md
radius_scale: xl 8px, 2xl 8px, 3xl 10px

elevation: two-layer-soft
shadow_lg: 0 8px 24px -6px rgba(SHADOW_INK,0.10), 0 2px 8px -2px rgba(SHADOW_INK,0.08)
shadow_2xl: 0 30px 60px -12px rgba(SHADOW_INK,0.18), 0 8px 24px -6px rgba(SHADOW_INK,0.10)
shadow_max_layers: 2

surface:
  card: bordered-lifted
  card_border: 1px solid border
  card_fill: bg_secondary
  card_grid: uniform-equal-height
  card_columns: 3

dark_section:
  ground: bg_dark
  guides: dotted-gutter
  guide_opacity: 0.07
  cut: diagonal
  cut_depth: 6vw
  accent_count: 1

gradient:
  hero: mesh-ribbon
  stops: accent, accent_secondary, accent_tertiary, accent_alt, bg_primary
  motion: slow-drift
  reduced_motion: static

cta:
  primary: solid accent fill, on_accent label
  secondary: transparent fill, 1px border, no second solid colour
  radius: rounded-md
  padding: px-6 py-3
  label_size: text-sm
  label_weight: 600
  affordance: trailing-chevron
  hover: scale-1.03 + accent-tinted shadow
  tap: scale-0.98

logo_bar:
  treatment: full-colour
  layout: marquee-when-over-5
  cell: w-40 h-10 object-contain
  eyebrow: uppercase tracking-wider text-sm muted
  band: border-y hairline

animation_engine: framer-motion
animation_intensity: subtle
entrance: fade-up
hover: scale + shadow-lift
timing: 0.6s cubic-bezier(0.22,1,0.36,1)
stagger: 0.12
smooth_scroll: false
section_overrides: hero:staggered-timeline stats:count-up logo_bar:marquee
gsap_plugins:
  # none — framer-motion is sufficient at `subtle` intensity

visual_density: medium
image_treatment: illustrated
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: cool-institutional — bg:{bg_primary}/{bg_secondary} text:{text_primary} heading:{text_heading} accent:{accent} border:{border}
Type: geometric-sans — heading:{heading_font},400 tracking:-0.02em leading:1.08 body:{body_font},400 scale:1.25 | two-tone headline
Space: generous — sections:py-20 md:py-28 lg:py-32 internal:gap-8 container:max-w-6xl
Radius: squarish — buttons:rounded-md(6px) cards:rounded-lg(8px) inputs:rounded-md
Motion: subtle/framer-motion — entrance:fade-up hover:scale+shadow timing:0.6s cubic-bezier(0.22,1,0.36,1) stagger:0.12 | hero:staggered-timeline stats:count-up
Density: medium | Images: illustrated
Elevation: two-layer-soft — lg:0 8px 24px -6px/0 2px 8px -2px 2xl:0 30px 60px -12px/0 8px 24px -6px
Surface: bordered-lifted — grid:uniform-equal-height cols:3
Dark: {bg_dark} — guides:dotted-gutter cut:diagonal
Gradient: mesh-ribbon — stops:accent,accent_secondary,accent_tertiary,accent_alt,bg_primary motion:slow-drift
CTA: radius:rounded-md size:px-6 py-3 weight:600 affordance:trailing-chevron
═══════════════════════
```

---

## Content Direction

**Tone:** Direct and trust-building. Plain language over jargon. Regulatory
standing stated as fact, early, without hedging (licence number, regulator,
year founded). Speed and cost are the two claims that convert.
**Hero copy pattern:** two-tone — `[plain lead clause] + [accent-gradient
outcome clause]`. Lead is ink, outcome carries the gradient.
**CTA language:** account-opening verbs, not sales verbs ("Open an account",
"Get started", "Buy now"). Secondary CTA is always explanatory ("See how it
works"), never a second conversion ask.
**Trust points:** 3-4 short factual chips directly under the hero CTAs —
regulator, settlement rail, founding year, jurisdiction.

---

## Photography / Visual Direction

- Product and app screenshots over stock photography. A real UI beats a smiling
  person for this industry.
- Icon-driven feature grids (Lucide), not spot illustration.
- Partner/regulator/exchange logos in **full colour**. Greyscaling them reads
  as hiding weak partners.
- Abstract gradient/mesh only in the hero and the dark CTA band; never behind
  body content where it fights text contrast.
- No emoji. No generic finance stock imagery (handshakes, rising arrows, coins).

---

## Known Pitfalls

- **`light-display` needs size to work.** Weight 400 headings at 32px read
  under-designed. The scale must actually reach 48-56px on desktop or the type
  system fails.
- **Two-tone headlines need a real split.** If the accent clause is a single
  short word the gradient has no room to travel and reads as a colour typo.
- **Shadow ink defaults to black and cheapens everything.** `shadow_ink` must
  be tinted toward the brand dark. Pure black at these blurs looks like a
  Bootstrap card.
- **`squarish` fights component libraries.** Most pulled components default to
  `rounded-2xl`/`rounded-full`. Radius overrides must be enforced at review or
  the card system silently reverts to pills.
- **Dark bands stack.** With a dark hero, a dark mid-band and a dark CTA the
  page has no light rhythm left. Cap at two dark bands, and if the hero is dark
  the mid-band must be light.
- **The mesh gradient is a hero-only move.** Repeated per section it becomes
  visual noise and costs paint time.
- **Reduced-motion fallback is mandatory** for the mesh/ribbon — it is a
  continuous animation over a large surface.

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-08-10 | Initial spine. Extracted from `tenants/xago/out/stripe-benchmark.json` (Stripe computed-style capture 2026-07-23) and reconciled against the shipped Xago build (`tenants/xago/site`, `theme.config.json`, `globals.css`, `DarkSection.tsx`, `sections/homepage/*`). Brand values stripped to role placeholders. | stripe-benchmark + xago |

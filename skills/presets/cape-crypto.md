# Preset: Cape Crypto (tenant)

Tenant: Cape Crypto — South African cryptocurrency exchange, FSP No. 53746.
Source: https://capecrypto.com

> **Tenant preset. Inherits the structural spine from
> `skills/presets/fintech-crypto.md`; this file supplies ONLY Cape Crypto's
> brand values.** Type scale ratio, weight distribution, radius steps, shadow
> geometry, spacing rhythm, grid, gradient stop ordering and CTA anatomy come
> from the spine and are not restated except where this tenant deliberately
> departs (see "Departures from capture" below).
>
> Palette and typography are measured, not chosen. Provenance for every value
> is in the table below.

---

## Measured brand values

Captured from `web-builder/output/extractions/cape-crypto-689443d1/extraction-data.json`
(24 computed style properties × 147 DOM nodes, capecrypto.com, 2026-08-03).
`n=` is the number of DOM nodes carrying that value.

| Role | Value | Evidence |
|------|-------|----------|
| Brand navy | `#20334A` `rgb(32,51,74)` | header bg, dark section bg (`padding: 80px 0`), heading colour — n=24 |
| Brand blue (accent) | `#004E89` `rgb(0,78,137)` | the only CTA fill on the page — n=2 (`a`, `padding: 8px 20px` / `8px 32px`, `color: #fff`, `font-weight: 500`, `font-size: 12.8px`, `transition: 0.2s`) |
| Slate | `#2B435F` `rgb(43,67,95)` | secondary heading colour — n=14 |
| Body ink | `#515151` `rgb(81,81,81)` | dominant text colour — n=87 |
| Surface tint | `#F8FAFC` `rgb(248,250,252)` | section bg + nav-item bg — n=6 |
| Muted on dark | `#94A3B8` `rgb(148,163,184)` | n=2; plus `rgba(255,255,255,0.8)` n=9 and `0.85` n=1 |
| Shadow | `rgba(32,51,74,0.04) 0 2px 12px 0` (n=7), `… 0 2px 8px 0` (n=3) | shadow ink is the brand navy — **measured, not assumed** |
| Wash gradient | `linear-gradient(135deg, rgb(240,244,248) 0%, rgb(232,237,243) 100%)` | n=2 — the only gradient on the site |
| Heading face | Plus Jakarta Sans (500/600/700) | n=19; `fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700&family=Roboto:wght@400;500;700` |
| Body face | Roboto (400/500/700) | n=128 |
| Weights in use | 400 (n=124), 700 (n=10), 800 (n=8), 500 (n=3), 600 (n=2) | |
| Size scale (px) | 56, 48, 40, 32, 20, 18, 16, 14, 12.8, 12 | 16px dominant (n=96) |
| Radius in use | 0 (n=117), 16 (n=10), 8 (n=9), 6 (n=6), 25 (n=3), 5 (n=2) | |
| Logo | `assets/images/logo-white.svg` 215×25 | white lockup — implies a dark ground behind the nav |
| Partners | Numeral, Aluma, Xago, Idatco | `assets/images/partners/*` |

**Not measured — recorded as gaps, not filled with invention:**

- **No off-hue accent exists on capecrypto.com.** The palette is a single blue
  hue arc. The spine's `accent_alt` tension stop has no captured value.
- **No mesh/ribbon gradient exists.** The only gradient is a flat 135° grey
  wash. `gradient.hero: mesh-ribbon` is a spine upgrade with no tenant
  precedent.
- **No animation was captured** (`animation-analysis.json` is effectively
  empty; `animationName` is unset across all 147 nodes). Motion values are
  inherited from the spine, not observed.
- **No dark-section treatment beyond a flat navy fill** — no dotted guides, no
  diagonal cut. Those arrive from the spine.
- Values below marked `# DERIVED` are computed from measured values by the
  rules in `style-schema.md` (lighten/darken by stated %), not observed.

---

## Default Section Sequence

Inherits the spine sequence. Tenant adjustments, justified by the capture:

```
1. HERO                 | gradient-split          (app-screenshot.png present)
2. LOGO-BAR             | scrolling-marquee       (4 partner logos → static row, see note)
3. TRUST-BADGES         | icon-strip              (FSP No. 53746 + flag-sa.png)
4. HOW-IT-WORKS         | numbered-steps          (step-signup/step-deposit/step-buy.png)
5. FEATURES             | icon-grid
6. STATS                | metric-row
7. FAQ                  | accordion
8. CTA                  | dark-band               (app-store + google-play badges)
```

Note: only 4 partner logos were captured, below the spine's marquee threshold
of 5 — render as a static centred row, not a marquee.

The block above is the **homepage** sequence and is used for any page type with
no block of its own. Until 2026-08-18 it was the sequence for *every* page:
five pages of four different types all demanded the same eight sections, and 19
of 21 omissions on the last build were `registry_gap_fill_no_source` — a
section demanded on a page whose source has no such block. The per-page-type
blocks below are the fix.

## Section Sequence — content

Measured from the ratified reference corpus, not from Cape Crypto's own pages.
`node scripts/quality/annotate-corpus-archetypes.js
benchmarks/corpora/enterprise-stablecoin-payments-measured` classifies BVNK's
three product/solution pages (payments, embedded-wallets, digital-assets) and
**HERO, FEATURES, HOW-IT-WORKS and FAQ appear on 3 of 3**. CTA is measured on
the reference home page and present in the harvest of every Cape Crypto content
page. LOGO-BAR, TRUST-BADGES and STATS are measured on **0 of 3** reference
solution pages — they are homepage furniture, and demanding them on a solution
page is what produced the gap-fills.

```
1. HERO                 | gradient-split
2. FEATURES             | icon-grid
3. HOW-IT-WORKS         | numbered-steps
4. FAQ                  | accordion
5. CTA                  | dark-band
```

## Section Sequence — about

From the same corpus: `about-us` classifies ABOUT, FEATURES, HOW-IT-WORKS
(3 measured of 7 sections; the remaining 4 are image-led sections the mapper
reports NOT_MEASURED rather than guessing). HERO opens the page and CTA closes
it, as on every other page of the reference.

```
1. HERO                 | gradient-split
2. ABOUT                | editorial-split
3. FEATURES             | icon-grid
4. HOW-IT-WORKS         | numbered-steps
5. CTA                  | dark-band
```

---

## Style Configuration

```yaml
color_temperature: cool-institutional
palette:
  bg_primary: rgb(248,250,252)
  bg_secondary: rgb(255,255,255)
  bg_accent: rgb(240,244,248)
  bg_dark: rgb(32,51,74)
  text_primary: rgb(81,81,81)
  text_heading: rgb(32,51,74)
  text_secondary_heading: rgb(43,67,95)
  text_muted: rgb(148,163,184)
  text_on_dark: rgb(255,255,255)
  text_muted_on_dark: rgba(255,255,255,0.8)
  accent: rgb(0,78,137)
  accent_hover: rgb(0,58,102)
  accent_secondary: rgb(27,111,168)
  accent_tertiary: rgb(127,178,214)
  accent_alt: rgb(32,51,74)
  on_accent: rgb(255,255,255)
  border: rgb(226,232,240)
  border_on_dark: rgba(255,255,255,0.12)
  shadow_ink: 32,51,74

typography:
  pairing: geometric-sans
  heading_font: Plus Jakarta Sans
  heading_weight: 400
  heading_tracking: -0.02em
  heading_leading: 1.08
  body_font: Roboto
  body_weight: 400
  ui_label_weight: 600
  scale_ratio: 1.25
  scale_px: 56, 48, 40, 32, 20, 18, 16, 14, 12
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
shadow_lg: 0 8px 24px -6px rgba(32,51,74,0.10), 0 2px 8px -2px rgba(32,51,74,0.08)
shadow_2xl: 0 30px 60px -12px rgba(32,51,74,0.18), 0 8px 24px -6px rgba(32,51,74,0.10)
shadow_max_layers: 2

surface:
  card: bordered-lifted
  card_border: 1px solid rgb(226,232,240)
  card_fill: rgb(255,255,255)
  card_grid: uniform-equal-height
  card_columns: 3

dark_section:
  ground: rgb(32,51,74)
  guides: dotted-gutter
  guide_opacity: 0.07
  cut: diagonal
  cut_depth: 6vw
  accent_count: 1

gradient:
  hero: mesh-ribbon
  stops: rgb(0,78,137), rgb(27,111,168), rgb(127,178,214), rgb(32,51,74), rgb(248,250,252)
  motion: slow-drift
  reduced_motion: static

cta:
  primary: solid rgb(0,78,137) fill, rgb(255,255,255) label
  secondary: transparent fill, 1px rgb(226,232,240) border
  radius: rounded-md
  padding: px-6 py-3
  label_size: text-sm
  label_weight: 600
  affordance: trailing-chevron
  hover: scale-1.03 + rgba(0,78,137,0.20) shadow
  tap: scale-0.98

logo_bar:
  treatment: full-colour
  layout: static-row
  cell: w-40 h-10 object-contain
  eyebrow: uppercase tracking-wider text-sm muted
  band: border-y hairline

animation_engine: framer-motion
animation_intensity: moderate
entrance: fade-up
hover: scale + shadow-lift
timing: 0.6s cubic-bezier(0.22,1,0.36,1)
stagger: 0.12
smooth_scroll: false
section_overrides: hero:staggered-timeline stats:count-up
gsap_plugins:
  # none

visual_density: medium
image_treatment: illustrated
```

**Derivation notes for the `# DERIVED` values above:**
`accent_hover #003A66` = accent darkened 10%. `accent_secondary #1B6FA8` /
`accent_tertiary #7FB2D6` = accent lightened ~15% / ~35% along its own hue —
these are the gradient's middle stops and had no measured counterpart.
`accent_alt #20334A` reuses the measured brand navy in place of the spine's
off-hue tension stop, because **Cape Crypto has no second hue** and inventing
one (a teal, a violet) would fabricate brand. The consequence is an honest one:
Cape Crypto's mesh gradient will read tonal rather than iridescent. That is a
correct outcome for a single-hue brand, not a defect to patch.
`bg_accent #F0F4F8` is the start stop of the site's own measured wash gradient
(`rgb(240,244,248)`), promoted to a palette role.
`border #E2E8F0` is the cool-neutral at ~92% lightness in `bg_primary`'s hue
family per the spine's derivation rule — no border colour was measured
(all 147 nodes reported no border colour among the captured properties).

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: cool-institutional — bg:#F8FAFC/#FFFFFF text:#515151 heading:#20334A accent:#004E89 border:#E2E8F0
Type: geometric-sans — heading:Plus Jakarta Sans,400 tracking:-0.02em leading:1.08 body:Roboto,400 scale:1.25 | two-tone headline
Space: generous — sections:py-20 md:py-28 lg:py-32 internal:gap-8 container:max-w-6xl
Radius: squarish — buttons:rounded-md(6px) cards:rounded-lg(8px) inputs:rounded-md
Motion: subtle/framer-motion — entrance:fade-up hover:scale+shadow timing:0.6s cubic-bezier(0.22,1,0.36,1) stagger:0.12 | hero:staggered-timeline stats:count-up
Density: medium | Images: illustrated
Elevation: two-layer-soft — lg:0 8px 24px -6px rgba(32,51,74,.10)/0 2px 8px -2px rgba(32,51,74,.08) 2xl:0 30px 60px -12px rgba(32,51,74,.18)/0 8px 24px -6px rgba(32,51,74,.10)
Surface: bordered-lifted — grid:uniform-equal-height cols:3
Dark: #20334A — guides:dotted-gutter cut:diagonal
Gradient: mesh-ribbon — stops:#004E89,#1B6FA8,#7FB2D6,#20334A,#F8FAFC motion:slow-drift
CTA: radius:rounded-md size:px-6 py-3 weight:600 affordance:trailing-chevron
═══════════════════════
```

---

## Departures from capture

Where the spine deliberately overrides what capecrypto.com currently does. The
capture is evidence of the brand, not a target to reproduce — the site scored
31.4 / critical on the 2026-08-03 UI/UX audit.

| Property | Captured | Spine value | Why |
|----------|----------|-------------|-----|
| CTA radius | 25px (pill) | 6px (`rounded-md`) | Pills read consumer-app; the spine's whole thesis is squarish = "we handle money". Benchmark `cta_buttons.radius_px: [4,5,6]`. |
| CTA label size | 12.8px / weight 500 | 14px / weight 600 | 12.8px is below comfortable tap-label size; the spine inverts weight against light headings. |
| Card radius | 16px (n=10) | 8px (`rounded-lg`) | Spine `squarish`. |
| Heading weight | 700/800 (n=18) | 400 with tight tracking | Spine `light-display`. This is the single largest perceived-quality change. |
| Shadow | one layer, α=0.04 | two layers, α 0.10/0.08 | α=0.04 is invisible in practice — cards read flat. Layer *count* and *ink* are kept from capture. |
| Dark section | flat navy fill | navy + dotted gutter guides + diagonal cut | Spine `dark_section`. |
| Hero background | flat 135° grey wash | mesh-ribbon in brand blues | Spine `gradient`. |

Everything in that table is a **structure** change. No brand value was altered:
the navy, the blue, the two typefaces, the shadow ink and the surface tint are
exactly as measured.

---

## Content Direction

**Tone:** Inherits the spine. Regulatory standing is Cape Crypto's strongest
asset and must appear above the fold: **FSP No. 53746**, South Africa.
**Hero copy pattern:** two-tone. Lead clause in `#20334A`, outcome clause in
the accent gradient. The existing site's pattern — `[Action] + [Asset] +
[Geography]` ("Buy Bitcoin South Africa") — maps cleanly: lead = "Buy Bitcoin",
accent clause = "in South Africa" / "within a minute".
**CTA language:** "Get started", "Buy now", "Open an account". Secondary is
explanatory, matching the Sign Up → Deposit → Buy step flow already on the site.
**Trust chips:** FSP No. 53746 · South Africa · [founding year — NOT CAPTURED] ·
[settlement rail — NOT CAPTURED]. Two of four chips need a brief input.

---

## Photography / Visual Direction

- `app-screenshot.png` is the hero visual — a real product screenshot, which is
  exactly what the spine prescribes. Do not replace with stock.
- `step-signup.png` / `step-deposit.png` / `step-buy.png` drive HOW-IT-WORKS.
- `flag-sa.png` supports the geography trust signal.
- App Store + Google Play badges belong in the dark CTA band, not the hero.
- Partner logos (Numeral, Aluma, Xago, Idatco) in **full colour**, static row.
- Logo is a white lockup (`logo-white.svg`) — the nav must sit on the navy
  ground or a dark-tinted scroll state. No dark-on-light logo asset was
  captured; one is needed if a light nav is chosen.

---

## Known Pitfalls

Inherits all spine pitfalls. Tenant-specific:

- **Single-hue palette.** Every accent role resolves to a blue. Hierarchy has
  to be carried by *lightness and surface*, not hue — get the elevation ramp
  right or the page reads monotone. This was already flagged on the previous
  version of this preset and it remains the tenant's core visual risk.
- **No dark-on-light logo asset.** Blocks a light-nav design.
- **Weight drop 700/800 → 400 is jarring at small sizes.** Apply
  `light-display` only to h1/h2 at ≥32px; h3 and below stay at 600.
- **Two measured accent nodes total.** The accent has almost no presence on the
  current site — expect the rebuild to look substantially more branded, and
  confirm that is wanted before the cold run.

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-08-03 | Initial preset extraction | capecrypto.com |
| 2026-08-10 | Rebuilt on the `fintech-crypto` structural spine. Palette/typography replaced with values measured from `output/extractions/cape-crypto-689443d1/extraction-data.json` (147 nodes) — the previous preset's `sky-900`/`sky-800`/`Plus Jakarta Sans-only` values were approximations and did not match the site. Added elevation/surface/dark_section/gradient/cta/logo_bar blocks, provenance table, departures table, and explicit gap list. | stripe-benchmark spine + cape-crypto extraction |

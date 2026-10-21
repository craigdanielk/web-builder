# THURIS — resolved decisions (operator, 2026-10-21)

Precedence: this file > CI Guide PDF v1.0 > handoff YAML. Anything not listed here
follows the PDF where it speaks, else the YAML.

## Tenant (written to Supabase)
- tenant `thuris` id 2ca018c2-0e7c-4fe7-ab3c-ddb1ecea9223, region `za`, client_code TH, type Client
- target_platform shopify · source_platform **none** (added to vocabulary, web-builder 0167ce95)
- industry `luxury-premium` (registry key `industry` added) · cms none · email none
- target_markets: South Africa, UAE, United States, European Union, Australia, Asia, Canada
- currencies: AED, ZAR, USD, EUR, AUD, CAD — **fixed per-currency prices, supplied by operator (PENDING)**
- lead market: **UAE** (hero tone, default currency AED, default locale)
- verticals row deleted (was a workaround)

## Colour — two-mode system (operator replacement for PDF §04)
Dark Ceremonial (dominant on commerce, 60–70%):
  THURIS Black #09070B · Nocturne #120D14 · Black Violet #18111A · Violet Charcoal #312832 (border)
  Warm Ivory #F4EEE4 (text) · Ash #A69A91 (muted)
Light Editorial (provenance/editorial sections):
  Bone #F4F0E8 · Parchment #E7DED2 · Ivory #FBF8F2 · Warm Hairline #CFC5B8 (border)
  Charcoal #241F1B (text) · Stone #736A61 (muted)
Metals: Champagne Gold #C1A36B (primary accent: logo detail, product names, rules, primary CTA)
        Antique Brass #9A7748 (secondary; preferred accent on Bone/Parchment)
Product: Smoked Violet #291723 (product world only) · Resin Plum #5A3145 (highlight only, rare)
Rules: never #000000; no metallic gradients; no bright yellow-gold; violet never dominant;
never all colours in one composition.
Pairings: Black+Ivory+Champagne (principal luxury) · Bone+Charcoal+Brass (editorial) ·
Black+Violet+Champagne (product/ceremonial) · Parchment+Charcoal+Champagne (print)

CTA fills: dark sections Champagne Gold #C1A36B + THURIS Black label (8.3:1);
light sections **Charcoal #241F1B + Bone label (15.4:1)** — Brass on Bone is 3.62:1, fails AA.
Brass stays hairlines/details only.

## Benchmark + overrides (operator 2026-10-21)
- Corpus: Amouage en-ae + Aesop Marrakech Intense + Aesop fragrance category. Le Labo DROPPED
  (location gate captured instead of product page).
- THURIS overrides via preset `## Tenant Design Overrides` (tenant override in compiler, not in
  the market benchmark): full dark + light palettes, base 17px, sections 140px, radius 0, Bodoni
  Moda / Inter. Kept from measurement: type ratio 1.143, heading weight 400.
- Motion: subtle (declared at ratification).

## Typography
Display: **Bodoni Moda** 400/500 (no bold Didone) · Body/UI: **Inter** 400/500/600
Eyebrows: Inter 500 uppercase, tracking 0.18–0.28em · Body 16–18px, lh 1.45–1.65 ·
Nav/buttons 11–13px tracked

## Layout (PDF §06)
Airy · 12-col desktop / 4-col mobile · max width 1320px · section spacing 120–160 desktop / 56–72 mobile
Radius 0–2px · 1px hairlines · buttons 48–52px, square
Motion: subtle, slow weighted reveals, opacity + vertical, 450–700ms; no spring/bounce/parallax/autoplay

## Logo
Use **PDF raster crops** temporarily (assets/logos/pdf-raster/) until production vectors exist.
Supplied SVGs NOT used (wordmark/monogram don't match approved artwork).
Rules per PDF: clear space = one capital-T height; wordmark min 160px; lockup 220px; monogram 32px.
Descriptor: BOTANICAL FRAGRANCE HOUSE.

## Imagery
Both, by section: light editorial sections = natural directional light, limestone/travertine/plaster;
dark product sections = low-key cinematic, obsidian/smoked violet, champagne metal.
**No generation** — image slots stay empty (recorded omissions) until real assets supplied.

## Benchmark
Market key: `luxury-botanical-oils` — commissioned from Amouage en-ae, Aesop Marrakech Intense,
Le Labo Santal 33. Operator-declared fields from this file.

## Copy (operator, 2026-10-21 — supersedes PDF §11 naming + YAML page_copy)
- Release name **The Founding Collection** (not "Founding Edition"); CTA "Reserve the Founding Collection"
- Product noun **botanical essence** (FAQ: "10 ml botanical essences, not eau de parfum")
- **90 bottles, 30 per essence — operator-confirmed.** Exact line: "The Founding Release is limited
  to 90 bottles — 30 of each botanical essence."
- Page copy source: THURIS-launch-copy.md (11 sections; `[HOLD: …]` items never render until supplied)

## Shopify store
thuris.myshopify.com · plan Basic App Development · was USD / United States / EDT
→ operator: base **ZAR / South Africa / SAST**; AED, USD, EUR, AUD, CAD as Markets with fixed prices.

## Commerce
Pay-in-full pre-order via Shopify selling plan. Checkout DISABLED until launch_blockers in the
handoff YAML are resolved (ship window, policies, shipping/tax/payments, store access, domain).
Front end built now; store wired when operator creates store + re-auths Shopify MCP.

## Session 2026-10-21 (b) — operator answers
- **Nav logo: none until production vectors.** The nav renders no wordmark (no raster, no
  re-typeset text stand-in); the empty brand slot is recorded. PDF raster crops are not used on the site.
- **Conformance expectation = effective style** (benchmark + `style.tenant_overrides`). Declared
  overrides are listed in the gate report as declared deviations, not violations.
  `dna_type_scale` (templates hardcoding heading px instead of the type scale) stays a real finding.
- **Intake lives in a tracked path:** `web-builder/intake/thuris/` (moved from the gitignored
  `output/intake/thuris/`).

## Session 2026-10-21 (c) — operator answers
- **Type scale: snap templates to the scale.** Headings read type-scale tokens derived from the
  benchmark's measured heading sizes (luxury-botanical-oils tops out at 32px); no hardcoded
  48/56/96px display sizes.
- **Shopify product model: 3 products + a Shopify Bundle.** Frankincense, Neroli, Rose Geranium
  as products (30 each); the complete Founding Collection as a Bundle of the three, so inventory
  draws from each pool natively.
- **Cart/checkout wording: agent-written interim wording authorised** ("add relevant wording for
  now"). Every such string is marked interim in the source and listed here until replaced.
- **Live store writes authorised** (thuris.myshopify.com), confirming each irreversible step.

## Session 2026-10-21 (d) — operator answers
- Base prices = the AED figures (base currency USD; the API cannot change it).
- Image pack v1 placed per its own placement map; cap-monogram + concealed-reducer held (vessel [HOLD]).
- `required_disclaimers` (amendment, needs_confirm) are internal notes — **not rendered**.
- Hero: image-led, copy left (pack H01); final band copy right (H03).
- GitHub repo (private craigdanielk/thuris) + Vercel project `thuris` created and linked; live at
  https://thuris.vercel.app. Next session: section-by-section upgrade.

## Session 2026-10-21 (e) — Homepage Visual Refinement V1 (operator brief) + answers
Brief V1 supersedes earlier choices where they conflict: nav wordmark restored (was "none until
vectors"); display type H1 56–68 / H2 40–48 / H3 26–32 / body 16–18 / eyebrow 11–12 (was the
benchmark's measured 32px ceiling); content max-width 1200, gutters 24–72, sections 112–144.
- **Prices: display the differentiated model AED 495 / 445 / 445** (Frankincense / Neroli / Rose
  Geranium). Commercially DISPUTED vs the earlier 395/445/395 until explicitly approved.
  **Bundle: no price shown** (price and discount unconfirmed). Prices live in ONE place in the source
  (data-field="price" on the collection cards); no duplicated constants. Shopify prices NOT mutated.
- **Wordmark: supplied SVG `assets/logos/thuris-primary.svg`** (operator: "use it anyway").
- **Caps: Higgsfield edit** — every pack image re-rendered with a plain solid brushed-metal cap top
  (the engraved TT monogram read as holes/slots). gpt_image_2_5, high, reference = pack master.
- **Provenance: species, countries of origin and the on-bottle statement are all documented** —
  they stay. Ritual copy is trimmed to remove application/wearing implications (launch-copy HOLD).

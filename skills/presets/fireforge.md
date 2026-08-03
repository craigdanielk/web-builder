# Preset: Fireforge — Premium Custom Fire Equipment (cinematic D2C commerce)

Industries: High-end custom braais / grills / parrillas, outdoor fireplaces & fire
features, bespoke metal fabrication D2C, luxury outdoor-living products

Visual DNA cloned from exoape.com (cinematic editorial agency) and fused with
high-ticket product-commerce + CRO. Extraction source:
`output/extractions/fireforge-exoape/` (fonts Times + Lausanne, single warm
accent, radius 100%, full-bleed imagery, vast negative space, oversized display
headlines overlapping media).

---

## Default Section Sequence

```
1. HERO               | full-bleed-cinematic-statement   (fire/product film, oversized headline overlap)
2. INTRO              | editorial-statement              (short premium manifesto, large type, huge whitespace)
3. PRODUCT SHOWCASE   | horizontal-scroll-gallery        (T100, Forge Axe, Custom — cinematic cards)
4. FEATURE            | text-media-split-pinned          (raise/lower mechanism macro, scroll-pinned)
5. CRAFT STORY        | full-bleed-media-caption         (Elemetal laser-cut fabrication = trust)
6. CRO TRUST BAND     | proof-strip                      (304 stainless · lifetime · locally forged · social proof)
7. CUSTOM BUILD       | lead-funnel-cta                  (B2B/bespoke — architect/designer channel)
8. CONTACT/QUOTE      | split-form-cinematic             (quote capture → Supabase)
9. FOOTER             | minimal-credits
```

**Optional sections (add based on brief):**
- PRODUCT DETAIL TEMPLATE (PDP) → hero → spec → feature macro → lifestyle → price → configure/quote / PayFast buy
- LIFESTYLE GALLERY (if more imagery available) → insert after position 5
- FAQ (objection-handling for high-ticket) → insert before CONTACT

---

## Style Configuration

```yaml
color_temperature: dark

palette:
  bg_primary: stone-950          # near-black matte
  bg_secondary: neutral-900
  bg_accent: stone-100           # inverted light editorial breaks
  text_primary: stone-200
  text_heading: white
  text_muted: stone-400
  accent: orange-600             # ember / fire — #E2541B feel
  accent_hover: orange-500
  accent_secondary: zinc-300     # brushed stainless
  border: neutral-800

typography:
  pairing: editorial-serif-grotesk     # exoape echo: display serif + grotesk body
  heading_font: Times New Roman / PP Editorial-style display serif
  heading_weight: 400
  body_font: Lausanne / Neue Haas Grotesk-style
  body_weight: 300
  scale_ratio: 1.333                   # big editorial jumps, oversized hero
  weight_distribution: high-contrast   # thin body vs huge display

whitespace: extra-generous
section_padding: 10rem
internal_gap: 3.5rem

border_radius:
  buttons: pill                  # radius 100% from extraction
  cards: sharp                   # cinematic full-bleed cards, square corners
  inputs: pill

animation_engine: gsap
animation_intensity: expressive
entrance: mask-reveal            # headlines rise behind mask (exoape signature)
hover: image-scale-parallax
timing: slow-cinematic (0.8–1.2s, power3.out)
smooth_scroll: false             # pipeline contract; Lenis layered post-gen for exoape buttery feel
section_overrides: hero:character-reveal showcase:horizontal-drag feature:scroll-pin craft:parallax-media
gsap_plugins:
  - ScrollTrigger
  - SplitText
  - Flip

visual_density: airy
image_treatment: full-bleed-cinematic   # large, edge-to-edge, dim overlay, warm grade
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: dark (stone-950/neutral-900/white/orange-600) | stainless:zinc-300
Type: editorial-serif-grotesk — display serif headings (huge), thin grotesk body, contrast 1.333
Space: extra-generous (10rem sections, airy)
Radius: pill buttons / sharp cinematic cards
Motion: expressive/gsap — entrance:mask-reveal hover:image-scale-parallax timing:0.8–1.2s power3.out | hero:character-reveal showcase:horizontal-drag feature:scroll-pin
Density: airy | Images: full-bleed-cinematic (dim overlay, warm grade)
═══════════════════════
```

---

## Content Direction

**Tone:** Confident, crafted, understated premium. Heritage + precision. Never loud retail. Speaks to design taste and permanence ("forged once, lasts a lifetime").
**Hero copy pattern:** Short evocative intro paragraph (upper area) + one oversized display line overlapping the fire/product imagery (e.g. "Fire, Forged.").
**CTA language:** "Configure yours" · "Request a quote" · "Start your build" · "Explore the T100". High-ticket → quote-first, not "Add to cart" for bespoke; PayFast checkout reserved for accessories/deposits.

---

## Photography / Visual Direction

- Full-bleed cinematic product + live-fire imagery; matte black + brushed 304 stainless; warm ember glow; golden-hour lifestyle in luxury SA outdoor kitchens.
- Heroes from `tenants/fireforge/image-pipeline/` (black-studio + lifestyle). Dim gradient overlay so oversized white display type stays legible over imagery.
- Avoid trade-show/workshop artefacts (carpet, mesh) — those raw refs are elevated by the image pipeline before use.

---

## Known Pitfalls

- Don't let CRO blocks cheapen the cinematic feel — keep conversion elements minimal, typographic, generous; trust band is a quiet strip, not a loud banner.
- High-ticket = quote-led; do not force live-checkout UX on R100k+ bespoke items.
- exoape's animation registered "none/css" in the detector (custom JS) — IGNORE that; motion intent is expressive gsap + Lenis. Trust the brief, not the detector score.

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-06-24 | Created from exoape.com clone extraction + Fireforge brief | fireforge |

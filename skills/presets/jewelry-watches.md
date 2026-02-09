# Preset: Jewelry & Watches

Industries: luxury jewelry, handcrafted pieces, watch brands, minimalist accessories,
engagement rings, artisan metalwork.

---

## Default Section Sequence

```
1. NAV              | sticky-transparent
2. HERO             | full-bleed-overlay
3. PRODUCT-SHOWCASE | single-hero
4. ABOUT            | editorial-split
5. FEATURES         | alternating-rows
6. GALLERY          | lightbox-grid
7. TESTIMONIALS     | single-featured
8. CTA              | centered
9. FOOTER           | minimal
```

**Optional sections (add based on brief):**
- HOW-IT-WORKS (if custom/bespoke process) → insert after ABOUT
- TRUST-BADGES (if certifications matter — GIA, hallmarks) → insert after TESTIMONIALS
- FAQ (if high-value purchase questions) → insert before CTA
- VIDEO (if brand film or craftsmanship documentary) → insert after ABOUT

---

## Style Configuration

```yaml
color_temperature: dark
palette:
  bg_primary: neutral-950
  bg_secondary: neutral-900
  bg_accent: neutral-800
  text_primary: neutral-200
  text_heading: white
  text_muted: neutral-400
  accent: amber-400
  accent_hover: amber-300
  border: neutral-700

typography:
  pairing: serif-sans
  heading_font: Playfair Display
  heading_weight: 700
  body_font: Inter
  body_weight: 300
  scale_ratio: 1.414
  weight_distribution: heavy-light

whitespace: generous
section_padding: py-28
internal_gap: gap-10

border_radius: sharp
buttons: rounded-sm
cards: rounded-sm
inputs: rounded-sm

animation_intensity: subtle
entrance: fade-up
hover: slight-lift
timing: "0.5s ease-out"

visual_density: low
image_treatment: full-bleed
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: dark — bg:neutral-950/neutral-900 text:neutral-200 accent:amber-400 border:neutral-700
Type: serif-sans — heading:Playfair Display,700 body:Inter,300 scale:1.414
Space: generous — sections:py-28 internal:gap-10
Radius: sharp — buttons:rounded-sm cards:rounded-sm inputs:rounded-sm
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.5s ease-out
Density: low | Images: full-bleed
═══════════════════════
```

---

## Content Direction

**Tone:** Refined, unhurried, precise. Third person or impersonal voice. Short,
deliberate sentences. Emphasize heritage, craftsmanship, and materials. Every
word should feel considered.

**Hero copy pattern:** Lead with the craft or material, not the sale.
"Handforged in 18k gold" not "Shop our rings." Single line, maximum two.

**CTA language:** Understated luxury. "View the collection" not "Shop now."
"Book a consultation" not "Contact us." "Explore craftsmanship" not "Learn more."

---

## Photography / Visual Direction

- Macro photography — extreme close-ups of metalwork, stone settings, watch mechanisms
- Dark backgrounds with dramatic side-lighting to emphasize dimensionality
- Minimal props — black velvet, marble, or bare skin only
- Avoid lifestyle scenes — focus on the object itself as sculpture
- Color grading should be rich with deep shadows and warm metallic highlights

---

## Known Pitfalls

- Dark backgrounds with light text need careful contrast tuning. neutral-200 on
  neutral-950 works, but neutral-400 (muted text) may be too low-contrast —
  test at body sizes.
- Gold accent (amber-400) on dark backgrounds is luxurious but can feel gaudy
  if overused. Reserve for CTAs and key highlights only.
- Sharp radius on dark backgrounds can feel brutalist rather than luxurious.
  The serif typography (Playfair Display) is critical to softening the feel.
- Macro photography requires extremely high resolution. Low-res jewelry shots
  look amateurish and destroy trust instantly.

---

## Reference Sites

Study these for pattern validation (not copying):
- Cartier, Mejuri, NOMOS Glashütte, Brilliant Earth, Tiffany & Co.
- Look for: product image presentation, dark mode execution, detail
  photography, animation restraint, trust-building elements

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

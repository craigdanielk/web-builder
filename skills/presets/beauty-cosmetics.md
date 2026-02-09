# Preset: Beauty & Cosmetics

Industries: skincare brands, makeup companies, wellness products, clean beauty,
fragrance, hair care, self-care brands.

---

## Default Section Sequence

```
1. NAV              | sticky-transparent
2. HERO             | product-hero
3. FEATURES         | alternating-rows
4. HOW-IT-WORKS     | icon-steps
5. PRODUCT-SHOWCASE | grid
6. TESTIMONIALS     | grid
7. NEWSLETTER       | split
8. FOOTER           | minimal
```

**Optional sections (add based on brief):**
- ANNOUNCEMENT-BAR (if free shipping/promotion) → insert before HERO
- STATS (if clinical results or user numbers) → insert after FEATURES
- FAQ (if ingredient questions common) → insert before NEWSLETTER
- BLOG-PREVIEW (if content/education focus) → insert before NEWSLETTER

---

## Style Configuration

```yaml
color_temperature: pastel
palette:
  bg_primary: rose-50
  bg_secondary: white
  bg_accent: pink-50
  text_primary: stone-800
  text_heading: stone-900
  text_muted: stone-400
  accent: rose-500
  accent_hover: rose-600
  border: rose-200

typography:
  pairing: serif-sans
  heading_font: Lora
  heading_weight: 600
  body_font: DM Sans
  body_weight: 400
  scale_ratio: 1.333
  weight_distribution: medium-regular

whitespace: generous
section_padding: py-24
internal_gap: gap-8

border_radius: full
buttons: rounded-2xl
cards: rounded-3xl
inputs: rounded-xl

animation_intensity: subtle
entrance: fade-up
hover: slight-lift
timing: "0.6s ease-out"

visual_density: low
image_treatment: contained
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: pastel — bg:rose-50/white text:stone-800 accent:rose-500 border:rose-200
Type: serif-sans — heading:Lora,600 body:DM Sans,400 scale:1.333
Space: generous — sections:py-24 internal:gap-8
Radius: full — buttons:rounded-2xl cards:rounded-3xl inputs:rounded-xl
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.6s ease-out
Density: low | Images: contained
═══════════════════════
```

---

## Content Direction

**Tone:** Warm, knowledgeable, intimate. Second person ("you" / "your skin").
Conversational but not casual. Focus on ritual, self-care, and ingredient
education. Avoid clinical coldness.

**Hero copy pattern:** Lead with a feeling or benefit, then the product.
"Radiance starts with what's underneath" not "Buy our new serum." Product is
the visual hero; copy supports.

**CTA language:** Inviting and personal. "Find your routine" not "Shop now."
"Discover the ritual" not "Buy products." "Start your journey" not "Sign up."

---

## Photography / Visual Direction

- Close-up product textures — creams, serums, powders on surfaces
- Warm, soft lighting with gentle shadows — never harsh studio flash
- Ingredient close-ups — botanicals, oils, minerals in natural settings
- Application moments — hands, skin, ritual — authentic not posed
- Color grading matches palette — warm pinks and soft neutrals

---

## Known Pitfalls

- Pastel palettes can wash out. Ensure rose-500 accent has sufficient contrast
  against rose-50 backgrounds (4.5:1 minimum for text).
- Full radius on everything can feel toy-like. The serif heading font (Lora)
  counterbalances the softness — don't swap it for a rounded sans.
- Beauty sites live or die by photography quality. Placeholder images in wrong
  tones will ruin the preset's feel entirely.
- Avoid the "Instagram brand" trap — too many lifestyle shots and not enough
  product information. The FEATURES and HOW-IT-WORKS sections must deliver
  substance.

---

## Reference Sites

Study these for pattern validation (not copying):
- Glossier, Drunk Elephant, Aesop, The Ordinary, Byredo
- Look for: product hero treatment, ingredient storytelling, routine/ritual
  sections, color palette restraint, mobile product browsing

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

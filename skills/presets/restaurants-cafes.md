# Preset: Restaurants & Cafes

Industries: fine dining, casual restaurants, specialty cuisine, wine bars,
cocktail bars, cafe chains, pop-up restaurants, catering.

---

## Default Section Sequence

```
1. NAV              | sticky-transparent
2. HERO             | full-bleed-overlay (atmospheric food or interior shot)
3. ABOUT            | editorial-split (chef story or founding narrative)
4. PRODUCT-SHOWCASE | single-hero (signature dish or menu highlight)
5. GALLERY          | lightbox-grid (food + ambiance photography)
6. TESTIMONIALS     | single-featured
7. CTA              | split-with-image (reservation or private dining)
8. CONTACT          | info-plus-form (hours, address, reservations)
9. FOOTER           | minimal
```

**Optional sections (add based on brief):**
- VIDEO (if chef's table or kitchen footage) → insert after ABOUT
- FEATURES (if private dining, events, catering services) → insert after GALLERY
- NEWSLETTER (if seasonal menu updates or events) → insert before FOOTER
- BLOG-PREVIEW (if recipes or culinary journal) → insert before CTA

---

## Style Configuration

```yaml
color_temperature: dark
palette:
  bg_primary: neutral-950
  bg_secondary: neutral-900
  bg_accent: amber-950
  text_primary: neutral-100
  text_heading: white
  text_muted: neutral-400
  accent: amber-500
  accent_hover: amber-400
  border: neutral-800

typography:
  pairing: editorial
  heading_font: Cormorant Garamond
  heading_weight: 600
  body_font: Inter
  body_weight: 300
  scale_ratio: 1.414
  weight_distribution: heavy-light

whitespace: generous
section_padding: py-24
internal_gap: gap-8

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
Palette: dark — bg:neutral-950/neutral-900 text:neutral-100 accent:amber-500 border:neutral-800
Type: editorial — heading:Cormorant Garamond,600 body:Inter,300 scale:1.414
Space: generous — sections:py-24 internal:gap-8
Radius: sharp — buttons:rounded-sm cards:rounded-sm inputs:rounded-sm
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.5s ease-out
Density: low | Images: full-bleed
═══════════════════════
```

---

## Content Direction

**Tone:** Understated, evocative, sensory. Third person or impersonal ("the
kitchen," "our table"). Short, deliberate sentences. Let images and atmosphere
carry most of the weight. Every word should earn its place. The copy sets a
mood, not a pitch.

**Hero copy pattern:** Minimal — a phrase or the restaurant name, never a
paragraph. "Seasonal. Local. Intentional." or just the name over a moody
interior shot. The image IS the message.

**Menu presentation:** Treat the menu as a design object. Clean typography,
generous spacing, no clip-art icons. Dish names in heading font, descriptions
in body. Price aligned right. Seasonal menus should feel curated, not listed.

**CTA language:** Elegant, never urgent. "Reserve a table" / "View the menu" /
"Join us" — soft commands that feel like invitations, not transactions.

---

## Photography / Visual Direction

- Dark, moody food photography: low-key lighting, rich shadows, warm highlights on dishes
- Interior shots emphasizing atmosphere: candlelight, textures, empty tables set for service
- Overhead and close-up plating shots with shallow depth of field
- Color grading: warm highlights, cool shadows, high contrast — cinematic not clinical
- Avoid bright, flat, overhead "food blog" photography — this is editorial, not Instagram

---

## Known Pitfalls

- Dark backgrounds require careful contrast management. Body text at weight 300
  on neutral-950 needs to be neutral-100 minimum, never neutral-300 or below.
  Test readability at every section.
- Sharp radius (rounded-sm) on dark backgrounds can feel stark. Use subtle
  border-neutral-800 borders to define card edges without harshness.
- "Subtle" animation on a dark site means almost invisible. The fade-up should be
  barely perceptible — 20px y-offset maximum. Anything more breaks the elegance.
- Menu sections are the most visited part of restaurant sites. If the brief includes
  a menu, it must be fast-loading, mobile-optimized, and never a PDF embed.

---

## Reference Sites

Study these for pattern validation (not copying):
- Noma, Eleven Madison Park, Chez Panisse, Hawksmoor, Le Bernardin
- Look for: hero atmosphere, menu typography, reservation flow, image-to-text
  ratio, dark palette execution, section pacing on scroll

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

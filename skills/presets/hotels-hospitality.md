# Preset: Hotels & Hospitality

Industries: boutique hotels, luxury resorts, vacation rentals, bed & breakfasts,
wellness retreats, glamping, hospitality groups.

---

## Default Section Sequence

```
1. NAV              | sticky-transparent
2. HERO             | video-background (property flyover or guest experience)
3. ABOUT            | editorial-split (property story or philosophy)
4. FEATURES         | alternating-rows (rooms, amenities, experiences)
5. GALLERY          | carousel (rooms, spaces, details, landscapes)
6. TESTIMONIALS     | carousel (guest reviews)
7. STATS            | inline-bar (awards, years, guest satisfaction)
8. CTA              | split-with-image (booking CTA with property shot)
9. CONTACT          | simple-form (booking inquiry or concierge)
10. FOOTER          | split
```

**Optional sections (add based on brief):**
- PRICING (if clear room tiers or packages) → insert after FEATURES
- VIDEO (if property film or experience reel) → insert after ABOUT
- FAQ (if common guest questions about location, amenities) → insert before CTA
- BLOG-PREVIEW (if travel journal or local guides) → insert before FOOTER

---

## Style Configuration

```yaml
color_temperature: neutral
palette:
  bg_primary: neutral-50
  bg_secondary: white
  bg_accent: amber-50
  text_primary: neutral-800
  text_heading: neutral-900
  text_muted: neutral-400
  accent: amber-600
  accent_hover: amber-700
  border: neutral-200

typography:
  pairing: serif-sans
  heading_font: Playfair Display
  heading_weight: 600
  body_font: Inter
  body_weight: 300
  scale_ratio: 1.414
  weight_distribution: heavy-light

whitespace: generous
section_padding: py-24
internal_gap: gap-10

border_radius: medium
buttons: rounded-lg
cards: rounded-xl
inputs: rounded-lg

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
Palette: neutral — bg:neutral-50/white text:neutral-800 accent:amber-600 border:neutral-200
Type: serif-sans — heading:Playfair Display,600 body:Inter,300 scale:1.414
Space: generous — sections:py-24 internal:gap-10
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.5s ease-out
Density: low | Images: full-bleed
═══════════════════════
```

---

## Content Direction

**Tone:** Serene, aspirational, immersive. Second person ("you" and "your stay").
Sentences should breathe — unhurried, sensory, evocative of place. The copy
should make you feel the linen, hear the waves, see the morning light. Never
salesy or feature-listy. This is storytelling, not a brochure.

**Hero copy pattern:** Minimal and evocative — a single line or the property name.
"Where the mountain meets the sea" or "A place to arrive." The video or image
carries the emotion; the text is a whisper, not a shout.

**Features / rooms:** Present each room or experience as its own world. Name,
a single evocative sentence, key details (size, view, amenities) in clean
typography. Alternating layout keeps the scroll feeling like a journey.

**CTA language:** Invitational and soft. "Reserve your stay" / "Begin planning" /
"Explore rooms" / "Inquire" — luxury hospitality never pushes. The CTA should
feel like an open door, not a checkout button.

---

## Photography / Visual Direction

- Full-bleed property photography: architecture, interiors, landscapes at golden hour
- Detail shots: crisp linens, artisan coffee service, bathroom textures, local flora
- Lifestyle moments: guest reading on terrace, couple at sunset, spa treatment in progress
- Color grading: warm, soft, slightly lifted shadows — luminous not contrasty
- Every image should transport — if it doesn't make someone want to be there, cut it

---

## Known Pitfalls

- Neutral palette with amber accents can feel too similar to the artisan-food preset.
  Differentiate through Playfair Display serif, generous gap-10 internal spacing,
  and the airy, light-background approach vs artisan-food's warmer stone tones.
- Body text at weight 300 on light backgrounds needs sufficient color contrast.
  neutral-800 on neutral-50 is safe, but never go lighter than neutral-400 for
  muted text.
- "Subtle" animation on a luxury site means graceful, not absent. The fade-up should
  feel like a curtain rising — smooth and inevitable. Duration 0.5s is the ceiling.
- Hospitality sites live and die by image quality. If the property photography isn't
  exceptional, the whole site falls flat. Flag this as a dependency in the brief review.

---

## Reference Sites

Study these for pattern validation (not copying):
- Aman Resorts, Ace Hotel, 1 Hotels, Soho House, Six Senses
- Look for: hero immersion, room presentation patterns, booking CTA placement,
  gallery treatments, typography scale on large screens, scroll pacing

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

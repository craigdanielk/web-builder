# Preset: Events & Venues

Industries: wedding venues, conference centers, coworking spaces, event planning,
concert venues, exhibition spaces, retreat centers.

---

## Default Section Sequence

```
1. NAV              | sticky-transparent
2. HERO             | full-bleed-overlay
3. ABOUT            | editorial-split
4. GALLERY          | lightbox-grid
5. FEATURES         | icon-grid (spaces / packages)
6. HOW-IT-WORKS     | numbered-steps (booking process)
7. TESTIMONIALS     | carousel
8. PRICING          | three-tier (packages or room options)
9. FAQ              | accordion
10. CONTACT         | info-plus-form (inquiry / booking)
11. FOOTER          | mega
```

**Optional sections (add based on brief):**
- STATS (if capacity/events-hosted numbers are impressive) → insert after ABOUT
- VIDEO (venue tour or highlight reel) → insert after HERO
- LOGO-BAR (if notable corporate clients or press features) → insert after ABOUT
- BLOG-PREVIEW (if venue publishes event recaps) → insert before FOOTER

---

## Style Configuration

```yaml
color_temperature: warm
palette:
  bg_primary: neutral-50
  bg_secondary: white
  bg_accent: amber-50
  text_primary: neutral-900
  text_heading: neutral-950
  text_muted: neutral-500
  accent: amber-600
  accent_hover: amber-700
  border: neutral-200

typography:
  pairing: serif-sans
  heading_font: Playfair Display
  heading_weight: 700
  body_font: Inter
  body_weight: 400
  scale_ratio: 1.414
  weight_distribution: heavy-light

whitespace: generous
section_padding: py-24
internal_gap: gap-8

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
Palette: warm — bg:neutral-50/white text:neutral-900 accent:amber-600 border:neutral-200
Type: serif-sans — heading:Playfair Display,700 body:Inter,400 scale:1.414
Space: generous — sections:py-24 internal:gap-8
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.5s ease-out
Density: low | Images: full-bleed
═══════════════════════
```

---

## Content Direction

**Tone:** Elegant, aspirational, warm. Second person ("your") for client-facing
copy, first person plural ("we") for venue story. Short, evocative sentences.
Paint the scene — what it feels like to be there.

**Hero copy pattern:** Lead with the experience, not the logistics.
"Where unforgettable moments begin" not "Book our 10,000 sq ft venue."
Let the photography do the heavy lifting; text should be minimal and refined.

**CTA language:** Warm and inviting, never transactional. "Plan your event"
not "Submit inquiry." "Explore our spaces" not "View pricing." "Schedule a
tour" not "Contact us."

**Industry-specific notes:** Wedding venues need emotional resonance; corporate
venues need credibility and specs. If the brief serves both, segment the gallery
and features into distinct collections (e.g., "Celebrations" and "Conferences").

---

## Photography / Visual Direction

- Full-bleed hero with warm, golden-hour or ambient-lit venue photography
- Wide-angle architectural shots showing space, light, and scale
- Detail shots: table settings, floral arrangements, lighting fixtures, textures
- Candid event moments — guests laughing, speakers presenting, couples dancing
- Avoid empty, sterile room photos. Every space shot should suggest life and energy

---

## Known Pitfalls

- Full-bleed venue photos need careful overlay gradients (from-black/50 to-transparent)
  to maintain text readability. Don't rely on image brightness alone.
- Serif headings at large scale ratios (1.414) can overwhelm on mobile. Ensure
  responsive font sizing scales down gracefully.
- "Elegant" doesn't mean slow. Keep page weight low — lazy-load gallery images
  and compress hero photography aggressively.
- Wedding and corporate audiences have very different visual expectations. If the
  venue serves both, don't default to one aesthetic. Use gallery segmentation.

---

## Reference Sites

Study these for pattern validation (not copying):
- Cedar Lakes Estate, The Hoxton, Convene, Soho Works, 1 Hotel Brooklyn Bridge
- Look for: hero image treatment, gallery layout, booking flow prominence,
  how they balance aspirational imagery with practical information (capacity, pricing)

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

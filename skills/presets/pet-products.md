# Preset: Pet Products & Wellness

Industries: premium pet food, pet accessories, pet wellness, grooming products,
pet subscription boxes, pet tech.

---

## Default Section Sequence

```
1. NAV              | sticky-solid
2. HERO             | split-image (happy pet + owner)
3. LOGO-BAR         | static-grid (press mentions or retail partners)
4. PRODUCT-SHOWCASE | hover-cards
5. HOW-IT-WORKS     | icon-steps (subscription or product process)
6. TESTIMONIALS     | carousel
7. FEATURES         | icon-grid
8. FAQ              | accordion
9. CTA              | centered
10. FOOTER          | mega
```

**Optional sections (add based on brief):**
- PRICING (if subscription model) → insert after HOW-IT-WORKS
- STATS (if strong metrics like pets served, meals delivered) → insert after LOGO-BAR
- BLOG-PREVIEW (if pet care content marketing) → insert before CTA
- TRUST-BADGES (if vet-approved, organic certifications) → insert after FEATURES

---

## Style Configuration

```yaml
color_temperature: pastel
palette:
  bg_primary: amber-50
  bg_secondary: white
  bg_accent: teal-50
  text_primary: stone-800
  text_heading: stone-900
  text_muted: stone-400
  accent: teal-600
  accent_hover: teal-700
  border: stone-200

typography:
  pairing: humanist
  heading_font: Source Sans 3
  heading_weight: 700
  body_font: Source Sans 3
  body_weight: 400
  scale_ratio: 1.250
  weight_distribution: heavy-light

whitespace: moderate
section_padding: py-20
internal_gap: gap-8

border_radius: pill
buttons: rounded-full
cards: rounded-2xl
inputs: rounded-full

animation_intensity: moderate
entrance: fade-up-stagger
hover: slight-lift
timing: "0.5s ease-out"

visual_density: medium
image_treatment: contained
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: pastel — bg:amber-50/white text:stone-800 accent:teal-600 border:stone-200
Type: humanist — heading:Source Sans 3,700 body:Source Sans 3,400 scale:1.250
Space: moderate — sections:py-20 internal:gap-8
Radius: pill — buttons:rounded-full cards:rounded-2xl inputs:rounded-full
Motion: moderate — entrance:fade-up-stagger hover:slight-lift timing:0.5s ease-out
Density: medium | Images: contained
═══════════════════════
```

---

## Content Direction

**Tone:** Warm, friendly, trustworthy. Second person ("you" and "your pet").
Conversational but informed — speak like a knowledgeable friend, not a vet
textbook. Slightly playful without being childish or cloying. Pet parents
are discerning; respect their intelligence.

**Hero copy pattern:** Lead with the pet's wellbeing and the owner's peace of
mind. "Real food your dog will actually love" not "Premium pet food for sale."
The emotional hook is the bond between pet and owner.

**HOW-IT-WORKS:** 3-4 clear steps for the subscription or product journey.
"Tell us about your pet → We customize the plan → Delivered to your door."
Use friendly icons and keep copy scannable.

**CTA language:** Warm and inviting. "Get started" / "Try it free" /
"Find the perfect fit" / "Meet our meals" — approachable, never pushy.
Emphasize free trials, satisfaction guarantees, or easy cancellation.

---

## Photography / Visual Direction

- Happy, natural pet photography: dogs mid-play, cats lounging, genuine moments
- Warm, bright lighting with soft shadows — studio-quality but not sterile
- Contained images with generous rounded corners (rounded-2xl) for friendly feel
- Product shots styled with natural elements (wooden bowls, linen, greenery)
- Avoid overly posed or stock-photo pets — authenticity reads immediately

---

## Known Pitfalls

- Pastel palette can feel washed out. The teal-600 accent needs to be used
  consistently on CTAs and interactive elements to provide visual anchors.
- Pill radius everywhere can feel childish. Use rounded-full on buttons and
  inputs, rounded-2xl on cards — the cards need slightly less roundness to
  maintain structure.
- "Friendly" doesn't mean cluttered. Keep the medium density disciplined.
  Every section needs clear hierarchy and breathing room despite the warm,
  inviting tone.
- Pet subscription sites often overuse "cute" copy. Keep the language warm
  but grounded in real benefits (nutrition, health, convenience).

---

## Reference Sites

Study these for pattern validation (not copying):
- The Farmer's Dog, Wild One, Fi, Bark, Ollie
- Look for: hero splits with pet imagery, subscription flow UX, testimonial
  presentation, trust signals (vet endorsements, ingredient transparency),
  color palette warmth

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

# Preset: Adventure Tours & Experiences

Industries: guided adventure tours, ocean/coastal experiences (surf, kayak, boat
cruises, shark/scuba diving), hiking & trekking operators, safari & wildlife tours,
zipline/canyoning, multi-day expeditions, activity booking operators. Booking-led
(experiences are the product), not gear retail.

> Sibling preset: `outdoor-adventure.md` covers gear/apparel **commerce**. This preset
> covers **bookable experiences** — the catalogue is tours, the conversion is a booking.

---

## Default Section Sequence

```
1.  HERO            | video-background      (epic coastline / on-water action footage)
2.  ABOUT           | editorial-split       (who we are — local guides, the promise)
3.  PRODUCT-SHOWCASE| hover-cards           (tours as cards: name · duration · from-price · difficulty)
4.  HOW-IT-WORKS    | numbered-steps        (book in 3 steps: choose · pick date · confirm)
5.  FEATURES        | icon-grid             (why us: certified guides, small groups, safety, gear incl.)
6.  STATS           | counter               (years running · guests hosted · tours · 5-star reviews)
7.  TESTIMONIALS    | wall                  (guest reviews w/ trip + rating)
8.  GALLERY         | masonry               (real trip photography)
9.  FAQ             | accordion             (booking, cancellation, fitness/safety, what to bring)
10. CTA             | split-image           (book your adventure / enquire)
```

NAV (`sticky-transparent`) and FOOTER (`mega`) are sourced from the `shared` page-type
preset and are not repeated here.

**Optional sections (add based on brief):**
- LOGO-BAR (`static-grid`) — if accredited / featured (TripAdvisor, PADI, tourism board) → insert after HERO
- VIDEO (`autoplay-hero`) — if a brand film / sizzle reel exists → insert after ABOUT
- TRUST-BADGES (`horizontal-strip`) — safety certs, insurance, awards → insert after HOW-IT-WORKS
- BLOG-PREVIEW — if adventure stories / trip journals → insert before CTA

---

## Style Configuration

```yaml
color_temperature: cool-coastal
palette:
  bg_primary: slate-50
  bg_secondary: white
  bg_accent: cyan-50
  text_primary: slate-900
  text_heading: slate-950
  text_muted: slate-500
  accent: cyan-700              # ocean
  accent_hover: cyan-800
  accent_secondary: amber-500   # sand / sun — reserve for primary booking CTAs
  border: slate-200

section_accents:
  hero: cyan-900                # deep-water overlay for legible hero text
  cta: amber-500               # warm, high-contrast booking CTA band

typography:
  pairing: display-clean
  heading_font: Clash Display
  heading_weight: 700
  body_font: Inter
  body_weight: 400
  scale_ratio: 1.333
  weight_distribution: heavy-light

whitespace: moderate
section_padding: py-20
internal_gap: gap-6

border_radius: medium
buttons: rounded-lg
cards: rounded-xl
inputs: rounded-lg

animation_engine: gsap
animation_intensity: moderate
entrance: fade-up-stagger
hover: lift-shadow
timing: "0.6s ease-out"
smooth_scroll: false
section_overrides: hero:video-parallax stats:count-up gallery:reveal-stagger cards:lift-shadow

visual_density: medium
image_treatment: full-bleed
```

---

## Compact Style Header

Copy this exactly into every section generation prompt:

```
═══ STYLE CONTEXT ═══
Palette: cool-coastal — bg:slate-50/white text:slate-900 accent:cyan-700 cta:amber-500 border:slate-200
Type: display-clean — heading:Clash Display,700 body:Inter,400 scale:1.333
Space: moderate — sections:py-20 internal:gap-6
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: moderate/gsap — entrance:fade-up-stagger hover:lift-shadow timing:0.6s ease-out | hero:video-parallax stats:count-up gallery:reveal-stagger
Density: medium | Images: full-bleed
═══════════════════════
```

---

## Content Direction

**Tone:** Bold, vivid, second person ("you"). Sell the feeling of the day — salt
air, the drop, the summit — before the logistics. Confident and reassuring on
safety without being clinical. Local and authentic over corporate.

**Hero copy pattern:** Lead with the experience, not the booking. "Meet the Atlantic
on its own terms" not "Book a tour today." Hero should make you feel the swell.

**Tours showcase (PRODUCT-SHOWCASE):** Each card is a bookable experience — title,
one-line hook, duration, group size, difficulty/fitness level, and "from R___"
price. Card CTA = "View dates" / "Check availability", never "Add to cart".

**How-it-works:** Reduce booking anxiety to three calm steps. Name what's included
(guide, gear, transfers) and the no-fuss cancellation up front.

**CTA language:** Invitational and time-aware. "Check availability" / "Book your
spot" / "Plan your adventure" / "Enquire". Avoid "Buy now".

---

## Photography / Visual Direction

- Full-bleed action & landscape: ocean breaks, sea cliffs, golden-hour coastline, on-water POV
- Real guests in real conditions — candid, motion acceptable; faces lit, joyful
- Guide-led shots that signal expertise and safety (briefings, gear, small groups)
- Cool, slightly desaturated grade with warm highlights — natural, not over-saturated
- Avoid stocky/staged hero images; in-situ trip photography converts better

---

## Known Pitfalls

- Cyan can drift "corporate/tech" if flat — let photography carry the ocean colour and
  keep cyan-700 for accents/links, amber-500 only for the primary booking CTA.
- Booking businesses live or die on trust: keep safety, cancellation, and "what's
  included" visible above the fold of the relevant sections — don't bury in FAQ alone.
- Video hero must have a strong static fallback frame; the hero should read complete
  before the clip loads (ties to the Wix hero Custom-Element spike, AAH-05).
- "From R___" pricing must be honest — undersold anchor prices erode trust at checkout.
- Difficulty/fitness labelling prevents bad-fit bookings and refunds — always include it.

---

## Reference Sites

Study for pattern validation (not copying):
- Intrepid Travel, G Adventures, Much Better Adventures, GetYourGuide, Viator,
  Airbnb Experiences, local operators (e.g. Cape-based ocean & adventure tours)
- Look for: experience-card patterns, availability/date UX, trust & safety framing,
  itinerary/how-it-works sequencing, review walls.

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-06-16 | Initial preset created (AAH-02). Adapted from `outdoor-adventure` for booking-led tours; cool-coastal palette; GSAP hero. | Atlantic Adventures (tenant `2832d4ce`) |

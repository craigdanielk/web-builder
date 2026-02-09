# Preset: Medical & Dental

Industries: medical practices, dental offices, specialist clinics, dermatology,
orthodontics, physical therapy, optometry, veterinary clinics.

---

## Default Section Sequence

```
1. NAV              | sticky-solid
2. HERO             | split-image (welcoming provider/facility photo)
3. FEATURES         | icon-grid (services offered)
4. TEAM             | featured-leadership (providers with credentials)
5. HOW-IT-WORKS     | icon-steps (patient journey: book → visit → follow-up)
6. TESTIMONIALS     | carousel (patient reviews)
7. FAQ              | categorized (insurance, procedures, first visits)
8. STATS            | inline-bar (patients served, years in practice)
9. TRUST-BADGES     | certification-logos (board certifications, affiliations)
10. CONTACT         | info-plus-form (appointment booking)
11. FOOTER          | mega
```

**Optional sections (add based on brief):**
- GALLERY (if facility tour or before/after results) → insert after TEAM
- BLOG-PREVIEW (if publishing health tips or practice news) → insert before CONTACT
- PRICING (if transparent pricing model) → insert after FEATURES
- VIDEO (if virtual tour or provider introduction) → insert after HERO

---

## Style Configuration

```yaml
color_temperature: pastel
palette:
  bg_primary: white
  bg_secondary: sky-50
  bg_accent: teal-50
  text_primary: slate-800
  text_heading: slate-900
  text_muted: slate-400
  accent: sky-600
  accent_hover: sky-700
  border: slate-200

typography:
  pairing: humanist
  heading_font: Open Sans
  heading_weight: 600
  body_font: Open Sans
  body_weight: 400
  scale_ratio: 1.250
  weight_distribution: medium-regular

whitespace: moderate
section_padding: py-20
internal_gap: gap-6

border_radius: full
buttons: rounded-2xl
cards: rounded-3xl
inputs: rounded-xl

animation_intensity: subtle
entrance: fade-up
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
Palette: pastel — bg:white/sky-50 text:slate-800 accent:sky-600 border:slate-200
Type: humanist — heading:Open Sans,600 body:Open Sans,400 scale:1.250
Space: moderate — sections:py-20 internal:gap-6
Radius: full — buttons:rounded-2xl cards:rounded-3xl inputs:rounded-xl
Motion: subtle — entrance:fade-up hover:slight-lift timing:0.5s ease-out
Density: medium | Images: contained
═══════════════════════
```

---

## Content Direction

**Tone:** Warm, reassuring, professional. Second person ("you're in good hands")
mixed with first person plural ("our team"). Simple, jargon-free language.
Patients are often anxious — every sentence should reduce friction and build
comfort.

**Hero copy pattern:** Reassurance + specialization + action. "Gentle,
comprehensive dental care for your whole family" or "Expert dermatology in
a space designed for your comfort." Never lead with clinical language.

**CTA language:** Low-barrier and specific. "Book your appointment" not
"Schedule a consultation." "Call us today" not "Get in touch." Include
phone number prominently — many medical patients prefer calling.

**Industry-specific notes:** The TEAM section is critical. Every provider needs
a warm, professional headshot, full credentials (degrees, board certifications,
specialties), and a brief personal note. Patients choose providers, not practices.
The FAQ section must cover insurance, new patient process, and common procedure
questions — this reduces call volume and builds trust before the first visit.

---

## Photography / Visual Direction

- Warm, well-lit photos of real providers interacting with patients (with consent)
- Clean, modern facility shots showing welcoming reception and treatment areas
- Friendly provider headshots: approachable expressions, professional but not stiff
- Avoid cold, clinical imagery — add warmth through natural light and soft tones
- If stock photos are necessary, choose diverse, natural-looking medical imagery

---

## Known Pitfalls

- Pastel palette (sky-50, teal-50) can feel washed-out on low-quality monitors.
  Ensure accent color (sky-600) provides sufficient contrast for all CTAs and links.
- Medical sites must be WCAG AA compliant — many patients are elderly or have
  visual impairments. Test slate-400 muted text against all backgrounds carefully.
- "Full" border radius on cards (rounded-3xl) works well for service cards but
  can distort small elements. Keep avatars and badges at rounded-full or rounded-xl.
- Provider headshots must be consistent: same background, similar framing, matching
  color temperature. Mismatched photos destroy the professional appearance instantly.

---

## Reference Sites

Study these for pattern validation (not copying):
- One Medical, Tend, ZocDoc, Aspen Dental, Warby Parker (for the retail-medical crossover)
- Look for: appointment booking flow, provider profiles, how they balance clinical
  credibility with approachable warmth, FAQ structure, mobile experience

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial preset created | — |

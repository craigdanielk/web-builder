# Preset: Premium Coffee & Tea E-Commerce

Industries: specialty coffee roasters, tea merchants, gourmet beverage retailers, artisan food & drink shops, Swiss/European premium beverage brands

---

## Default Section Sequence

```
1. HERO                 | full-bleed-overlay
2. FEATURES             | icon-grid
3. PRODUCTS             | featured-grid
4. PRODUCTS             | category-showcase
5. FOOTER               | mega
```

**Optional sections (add based on brief):**
- TESTIMONIALS (if social proof needed) → insert after position 3
- ABOUT (if brand story emphasis) → insert after HERO
- NEWSLETTER (if email collection priority) → insert before FOOTER

---

## Style Configuration

```yaml
color_temperature: warm-luxe
palette:
  bg_primary: stone-50
  bg_secondary: neutral-900
  bg_accent: amber-700
  text_primary: neutral-900
  text_heading: neutral-900
  text_muted: neutral-700
  accent: amber-700
  accent_hover: amber-800
  border: stone-200

typography:
  pairing: modern-humanist
  heading_font: Figtree
  heading_weight: 600
  body_font: Instrument Sans
  body_weight: 400
  scale_ratio: 1.250
  weight_distribution: medium-contrast

whitespace: generous
section_padding: 5rem
internal_gap: 2.5rem

border_radius: sharp
buttons: 3.2px
cards: 3.2px
inputs: 3.2px

animation_engine: css
animation_intensity: expressive
entrance: fadeIn, blockFadeIn, blockFadeInLeft
hover: transform-scale, opacity-fade
timing: 0.7s ease-in-out, 0.25s ease-out
smooth_scroll: false
section_overrides: hero:FadeIn products:fadeInUp cta:bounceIn

visual_density: spacious
image_treatment: natural-photography
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: warm-luxe • stone-50 bg • amber-700 accent • neutral-900 text
Type: Figtree/Instrument Sans • 600/400 • 1.250 scale • medium-contrast
Space: generous (5rem section, 2.5rem gap)
Radius: sharp (3.2px uniform)
Motion: expressive/css — entrance:fadeIn,blockFadeIn,blockFadeInLeft hover:transform-scale,opacity-fade timing:0.7s-ease-in-out,0.25s-ease-out | hero:FadeIn products:fadeInUp cta:bounceIn
Density: spacious | Images: natural-photography
═══════════════════════
```

---

## Content Direction

**Tone:** Heritage-modern, confident, quality-focused with Swiss precision. Emphasizes tradition ("260 Jahre Erfahrung") while maintaining contemporary approachability. German-language primary with professional, established voice.

**Hero copy pattern:** Historical credibility statement + value proposition. Lead with heritage and experience metrics, follow with emotional benefit. Format: "[X] Jahre [craft descriptor] in [emotional benefit]"

**CTA language:** Direct German imperatives. "Mehr anzeigen" (Show more) as primary discovery action. "Schließen" for dismissals. Use action-first verbs without fluff. Keep CTAs functional and clear over clever.

---

## Photography / Visual Direction

- Product photography: Clean, well-lit shots on neutral backgrounds emphasizing packaging design
- Lifestyle imagery: Warm, inviting coffee/tea preparation moments with natural lighting
- Ingredient close-ups: Rich texture shots of beans, leaves, and natural ingredients (almond, banana, cucumber, melon)
- Color grading: Warm amber and brown tones with high contrast to match the #c09a5d accent
- Composition: Centered products with generous whitespace, minimal props
- Style: Premium editorial meets approachable Swiss craft aesthetic

---

## Known Pitfalls

- High animation intensity (85 animated elements, 115 transitions) can impact performance — prioritize critical path rendering and defer non-essential animations
- Multiple custom icon fonts and swiper implementations may bloat bundle size — consolidate or use SVG sprites
- Extensive CSS keyframe library (200+ animations defined) suggests overuse — audit and remove unused animations
- German-language content requires proper translation workflow and may need language switcher prominence
- Golden accent color (#c09a5d) has low contrast on white backgrounds — ensure WCAG AA compliance for text usage
- Full-bleed hero with overlay needs fallback for CLS if using lazy-loaded images
- Mega footer structure can become unwieldy on mobile — test collapse patterns thoroughly

---

## Reference Sites

https://shop.turmkaffee.ch/

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2025-01-XX | Initial preset creation | Turmkaffee analysis |
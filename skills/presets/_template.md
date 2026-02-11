# Preset: [Industry Name]

Industries: [list of specific business types this covers]

---

## Default Section Sequence

```
1. [ARCHETYPE]      | [variant]
2. [ARCHETYPE]      | [variant]
...
```

**Optional sections (add based on brief):**
- [ARCHETYPE] (if [condition]) → insert [position]

---

## Style Configuration

```yaml
color_temperature: 
palette:
  bg_primary: 
  bg_secondary: 
  bg_accent: 
  text_primary: 
  text_heading: 
  text_muted: 
  accent: 
  accent_hover: 
  accent_secondary:            # optional — second brand color
  accent_tertiary:             # optional — third brand color
  border: 

section_accents:               # optional — per-section color overrides
  # section_class: tailwind-color

typography:
  pairing: 
  heading_font: 
  heading_weight: 
  body_font: 
  body_weight: 
  scale_ratio: 
  weight_distribution: 

whitespace: 
section_padding: 
internal_gap: 

border_radius: 
buttons: 
cards: 
inputs: 

animation_engine:           # framer-motion or gsap
animation_intensity:        # none, subtle, moderate, expressive
entrance:
hover:
timing:
smooth_scroll:              # false (native scroll — Lenis removed)
section_overrides:          # hero:character-reveal stats:count-up map:marker-pulse

visual_density: 
image_treatment: 
```

---

## Compact Style Header

```
═══ STYLE CONTEXT ═══
Palette: 
Type: 
Space: 
Radius: 
Motion: [intensity]/[engine] — entrance:[preset] hover:[preset] timing:[values] | [section-overrides]
Density: [option] | Images: [treatment]
═══════════════════════
```

---

## Content Direction

**Tone:** 
**Hero copy pattern:** 
**CTA language:** 

---

## Photography / Visual Direction

- 

---

## Known Pitfalls

- 

---

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|

# Style System Schema

Every website's visual identity can be described through a finite set of
configurable dimensions. This schema defines those dimensions, their options,
and the Tailwind CSS mappings for each.

When generating a site, the style configuration is expressed as a compact
style header that gets prepended to every section generation prompt.

---

## Dimensions

### 1. Color Temperature

The emotional tone set by the color palette. Pick a temperature, then derive
the specific palette from it.

| Option | Description | Typical Palette |
|--------|-------------|-----------------|
| `warm` | Inviting, human, approachable | Ambers, terracottas, creams, golden yellows |
| `cool` | Professional, tech, trustworthy | Blues, slates, whites, steel grays |
| `neutral` | Sophisticated, versatile | True grays, blacks, whites, minimal accent |
| `vibrant` | Energetic, bold, youthful | Saturated primaries, bold contrasts, bright accents |
| `earth` | Natural, organic, artisanal | Greens, browns, clay, sage, olive, cream |
| `dark` | Premium, dramatic, modern | Dark backgrounds, light text, neon or metallic accents |
| `pastel` | Soft, friendly, gentle | Muted pastels, light backgrounds, subtle contrasts |

**Token structure for any temperature:**
```
--color-bg-primary:          Main background
--color-bg-secondary:        Alternate section background
--color-bg-accent:           Highlighted areas
--color-text-primary:        Body text
--color-text-heading:        Heading text
--color-text-muted:          Secondary/caption text
--color-accent:              CTA buttons, links, highlights
--color-accent-hover:        Hover state of accent
--color-accent-secondary:    Optional second brand color
--color-accent-tertiary:     Optional third brand color
--color-border:              Subtle borders and dividers
```

#### Multi-Accent Systems

When a site uses distinct accent colors per section or product category,
the preset defines secondary/tertiary accents and optional `section_accents`.

```
section_accents:
  scroll: green-500        # Scroll tool section uses green accent
  svg: purple-500          # SVG tool section uses purple accent
  text: pink-500           # Text tool section uses pink accent
```

Section accents are applied via the section generation prompt, not `globals.css`.
The compact style header includes an `Accents:` line when multi-accent is detected:

```
Palette: dark-neutral (black/stone-950/amber-50/orange-500)
  Accents: scroll:green-500 svg:purple-500 text:pink-500
```

**Tailwind mapping example (warm):**
```
bg-primary:    bg-amber-50 / bg-cream-50
bg-secondary:  bg-white / bg-stone-50
text-primary:  text-stone-900
text-heading:  text-stone-950
text-muted:    text-stone-500
accent:        bg-amber-600 text-white
accent-hover:  bg-amber-700
border:        border-stone-200
```

### 2. Typography

Two sub-dimensions: the pairing archetype and the scale ratio.

**Pairing archetypes:**

| Option | Heading Font Style | Body Font Style | Feeling |
|--------|-------------------|-----------------|---------|
| `serif-sans` | Serif (Playfair, Lora, DM Serif) | Sans (Inter, DM Sans, Outfit) | Editorial, premium, traditional |
| `geometric-sans` | Geometric sans (Sora, Space Grotesk, Urbanist) | Same family or similar | Modern, tech, clean |
| `mono-sans` | Monospace (JetBrains Mono, IBM Plex Mono) | Sans serif | Technical, developer, data |
| `display-clean` | Display (Clash Display, Cabinet Grotesk) | Clean sans | Creative, bold, agency |
| `humanist` | Humanist sans (Source Sans, Open Sans) | Same family | Friendly, accessible, corporate |
| `editorial` | High-contrast serif (Cormorant, Bodoni Moda) | Light sans | Luxury, fashion, magazine |

**Scale ratios:**

| Ratio | Name | Feel | h1 (base 16px) |
|-------|------|------|-----------------|
| 1.200 | Minor Third | Compact, technical | 28px |
| 1.250 | Major Third | Balanced, versatile | 31px |
| 1.333 | Perfect Fourth | Comfortable, readable | 37px |
| 1.414 | Augmented Fourth | Spacious, editorial | 40px |
| 1.500 | Perfect Fifth | Dramatic, statement | 54px |
| 1.618 | Golden Ratio | Grand, heroic | 67px |

**Weight distribution:**
- `heavy-light`: Bold headings (700-900), light body (300-400). Modern feel.
- `medium-regular`: Medium headings (500-600), regular body (400). Corporate feel.
- `uniform`: Same weight throughout (400-500). Minimal feel.

### 3. Whitespace

The breathing room between and within sections.

| Option | Section Padding | Internal Spacing | Feel |
|--------|----------------|-------------------|------|
| `tight` | py-12 to py-16 | gap-4 to gap-6 | Dense, app-like, data-rich |
| `moderate` | py-16 to py-20 | gap-6 to gap-8 | Balanced, professional |
| `generous` | py-24 to py-32 | gap-8 to gap-12 | Premium, editorial, breathing room |

### 4. Border Radius

One of the strongest visual identity signals. Must be consistent across ALL elements.

| Option | Value | Buttons | Cards | Inputs | Feel |
|--------|-------|---------|-------|--------|------|
| `sharp` | 0-2px | rounded-none/rounded-sm | rounded-sm | rounded-sm | Serious, editorial, brutalist |
| `medium` | 8-12px | rounded-lg | rounded-xl | rounded-lg | Modern SaaS, balanced |
| `full` | 16-24px | rounded-2xl | rounded-3xl | rounded-xl | Friendly, consumer, soft |
| `pill` | 9999px (buttons) | rounded-full | rounded-2xl | rounded-full | Playful, modern, app-like |

### 5. Animation Intensity

How much motion the site uses. More is not always better.

| Option | Scroll Effects | Hover States | Page Load | Micro-interactions |
|--------|---------------|--------------|-----------|-------------------|
| `none` | No animation | Subtle color change only | Instant | None |
| `subtle` | Fade-up on enter | Slight lift/shadow | Gentle fade-in | Minimal |
| `moderate` | Staggered reveals, parallax | Scale + shadow + color | Orchestrated entrance | Button feedback, toggles |
| `expressive` | Complex scroll sequences | Morphing, trails | Full choreography | Particle effects, cursors |

#### Animation Engine

Choose which animation library powers the site. This is a preset-level decision.

| Engine | Dependencies | Best For | Scroll Awareness |
|--------|-------------|----------|-----------------|
| `framer-motion` | `framer-motion` | Simple sites, quick builds, subtle/moderate intensity | `whileInView` (basic) |
| `gsap` | `gsap` | Advanced sites, expressive intensity, scroll-driven choreography | `ScrollTrigger` (full control) |

**Rule of thumb:** Use `framer-motion` for `subtle` intensity. Use `gsap` for `moderate` or `expressive`.

#### Framer Motion Defaults (engine: framer-motion)

```
subtle:
  initial: { opacity: 0, y: 20 }
  animate: { opacity: 1, y: 0 }
  transition: { duration: 0.5, ease: "easeOut" }

moderate:
  initial: { opacity: 0, y: 30 }
  animate: { opacity: 1, y: 0 }
  transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] }
  stagger: 0.1

expressive:
  initial: { opacity: 0, y: 40, scale: 0.95 }
  animate: { opacity: 1, y: 0, scale: 1 }
  transition: { duration: 0.8, ease: [0.22, 1, 0.36, 1] }
  stagger: 0.15
  parallax: true
```

#### GSAP Defaults (engine: gsap)

Reference `skills/animation-patterns.md` for full code snippets.

```
subtle:
  patterns: fade-up-single
  scroll-trigger: start "top 85%", once: true
  hover: CSS transitions only
  extras: none

moderate:
  patterns: fade-up-stagger, word-reveal, count-up, bounce-loop
  scroll-trigger: start "top 80%", once: true
  hover: lift + shadow (CSS) or icon-glow (GSAP)
  extras: none

expressive:
  patterns: all of moderate + character-reveal, marker-pulse,
            staggered-timeline, cursor-trail
  scroll-trigger: start "top 75%", once: true
  hover: icon-glow, morphing
  extras: cursor-trail component
```

#### Section-Specific Pattern Overrides

When using GSAP, specific section archetypes get specialized patterns
(instead of the generic fade-up). See `skills/animation-patterns.md` for
the Pattern-to-Archetype Map. Key overrides:

- **HERO**: `character-reveal` or `word-reveal` + `staggered-timeline`
- **STATS**: `count-up` per metric
- **MAP/TRIALS**: `marker-pulse` on SVG points
- **CTA**: `staggered-timeline` for heading → button sequence

#### GSAP Boilerplate (canonical React pattern)

```tsx
"use client";
import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

export default function SectionName() {
  const sectionRef = useRef<HTMLElement>(null);
  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);
    const ctx = gsap.context(() => {
      // animations scoped to sectionRef
    }, sectionRef);
    return () => ctx.revert();
  }, []);
  return <section ref={sectionRef}>...</section>;
}
```

### 6. Visual Density

How much content per viewport height.

| Option | Grid Columns | Card Size | Section Height | Feel |
|--------|-------------|-----------|----------------|------|
| `high` | 3-4 columns | Compact | Shorter sections | Dashboard, marketplace, data |
| `medium` | 2-3 columns | Standard | Standard sections | Balanced, most sites |
| `low` | 1-2 columns | Large | Tall sections | Portfolio, luxury, editorial |

### 7. Image Treatment

How imagery is presented across the site.

| Option | Description | CSS/Tailwind | When to Use |
|--------|-------------|-------------|-------------|
| `reference` | Actual images from source website | backgroundImage with URL | When image manifest exists |
| `full-bleed` | Edge-to-edge images, no container | w-full, no rounded corners | Hero, CTA backgrounds |
| `contained` | Images within containers with radius | rounded-xl, max-w-*, shadow | Product cards, about sections |
| `duotone` | Filtered to two-tone color treatment | mix-blend-mode, filters | Brand-heavy designs |
| `illustrated` | Vector illustrations, icons, no photos | SVG-based | Tech, SaaS products |
| `gradient` | Abstract gradient backgrounds, no photos | bg-gradient-to-* | Fallback when no images |
| `text-only` | No imagery, typography-driven | — | Minimal/editorial sites |

**Image Rendering Standard:**
- PRIMARY: CSS `backgroundImage` on divs with `role="img"` + `aria-label`
- SECONDARY: `<img>` tags ONLY for logos, icons, or content images
- FALLBACK: Gradients when no reference images available
- NEVER: Generic placeholder services (`/api/placeholder`, `placehold.co`)
- See `skills/components/image-patterns.md` for standard rendering patterns

---

## Compact Style Header Format

This is the format prepended to every section generation prompt. It must be
concise enough to not consume significant context but complete enough to
ensure cross-section consistency.

```
═══ STYLE CONTEXT ═══
Palette: [temperature] — bg:[token] text:[token] accent:[token] border:[token]
Type: [pairing] — heading:[font,weight] body:[font,weight] scale:[ratio]
Space: [whitespace] — sections:[padding] internal:[gap]
Radius: [option] — buttons:[value] cards:[value] inputs:[value]
Motion: [intensity]/[engine] — entrance:[preset] hover:[preset] timing:[values] | [section-overrides]
Density: [option] | Images: [treatment]
═══════════════════════
```

**Example (artisan coffee roaster):**
```
═══ STYLE CONTEXT ═══
Palette: warm-earth — bg:stone-50/white text:stone-900 accent:amber-700 border:stone-200
Type: serif-sans — heading:DM Serif Display,700 body:DM Sans,400 scale:1.333
Space: generous — sections:py-24 internal:gap-8
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: moderate/gsap — entrance:fade-up-stagger hover:lift-shadow timing:0.6s ease-out | hero:word-reveal stats:count-up
Density: low | Images: full-bleed
═══════════════════════
```

---

## Combining Dimensions: Quick Reference

Not all combinations work equally well. These are tested pairings:

| Combination | Works Because |
|-------------|---------------|
| warm + serif-sans + generous + medium radius | Classic editorial premium feel |
| cool + geometric-sans + moderate + medium radius | Standard SaaS, trustworthy |
| neutral + display-clean + generous + sharp radius | Agency/portfolio, bold |
| earth + serif-sans + generous + full radius | Artisan/organic, approachable |
| dark + mono-sans + tight + sharp radius | Developer tools, technical |
| vibrant + geometric-sans + moderate + pill radius | Consumer app, energetic |
| pastel + humanist + generous + full radius | Health/wellness, gentle |

---

## Maintenance Log

| Date | Change | Source |
|------|--------|--------|
| 2026-02-08 | Initial schema created | — |
| 2026-02-08 | Added GSAP animation engine, section-specific overrides, boilerplate pattern | farm-minerals-promo rebuild |
| 2026-02-09 | Added `reference` image treatment option, image rendering standard | bluebird-coffee-roastery planning |

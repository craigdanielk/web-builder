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
- `light-display`: Large headings at 300-400 with tight tracking (-0.02em) and
  tight leading (1.05-1.10); emphasis carried by *size and colour*, not weight.
  UI labels/eyebrows stay 500-600. Premium fintech/infra feel.
  Source: `stripe-benchmark.json → type_system` (`weights_used: ["300","400"]`,
  "headlines are LIGHT-weight, large, tight leading — not bold").
  Implemented at Xago as a global `h1, h2 { font-weight: 400; letter-spacing:
  -0.02em; line-height: 1.08 }` in `globals.css`.

**Two-tone headline** (optional sub-dimension, pairs with `light-display`):

The headline splits into a lead clause in ink and a trailing clause carrying a
brand gradient (`background-clip: text`). Structural, not brand-specific — the
gradient stops are `accent → accent_2 → accent_3` whatever those resolve to.

```
typography:
  headline_treatment: two-tone        # or: solid
  headline_gradient_angle: 100deg     # Xago globals.css `.text-accent-gradient`
```
Source: `stripe-benchmark.json → type_system` ("Two-tone: first clause solid
ink, trailing clause coloured by the hero gradient"); Xago implementation
`site/src/app/globals.css @utility text-accent-gradient` (stops at 0%/55%/100%).

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
| `squarish` | 4-8px | rounded-md (6px) | rounded-lg (8px) | rounded-md | Infrastructure, fintech, "we handle money" |
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

### 8. Elevation

How surfaces lift off the page. Previously implicit (sections just said
`shadow-lg`); made explicit because layering is the single strongest
"expensive vs cheap" tell and it is fully token-expressible.

| Option | Layers | Shape | Feel |
|--------|--------|-------|------|
| `flat` | 0 | borders only, no shadow | Editorial, brutalist, print |
| `hairline` | 1 | very tight, very low alpha (`0 2px 12px rgba(ink,0.04)`) | Restrained, institutional |
| `two-layer-soft` | 2 | one wide+far offset at low alpha, one tight+near at lower alpha | Premium; the Stripe signature |
| `hard` | 1 | zero blur, offset (`4px 4px 0`) | Neo-brutalist, playful |

**`two-layer-soft` is the structural rule, not a colour:**

```
shadow_lg  = 0 <near-y> <near-blur> <near-spread> rgba(SHADOW_INK, α₁)
           , 0 <tight-y> <tight-blur> <tight-spread> rgba(SHADOW_INK, α₂)
```
with the invariants: two layers max; the far layer is ~3-4× the blur of the
near layer; α₁ > α₂; both use a *negative spread* so the shadow stays under
the card; `SHADOW_INK` is a tint of the palette's darkest brand colour, never
pure black.

| Ramp step | Far layer | Near layer |
|-----------|-----------|------------|
| `shadow_lg` (resting card) | `0 8px 24px -6px rgba(INK,0.10)` | `0 2px 8px -2px rgba(INK,0.08)` |
| `shadow_2xl` (hover / featured) | `0 30px 60px -12px rgba(INK,0.18)` | `0 8px 24px -6px rgba(INK,0.10)` |

Source: Stripe's measured pair, `stripe-benchmark.json → shadow_system`:
`signature_soft = 0 30px 60px -50px rgba(0,0,0,0.1), 0 30px 60px -10px
rgba(50,50,93,0.25)` and `subtle = 0 16px 32px 0 rgba(50,50,93,0.12)`;
`max_layers: 2`. Note Stripe tints with `rgb(50,50,93)` — a blue-violet ink,
not black. The ramp above is the *Xago-shipped* recast
(`theme.config.json → tokens.shadow`, `SHADOW_INK = rgb(60,40,20)` warm) which
is what survived a real build; the geometry (offsets, blur ratio, negative
spread, 2 layers) is the transferable part, the ink tint is per-tenant.

**Gap:** Stripe's dark-surface elevation was not captured. Xago invented an
inset-highlight recipe for its dark app shell
(`--shadow-card: 0 1px 0 rgba(255,255,255,0.03) inset, 0 12px 32px -16px
rgba(0,0,0,0.7)`, `globals.css`). Recorded as Xago-origin, not benchmark-derived.

### 9. Surface (card treatment)

The card is the atom of a fintech page. Three properties travel together.

| Option | Radius | Border | Shadow | Fill |
|--------|--------|--------|--------|------|
| `bordered-flat` | squarish (6-8px) | 1px, pale, ~5% of ink | none | surface |
| `bordered-lifted` | squarish (6-8px) | 1px, pale, ~5% of ink | `two-layer-soft` | pure white / lightest surface |
| `shadow-only` | medium | none | `two-layer-soft` | white |
| `glass` | medium | 1px white/10 | `hairline` | translucent |

```
surface:
  card: bordered-lifted
  card_grid: uniform-equal-height    # or: masonry, staggered
  card_columns: 3                    # dense 2-3 col, not 1-2
```

`bordered-lifted` + `uniform-equal-height` + 3 columns is the benchmark's
information-card system. Source: `stripe-benchmark.json → card_system`
("Squarish, uniform info-cards. Small radii (4-8px), 1px pale borders (rgb
229,237,245), NOT rounded pills"; `xago_recast.grid: "uniform equal-height,
2-3 col, dense"`). Xago ships it as the `card-x` utility in `globals.css`:
`border-radius: var(--radius-2xl)` (0.5rem = 8px) + `1px solid
var(--color-xago-border)` + `var(--shadow-lg)` + white fill.

The border colour is **derived, not authored**: it is the palette's neutral
pulled to ~92-93% lightness in the same hue family as the background, so a warm
background gets a warm border (`#ece9e4`) and a cool one gets a cool border
(`#e2e8f0`). Never a grey borrowed from another palette.

### 10. Dark Section System

A full-bleed dark band used to break a light page and carry depth. Structural
kit; every value below is a relationship, not a colour.

| Element | Rule |
|---------|------|
| Ground | The palette's darkest brand colour at full bleed — *brand navy/ink, never `#000`* |
| Accent | Exactly ONE bright accent inside the band (the brand accent) |
| Gutter guides | Faint dotted vertical rules at container gutters, `border-dotted` at 6-8% white |
| Section boundary | Diagonal `clip-path` wedge resolving to the adjacent light section's background |
| Text | Primary at ~96% lightness, muted at ~80%, on the dark ground |

```
dark_section:
  ground: brand_dark               # palette key, not a hex
  guides: dotted-gutter            # dotted-gutter | none
  cut: diagonal                    # diagonal | straight
  cut_depth: 6vw                   # min 40px
  accent_count: 1
```

Source: `stripe-benchmark.json → dark_section_system` (dotted vertical column
guides + diagonal clip-path boundary + single bright accent). Shipped at Xago
as `src/components/layout/DarkSection.tsx` — a reusable wrapper with `guides`,
`topCut`/`bottomCut`, `cutColor`, `navy` props; the 3-column dotted grid is
aligned to `max-w-6xl px-6 lg:px-8` and drawn at `white/[0.07]`.

### 11. Gradient Treatment

| Option | Description | When |
|--------|-------------|------|
| `none` | Flat fills only | Editorial, brutalist |
| `subtle-wash` | Single low-contrast linear wash on a section bg | Most sites |
| `mesh-ribbon` | Animated multi-stop mesh/ribbon sweeping the hero; reduced-motion → static | Premium fintech hero |

```
gradient:
  hero: mesh-ribbon
  stops: accent, accent_2, accent_3, accent_alt, bg   # palette keys, in order
  motion: slow-drift                                   # slow-drift | static
  reduced_motion: static                               # REQUIRED
```

The structural rule is **4-5 stops walking one hue arc, ending in the page
background**, with one off-hue stop for tension. Stripe's arc is
blue→purple→pink→orange→yellow (`linear-gradient(90deg, rgb(114,50,241) 3%,
rgb(251,118,250) 50%, rgb(255,207,94))`, plus a
`radial-gradient(103% 102% at 50% 102%, …)`). Xago's is
`accent #f47643 → accent_2 #ff9d6b → accent_3 #ffcf94 → violet #7c5cfc (the
off-hue tension stop) → warm-white`. Same *shape*, different hue arc.
Source: `stripe-benchmark.json → hero_gradient_ribbon`; Xago components
`animations/mesh-gradient.tsx` + `animations/diagonal-ribbon.tsx`.

**Reduced-motion static fallback is mandatory**, per the benchmark's own
`technique` note.

### 12. CTA System

| Property | Rule | Source |
|----------|------|--------|
| Radius | Tracks `border_radius` but one step tighter than cards — 4-6px under `squarish` | benchmark `cta_buttons.radius_px: [4,5,6]` |
| Size | Small. Compact padding (`px-6 py-3`), label at 13-14px | benchmark: "SMALL squarish buttons… compact padding" |
| Label weight | 500-600 — heavier than the headline. Deliberate inversion under `light-display` | Xago `01-hero.tsx`: `text-sm font-semibold` |
| Primary | Solid accent fill, label = contrast-safe `on_accent` | benchmark `cta_buttons` |
| Secondary | Transparent/lightest fill + 1px border, never a second solid colour | benchmark: "secondary white-bordered" |
| Affordance | Trailing chevron/arrow glyph on the primary | benchmark `cta_buttons` |
| Hover | `scale 1.03` + tinted accent shadow; tap `scale 0.98`, 0.2s | Xago `01-hero.tsx` (implementation choice, not benchmarked) |

### 13. Logo Bar

| Property | Rule |
|----------|------|
| Treatment | **Full-colour logos**, not greyscaled |
| Layout | Single row; marquee when > 5 logos, static centred row otherwise |
| Frame | Fixed-size flex cells (`w-40 h-10`), object-contain, so unequal logo aspect ratios still align |
| Eyebrow | Small uppercase muted label above (`text-sm uppercase tracking-wider`) |
| Band | Light band with `border-y` hairline, tighter vertical padding than a content section (`py-10 md:py-14`) |

Source: `stripe-benchmark.json → logo_bar` establishes full-colour only. The
layout/frame/eyebrow rules are from the Xago implementation
(`sections/homepage/02-logo_bar.tsx`) — **not benchmarked**, recorded as
implementation-derived.

---

## Structural Spine vs. Brand Inputs

A preset carries two kinds of value and they must not be confused.

**Structural (shared, industry-level — belongs in a preset):** type scale ratio
and weight *distribution*, radius *step relationships*, shadow *geometry* and
layer count, spacing rhythm, grid columns, card anatomy, gradient stop *count
and ordering*, CTA size/weight *inversion*, section rhythm.

**Brand (per-tenant — never in a shared preset):** accent hex values, font
families, logo, imagery, the shadow *ink tint*, the dark-section *ground* hex,
copy and tone.

The mechanism already exists and should be used rather than replaced:

1. A shared industry preset declares palette/typography keys with brand-neutral
   role names and placeholder values.
2. `scripts/seed_supabase.py:parse_yaml_style_block()` lifts the `## Style
   Configuration` YAML into `industry_styles.style_config`.
3. `orchestrate.py` merges `tenant_context.palette` **over** the industry
   palette (tenant capture wins) before any section is generated.
4. Every key under `style_config.palette` and `style_config.typography` becomes
   a `{{brand.<key>}}` token available to Supabase/local templates.

So: **a shared preset holds structure and role names; a tenant preset (or
tenant phase0 capture) holds hexes and fonts.** A hex in a shared industry
preset is a bug, not a default.

Two live constraints on how these blocks may be written:

- `parse_yaml_style_block()` is a hand-rolled parser supporting **exactly two
  levels** (top-level scalar, or one nested mapping) and **no lists**. All new
  dimensions above are therefore expressed as flat scalars inside a single
  nested block. Comma-joined strings stand in for lists.
- **Colour values in the YAML block must be written `rgb()` / `rgba()`, never
  hex.** `parse_yaml_style_block()` strips everything from the first `#` onward
  as an inline comment, so `accent: "#004E89"` is stored as `"`. Verified by
  running the parser against a hex-valued preset. This is why the existing 35
  presets use Tailwind class names — none of them ever needed an exact brand
  hex. `rgb()` survives the parser, is valid CSS, is valid inside Tailwind
  arbitrary values (`bg-[rgb(0,78,137)]`), and is the form the extraction
  pipeline already captures. Hexes remain fine in prose, provenance tables and
  the Compact Style Header (a free-text field).
- Only `palette.*` and `typography.*` are swept into `{{brand.*}}` tokens
  (`orchestrate.py` ~line 2790). Keys under new blocks such as `elevation:` or
  `surface:` reach the LLM prompt path but **not** the template-substitution
  path. Elevation/surface values that templates must consume are therefore
  mirrored into `palette` (e.g. `shadow_ink`, `border`) until that sweep is
  widened — which is the slot-contract agent's call, not this schema's.

---

## What Tokens Cannot Carry

The benchmark is a *computed-style* capture. It records what every element
looked like; it records nothing about how the page was composed. Dimensions
1-13 above are the complete set of what is token-expressible. Everything below
is real, load-bearing quality that **must live in the section templates** —
no preset value will ever produce it, and no consistency review will ever
catch its absence.

**Owned by templates, not tokens:**

| Concern | What it means |
|---------|---------------|
| Section rhythm | The light/dark/light alternation across a page; where the hairline band falls; how many dark bands and where. A preset can state a rule (as `fintech-crypto.md` does) but only the assembled page can honour it. |
| Vertical hierarchy | Which section gets the 56px headline and which gets 32px. The scale exists in tokens; its *assignment down the page* does not. |
| Whitespace at page scale | `section_padding` is per-section. The felt quality comes from padding *varying* — a hero at `pt-48 pb-40`, a logo band at `py-10`, a content section at `py-28`. Uniform padding across every section reads flat no matter how generous the value. Xago's shipped homepage uses eight distinct padding values across nine sections. |
| Asymmetry | Stripe's hero is a 7/5 split, not 6/6. Grid column *ratios* per section are compositional. |
| Content density per section | How many cards, how many words in a subhead, whether a section carries one idea or four. |
| Where the signature move lands | The mesh gradient belongs in the hero and nowhere else; the globe belongs in one section. Tokens say *what* the effect is, never *where it earns its place*. |
| Eyebrow / heading / subhead triads | The recurring three-part section header is a template pattern. |
| Trust-signal placement | That regulatory standing appears above the fold is a composition decision. |
| Copy | Entirely outside this schema. |

**Also not captured by the benchmark** (gaps in the source, not in the schema):
dark-surface elevation, focus-visible treatment, motion timing/easing (Stripe's
animation was observed as "animated" with no measured durations), responsive
breakpoint behaviour, and any state other than resting (hover, active,
disabled, error). Every motion and state value in the fintech spine is
therefore **Xago implementation-derived, not benchmark-derived**, and is
labelled as such at the point of use.

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
Elevation: [option] — lg:[shadow] 2xl:[shadow]          ← optional, omit when `flat`
Surface: [card] — grid:[card_grid] cols:[card_columns]  ← optional
Dark: [ground] — guides:[guides] cut:[cut]              ← optional, omit when no dark band
Gradient: [hero] — stops:[stops] motion:[motion]        ← optional, omit when `none`
CTA: radius:[value] size:[padding] weight:[weight] affordance:[glyph]
═══════════════════════
```

The five optional lines are emitted only when the preset declares the
corresponding block. A preset that says nothing about elevation, surfaces, dark
sections or gradients produces the exact seven-line header as before — this is
a superset, so all 35 existing presets keep rendering an unchanged header.

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
| 2026-08-10 | Fintech token spine. Dimensions 8-13 added (Elevation, Surface, Dark Section, Gradient, CTA, Logo Bar). `light-display` weight distribution + two-tone headline. `squarish` radius option. "Structural Spine vs Brand Inputs" section. Compact header gains 5 optional lines (backward compatible). | `tenants/xago/out/stripe-benchmark.json` (Stripe computed-style capture, 2026-07-23) + shipped Xago implementation (`tenants/xago/site`, Lighthouse 89-98) |

# Pinned Horizontal Scroll & Showcase Card Differentiation

**Status:** Planning
**Created:** 2026-02-11
**Depends on:** GSAP Ecosystem Integration (v1.0.0), Animation Component Library (v0.6.0+)
**Scope:** New section archetype, GSAP pinned scroll component, showcase card variants, detection integration
**Target version:** v1.1.0
**Evidence:** gsap-v10 build review, gsap.com reference (pinned scroll hero), Apple product pages, creative agency portfolios

---

## Problem Statement

Two critical visual patterns are missing from the system — both are signature techniques of premium websites:

### 1. Pinned Horizontal Scroll ("Scroll-Hijack")

The pattern where a section **pins** in the viewport and **vertical scroll input translates to horizontal movement**. Content, animated elements, and interactive scenes scroll horizontally while the section stays fixed. Only unpins after all horizontal content is exhausted.

**Where it's used:**
- gsap.com homepage (animated shapes + colored blocks section)
- Apple product pages (iPhone, MacBook hero sections)
- Creative agency portfolios (case study showcases)
- Award-winning sites on Awwwards, FWA, CSS Design Awards

**What we have:**
- `scroll/horizontal-scroll.tsx` — Framer Motion version using `sticky top-0` + `h-[300vh]` + `useScroll`/`useTransform`. Simple card carousel, not a rich animated scene.
- `scroll/pin-and-reveal.tsx` — Misclassified as UI, not actually pin+scroll.
- `horizontal_scroll` exists as a motion intent in the taxonomy but has no section archetype.

**What's missing:**
- A GSAP `ScrollTrigger({ pin: true, scrub: true })` component — the proper implementation
- A section archetype in `section-taxonomy.md` so the scaffold can recommend it
- Detection of this pattern on reference sites (pinned sections with horizontal translate)
- The ability to compose rich animated scenes inside the pinned container

### 2. Showcase Card Differentiation

Product/showcase cards that should each demonstrate a **different** animation technique currently all render with identical visual treatment. The gsap-v10 build shows 8 brand cards (Nike, Apple, Tesla, etc.) each labeled with a different animation style ("3D Product Rotation", "Morph Path Animation") but sharing the same gradient background.

**What's missing:**
- A `demo-cards` variant of PRODUCT-SHOWCASE where each card has a unique micro-animation
- Section prompt instructions to differentiate cards visually
- A mapping from animation label → visual indicator (SVG stroke for DrawSVG, morphing blob for MorphSVG, orbiting dot for MotionPath, etc.)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│  TRACK A: Pinned Horizontal Scroll                        │
│  A1. GSAP component (pin + scrub + horizontal translate)  │
│  A2. Section archetype + variants in taxonomy             │
│  A3. Detection in animation-detector.js                   │
│  A4. Scaffold integration (recommend when detected)       │
│  A5. Rich scene composition (nested animations)           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  TRACK B: Showcase Card Differentiation                   │
│  B1. New PRODUCT-SHOWCASE variant: demo-cards             │
│  B2. Micro-animation library (6-8 card-level effects)     │
│  B3. Section prompt enhancement (per-card visual rules)   │
│  B4. Animation-label → visual-indicator mapping           │
└──────────────────────────────────────────────────────────┘
```

**Tracks A and B are independent** — can be implemented in parallel.

---

## Track A: Pinned Horizontal Scroll

### A1. Create GSAP Pinned Horizontal Scroll Component

**File:** `skills/animation-components/scroll/gsap-pinned-horizontal.tsx` (new)

A production-ready GSAP component implementing the canonical pinned scroll pattern:

```tsx
"use client";
import { useRef, useEffect, ReactNode } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

interface PinnedHorizontalScrollProps {
  children: ReactNode;
  className?: string;
  /** How many viewport widths the scroll extends (default: auto from content) */
  scrollLength?: number;
  /** Scrub smoothness — 0 = instant, 1 = smooth, 2+ = very smooth */
  scrub?: number | boolean;
  /** Easing for the horizontal translate */
  ease?: string;
  /** Enable snap to panel boundaries */
  snap?: boolean;
  /** Offset from top when pinned (for fixed navs) */
  pinSpacing?: boolean;
}

export default function PinnedHorizontalScroll({
  children,
  className = "",
  scrub = 1,
  ease = "none",
  snap = false,
  pinSpacing = true,
}: PinnedHorizontalScrollProps) {
  const sectionRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sectionRef.current || !containerRef.current) return;
    
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const container = containerRef.current;
    const scrollWidth = container.scrollWidth - window.innerWidth;

    const tween = gsap.to(container, {
      x: -scrollWidth,
      ease,
      scrollTrigger: {
        trigger: sectionRef.current,
        pin: true,
        pinSpacing,
        scrub,
        end: () => `+=${scrollWidth}`,
        invalidateOnRefresh: true,
        ...(snap ? {
          snap: {
            snapTo: 1 / (container.children.length - 1),
            duration: { min: 0.2, max: 0.5 },
            ease: "power1.inOut",
          }
        } : {}),
      },
    });

    return () => {
      tween.scrollTrigger?.kill();
      tween.kill();
    };
  }, [scrub, ease, snap, pinSpacing]);

  return (
    <section ref={sectionRef} className={className}>
      <div className="h-screen flex items-center overflow-hidden">
        <div ref={containerRef} className="flex will-change-transform">
          {children}
        </div>
      </div>
    </section>
  );
}
```

**Key differences from existing `horizontal-scroll.tsx`:**
- Uses GSAP `ScrollTrigger({ pin: true })` instead of Framer Motion `sticky`
- `scrub` for smooth 1:1 scroll coupling (not just progress-mapped transform)
- `snap` option for panel-based snapping
- `invalidateOnRefresh` for responsive recalculation
- Proper cleanup (kills ScrollTrigger instance)
- `will-change-transform` for GPU acceleration

### A2. Add Section Archetype to Taxonomy

**File:** `skills/section-taxonomy.md`

Add new archetype:

```markdown
### PINNED-SCROLL
**Purpose:** Full-viewport section that pins in place while content scrolls horizontally. The signature pattern of premium marketing sites — vertical scroll input translates to horizontal movement with animated elements.
**Variants:**
- `horizontal-panels` — Discrete content panels scrolling horizontally (case studies, features)
- `animated-scene` — Continuous animated landscape with elements entering/exiting (GSAP homepage style)
- `product-journey` — Product images/specs flowing left-to-right with parallax layers (Apple style)
- `timeline-scroll` — Chronological content scrolling horizontally with year/milestone markers

**Animation:** `gsap-pinned-horizontal` component with `ScrollTrigger({ pin: true, scrub: true })`. Inner elements use `gsap.fromTo()` with the same ScrollTrigger for coordinated entrance/exit timing. Can compose with `motionpath-orbit`, `drawsvg-reveal`, and `morphsvg-shape-shift` for rich scenes.
**Structure:** Section wrapper (100vh, relative) → sticky container (100vh, flex, overflow-hidden) → horizontal track (flex, gap, will-change-transform) → panels/scenes
**Notes:** 
- The `h-[300vh]` or equivalent tall wrapper controls how long the pin lasts
- Each panel should be `min-w-screen` or `w-[100vw]` for full-viewport panels
- For `animated-scene`, inner elements need their own ScrollTrigger with `containerAnimation` to animate within the horizontal scroll
- Always include a visual scroll progress indicator (dot trail, progress bar, or panel counter)
- Mobile fallback: convert to vertical stack or swipeable carousel (use gsap.matchMedia)
```

### A3. Detect Pinned Scroll Pattern in Extraction

**File:** `scripts/quality/lib/animation-detector.js`

Add detection logic in the page.evaluate section:

```javascript
// Detect pinned horizontal scroll sections
const pinnedSections = document.querySelectorAll('[style*="position: fixed"], [style*="position: sticky"]');
const pinnedScrollDetected = Array.from(pinnedSections).some(el => {
  const children = el.querySelectorAll('[style*="translateX"], [style*="translate3d"]');
  return children.length > 0;
});
```

Also detect in `gsap-extractor.js` — look for `ScrollTrigger` calls with `pin: true`:

```javascript
// In classifyPluginUsage or separate function
const pinScrollMatches = [...allCode.matchAll(/pin\s*:\s*true[^}]*scrub\s*:/g)];
```

Add to evidence output: `evidence.pinnedScrollDetected = true`

### A4. Scaffold Integration

**File:** `scripts/orchestrate.py` (stage_scaffold prompt)

When `identification.pinnedScrollDetected` is true, add to the scaffold prompt:

```
The reference site uses a PINNED HORIZONTAL SCROLL section — where the section 
pins in the viewport and vertical scroll translates to horizontal content movement.
Include a PINNED-SCROLL section in the scaffold. Choose the variant that best 
matches what was detected:
- animated-scene: floating shapes, color transitions, interactive elements
- horizontal-panels: discrete content cards or case studies
- product-journey: product images with parallax layers
- timeline-scroll: chronological milestones
```

### A5. Rich Scene Composition (Advanced)

**File:** `templates/section-instructions-gsap.md` + `skills/animation-patterns.md`

Add instructions for composing animations **inside** a pinned scroll:

```markdown
## Nested Animations Inside Pinned Scroll

When building a PINNED-SCROLL section with variant `animated-scene`, inner elements 
need their own animations coordinated with the horizontal scroll:

```tsx
// The main horizontal scroll
const scrollTween = gsap.to(track, {
  x: -scrollWidth,
  ease: "none",
  scrollTrigger: { trigger: section, pin: true, scrub: 1 }
});

// Nested element animation WITHIN the horizontal scroll
gsap.fromTo(".floating-shape", 
  { scale: 0, rotation: -180 },
  { scale: 1, rotation: 0, 
    scrollTrigger: {
      trigger: ".floating-shape",
      containerAnimation: scrollTween, // KEY: ties to horizontal scroll
      start: "left center",
      end: "right center",
      scrub: true,
    }
  }
);
```

The `containerAnimation` parameter is CRITICAL — it makes nested ScrollTriggers 
respond to the horizontal scroll position instead of vertical page scroll.
```

**New animation pattern in `animation-patterns.md`:**

```markdown
### `pinned-horizontal-scene`
Pinned section with horizontal scroll and nested animated elements. The signature 
premium website pattern (GSAP homepage, Apple product pages).

**Plugin:** ScrollTrigger (pin + scrub + containerAnimation)
**Section fit:** PINNED-SCROLL (all variants), HERO (product-journey)
```

---

## Track B: Showcase Card Differentiation

### B1. New PRODUCT-SHOWCASE Variant: `demo-cards`

**File:** `skills/section-taxonomy.md`

Add to PRODUCT-SHOWCASE variants:

```markdown
- `demo-cards` — Each card demonstrates a different animation technique with a unique 
  visual indicator. Cards share layout but differ in: gradient direction/colors, 
  micro-animation (SVG stroke, morphing blob, orbiting dot, flip transition), and 
  hover effect. Used when showcasing animation capabilities or diverse product features.
```

### B2. Micro-Animation Card Effects Library

Create 6 small, card-scoped animation effects that can be assigned per-card:

| Effect | Visual | Maps to |
|--------|--------|---------|
| `card-stroke-draw` | SVG path drawing around card border | DrawSVG |
| `card-morph-blob` | Background blob morphing shapes | MorphSVG |
| `card-orbit-dot` | Small dot orbiting the card | MotionPath |
| `card-flip-preview` | Card content flips to reveal alt state | Flip |
| `card-text-scramble` | Title text scrambles on hover | ScrambleText |
| `card-3d-rotate` | Subtle 3D perspective rotation on hover | GSAP + transforms |
| `card-gradient-shift` | Unique gradient that shifts on hover | CSS + GSAP |
| `card-particle-burst` | Particles burst from card on hover | Canvas / GSAP |

These don't need to be full components — they can be **inline patterns** documented in `animation-patterns.md` and referenced by the section prompt.

### B3. Section Prompt Enhancement

**File:** `templates/section-prompt.md`

When the section archetype is PRODUCT-SHOWCASE with variant `demo-cards`, add to prompt:

```
CRITICAL: Each card in this showcase MUST have a visually DISTINCT treatment:
1. Each card gets a UNIQUE gradient direction and color combination from the palette
2. Each card gets a UNIQUE micro-animation that represents its label/category:
   - "3D Product Rotation" → subtle CSS perspective rotate on hover
   - "Morph Path Animation" → background SVG blob that morphs shape
   - "Motion Path Sequences" → small dot orbiting the card border
   - "Flip Layout Transitions" → card flip animation on hover
   - "DrawSVG Sequences" → SVG stroke drawing around the card on scroll
   - "Text Animations" → title text scrambles/reveals on hover
3. Each card's hover state must be different from other cards
4. Use the detected GSAP plugins for these effects where available

DO NOT give all cards the same gradient, same hover effect, or same layout.
The entire point of this section is showing VARIETY.
```

### B4. Animation-Label → Visual-Indicator Mapping

**File:** `scripts/quality/lib/animation-injector.js`

Add a mapping function that, when generating a PRODUCT-SHOWCASE demo-cards section, assigns specific micro-animations to each card based on detected plugins:

```javascript
const CARD_ANIMATION_MAP = {
  'DrawSVG':     { effect: 'card-stroke-draw', description: 'SVG path draws around card border on scroll' },
  'MorphSVG':    { effect: 'card-morph-blob', description: 'Background blob morphs between shapes' },
  'MotionPath':  { effect: 'card-orbit-dot', description: 'Small element orbits along card border path' },
  'Flip':        { effect: 'card-flip-preview', description: 'Card flips to reveal alternate content on hover' },
  'SplitText':   { effect: 'card-text-scramble', description: 'Title text reveals character by character' },
  'ScrollTrigger': { effect: 'card-3d-rotate', description: 'Perspective rotation responding to scroll' },
  'Draggable':   { effect: 'card-drag-preview', description: 'Card is slightly draggable with inertia snap-back' },
  'CustomEase':  { effect: 'card-gradient-shift', description: 'Custom-eased gradient color shift on hover' },
};
```

This mapping gets injected into the section prompt so Claude knows what effect to apply to each card.

---

## Implementation Order

```
Parallel Track A + B:

Track A (Pinned Horizontal Scroll):
  A1. Create GSAP component              → 1 hour
  A2. Add taxonomy archetype             → 30 min
  A3. Detection in extraction            → 1 hour
  A4. Scaffold integration               → 30 min
  A5. Rich scene composition docs        → 1 hour
                                          ≈ 4 hours

Track B (Showcase Cards):
  B1. New variant in taxonomy            → 15 min
  B2. Card micro-animation patterns      → 1 hour
  B3. Section prompt enhancement         → 30 min
  B4. Animation-label mapping            → 30 min
                                          ≈ 2.5 hours

Post-implementation:
  - Rebuild animation registry           → 2 seconds
  - Test against gsap.com                → 10 min
  - Deploy and verify                    → 5 min
```

Total: ~6-7 hours estimated, reducible to ~30 min with parallel agents.

---

## Test Strategy

### Track A Tests
- Component renders without error in Next.js
- Pin triggers at correct scroll position
- Horizontal translate matches scroll input
- Unpin occurs at end of content
- Mobile fallback (matchMedia reduce) works
- `containerAnimation` nested animations fire correctly
- Detection: feed extraction with `pin: true` + `scrub` → assert `pinnedScrollDetected`

### Track B Tests
- PRODUCT-SHOWCASE demo-cards generates 6+ unique card treatments
- Each card has a different gradient
- Each card has a different hover animation
- Cards match detected plugin labels when available
- Fallback: when no plugins detected, use CSS-only effects

### Integration Test
- Full pipeline against gsap.com with v1.1.0 → verify:
  - PINNED-SCROLL section appears in scaffold
  - Showcase cards have differentiated treatments
  - No truncation (section is complex — monitor token budget)
  - Vercel build succeeds

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Pinned scroll conflicts with Framer Motion entrance animations | Medium | Section breaks | Use GSAP-only for the pinned section, Framer only for non-pinned sections |
| `containerAnimation` requires GSAP 3.12+ | Low | Nested animations fail | Pin to gsap@3.12.5+ in package.json |
| Mobile pinned scroll feels jarring | High | Bad UX on mobile | Always implement `matchMedia` fallback to vertical stack |
| Token budget insufficient for animated-scene variant | High | Truncated section | Set minimum 8192 tokens for PINNED-SCROLL archetype |
| Card micro-animations bloat section size | Medium | Token truncation | Keep each card effect to 5-8 lines max, use CSS where possible |

---

## Success Criteria (v1.1.0)

- [ ] GSAP pinned horizontal scroll component works in Next.js
- [ ] PINNED-SCROLL archetype in taxonomy with 4 variants
- [ ] Pin+scrub pattern detected during URL extraction
- [ ] Scaffold recommends PINNED-SCROLL when detected on reference site
- [ ] Nested `containerAnimation` documented and usable
- [ ] Mobile fallback implemented (vertical stack or swipeable)
- [ ] PRODUCT-SHOWCASE demo-cards variant generates visually unique cards
- [ ] Each card has distinct gradient + micro-animation
- [ ] Card effects map to detected GSAP plugins
- [ ] gsap.com rebuild includes pinned scroll section
- [ ] gsap.com rebuild shows differentiated showcase cards

---

## Maintenance Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-11 | Plan created from gsap-v10 build review | system |

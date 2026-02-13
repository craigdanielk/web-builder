# Animation Patterns Library

Reusable GSAP and Framer Motion animation patterns for the web-builder pipeline.
Each pattern includes the exact React/TypeScript code snippet, when to use it,
and configuration notes. Reference patterns by name in scaffolds and presets.

**Dependencies:** `gsap` (includes ScrollTrigger)

---

## Boilerplate: GSAP in React

Every GSAP-powered section must follow this pattern for proper setup and cleanup:

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
      // all animations scoped to sectionRef
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  return <section ref={sectionRef}>...</section>;
}
```

**Rules:**
- `gsap.registerPlugin(ScrollTrigger)` must be inside `useEffect` (not module-level)
- `gsap.context()` scopes all animations to the section and handles cleanup on unmount
- Return `ctx.revert()` in the cleanup function — this undoes all animations

---

## A. Scroll-Triggered Entrance

> **SSR WARNING**: All entrance animations below should use **Framer Motion `whileInView`**, NOT `gsap.from()`. The GSAP `from()` approach causes invisible elements in Next.js SSR. See `templates/section-instructions-gsap.md` for the correct hybrid pattern. GSAP should only be used for interactive, scroll-linked, continuous, and text-split animations.

### `fade-up-stagger`

Elements slide up and fade in with stagger timing. The workhorse pattern — use for card grids, feature lists, any multi-element layout.

```tsx
gsap.from(".card", {
  y: 40,
  opacity: 0,
  duration: 0.8,
  stagger: 0.12,
  ease: "power3.out",
  scrollTrigger: {
    trigger: sectionRef.current,
    start: "top 80%",
    once: true,
  },
});
```

**Config:**
- `y: 40` — distance to slide (30-60px typical)
- `stagger: 0.12` — delay between elements (0.06-0.2s range)
- `start: "top 80%"` — triggers when section top hits 80% viewport height
- `once: true` — fires once, doesn't reverse on scroll-up

**When to use:** Features, benefits cards, product grids, team members, any repeating elements.

---

### `fade-up-single`

Single element entrance. Simpler than stagger — use for headings, paragraphs, standalone CTAs.

```tsx
gsap.from(elementRef.current, {
  y: 30,
  opacity: 0,
  duration: 0.7,
  ease: "power2.out",
  scrollTrigger: {
    trigger: elementRef.current,
    start: "top 85%",
    once: true,
  },
});
```

**When to use:** Section headings, body text, single CTA blocks, callout boxes.

---

## B. Text Reveals

### `character-reveal`

Each character fades in with a 3D rotation stagger. High-impact — use for hero headlines only.

**JSX (split text into character spans):**
```tsx
const title = "CropTab™";
const charsRef = useRef<(HTMLSpanElement | null)[]>([]);

<h1>
  {title.split("").map((char, i) => (
    <span
      key={i}
      ref={(el) => { charsRef.current[i] = el; }}
      className="inline-block"
      style={{ display: char === " " ? "inline" : "inline-block" }}
    >
      {char === " " ? "\u00A0" : char}
    </span>
  ))}
</h1>
```

**Animation:**
```tsx
const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
tl.from(charsRef.current.filter(Boolean), {
  opacity: 0,
  y: 40,
  rotateX: -90,
  stagger: 0.03,
  duration: 0.8,
});
```

**Config:**
- `stagger: 0.03` — fast character reveal (0.02-0.05s range)
- `rotateX: -90` — 3D flip-in effect (remove for simpler fade)
- `duration: 0.8` — per-character animation length

**When to use:** Hero headlines, brand names, single-word impact statements.

---

### `word-reveal`

Words slide up from below with stagger. Mid-impact — use for section headings.

**JSX (split into word spans with overflow hidden wrapper):**
```tsx
const heading = "Cleaner for the Planet";
<h2 ref={headingRef}>
  {heading.split(" ").map((word, i) => (
    <span key={i} className="inline-block overflow-hidden mr-[0.3em]">
      <span data-word className="inline-block">
        {word}
      </span>
    </span>
  ))}
</h2>
```

**Animation:**
```tsx
gsap.from("[data-word]", {
  y: "100%",
  opacity: 0,
  duration: 0.7,
  stagger: 0.06,
  ease: "power3.out",
  scrollTrigger: {
    trigger: headingRef.current,
    start: "top 85%",
    once: true,
  },
});
```

**Config:**
- `y: "100%"` — slides up from below the overflow-hidden wrapper (clip reveal effect)
- `stagger: 0.06` — slower than character reveal
- Requires `overflow-hidden` on the parent span for the clip effect

**When to use:** Section headings for emphasis, sustainability/impact statements.

---

### `line-reveal`

Lines reveal one at a time with a wipe effect. Use for paragraphs or multi-line headings.

```tsx
gsap.from(".reveal-line", {
  clipPath: "inset(0 100% 0 0)",
  opacity: 0,
  duration: 0.8,
  stagger: 0.15,
  ease: "power2.inOut",
  scrollTrigger: {
    trigger: containerRef.current,
    start: "top 80%",
    once: true,
  },
});
```

**When to use:** About sections, long-form quotes, editorial text blocks.

---

## C. Number Counters

### `count-up`

Numbers animate from 0 to target value on scroll. Use for stats/metrics.

```tsx
interface Metric {
  value: string;      // display value: "100×", "0.5", "≥5×"
  countTo: number;    // numeric target: 100, 0.5, 5
  prefix?: string;    // "≥"
  suffix?: string;    // "×", " ton"
  decimals?: number;  // decimal places
}

const metrics: Metric[] = [
  { value: "4", countTo: 4, suffix: "" },
  { value: "100×", countTo: 100, suffix: "×" },
  { value: "0.5", countTo: 0.5, suffix: " ton", decimals: 1 },
  { value: "≥5×", countTo: 5, prefix: "≥", suffix: "×" },
];

// In useEffect:
metricRefs.current.forEach((el, i) => {
  if (!el) return;
  const m = metrics[i];
  const proxy = { val: 0 };
  gsap.to(proxy, {
    val: m.countTo,
    duration: 1.6,
    ease: "power2.out",
    scrollTrigger: {
      trigger: el,
      start: "top 85%",
      once: true,
    },
    onUpdate() {
      const formatted = m.decimals
        ? proxy.val.toFixed(m.decimals)
        : String(Math.round(proxy.val));
      el.textContent = `${m.prefix || ""}${formatted}${m.suffix || ""}`;
    },
  });
});
```

**Config:**
- `duration: 1.6` — longer than entrance animations for dramatic effect
- `decimals` — controls `.toFixed()` for values like 0.5
- `prefix/suffix` — handles "≥", "×", " ton", etc.

**When to use:** Stats sections, metrics strips, impact numbers, ROI figures.

---

## D. SVG Animations

### `marker-pulse`

SVG circle markers appear with a bounce, then pulse continuously. Use for maps and data visualizations.

```tsx
// Phase 1: Entrance (staggered scale-up)
gsap.from(".map-marker", {
  scale: 0,
  opacity: 0,
  duration: 0.4,
  stagger: 0.08,
  ease: "back.out(2)",
  scrollTrigger: {
    trigger: sectionRef.current,
    start: "top 70%",
    once: true,
  },
  onComplete: () => {
    // Phase 2: Continuous pulse after entrance
    document.querySelectorAll(".map-marker").forEach((el) => {
      gsap.to(el, {
        scale: 1.4,
        opacity: 0.6,
        duration: 1,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
        transformOrigin: "center center",
      });
    });
  },
});
```

**Config:**
- `ease: "back.out(2)"` — overshoot bounce on entrance (the `2` controls overshoot amount)
- `repeat: -1, yoyo: true` — infinite pulse cycle
- `transformOrigin: "center center"` — critical for SVG elements (default is top-left)

**When to use:** Map markers, data points on visualizations, icon highlights.

---

### `path-draw`

SVG path draws itself on scroll. Use for decorative elements, route lines, connecting lines.

```tsx
const path = document.querySelector(".draw-path") as SVGPathElement;
const length = path.getTotalLength();
path.style.strokeDasharray = `${length}`;
path.style.strokeDashoffset = `${length}`;

gsap.to(path, {
  strokeDashoffset: 0,
  duration: 2,
  ease: "power2.inOut",
  scrollTrigger: {
    trigger: path,
    start: "top 75%",
    once: true,
  },
});
```

**When to use:** Decorative paths, connecting timelines, route illustrations.

---

### `icon-glow`

Radial gradient glow follows cursor position over an icon/element. Interactive hover effect.

```tsx
const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
  const rect = e.currentTarget.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  e.currentTarget.style.background = `radial-gradient(
    circle at ${x}px ${y}px,
    rgba(255, 188, 3, 0.3) 0%,
    transparent 60%
  )`;
};

const handleMouseLeave = (e: React.MouseEvent<HTMLDivElement>) => {
  e.currentTarget.style.background = "transparent";
};
```

**Config:**
- Color (`rgba(255, 188, 3, 0.3)`) — should match the site's accent/gold color
- Spread (`60%`) — how far the glow extends

**When to use:** Feature icons, interactive cards, CTA areas. Apply to the icon container, not the icon itself.

---

## E. Timeline Sequences

### `staggered-timeline`

Chain multiple animations with negative time offsets for overlap. Use when elements should reveal in a choreographed sequence.

```tsx
const tl = gsap.timeline({
  defaults: { ease: "power3.out" },
  scrollTrigger: {
    trigger: sectionRef.current,
    start: "top 75%",
    once: true,
  },
});

tl.from(".headline", { y: 40, opacity: 0, duration: 0.8 })
  .from(".subtitle", { y: 30, opacity: 0, duration: 0.6 }, "-=0.4")
  .from(".body-text", { y: 20, opacity: 0, duration: 0.5 }, "-=0.3")
  .from(".cta-button", { y: 20, opacity: 0, duration: 0.4 }, "-=0.2");
```

**Config:**
- `"-=0.4"` — starts 0.4s before previous animation ends (overlap)
- Each element animates slightly faster than the last for acceleration feel
- Attach ScrollTrigger to the timeline itself, not individual tweens

**When to use:** Hero sections, CTA sections, any section with heading + subtitle + body + button.

---

### `entrance-then-loop`

Two-phase: entrance animation completes, then a continuous loop begins. Use for decorative elements that need both.

```tsx
gsap.from(".element", {
  scale: 0,
  opacity: 0,
  duration: 0.6,
  scrollTrigger: { trigger: sectionRef.current, start: "top 80%", once: true },
  onComplete: () => {
    gsap.to(".element", {
      y: -10,
      duration: 2,
      repeat: -1,
      yoyo: true,
      ease: "sine.inOut",
    });
  },
});
```

**When to use:** Map markers (appear → pulse), scroll indicators (appear → bounce), decorative icons.

---

## F. Continuous Motion

### `bounce-loop`

Gentle up-down bounce. Use for scroll indicators, arrows, attention cues.

```tsx
gsap.to(chevronRef.current, {
  y: 10,
  duration: 1.2,
  repeat: -1,
  yoyo: true,
  ease: "sine.inOut",
});
```

**When to use:** Hero scroll indicators, "scroll down" arrows, attention dots.

---

### `float-loop`

Slow floating movement. More subtle than bounce — use for background decorative elements.

```tsx
gsap.to(".float-element", {
  y: -15,
  x: 5,
  rotation: 2,
  duration: 3,
  repeat: -1,
  yoyo: true,
  ease: "sine.inOut",
});
```

**When to use:** Background shapes, decorative icons, product images that need life.

---

### `rotate-loop`

Slow continuous rotation. Use sparingly for loading indicators or decorative shapes.

```tsx
gsap.to(".rotate-element", {
  rotation: 360,
  duration: 20,
  repeat: -1,
  ease: "none",
});
```

**When to use:** Decorative circular elements, loading spinners, abstract shapes.

---

## G. Mouse/Cursor Effects

### `cursor-trail`

Color squares follow the cursor with a fade trail. Page-level component — add to layout, not individual sections.

See `skills/components/cursor-trail.md` for the full component code.

**Config:**
- Desktop-only (detect `pointer: fine` media query)
- Colors should match the site's accent palette
- Performance: uses `requestAnimationFrame`, elements have `pointer-events: none`
- Disable over form fields and interactive elements

**When to use:** Expressive animation intensity sites. Adds personality to portfolio, creative, and premium sites.

---

### `icon-glow-follow`

A glowing highlight that follows the cursor over a specific element. See pattern D: `icon-glow` above.

**When to use:** Feature cards, CTAs, hero interactive areas.

---

## H. Scroll Behavior

### Smooth Scrolling — REMOVED

Lenis was removed from the pipeline. It hijacks native scroll and fights with GSAP
ScrollTrigger, causing flickering and broken interactions even with the bridge pattern.

**Current approach:** Use native browser scroll. GSAP ScrollTrigger works directly
with the browser's scroll position — no wrapper component needed. Add
`html { scroll-behavior: smooth; }` in CSS if you want smooth anchor scrolling.

**Do not add Lenis, locomotive-scroll, or any other scroll hijacking library.**

---

## Pattern-to-Archetype Map

Quick reference for which patterns to use with which section archetypes:

| Section Archetype | Default Pattern(s) | Upgrade Pattern(s) |
|-------------------|--------------------|--------------------|
| **NAV** | CSS transitions only | — |
| **HERO** | `fade-up-single` | `character-reveal` + `staggered-timeline` + `bounce-loop` (scroll indicator) |
| **STATS** | `fade-up-stagger` | `count-up` per metric |
| **FEATURES** | `fade-up-stagger` | + `icon-glow` on hover |
| **ABOUT/PROBLEM** | `fade-up-single` | `word-reveal` on heading |
| **HOW-IT-WORKS** | `fade-up-stagger` | `staggered-timeline` for sequential steps |
| **PRODUCT-SHOWCASE** | `fade-up-stagger` | `gsap-pinned-horizontal` for horizontal showcase variant |
| **TESTIMONIALS** | `fade-up-stagger` | — |
| **CTA** | `fade-up-single` | `staggered-timeline` for heading → button |
| **MAP/TRIALS** | `fade-up-single` | `marker-pulse` on SVG points |
| **FORM/CONTACT** | `fade-up-stagger` | — |
| **FOOTER** | `fade-up-single` | — |

---

## Ease Reference

Named eases used across patterns:

| Ease | Feel | Use For |
|------|------|---------|
| `power2.out` | Smooth deceleration | General entrances |
| `power3.out` | Snappy entrance | Text reveals, stagger |
| `back.out(2)` | Overshoot bounce | SVG markers, playful elements |
| `sine.inOut` | Gentle oscillation | Continuous loops (pulse, float, bounce) |
| `power2.inOut` | Symmetric speed | Path drawing, line reveals |
| `none` | Linear | Continuous rotation |

---

## I. VengenceUI Components (v0.7.0)

Pre-built React components from VengenceUI, refactored to web-builder conventions. Each is a self-contained `.tsx` file in the animation component library. Import via the component injection system (Tier 1) — `selectAnimation()` handles selection automatically based on archetype affinity and intensity.

### `character-flip`

3D character flip animation using Framer Motion `AnimatePresence`. Each character rotates on Y-axis with stagger timing. Higher visual impact than `character-reveal`.

**Category:** `text/` | **Engine:** framer-motion | **Intensity:** expressive
**Pattern:** Standalone — takes `text` prop, renders character spans
**Best for:** HERO (0.9), CTA (0.5), ABOUT (0.3)

---

### `border-beam`

Rotating gradient beam that travels along the border of a container. Pure CSS animation using `conic-gradient` and `@keyframes`. Low performance cost.

**Category:** `effect/` | **Engine:** css | **Intensity:** moderate
**Pattern:** Wrapper — wraps children, adds beam overlay via `::after`
**Best for:** PRICING (0.9), CTA (0.8), FEATURES (0.7), PRODUCT-SHOWCASE (0.6)

---

### `glow-border`

Aurora-style conic-gradient glow effect around card borders. Animated with CSS `@keyframes` rotation. More dramatic than `border-beam`.

**Category:** `effect/` | **Engine:** css | **Intensity:** expressive
**Pattern:** Wrapper — wraps children with animated glow border
**Best for:** CTA (0.9), PRICING (0.8), PRODUCT-SHOWCASE (0.7), FEATURES (0.5)

---

### `staggered-grid`

GSAP ScrollTrigger-powered grid reveal. Children appear in staggered sequence with scale + opacity. More dynamic than `fade-up-stagger` for grid layouts.

**Category:** `entrance/` | **Engine:** gsap | **Intensity:** expressive
**Pattern:** Wrapper — children become grid items that stagger-reveal on scroll
**Best for:** GALLERY (0.95), FEATURES (0.8), TEAM (0.8), PRODUCT-SHOWCASE (0.7), PORTFOLIO (0.9)

---

### `spotlight-follow`

Mouse-following spotlight effect using Framer Motion `useMotionValue`. Creates a radial gradient highlight that tracks cursor position. Navigation-optimized.

**Category:** `interactive/` | **Engine:** framer-motion | **Intensity:** expressive
**Pattern:** Standalone — designed for navigation bars, takes menu items as children
**Best for:** NAV (0.95), HERO (0.3)

---

### `cursor-trail`

Pixelated image trail that follows mouse movement. Creates grid of colored squares at cursor path with fade-out. Page-level effect — attaches to document.

**Category:** `interactive/` | **Engine:** css+react | **Intensity:** dramatic
**Pattern:** Standalone — mounts at page level, listens to `mousemove` on document
**Best for:** HERO (0.7), GALLERY (0.5), PORTFOLIO (0.5)

---

### `page-loader`

Full-screen GSAP-powered loading overlay that reveals the page beneath. Uses clip-path animation for the reveal transition.

**Category:** `entrance/` | **Engine:** gsap | **Intensity:** dramatic
**Pattern:** Standalone — full-screen overlay, auto-dismisses after animation
**Best for:** HERO (0.8), NAV (0.3)

---

### `perspective-grid`

3D perspective CSS grid background. Creates a visual depth effect with CSS `perspective` and `transform: rotateX()`. Static but visually striking.

**Category:** `background/` | **Engine:** css | **Intensity:** moderate
**Pattern:** Standalone — renders grid element, accepts `className` for sizing
**Best for:** HERO (0.8), CTA (0.6), FEATURES (0.5), ABOUT (0.4)

---

### `aurora-background`

Animated aurora/northern-lights gradient background using CSS keyframes + Framer Motion for entrance. Soft gradient blobs shift and blend.

**Category:** `background/` | **Engine:** css+framer | **Intensity:** expressive
**Pattern:** Wrapper — children render over the animated background
**Best for:** HERO (0.95), CTA (0.7), ABOUT (0.4)

---

### `count-up` (v0.7.0 replacement)

Smooth vertical slide number animation using Framer Motion `layoutId` and spring physics. Replaces v0.6.0 basic GSAP counter. Each digit slides independently.

**Category:** `continuous/` | **Engine:** framer-motion | **Intensity:** moderate
**Pattern:** Standalone — takes `value` prop (number), renders animated digits
**Best for:** STATS (1.0), HERO (0.3)

---

### `marquee` (v0.7.0 replacement)

Infinite horizontal scroll with progressive blur masks on edges. CSS-only animation with configurable speed and direction. Replaces v0.6.0 basic CSS marquee.

**Category:** `continuous/` | **Engine:** css | **Intensity:** subtle
**Pattern:** Wrapper — children become marquee items, duplicated for seamless loop
**Best for:** LOGOS (1.0), TESTIMONIALS (0.7), GALLERY (0.5)

---

## Pattern-to-Archetype Map (Updated v0.7.0)

The `selectAnimation()` algorithm in `animation-injector.js` uses the `affinity` field in `registry.json` for automated selection. The table below is a simplified reference — for exact scores see `registry.json`.

| Section Archetype | Subtle | Moderate | Expressive | Dramatic |
|---|---|---|---|---|
| **HERO** | fade-up-single | perspective-grid | character-reveal, aurora-background, character-flip | page-loader, cursor-trail |
| **FEATURES** | fade-up-stagger | border-beam | staggered-grid, glow-border | — |
| **STATS** | fade-up-stagger | count-up | — | — |
| **CTA** | fade-up-single | border-beam | glow-border, aurora-background | — |
| **GALLERY** | fade-up-stagger | — | staggered-grid | — |
| **PRICING** | fade-up-stagger | border-beam | glow-border | — |
| **NAV** | — | — | spotlight-follow | — |
| **LOGOS** | marquee | — | — | — |

---

## J. GSAP Plugin Patterns

Plugin-based patterns requiring `gsap.registerPlugin(...)`. Use core GSAP + ScrollTrigger for most entrances; reserve these for text splits, layout transitions, SVG drawing, motion paths, and responsive control.

---

### `splittext-chars-stagger`

Character-by-character entrance reveal. Split text into characters and stagger-animate them in with optional 3D rotation.

**Plugin:** SplitText (GSAP)  
**Registration:** `gsap.registerPlugin(SplitText)`

```tsx
"use client";
import { useRef, useEffect } from "react";
import gsap from "gsap";
import { SplitText } from "gsap/SplitText";

gsap.registerPlugin(SplitText);

// Inside component:
useEffect(() => {
  const split = new SplitText(titleRef.current, { type: "chars" });
  gsap.from(split.chars, {
    y: 40,
    rotateX: -90,
    stagger: 0.03,
    duration: 0.8,
    ease: "back.out(1.7)",
    scrollTrigger: { trigger: titleRef.current, start: "top 80%" }
  });
  return () => split.revert();
}, []);
```

**Note:** SplitText is safe for entrance since the characters exist in DOM — set initial CSS `visibility: visible` as needed.

**Section fit:** HERO headlines, CTA titles, page transitions.

---

### `splittext-words-wave`

Word-by-word wave entrance. Split text into words and animate each word in with opacity and vertical motion.

```tsx
const split = new SplitText(el, { type: "words" });
gsap.from(split.words, {
  opacity: 0, y: 20, stagger: 0.05, duration: 0.6, ease: "power2.out"
});
return () => split.revert();
```

**Section fit:** TESTIMONIALS quotes, ABOUT descriptions.

---

### `splittext-lines-reveal`

Line-by-line masked reveal. Split into lines with overflow hidden and animate each line up for a wipe effect.

```tsx
const split = new SplitText(el, { type: "lines", linesClass: "line-wrapper" });
gsap.set(split.lines, { overflow: "hidden" });
gsap.from(split.lines, {
  y: "100%", stagger: 0.1, duration: 0.8, ease: "power3.out"
});
return () => split.revert();
```

**Section fit:** HERO subtitles, STORY body text.

---

### `scramble-reveal`

Random character scramble resolving to final text. Text appears to unscramble into the target string.

**Plugin:** ScrambleTextPlugin (GSAP)

```tsx
gsap.to(el, {
  duration: 1.5,
  scrambleText: { text: "Final Text", chars: "!@#$%&*", speed: 0.3 },
  scrollTrigger: { trigger: el, start: "top 80%" }
});
```

**Section fit:** HERO taglines, CTA headers, tech-themed sections.

---

### `scramble-hover`

Scramble on hover interaction. Text scrambles and resolves on mouse enter for a tech/glitch feel.

```tsx
const onEnter = () => gsap.to(el, { scrambleText: { text: el.textContent, speed: 0.5 }, duration: 0.8 });
```

**Section fit:** NAV links, button labels.

---

### `flip-layout-transition`

Animated layout change for tabs, filters, or view toggles. Capture state before DOM change, apply change, then animate from the previous state.

**Plugin:** Flip (GSAP)  
**Registration:** `gsap.registerPlugin(Flip)`

```tsx
import { Flip } from "gsap/Flip";
gsap.registerPlugin(Flip);

const state = Flip.getState(items);
// Apply DOM changes (filter, reorder, toggle class)
container.classList.toggle("grid-view");
Flip.from(state, { duration: 0.6, ease: "power1.inOut", stagger: 0.05, absolute: true });
```

**Section fit:** PRODUCT-SHOWCASE filter tabs, GALLERY layout toggles.

---

### `flip-expand-card`

Card expanding to detail view. Use Flip to animate between collapsed and expanded layout.

```tsx
const state = Flip.getState(card);
card.classList.toggle("expanded");
Flip.from(state, { duration: 0.5, ease: "power2.inOut" });
```

**Section fit:** PORTFOLIO cards, TEAM member details.

---

### `drawsvg-logo-reveal`

SVG stroke drawing animation on scroll. Path draws from start to end for logo or graphic reveals.

**Plugin:** DrawSVGPlugin (GSAP)  
**Registration:** `gsap.registerPlugin(DrawSVGPlugin)`

```tsx
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";
gsap.registerPlugin(DrawSVGPlugin);

gsap.from(".logo-path", {
  drawSVG: "0%",
  duration: 2,
  ease: "power2.inOut",
  scrollTrigger: { trigger: ".logo-section", start: "top 70%" }
});
```

**Section fit:** HERO logo reveals, ABOUT brand story.

---

### `drawsvg-path-progress`

Progress indicator drawing with scroll. Path draw progress is tied to scroll position (scrub).

```tsx
gsap.to(".progress-path", {
  drawSVG: "0% 100%",
  scrollTrigger: { trigger: ".timeline", scrub: true, start: "top center", end: "bottom center" }
});
```

**Section fit:** HOW-IT-WORKS steps, TIMELINE sections.

---

### `morphsvg-shape-shift`

Morphing between two SVG shapes. One path morphs into another; good for loops or state changes.

**Plugin:** MorphSVGPlugin (GSAP)  
**Registration:** `gsap.registerPlugin(MorphSVGPlugin)`

```tsx
import { MorphSVGPlugin } from "gsap/MorphSVGPlugin";
gsap.registerPlugin(MorphSVGPlugin);

gsap.to("#shape1", { morphSVG: "#shape2", duration: 1.5, ease: "power2.inOut", repeat: -1, yoyo: true });
```

**Section fit:** HERO background shapes, FEATURES decorative elements.

---

### `morphsvg-icon-morph`

Icon morphing on hover or state change. SVG path morphs between two predefined paths (e.g. hamburger ↔ X).

```tsx
const onToggle = (isActive) => {
  gsap.to("#icon-path", { morphSVG: isActive ? "#icon-active" : "#icon-default", duration: 0.4 });
};
```

**Section fit:** FEATURES interactive icons, NAV hamburger-to-X.

---

### `motionpath-orbit`

Element orbiting along a circular or custom path. Use for satellites, planets, or decorative motion.

**Plugin:** MotionPathPlugin (GSAP)  
**Registration:** `gsap.registerPlugin(MotionPathPlugin)`

```tsx
import { MotionPathPlugin } from "gsap/MotionPathPlugin";
gsap.registerPlugin(MotionPathPlugin);

gsap.to(".satellite", {
  motionPath: { path: "#orbit-path", align: "#orbit-path", autoRotate: true },
  duration: 8, repeat: -1, ease: "none"
});
```

**Section fit:** HERO background elements, FEATURES tech diagrams.

---

### `motionpath-follow-scroll`

Element following a path driven by scroll. Path progress is scrubbed to scroll position.

```tsx
gsap.to(".element", {
  motionPath: { path: "#scroll-path", align: "#scroll-path" },
  scrollTrigger: { trigger: ".section", scrub: 1 }
});
```

**Section fit:** HOW-IT-WORKS journey visualization.

---

### `draggable-carousel`

Touch-friendly draggable carousel with inertia and optional snap to item positions.

**Plugin:** Draggable, InertiaPlugin (GSAP)  
**Registration:** `gsap.registerPlugin(Draggable, InertiaPlugin)`

```tsx
import { Draggable } from "gsap/Draggable";
import { InertiaPlugin } from "gsap/InertiaPlugin";
gsap.registerPlugin(Draggable, InertiaPlugin);

Draggable.create(".carousel-track", {
  type: "x", bounds: ".carousel-wrapper",
  inertia: true, snap: (val) => Math.round(val / cardWidth) * cardWidth
});
```

**Section fit:** TESTIMONIALS carousel, PRODUCT-SHOWCASE slider.

---

### `observer-swipe-nav`

Swipe gesture navigation. Left/right touch or pointer moves trigger prev/next actions.

**Plugin:** Observer (GSAP)  
**Registration:** `gsap.registerPlugin(Observer)`

```tsx
import { Observer } from "gsap/Observer";
gsap.registerPlugin(Observer);

Observer.create({
  target: sectionRef.current,
  type: "touch,pointer",
  onLeft: () => goToNext(),
  onRight: () => goToPrev(),
  tolerance: 50
});
```

**Section fit:** HERO full-page sections, GALLERY mobile swipe.

---

### `scrollsmoother-parallax`

Smooth scrolling with parallax layers. Requires a wrapper structure and uses `data-speed` on elements.

**Plugin:** ScrollSmoother (GSAP)  
**Registration:** `gsap.registerPlugin(ScrollTrigger, ScrollSmoother)`

```tsx
import { ScrollSmoother } from "gsap/ScrollSmoother";
gsap.registerPlugin(ScrollTrigger, ScrollSmoother);

// Requires wrapper structure: #smooth-wrapper > #smooth-content
ScrollSmoother.create({
  smooth: 1.5, effects: true, normalizeScroll: true
});
// Then use data-speed on elements: <div data-speed="0.5">Parallax</div>
```

**Note:** Conflicts with Lenis. Use one smooth-scroll solution per project.

**Section fit:** Full-page parallax, HERO or scroll-driven storytelling.

---

### `custom-ease-brand`

Custom branded easing curve. Define a named ease from SVG-style cubic bezier and use it across tweens.

**Plugin:** CustomEase (GSAP)  
**Registration:** `gsap.registerPlugin(CustomEase)`

```tsx
import { CustomEase } from "gsap/CustomEase";
gsap.registerPlugin(CustomEase);

CustomEase.create("brandEase", "M0,0 C0.175,0.885 0.32,1 1,1");
gsap.to(el, { y: 0, ease: "brandEase", duration: 0.8 });
```

**Section fit:** Any section where a consistent branded motion curve is required.

---

### `matchmedia-responsive`

Responsive animation breakpoints. Run different animations or disable motion by viewport and `prefers-reduced-motion`.

```tsx
const mm = gsap.matchMedia();
mm.add("(min-width: 768px)", () => {
  // Desktop animations
  gsap.from(".cards", { x: -100, stagger: 0.1, scrollTrigger: { trigger: ".cards" } });
});
mm.add("(max-width: 767px)", () => {
  // Simpler mobile animations
  gsap.from(".cards", { opacity: 0, stagger: 0.05 });
});
mm.add("(prefers-reduced-motion: reduce)", () => {
  // Disable all animations
  gsap.set(".animated", { clearProps: "all" });
});
return () => mm.revert();
```

**Section fit:** All sections — use for responsive and accessibility-aware animation control.

---

### `ease-rough`

Rough or hand-drawn easing. Adds irregular motion for an organic, illustrated feel.

**Plugin:** EasePack (GSAP)  
**Registration:** `gsap.registerPlugin(EasePack)`

```tsx
import { EasePack } from "gsap/EasePack";
gsap.registerPlugin(EasePack);
gsap.to(el, { rotation: 360, ease: "rough({ strength: 2, points: 50, template: power2.inOut })" });
```

**Section fit:** Playful or hand-drawn brand sections, decorative motion.

---

### `ease-slow-mo`

Slow-motion middle segment. Motion eases in, slows in the middle, then eases out.

```tsx
gsap.to(el, { x: 300, ease: "slow(0.5, 0.8, false)", duration: 2 });
```

**Section fit:** Emphasis on a single motion, dramatic pauses.

---

### `ease-expo-scale`

Exponential scaling ease. Useful for zoom or scale animations with exponential feel.

```tsx
gsap.to(el, { x: 600, ease: "expoScale(1, 10, power1.inOut)", duration: 1.5 });
```

**Section fit:** Scale reveals, zoom effects, data visualizations.

---

### `pinned-horizontal-scene`

Pinned section with horizontal scroll and nested animated elements. The signature premium website pattern (GSAP homepage, Apple product pages).

**Plugin:** ScrollTrigger (pin + scrub + containerAnimation)

```tsx
"use client";
import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

// Inside component useEffect:
const section = sectionRef.current;
const track = trackRef.current;
const scrollWidth = track.scrollWidth - window.innerWidth;

// Main horizontal scroll tween
const scrollTween = gsap.to(track, {
  x: -scrollWidth,
  ease: "none",
  scrollTrigger: {
    trigger: section,
    pin: true,
    scrub: 1,
    end: () => `+=${scrollWidth}`,
    invalidateOnRefresh: true,
  },
});

// Nested element animation WITHIN the horizontal scroll
gsap.fromTo(".floating-shape",
  { scale: 0, rotation: -180 },
  {
    scale: 1,
    rotation: 0,
    scrollTrigger: {
      trigger: ".floating-shape",
      containerAnimation: scrollTween, // KEY: ties to horizontal scroll
      start: "left center",
      end: "right center",
      scrub: true,
    },
  }
);

// Color/background transitions between panels
gsap.to(section, {
  backgroundColor: "#1a1a2e",
  scrollTrigger: {
    trigger: ".panel-2",
    containerAnimation: scrollTween,
    start: "left center",
    toggleActions: "play none none reverse",
  },
});
```

**Critical:** The `containerAnimation` parameter makes nested ScrollTriggers respond to horizontal scroll position instead of vertical page scroll. Without it, nested animations fire based on the page's vertical scroll, which breaks the effect.

**Section fit:** Any section needing horizontal scroll immersion — PRODUCT-SHOWCASE (horizontal showcase), FEATURES (horizontal panels), GALLERY (carousel/showcase), HERO (product-journey), HOW-IT-WORKS (timeline). Applied via animation injection, not as a dedicated archetype.

---

## K. Card Micro-Animation Effects

Small, card-scoped animation effects for PRODUCT-SHOWCASE `demo-cards` variant. Each effect is 5-8 lines and designed to differentiate individual cards within a grid. These are inline patterns — not standalone components.

---

### `card-stroke-draw`

SVG path drawing around card border on scroll entry. Creates an animated border reveal.

**Maps to:** DrawSVG plugin

```tsx
// Add an SVG rect overlay matching the card dimensions
<svg className="absolute inset-0 w-full h-full pointer-events-none">
  <rect className="card-border" x="1" y="1" width="calc(100%-2)" height="calc(100%-2)"
    rx="12" fill="none" stroke="currentColor" strokeWidth="2" />
</svg>

// In useEffect:
gsap.fromTo(".card-border", { drawSVG: "0%" }, {
  drawSVG: "100%", duration: 1.5, ease: "power2.inOut",
  scrollTrigger: { trigger: cardRef, start: "top 80%", once: true }
});
```

**Section fit:** PRODUCT-SHOWCASE demo-cards (DrawSVG card).

---

### `card-morph-blob`

Background blob that morphs between organic shapes on hover. Creates a living, breathing card background.

**Maps to:** MorphSVG plugin

```tsx
// Background SVG blob with two shape targets
<svg viewBox="0 0 200 200" className="absolute -z-10 opacity-20">
  <path id="blob1" d="M40,-50C..." fill="currentColor" />
  <path id="blob2" d="M30,-40C..." style={{ visibility: "hidden" }} />
</svg>

// On mouseenter:
gsap.to("#blob1", { morphSVG: "#blob2", duration: 1.2, ease: "elastic.out(1, 0.5)" });
// On mouseleave: reverse
gsap.to("#blob1", { morphSVG: "#blob1", duration: 0.8, ease: "power2.inOut" });
```

**Section fit:** PRODUCT-SHOWCASE demo-cards (MorphSVG card).

---

### `card-orbit-dot`

Small dot orbiting along the card border path. Creates a subtle motion indicator.

**Maps to:** MotionPath plugin

```tsx
// Small dot element + SVG border path
<div className="orbit-dot w-2 h-2 rounded-full bg-accent absolute" />
<svg className="absolute inset-0"><rect id="orbit-path" ... /></svg>

// In useEffect:
gsap.to(".orbit-dot", {
  motionPath: { path: "#orbit-path", autoRotate: false },
  duration: 4, repeat: -1, ease: "none"
});
```

**Section fit:** PRODUCT-SHOWCASE demo-cards (MotionPath card).

---

### `card-flip-preview`

Card flips to reveal alternate content on hover. Uses CSS perspective + GSAP Flip or simple rotateY.

**Maps to:** Flip plugin (or CSS fallback)

```tsx
// Card has front + back faces
<div className="relative" style={{ perspective: "1000px" }}>
  <div ref={cardInner} className="transition-transform duration-500"
    style={{ transformStyle: "preserve-3d" }}>
    <div className="backface-hidden">{/* front */}</div>
    <div className="backface-hidden rotate-y-180 absolute inset-0">{/* back */}</div>
  </div>
</div>

// On hover via GSAP:
gsap.to(cardInner, { rotateY: 180, duration: 0.6, ease: "power2.inOut" });
```

**Section fit:** PRODUCT-SHOWCASE demo-cards (Flip card).

---

### `card-text-scramble`

Title text scrambles through random characters on hover, then resolves to the real text.

**Maps to:** ScrambleText plugin

```tsx
// On mouseenter:
gsap.to(titleRef, {
  duration: 1.2,
  scrambleText: { text: "Original Title", chars: "!<>-_\\/[]{}=+*^?#", speed: 0.4 },
  ease: "none"
});
```

**Section fit:** PRODUCT-SHOWCASE demo-cards (ScrambleText card).

---

### `card-3d-rotate`

Subtle 3D perspective rotation following mouse position on the card. Gives a "tilting card" feel.

**Maps to:** GSAP + transforms (no plugin required)

```tsx
// On mousemove within card:
const rect = card.getBoundingClientRect();
const x = (e.clientX - rect.left) / rect.width - 0.5;
const y = (e.clientY - rect.top) / rect.height - 0.5;
gsap.to(card, {
  rotateY: x * 15, rotateX: -y * 15,
  duration: 0.3, ease: "power2.out",
  transformPerspective: 800
});
// On mouseleave: reset to 0
gsap.to(card, { rotateY: 0, rotateX: 0, duration: 0.5, ease: "elastic.out(1, 0.5)" });
```

**Section fit:** PRODUCT-SHOWCASE demo-cards (3D card), any interactive card.

---

### `card-gradient-shift`

Unique gradient that shifts hue/position on hover using GSAP + CSS custom properties.

**Maps to:** GSAP + CustomEase (or CSS fallback)

```tsx
// Each card gets a unique --gradient-angle and --accent CSS var
<div style={{ background: "linear-gradient(var(--gradient-angle), var(--accent), transparent)" }}>

// On hover:
gsap.to(card, {
  "--gradient-angle": "+=60deg",
  duration: 0.8, ease: "power2.inOut"
});
```

**Section fit:** PRODUCT-SHOWCASE demo-cards (gradient card), CTA hover areas.

---

### `card-particle-burst`

Particles burst outward from card center on hover. Lightweight DOM-based particle effect.

**Maps to:** GSAP (no plugin required)

```tsx
// Create 8-12 small dot divs absolutely positioned at card center
// On mouseenter:
particles.forEach((dot, i) => {
  const angle = (i / particles.length) * Math.PI * 2;
  gsap.fromTo(dot,
    { x: 0, y: 0, opacity: 1, scale: 1 },
    { x: Math.cos(angle) * 60, y: Math.sin(angle) * 60,
      opacity: 0, scale: 0, duration: 0.6,
      ease: "power2.out", delay: i * 0.02 }
  );
});
```

**Section fit:** PRODUCT-SHOWCASE demo-cards (particle card), playful CTA areas.

---

## Maintenance Log

| Date | Change | Source |
|------|--------|--------|
| 2026-02-11 | Added K. Card Micro-Animation Effects: 8 card-scoped patterns (card-stroke-draw, card-morph-blob, card-orbit-dot, card-flip-preview, card-text-scramble, card-3d-rotate, card-gradient-shift, card-particle-burst) for PRODUCT-SHOWCASE demo-cards variant | Track B v1.1.0 |
| 2026-02-11 | Added `pinned-horizontal-scene` pattern, PINNED-SCROLL to archetype map | Track A v1.1.0 |
| 2026-02-11 | Reclassified PINNED-SCROLL: removed from archetype map, updated section fit to list applicable archetypes | v1.1.2 |
| 2026-02-11 | Added F. GSAP Plugin Patterns: SplitText, ScrambleText, Flip, DrawSVG, MorphSVG, MotionPath, Draggable, Observer, ScrollSmoother, CustomEase, matchMedia, EasePack | Pattern doc expansion |
| 2026-02-10 | Added 11 VengenceUI patterns (9 new + 2 replacements), new effect/ and background/ categories, updated archetype map with affinity scores | Animation classification plan v0.7.0 |
| 2026-02-08 | Initial library created from farm-minerals-site production patterns | farm-minerals-promo rebuild |

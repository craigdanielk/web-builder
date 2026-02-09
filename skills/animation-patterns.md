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
| **PRODUCT-SHOWCASE** | `fade-up-stagger` | — |
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

## Maintenance Log

| Date | Change | Source |
|------|--------|--------|
| 2026-02-08 | Initial library created from farm-minerals-site production patterns | farm-minerals-promo rebuild |

## Instructions

Generate a complete, self-contained React component for this section.

**Icon Rule:** NEVER use emoji characters. Import icons from `lucide-react` (e.g., `import { Zap } from 'lucide-react'`). Render as `<Zap className="w-6 h-6" />`.

## GSAP-First Animation Rule

When the animation engine is `gsap`, use **GSAP for ALL animations** — including scroll-triggered entrances. Do NOT default to Framer Motion `whileInView` for entrances.

**The SSR-safe GSAP entrance pattern:**
```tsx
// GSAP entrance — SSR-safe because ScrollTrigger only fires client-side in useEffect
useEffect(() => {
  gsap.registerPlugin(ScrollTrigger);
  const ctx = gsap.context(() => {
    gsap.from(".animate-item", {
      y: 40, opacity: 0, duration: 0.8, stagger: 0.12,
      ease: "power3.out",
      scrollTrigger: { trigger: sectionRef.current, start: "top 80%", once: true }
    });
  }, sectionRef);
  return () => ctx.revert();
}, []);
```

**Why this is SSR-safe:** `useEffect` only runs on the client. `gsap.from()` inside `useEffect` + `gsap.context()` means the "from" state (opacity: 0) is never applied during SSR/hydration. Elements render visible in HTML, then GSAP animates them from the "from" values on scroll. `ctx.revert()` cleans up properly.

**The old `gsap.from()` SSR bug was caused by:** calling `gsap.from()` at the module level or outside `useEffect`, where it runs during SSR and applies `opacity: 0` before hydration. Inside `useEffect` with ScrollTrigger `once: true`, this cannot happen.

**When to use each engine:**
- **Entrance animations** (fade-in, slide-up on scroll): Use **GSAP** `gsap.from()` inside `useEffect` with `scrollTrigger: { once: true }` — SSR-safe, consistent with the rest of the GSAP pipeline
- **Interactive effects** (hover tilt, magnetic buttons): Use **GSAP** `gsap.to()` — triggered by user action
- **Scroll-linked effects** (parallax, scrub): Use **GSAP** ScrollTrigger with `scrub: true`
- **Continuous animations** (floating, pulsing, rotating): Use **GSAP** `gsap.to()` with `repeat: -1`
- **Text effects** (SplitText character reveals): Use **GSAP** SplitText — split text into chars/words, animate with stagger
- **Layout animations** (AnimatePresence, layout shifts): Use **Framer Motion** — only case where Framer is preferred in a GSAP build
- **Plugin-detected patterns**: If plugins like SplitText, Observer, Flip, DrawSVG, MorphSVG, or MotionPath are listed in the Animation Context, you MUST use them in appropriate sections. Do not ignore detected plugins.

**Only import `framer-motion` when you genuinely need:**
- `AnimatePresence` for mount/unmount transitions
- `layoutId` for shared layout animations
- Do NOT import `framer-motion` just for `whileInView` — use GSAP ScrollTrigger instead

---

Requirements:
1. Use TypeScript with React.FC typing
2. Use ONLY the colors, fonts, spacing, radius, and animation values from
   the STYLE CONTEXT header above. Do not introduce any values not specified.
3. The component must be self-contained — no external dependencies beyond:
   - React (including useEffect, useRef)
   - GSAP (`import { gsap } from "gsap"`)
   - GSAP ScrollTrigger (`import { ScrollTrigger } from "gsap/ScrollTrigger"`)
   - Tailwind CSS classes
4. Use semantic HTML elements (section, nav, article, etc.)
5. Include responsive design: mobile-first, with sm/md/lg breakpoints
6. GSAP setup pattern (MUST follow exactly):
   ```tsx
   const sectionRef = useRef<HTMLElement>(null);
   useEffect(() => {
     gsap.registerPlugin(ScrollTrigger);
     const ctx = gsap.context(() => {
       // All animations here, scoped to sectionRef
     }, sectionRef);
     return () => ctx.revert();
   }, []);
   ```
7. ScrollTrigger pattern:
   - **Entrance animations:** Use GSAP `gsap.from()` inside `useEffect` with `scrollTrigger: { trigger: el, start: "top 80%", once: true }` — this is SSR-safe (see GSAP-First Animation Rule above)
   - For scroll-linked (parallax, scrub) use `scrollTrigger: { trigger: element, scrub: true }`
   - Use `stagger` with GSAP for multi-element reveals: `gsap.from(".items", { stagger: 0.12, ... })`
   - For counter/number animations use: `gsap.to(obj, { value: target, snap: { value: 1 }, ... })`
8. If a Reference Animation Pattern is provided above, use that exact GSAP pattern
   with the timing values from the style header's Motion line
9. Hover effects: Use GSAP `gsap.to()` on mouse enter/leave for interactive
   effects. Only use Framer Motion `motion.div` with `whileHover` if you also need
   `AnimatePresence` or `layoutId` in the same component. Prefer GSAP for consistency.
10. All text content should be realistic for the client — not lorem ipsum
11. Export the component as default

---

## GSAP Plugin Registration Pattern

When using ANY GSAP plugin, you must register it. All plugins are included in the `gsap` npm package. Use this pattern at the top of your component:

```tsx
"use client";
import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
// Add other plugins as needed

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger, SplitText);
}
```

**Critical:** Always wrap `registerPlugin` in `typeof window !== "undefined"` check for Next.js SSR safety. Plugins that access the DOM will fail during server rendering.

---

## Plugin: SplitText

SplitText splits text nodes into individual characters, words, or lines for animation. Always revert on cleanup.

**Import:** `import { SplitText } from "gsap/SplitText"`

**Usage patterns:**

1. **Character reveal** (HERO headlines):
```tsx
useEffect(() => {
  const split = new SplitText(titleRef.current, { type: "chars" });
  gsap.from(split.chars, {
    y: 40, rotateX: -90, opacity: 0,
    stagger: 0.03, duration: 0.8,
    ease: "back.out(1.7)",
    scrollTrigger: { trigger: titleRef.current, start: "top 80%", once: true }
  });
  return () => split.revert();
}, []);
```

2. **Word wave** (TESTIMONIALS, ABOUT):
```tsx
const split = new SplitText(el, { type: "words" });
gsap.from(split.words, { opacity: 0, y: 20, stagger: 0.05, duration: 0.6 });
return () => split.revert();
```

3. **Line reveal with mask** (body text):
```tsx
const split = new SplitText(el, { type: "lines", linesClass: "overflow-hidden" });
gsap.from(split.lines, { y: "100%", stagger: 0.1, duration: 0.8, ease: "power3.out" });
return () => split.revert();
```

**Rules:**
- ALWAYS call `split.revert()` in useEffect cleanup
- Wrap in `typeof window !== "undefined"` if needed
- SplitText works on text already in DOM — safe for entrance animation (unlike gsap.from with opacity)

---

## Plugin: Flip

Flip captures DOM state before a change, then animates to the new state. Perfect for layout transitions.

**Import:** `import { Flip } from "gsap/Flip"`

**Usage patterns:**

1. **Filter grid** (PRODUCT-SHOWCASE, GALLERY):
```tsx
const handleFilter = (category) => {
  const state = Flip.getState(itemsRef.current.children);
  // Apply DOM changes
  setActiveFilter(category);
  // After React re-render, animate
  requestAnimationFrame(() => {
    Flip.from(state, {
      duration: 0.6, ease: "power1.inOut",
      stagger: 0.05, absolute: true,
      onEnter: elements => gsap.fromTo(elements, {opacity: 0, scale: 0.8}, {opacity: 1, scale: 1, duration: 0.4}),
      onLeave: elements => gsap.to(elements, {opacity: 0, scale: 0.8, duration: 0.3})
    });
  });
};
```

2. **Card expand** (PORTFOLIO, TEAM):
```tsx
const toggleExpand = () => {
  const state = Flip.getState(cardRef.current);
  cardRef.current.classList.toggle("expanded");
  Flip.from(state, { duration: 0.5, ease: "power2.inOut" });
};
```

**Rules:**
- `Flip.getState()` BEFORE the DOM change
- `Flip.from()` AFTER the DOM change
- Use `absolute: true` for grid transitions to prevent layout jumps

---

## Plugin: DrawSVG

Animates SVG stroke drawing from 0% to 100%.

**Import:** `import { DrawSVGPlugin } from "gsap/DrawSVGPlugin"`

**Usage:**
```tsx
gsap.fromTo(".svg-path", { drawSVG: "0%" }, {
  drawSVG: "100%",
  duration: 2, ease: "power2.inOut",
  scrollTrigger: { trigger: ".svg-section", start: "top 70%" }
});
```

**Rules:**
- Target must be SVG `<path>`, `<line>`, `<circle>`, or `<rect>` elements
- The element must have a visible stroke (set `stroke` and `strokeWidth` in CSS/SVG)
- Use `drawSVG: "0%"` as starting state, `drawSVG: "100%"` as end
- Works great with `scrub: true` for scroll-linked progress

---

## Plugin: MorphSVG

Morphs one SVG shape into another.

**Import:** `import { MorphSVGPlugin } from "gsap/MorphSVGPlugin"`

**Usage:**
```tsx
gsap.to("#shape1", {
  morphSVG: "#shape2",
  duration: 1.5, ease: "power2.inOut"
});
```

**Rules:**
- Both shapes should have similar point counts for smooth morphing
- Use `MorphSVGPlugin.convertToPath()` to convert primitives to paths
- Great for icon state changes (hamburger → X, play → pause)

---

## Plugin: MotionPath

Animates elements along SVG paths.

**Import:** `import { MotionPathPlugin } from "gsap/MotionPathPlugin"`

**Usage:**
```tsx
gsap.to(".element", {
  motionPath: {
    path: "#orbit-path",
    align: "#orbit-path",
    autoRotate: true,
    alignOrigin: [0.5, 0.5]
  },
  duration: 8, repeat: -1, ease: "none"
});
```

**Rules:**
- Path must be a valid SVG `<path>` element
- Use `autoRotate: true` to orient element along the path direction
- `alignOrigin: [0.5, 0.5]` centers the element on the path

---

## Plugin: CustomEase

Create custom easing curves for brand-specific motion.

**Import:** `import { CustomEase } from "gsap/CustomEase"`

**Usage:**
```tsx
CustomEase.create("brandEase", "M0,0 C0.175,0.885 0.32,1 1,1");
gsap.to(el, { y: 0, ease: "brandEase", duration: 0.8 });
```

**Rules:**
- Define custom eases ONCE (in a setup useEffect or module scope)
- The SVG path string defines the curve shape
- Reference by name string in any GSAP tween

---

## Plugin: Observer

Detects user gestures (swipe, scroll velocity, wheel).

**Import:** `import { Observer } from "gsap/Observer"`

**Usage:**
```tsx
Observer.create({
  target: sectionRef.current,
  type: "touch,pointer,wheel",
  onUp: () => slideNext(),
  onDown: () => slidePrev(),
  tolerance: 50,
  preventDefault: true
});
```

---

## matchMedia (Built-in)

Responsive animation breakpoints. No import needed — built into GSAP core.

**Usage:**
```tsx
useEffect(() => {
  const mm = gsap.matchMedia();
  
  mm.add("(min-width: 768px)", () => {
    // Desktop-only animations
    gsap.from(".cards", { x: -100, stagger: 0.1, scrollTrigger: { trigger: ".cards" } });
  });
  
  mm.add("(max-width: 767px)", () => {
    // Simpler mobile animations
    gsap.from(".cards", { opacity: 0, y: 20, stagger: 0.05 });
  });
  
  mm.add("(prefers-reduced-motion: reduce)", () => {
    gsap.set(".animated", { clearProps: "all" });
  });
  
  return () => mm.revert();
}, []);
```

**Rules:**
- ALWAYS include `prefers-reduced-motion: reduce` handler
- ALWAYS call `mm.revert()` in cleanup
- Desktop animations can be complex; mobile should be simpler

---

## Next.js Import Pattern for All Plugins

```tsx
"use client";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import { Flip } from "gsap/Flip";
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";
import { MotionPathPlugin } from "gsap/MotionPathPlugin";
import { CustomEase } from "gsap/CustomEase";
import { Observer } from "gsap/Observer";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger, SplitText, Flip, DrawSVGPlugin, MotionPathPlugin, CustomEase, Observer);
}
```

Only import plugins that the section actually uses. Do not import all plugins in every section.

---

## Pinned Horizontal Scroll Technique

When a section uses the **pinned horizontal scroll** technique (detected via animation injection or reference extraction), follow these rules:

### Structure
```tsx
<section ref={sectionRef} className="relative">
  <div className="h-screen flex items-center overflow-hidden">
    <div ref={trackRef} className="flex will-change-transform">
      {/* Each panel is min-w-[100vw] or content-sized */}
      <div className="min-w-[100vw] h-screen flex items-center justify-center px-20">
        Panel 1 content
      </div>
      <div className="min-w-[100vw] h-screen flex items-center justify-center px-20">
        Panel 2 content
      </div>
    </div>
  </div>
</section>
```

### ScrollTrigger Setup
```tsx
useEffect(() => {
  gsap.registerPlugin(ScrollTrigger);
  const ctx = gsap.context(() => {
    const track = trackRef.current;
    const scrollWidth = track.scrollWidth - window.innerWidth;

    // Main horizontal scroll
    const scrollTween = gsap.to(track, {
      x: -scrollWidth,
      ease: "none",
      scrollTrigger: {
        trigger: sectionRef.current,
        pin: true,
        scrub: 1,
        end: () => `+=${scrollWidth}`,
        invalidateOnRefresh: true,
      },
    });

    // Nested animations WITHIN the horizontal scroll
    gsap.fromTo(".element-in-panel",
      { opacity: 0, y: 50 },
      {
        opacity: 1, y: 0,
        scrollTrigger: {
          trigger: ".element-in-panel",
          containerAnimation: scrollTween,
          start: "left 80%",
          end: "left 30%",
          scrub: true,
        },
      }
    );
  }, sectionRef);
  return () => ctx.revert();
}, []);
```

### Rules for Pinned Horizontal Scroll
1. **ALWAYS use `containerAnimation`** for nested animations inside the pinned section. Without it, nested ScrollTriggers respond to vertical page scroll, not the horizontal scroll position.
2. **ALWAYS add `gsap.matchMedia()`** for mobile fallback — convert to vertical stack on screens < 768px.
3. **ALWAYS add `invalidateOnRefresh: true`** for responsive recalculation on resize.
4. **NEVER use `gsap.from()` with `opacity: 0`** for elements inside the pinned scroll. Use `gsap.fromTo()` instead to avoid SSR invisibility.
5. **Set `will-change-transform`** on the horizontal track for GPU acceleration.
6. For animated scene layouts: inner elements like floating shapes, SVGs, and decorative elements each get their own `containerAnimation`-based ScrollTrigger.
7. For horizontal panel layouts: each panel is `min-w-[100vw]` and self-contained.
8. For product journey layouts: use parallax layers with different `start`/`end` values within the `containerAnimation` for depth.
9. Include a visual progress indicator (progress bar, dot trail, or panel counter).

**Applicable archetypes:** PRODUCT-SHOWCASE, FEATURES, GALLERY, HERO, HOW-IT-WORKS — any section where horizontal immersion enhances the content narrative.

---

Output ONLY the component code. No explanation, no markdown code fences.

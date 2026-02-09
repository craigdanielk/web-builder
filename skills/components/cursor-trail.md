# Cursor Trail Component

A page-level mouse-following effect that creates a trail of colored squares
behind the cursor. Adds personality to sites with `expressive` animation intensity.

**Dependencies:** None (pure React + CSS)
**Level:** Page-level — add to layout.tsx, not individual sections

---

## Full Component Code

```tsx
// src/components/cursor-trail.tsx
"use client";

import { useEffect, useRef, useCallback } from "react";

interface CursorTrailProps {
  /** Trail element colors — should match site accent palette */
  colors?: string[];
  /** Number of trail elements */
  count?: number;
  /** Size of each trail square in pixels */
  size?: number;
  /** How quickly trail elements fade (ms) */
  fadeMs?: number;
}

export function CursorTrail({
  colors = ["#8fa36c", "#a7bf85", "#FFBC03", "#404F1D"],
  count = 12,
  size = 8,
  fadeMs = 400,
}: CursorTrailProps) {
  const trailRef = useRef<HTMLDivElement[]>([]);
  const posRef = useRef({ x: 0, y: 0 });
  const frameRef = useRef<number>(0);
  const indexRef = useRef(0);

  const createTrailElement = useCallback(() => {
    const el = document.createElement("div");
    el.style.cssText = `
      position: fixed;
      width: ${size}px;
      height: ${size}px;
      pointer-events: none;
      z-index: 9999;
      opacity: 0;
      transition: opacity ${fadeMs}ms ease-out;
      border-radius: 1px;
    `;
    document.body.appendChild(el);
    return el;
  }, [size, fadeMs]);

  useEffect(() => {
    // Desktop only — skip on touch devices
    const isDesktop = window.matchMedia("(pointer: fine)").matches;
    if (!isDesktop) return;

    // Create trail elements
    const elements: HTMLDivElement[] = [];
    for (let i = 0; i < count; i++) {
      elements.push(createTrailElement());
    }
    trailRef.current = elements;

    const handleMouseMove = (e: MouseEvent) => {
      posRef.current = { x: e.clientX, y: e.clientY };

      const el = elements[indexRef.current % count];
      el.style.left = `${e.clientX - size / 2}px`;
      el.style.top = `${e.clientY - size / 2}px`;
      el.style.backgroundColor = colors[indexRef.current % colors.length];
      el.style.opacity = "0.7";

      // Fade out after brief display
      setTimeout(() => {
        el.style.opacity = "0";
      }, 50);

      indexRef.current++;
    };

    document.addEventListener("mousemove", handleMouseMove, { passive: true });

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      elements.forEach((el) => el.remove());
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [colors, count, size, createTrailElement]);

  return null; // Renders nothing — trail is managed via DOM
}
```

---

## Usage in layout.tsx

```tsx
import { CursorTrail } from "@/components/cursor-trail";

export default function RootLayout({ children }) {
  return (
    <html><body>
      <CursorTrail
        colors={["#8fa36c", "#a7bf85", "#FFBC03"]}
        count={12}
        size={8}
        fadeMs={400}
      />
      {children}
    </body></html>
  );
}
```

---

## Configuration by Site

| Site Type | Colors | Count | Size | Fade |
|-----------|--------|-------|------|------|
| Farm/agriculture | `["#8fa36c", "#a7bf85", "#FFBC03"]` | 12 | 8 | 400 |
| Artisan/coffee | `["#b45309", "#d97706", "#fbbf24"]` | 10 | 6 | 350 |
| Tech/SaaS | `["#3b82f6", "#60a5fa", "#93c5fd"]` | 8 | 4 | 300 |
| Luxury/fashion | `["#a8a29e", "#d6d3d1", "#f5f5f4"]` | 6 | 3 | 500 |

---

## Performance Notes

- Uses `pointer-events: none` on all trail elements — no click interference
- `passive: true` on mousemove listener — no scroll jank
- Only creates DOM elements on mount, reuses them cyclically
- Desktop-only via `(pointer: fine)` media query — zero overhead on mobile
- Trail elements are `position: fixed` — no layout recalculation

---

## When to Include

- **Include** when preset has `animation_intensity: expressive`
- **Include** when brief specifically requests cursor/mouse effects
- **Skip** for `subtle` or `moderate` animation intensity
- **Skip** for mobile-focused or accessibility-priority sites

---

## Maintenance Log

| Date | Change | Source |
|------|--------|--------|
| 2026-02-08 | Initial component created | farm-minerals-promo analysis |

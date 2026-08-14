"use client";

// hover-glow — a cursor-tracking accent glow behind arbitrary section content.
//
// WHAT THIS REPLACED, AND WHY IT HAD TO GO. This file previously held a
// `TubesBackground` that reached for a WebGL neon-tube cursor effect via
// `await import("https://cdn.jsdelivr.net/npm/threejs-components@.../tubes1.min.js")`.
// A remote-URL dynamic import is not something the app bundler can resolve: Turbopack
// compiled it to `t.x(url, () => require(url), true)`, its external-ESM-import helper,
// which is defined only in the server runtime. In a client chunk `t.x` is undefined,
// so the call threw `TypeError: t.x is not a function` on first paint of every page
// that used the component — deterministically, with no network request ever made. The
// old try/catch swallowed it into a console.error and left a dead <canvas>, so the
// failure looked like a logging quirk instead of an effect that had never once run.
//
// It was also wrong for this design system even if it had loaded: neon tubes with
// additive lights (magenta/green/violet on hardcoded hex literals) are an effect that
// only reads on a DARK ground. The system ground is now #ffffff via --background, and
// additive light on white is invisible. And the old wrapper put `pointer-events-none`
// on the CONTENT layer, so every link and button inside the wrapped section was dead,
// while the wrapper itself swallowed clicks to randomize tube colors.
//
// So: no remote import, no WebGL, no new dependency, no palette literals. The glow is
// a radial gradient mixed from --accent, which is correct on any ground the tokens
// define. The glow layer is the thing that is pointer-transparent; children keep their
// interactivity.

import React, { useCallback, useEffect, useRef, useState } from "react";

interface HoverGlowProps {
  /** Content to render above the glow. Stays fully interactive. */
  children?: React.ReactNode;
  /** Additional CSS classes for the wrapper */
  className?: string;
  /** Radius of the glow in pixels */
  radius?: number;
  /** Peak opacity of the accent at the cursor, 0-1 */
  intensity?: number;
  /** Inline styles for the wrapper */
  style?: React.CSSProperties;
}

export function HoverGlow({
  children,
  className = "",
  radius = 420,
  intensity = 0.14,
  style,
}: HoverGlowProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<number | null>(null);
  const [active, setActive] = useState(false);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  // Written straight to the element's custom properties rather than to React state:
  // a pointermove that re-rendered the subtree would re-render every child section on
  // every mouse pixel. Coalesced into one rAF so a 1000Hz pointer still paints once
  // per frame.
  const handlePointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (reduced) return;
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
    const rect = wrapper.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    if (frameRef.current !== null) return;
    frameRef.current = requestAnimationFrame(() => {
      frameRef.current = null;
      const glow = glowRef.current;
      if (!glow) return;
      glow.style.setProperty("--glow-x", `${x}px`);
      glow.style.setProperty("--glow-y", `${y}px`);
    });
  }, [reduced]);

  useEffect(() => () => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
  }, []);

  // Under reduced motion the glow is a static centred wash — the decoration survives,
  // the cursor chase does not.
  const visible = reduced || active;

  return (
    <div
      ref={wrapperRef}
      className={`relative isolate overflow-hidden ${className}`}
      style={style}
      onPointerMove={handlePointerMove}
      onPointerEnter={() => setActive(true)}
      onPointerLeave={() => setActive(false)}
    >
      <div
        ref={glowRef}
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          // color-mix keeps the glow bound to the design token instead of a literal,
          // so it follows --accent when the palette changes.
          background: `radial-gradient(${radius}px circle at var(--glow-x, 50%) var(--glow-y, 50%), color-mix(in srgb, var(--accent) ${Math.round(intensity * 100)}%, transparent), transparent 70%)`,
          opacity: visible ? 1 : 0,
          transition: "opacity 400ms ease-out",
        }}
      />
      {children}
    </div>
  );
}

export default HoverGlow;

/**
 * Legacy export name. Builds emitted before this rewrite import the default, but the
 * component registry records `export_name: "TubesBackground"`; keeping the alias means
 * the registry entry and any already-generated page stay valid.
 */
export { HoverGlow as TubesBackground };

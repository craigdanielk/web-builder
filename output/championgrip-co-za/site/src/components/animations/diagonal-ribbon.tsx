"use client";

import React from "react";
import { motion, useReducedMotion } from "framer-motion";

/**
 * DiagonalRibbon — two blurred, rotated colour bands that drift slowly across a
 * hero. A high-contrast motion accent that reads as premium without competing
 * with foreground copy.
 *
 * TENANT-AGNOSTIC. Band colours are a prop and default to CSS custom
 * properties. Pattern only — no third-party assets.
 *
 * Ported from a production fintech site; the only change on the way in is that
 * the three brand hexes became the `colors` prop.
 *
 * reduced-motion => static.
 */
export type DiagonalRibbonProps = {
  className?: string;
  /**
   * Three band colours, in gradient order. Any CSS colour, including
   * `var(--token)`. Fewer than three is fine — the list is cycled.
   */
  colors?: string[];
  /** Rotation of both bands in degrees (default -18) */
  angle?: number;
  /** Blur radius in px on the primary band; the secondary uses ~75% (default 46) */
  blur?: number;
  /** Multiplies both drift durations. >1 is slower. (default 1) */
  speedFactor?: number;
  /** 0..1 opacity of the whole ribbon (default 1) */
  intensity?: number;
};

const DEFAULT_COLORS = [
  "var(--brand-accent, #6366f1)",
  "var(--brand-accent-soft, #8b5cf6)",
  "var(--brand-accent-alt, #06b6d4)",
];

export default function DiagonalRibbon({
  className = "",
  colors = DEFAULT_COLORS,
  angle = -18,
  blur = 46,
  speedFactor = 1,
  intensity = 1,
}: DiagonalRibbonProps) {
  const reduce = useReducedMotion();
  const palette = colors.length > 0 ? colors : DEFAULT_COLORS;
  const c = (i: number) => palette[i % palette.length];

  // Alpha lives in the gradient's transparent stops rather than in the colours,
  // so any CSS colour format — including a var() the component cannot parse —
  // works unchanged.
  const primary = `linear-gradient(115deg, transparent 18%, ${c(0)} 40%, ${c(1)} 50%, ${c(2)} 66%, transparent 84%)`;
  const secondary = `linear-gradient(115deg, transparent 34%, ${c(1)} 50%, transparent 64%)`;

  return (
    <div
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
      aria-hidden
      style={{ opacity: intensity }}
    >
      <motion.div
        className="absolute -inset-[45%]"
        style={{ rotate: `${angle}deg`, background: primary, filter: `blur(${blur}px)`, opacity: 0.5 }}
        initial={{ x: "-8%" }}
        animate={reduce ? {} : { x: ["-9%", "9%", "-9%"] }}
        transition={{ duration: 20 * speedFactor, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -inset-[45%]"
        style={{ rotate: `${angle}deg`, background: secondary, filter: `blur(${blur * 0.74}px)`, opacity: 0.38 }}
        initial={{ x: "7%" }}
        animate={reduce ? {} : { x: ["8%", "-8%", "8%"] }}
        transition={{ duration: 26 * speedFactor, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}

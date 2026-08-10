"use client";

import React, { useId } from "react";
import { motion, useReducedMotion } from "framer-motion";

/**
 * CorridorFlow — sweeping curved streams for section backgrounds.
 *
 * A field of long bezier paths that animate their own draw under a radial mask,
 * so overlaid content stays readable while the background still moves. Fills a
 * section boldly and stays behind the cards.
 *
 * TENANT-AGNOSTIC. Gradient stops are a prop and default to CSS custom
 * properties. Nothing brand-specific remains.
 *
 * Ported from a production fintech site. Two changes on the way in:
 * hardcoded brand hexes became the `colors` prop, and the SVG gradient id was
 * a fixed string — two instances on one page both resolved `url(#corridor-grad)`
 * to whichever mounted first, so the second silently inherited the first's
 * colours. It is now per-instance via useId.
 *
 * reduced-motion => static, fully drawn.
 */
export type CorridorFlowProps = {
  className?: string;
  /**
   * Gradient stops along the stream, left to right. Any CSS colour, including
   * `var(--token)`. The first and last stops are faded to transparent at the
   * edges regardless, so pass the solid colours you want in the middle.
   */
  colors?: string[];
  /** Number of streams (default 24) */
  lineCount?: number;
  /** Base seconds for one draw cycle; each line varies around it (default 14) */
  duration?: number;
  /** CSS mask keeping the centre lit and the edges dark (default radial) */
  maskImage?: string;
};

const DEFAULT_COLORS = [
  "var(--brand-accent, #6366f1)",
  "var(--brand-accent-soft, #8b5cf6)",
  "var(--brand-accent-alt, #06b6d4)",
];

const DEFAULT_MASK = "radial-gradient(120% 100% at 70% 40%, #000 30%, transparent 82%)";

export default function CorridorFlow({
  className = "",
  colors = DEFAULT_COLORS,
  lineCount = 24,
  duration = 14,
  maskImage = DEFAULT_MASK,
}: CorridorFlowProps) {
  const reduce = useReducedMotion();
  // Unique per instance. useId output contains ':' in React 18+, which is not a
  // valid CSS identifier inside url(), so it is stripped.
  const gradientId = `corridor-grad-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;

  const palette = colors.length > 0 ? colors : DEFAULT_COLORS;
  const N = Math.max(1, lineCount);

  const paths = Array.from({ length: N }, (_, i) => {
    const p = i - N / 2;
    return `M ${-100} ${120 + p * 34} C ${360} ${60 + p * 30}, ${840} ${420 + p * 30}, ${1300} ${300 + p * 34}`;
  });

  // Transparent at both edges, solid across the middle — the fade is structural,
  // the colours are the caller's.
  const stops: Array<{ offset: string; color: string; opacity: number }> = [
    { offset: "0%", color: palette[0], opacity: 0 },
    ...palette.map((color, i) => ({
      offset: `${35 + (i * 53) / Math.max(1, palette.length - 1 || 1)}%`,
      color,
      opacity: 0.55 - i * 0.05,
    })),
    { offset: "100%", color: palette[palette.length - 1], opacity: 0 },
  ];

  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden>
      <svg
        className="h-full w-full"
        viewBox="0 0 1200 640"
        preserveAspectRatio="xMidYMid slice"
        fill="none"
        style={{ WebkitMaskImage: maskImage, maskImage }}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0.3">
            {stops.map((s, i) => (
              <stop key={i} offset={s.offset} stopColor={s.color} stopOpacity={Math.max(0, s.opacity)} />
            ))}
          </linearGradient>
        </defs>
        {paths.map((d, i) => (
          <motion.path
            key={i}
            d={d}
            stroke={`url(#${gradientId})`}
            strokeWidth={0.9 + (i % 4) * 0.35}
            strokeLinecap="round"
            initial={reduce ? { pathLength: 1, opacity: 0.5 } : { pathLength: 0.15, opacity: 0.25 }}
            animate={reduce ? { pathLength: 1, opacity: 0.5 } : { pathLength: [0.15, 1, 0.15], opacity: [0.25, 0.55, 0.25] }}
            transition={
              reduce ? undefined : { duration: duration + (i % 6) * 2.5, repeat: Infinity, ease: "easeInOut", delay: i * 0.25 }
            }
          />
        ))}
      </svg>
    </div>
  );
}

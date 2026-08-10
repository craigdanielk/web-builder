"use client";

import React from "react";

/**
 * MeshGradient — flowing mesh-gradient field for hero/section backgrounds.
 *
 * Several soft radial colour blooms drift slowly over each other to produce a
 * living gradient. Pure CSS: no shader, no canvas, no external asset, no
 * runtime cost beyond four compositor-layer transforms.
 *
 * TENANT-AGNOSTIC. Every colour arrives as a prop and defaults to a CSS custom
 * property, so a design-token layer can drive the whole field without touching
 * this file. Nothing here is brand-specific.
 *
 * Ported from a production fintech site (Lighthouse 89-98). Two changes on the
 * way in: colours were hardcoded brand values and are now props, and the
 * original used `<style jsx>`, which requires styled-jsx to be configured. The
 * keyframes are static, so they live in a plain <style> element instead and the
 * per-bloom colours ride on inline styles — same output, one less build-time
 * dependency.
 *
 * Honours prefers-reduced-motion by rendering a static composition.
 */
export type MeshGradientProps = {
  className?: string;
  /** 0..1 overall opacity of the field (default 0.9) */
  intensity?: number;
  /**
   * Four bloom colours, painted back-to-front. Any CSS colour, including
   * `var(--token)`. Fewer than four is fine — the list is cycled.
   */
  colors?: string[];
  /** Per-bloom opacity, same order as `colors` (default [0.85, 0.8, 0.7, 0.45]) */
  opacities?: number[];
  /** Blur radius in px applied to every bloom (default 70) */
  blur?: number;
  /** Multiplies every drift duration. >1 is slower. (default 1) */
  speedFactor?: number;
};

const DEFAULT_COLORS = [
  "var(--brand-accent, #6366f1)",
  "var(--brand-accent-soft, #8b5cf6)",
  "var(--brand-highlight, #f59e0b)",
  "var(--brand-accent-alt, #06b6d4)",
];

const DEFAULT_OPACITIES = [0.85, 0.8, 0.7, 0.45];

/** Geometry is the composition, not the brand — it stays fixed. */
const BLOOMS = [
  { top: "-12%", left: "-8%", width: "55%", height: "65%", stop: "68%", duration: 22, anim: "aurelix-mesh-drift-1" },
  { top: "8%", right: "-14%", width: "60%", height: "70%", stop: "70%", duration: 26, anim: "aurelix-mesh-drift-2" },
  { bottom: "-18%", left: "18%", width: "55%", height: "60%", stop: "72%", duration: 30, anim: "aurelix-mesh-drift-3" },
  { top: "22%", left: "30%", width: "42%", height: "48%", stop: "70%", duration: 34, anim: "aurelix-mesh-drift-4" },
] as const;

const KEYFRAMES = `
@keyframes aurelix-mesh-drift-1 {
  from { transform: translate3d(0, 0, 0) scale(1); }
  to   { transform: translate3d(12%, 10%, 0) scale(1.12); }
}
@keyframes aurelix-mesh-drift-2 {
  from { transform: translate3d(0, 0, 0) scale(1.05); }
  to   { transform: translate3d(-14%, 8%, 0) scale(0.95); }
}
@keyframes aurelix-mesh-drift-3 {
  from { transform: translate3d(0, 0, 0) scale(1); }
  to   { transform: translate3d(10%, -12%, 0) scale(1.1); }
}
@keyframes aurelix-mesh-drift-4 {
  from { transform: translate3d(0, 0, 0) scale(0.9); }
  to   { transform: translate3d(-10%, -8%, 0) scale(1.15); }
}
@media (prefers-reduced-motion: reduce) {
  [data-aurelix-mesh-bloom] { animation: none !important; }
}
`;

const MeshGradient: React.FC<MeshGradientProps> = ({
  className = "",
  intensity = 0.9,
  colors = DEFAULT_COLORS,
  opacities = DEFAULT_OPACITIES,
  blur = 70,
  speedFactor = 1,
}) => {
  const palette = colors.length > 0 ? colors : DEFAULT_COLORS;

  return (
    <div
      aria-hidden
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
      style={{ opacity: intensity }}
    >
      <style>{KEYFRAMES}</style>
      {BLOOMS.map((bloom, i) => {
        const color = palette[i % palette.length];
        const opacity = opacities[i] ?? DEFAULT_OPACITIES[i] ?? 0.7;
        const { anim, duration, stop, ...box } = bloom;
        return (
          <span
            key={i}
            data-aurelix-mesh-bloom=""
            style={{
              ...box,
              position: "absolute",
              borderRadius: "50%",
              filter: `blur(${blur}px)`,
              willChange: "transform",
              opacity,
              background: `radial-gradient(circle at 50% 50%, ${color}, transparent ${stop})`,
              animation: `${anim} ${duration * speedFactor}s ease-in-out infinite alternate`,
            }}
          />
        );
      })}
    </div>
  );
};

export default MeshGradient;

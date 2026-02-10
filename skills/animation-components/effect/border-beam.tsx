"use client";
// @ts-nocheck

import React from "react";

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

interface BorderBeamProps {
  /** Content to wrap with the beam effect */
  children?: React.ReactNode;
  /** Additional CSS classes */
  className?: string;
  /** Size of the beam element in pixels */
  size?: number;
  /** Animation duration in seconds */
  duration?: number;
  /** Width of the border in pixels */
  borderWidth?: number;
  /** Anchor point percentage */
  anchor?: number;
  /** Gradient start color */
  colorFrom?: string;
  /** Gradient end color */
  colorTo?: string;
  /** Animation delay in seconds */
  delay?: number;
}

function BorderBeam({
  children,
  className,
  size = 200,
  duration = 15,
  anchor = 90,
  borderWidth = 1.5,
  colorFrom = "#ffaa40",
  colorTo = "#9c40ff",
  delay = 0,
}: BorderBeamProps) {
  return (
    <div className={cn("relative", className)}>
      <style>{`
        @keyframes border-beam {
          100% {
            offset-distance: 100%;
          }
        }
      `}</style>
      <div
        style={
          {
            "--size": size,
            "--duration": duration,
            "--anchor": anchor,
            "--border-width": borderWidth,
            "--color-from": colorFrom,
            "--color-to": colorTo,
            "--delay": delay,
          } as React.CSSProperties
        }
        className={cn(
          "absolute inset-[0] rounded-[inherit] [border:calc(var(--border-width)*1px)_solid_transparent]",
          "![mask-clip:padding-box,border-box] ![mask-composite:intersect] [mask:linear-gradient(transparent,transparent),linear-gradient(white,white)]",
          "after:absolute after:aspect-square after:w-[calc(var(--size)*1px)] after:[animation:border-beam_calc(var(--duration)*1s)_infinite_linear] after:[animation-delay:var(--delay)s] after:[background:linear-gradient(to_left,var(--color-from),var(--color-to),transparent)] after:[offset-anchor:calc(var(--anchor)*1%)_50%] after:[offset-path:rect(0_auto_auto_0_round_calc(var(--size)*1px))]"
        )}
      />
      {children}
    </div>
  );
}

export default BorderBeam;

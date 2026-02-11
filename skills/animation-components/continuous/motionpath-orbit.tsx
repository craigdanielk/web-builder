"use client";

import { useRef, useEffect, ReactNode } from "react";
import gsap from "gsap";
import { MotionPathPlugin } from "gsap/MotionPathPlugin";

if (typeof window !== "undefined") {
  gsap.registerPlugin(MotionPathPlugin);
}

interface MotionPathOrbitProps {
  pathData: string;
  className?: string;
  duration?: number;
  children?: ReactNode;
}

export default function MotionPathOrbit({
  pathData,
  className = "",
  duration = 8,
  children,
}: MotionPathOrbitProps) {
  const ref = useRef<HTMLDivElement>(null);
  const pathRef = useRef<SVGPathElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const pathEl = pathRef.current;
    if (!pathEl) return;

    const tween = gsap.to(ref.current, {
      duration,
      repeat: -1,
      ease: "none",
      motionPath: {
        path: pathEl,
        align: pathEl,
        alignOrigin: [0.5, 0.5],
        autoRotate: true,
      },
    });

    return () => tween.kill();
  }, [pathData, duration]);

  return (
    <>
      <svg
        aria-hidden
        className="absolute w-0 h-0 overflow-visible pointer-events-none"
        style={{ position: "absolute", width: 0, height: 0, overflow: "visible" }}
      >
        <path ref={pathRef} d={pathData} fill="none" />
      </svg>
      <div ref={ref} className={className}>
        {children}
      </div>
    </>
  );
}

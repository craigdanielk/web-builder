"use client";

import { useRef, useState, useCallback } from "react";
import gsap from "gsap";
import { MorphSVGPlugin } from "gsap/MorphSVGPlugin";

if (typeof window !== "undefined") {
  gsap.registerPlugin(MorphSVGPlugin);
}

interface MorphSVGIconProps {
  fromPath: string;
  toPath: string;
  className?: string;
  width?: number | string;
  height?: number | string;
  duration?: number;
}

export default function MorphSVGIcon({
  fromPath,
  toPath,
  className = "",
  width = 24,
  height = 24,
  duration = 0.4,
}: MorphSVGIconProps) {
  const pathRef = useRef<SVGPathElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  const morphTo = useCallback(
    (targetPath: string) => {
      if (!pathRef.current) return;
      const prefersReducedMotion = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (prefersReducedMotion) return;
      gsap.to(pathRef.current, {
        duration,
        morphSVG: { shape: targetPath },
        ease: "power2.inOut",
      });
    },
    [duration]
  );

  const handleMouseEnter = () => {
    setIsHovered(true);
    morphTo(toPath);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    morphTo(fromPath);
  };

  return (
    <svg
      className={className}
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <path ref={pathRef} d={isHovered ? toPath : fromPath} fill="currentColor" />
    </svg>
  );
}

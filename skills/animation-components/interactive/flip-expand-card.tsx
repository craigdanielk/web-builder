"use client";

import { useRef, ReactNode, useState } from "react";
import gsap from "gsap";
import { Flip } from "gsap/Flip";

if (typeof window !== "undefined") {
  gsap.registerPlugin(Flip);
}

interface FlipExpandCardProps {
  children: ReactNode;
  className?: string;
  expandedClassName?: string;
  duration?: number;
}

export default function FlipExpandCard({
  children,
  className = "",
  expandedClassName = "",
  duration = 0.5,
}: FlipExpandCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);

  const handleClick = () => {
    if (!ref.current) return;
    const prefersReducedMotion = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const state = Flip.getState(ref.current);
    setExpanded((e) => !e);
    requestAnimationFrame(() => {
      if (!ref.current) return;
      ref.current.classList.toggle(expandedClassName, !expanded);
      ref.current.classList.toggle("expanded", !expanded);
      if (!prefersReducedMotion) {
        Flip.from(state, { duration, ease: "power2.inOut" });
      }
    });
  };

  return (
    <div
      ref={ref}
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), handleClick())}
      className={className}
      aria-expanded={expanded}
    >
      {children}
    </div>
  );
}

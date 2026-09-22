"use client";

import { useRef, useLayoutEffect, ReactNode } from "react";
import gsap from "gsap";
import { Flip } from "gsap/Flip";

if (typeof window !== "undefined") {
  gsap.registerPlugin(Flip);
}

interface FlipGridFilterProps {
  children: ReactNode;
  className?: string;
  duration?: number;
  stagger?: number;
  /** When this key changes, Flip animates from the previous layout. Omit to use ref.capture()/ref.run() from parent. */
  layoutKey?: string | number;
}

export default function FlipGridFilter({
  children,
  className = "",
  duration = 0.6,
  stagger = 0.05,
  layoutKey,
}: FlipGridFilterProps) {
  const ref = useRef<HTMLDivElement>(null);
  const prevStateRef = useRef<ReturnType<typeof Flip.getState> | null>(null);
  const prevKeyRef = useRef<string | number | undefined>(undefined);

  useLayoutEffect(() => {
    if (!ref.current) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      prevKeyRef.current = layoutKey;
      return;
    }

    const container = ref.current;
    const items = container.children;

    if (layoutKey !== undefined && prevKeyRef.current !== layoutKey && prevStateRef.current && items.length > 0) {
      Flip.from(prevStateRef.current, {
        duration,
        stagger,
        ease: "power1.inOut",
        absolute: true,
      });
      prevStateRef.current = null;
    }

    prevKeyRef.current = layoutKey;
    if (items.length > 0) {
      prevStateRef.current = Flip.getState(items);
    }
  }, [children, layoutKey, duration, stagger]);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}

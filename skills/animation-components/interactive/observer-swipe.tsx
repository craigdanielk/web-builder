"use client";

import { useRef, useEffect, ReactNode } from "react";
import gsap from "gsap";
import { Observer } from "gsap/Observer";

if (typeof window !== "undefined") {
  gsap.registerPlugin(Observer);
}

interface ObserverSwipeProps {
  children: ReactNode;
  className?: string;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  tolerance?: number;
}

export default function ObserverSwipe({
  children,
  className = "",
  onSwipeLeft,
  onSwipeRight,
  tolerance = 50,
}: ObserverSwipeProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const observer = Observer.create({
      target: ref.current,
      type: "touch,pointer",
      onLeft: () => onSwipeLeft?.(),
      onRight: () => onSwipeRight?.(),
      tolerance,
      preventDefault: false,
    });

    return () => observer.kill();
  }, [onSwipeLeft, onSwipeRight, tolerance]);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}

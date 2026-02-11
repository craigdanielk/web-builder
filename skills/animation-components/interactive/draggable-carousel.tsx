"use client";

import { useRef, useEffect, ReactNode } from "react";
import gsap from "gsap";
import { Draggable } from "gsap/Draggable";
import { InertiaPlugin } from "gsap/InertiaPlugin";

if (typeof window !== "undefined") {
  gsap.registerPlugin(Draggable, InertiaPlugin);
}

interface DraggableCarouselProps {
  children: ReactNode;
  className?: string;
  cardWidth?: number;
  gap?: number;
  inertia?: boolean;
}

export default function DraggableCarousel({
  children,
  className = "",
  cardWidth = 300,
  gap = 16,
  inertia = true,
}: DraggableCarouselProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!trackRef.current || !wrapRef.current) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const track = trackRef.current;
    const wrapper = wrapRef.current;
    const totalWidth = (track.children.length * (cardWidth + gap)) - gap;
    const maxScroll = -(totalWidth - wrapper.offsetWidth);

    const draggables = Draggable.create(track, {
      type: "x",
      bounds: { minX: Math.min(0, maxScroll), maxX: 0 },
      inertia,
      edgeResistance: 0.75,
      cursor: "grab",
      activeCursor: "grabbing",
      snap: (value) => {
        const snapped = Math.round(value / (cardWidth + gap)) * (cardWidth + gap);
        return Math.max(maxScroll, Math.min(0, snapped));
      },
    });

    return () => {
      draggables.forEach((d) => d.kill());
    };
  }, [cardWidth, gap, inertia]);

  return (
    <div ref={wrapRef} className={`overflow-hidden ${className}`}>
      <div
        ref={trackRef}
        className="flex will-change-transform"
        style={{ gap, width: "max-content" }}
      >
        {children}
      </div>
    </div>
  );
}

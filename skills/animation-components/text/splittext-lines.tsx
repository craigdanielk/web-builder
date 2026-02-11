"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger, SplitText);
}

interface SplitTextLinesProps {
  text: string;
  className?: string;
  stagger?: number;
  duration?: number;
  trigger?: boolean;
}

export default function SplitTextLines({
  text,
  className = "",
  stagger = 0.1,
  duration = 0.8,
  trigger = true,
}: SplitTextLinesProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const split = new SplitText(ref.current, {
      type: "lines",
      linesClass: "split-line-wrapper",
    });

    gsap.set(split.lines, { overflow: "hidden" });

    const tween = gsap.from(split.lines, {
      y: "100%",
      stagger,
      duration,
      ease: "power3.out",
      ...(trigger
        ? {
            scrollTrigger: {
              trigger: ref.current,
              start: "top 85%",
              once: true,
            },
          }
        : {}),
    });

    return () => {
      tween.kill();
      if (split.revert) split.revert();
    };
  }, [text, stagger, duration, trigger]);

  return (
    <div ref={ref} className={className}>
      {text}
    </div>
  );
}

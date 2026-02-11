"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger, SplitText);
}

interface SplitTextCharsProps {
  text: string;
  className?: string;
  stagger?: number;
  duration?: number;
  ease?: string;
  trigger?: boolean;
}

export default function SplitTextChars({
  text,
  className = "",
  stagger = 0.03,
  duration = 0.8,
  ease = "back.out(1.7)",
  trigger = true,
}: SplitTextCharsProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const split = new SplitText(ref.current, { type: "chars" });

    const tween = gsap.from(split.chars, {
      y: 40,
      rotateX: -90,
      opacity: 0,
      stagger,
      duration,
      ease,
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
  }, [text, stagger, duration, ease, trigger]);

  return (
    <div ref={ref} className={className}>
      {text}
    </div>
  );
}

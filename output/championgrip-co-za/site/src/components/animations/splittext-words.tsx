"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger, SplitText);
}

interface SplitTextWordsProps {
  text: string;
  className?: string;
  stagger?: number;
  duration?: number;
  trigger?: boolean;
}

export default function SplitTextWords({
  text,
  className = "",
  stagger = 0.05,
  duration = 0.6,
  trigger = true,
}: SplitTextWordsProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const split = new SplitText(ref.current, { type: "words" });

    const tween = gsap.from(split.words, {
      opacity: 0,
      y: 20,
      stagger,
      duration,
      ease: "power2.out",
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

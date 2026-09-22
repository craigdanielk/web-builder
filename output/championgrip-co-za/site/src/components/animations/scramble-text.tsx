"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ScrambleTextPlugin } from "gsap/ScrambleTextPlugin";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger, ScrambleTextPlugin);
}

interface ScrambleTextProps {
  text: string;
  className?: string;
  chars?: string;
  speed?: number;
  duration?: number;
  trigger?: boolean;
}

export default function ScrambleText({
  text,
  className = "",
  chars = "!@#$%&*",
  speed = 0.3,
  duration = 1.5,
  trigger = true,
}: ScrambleTextProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      ref.current.textContent = text;
      return;
    }

    ref.current.textContent = "";

    const tween = gsap.to(ref.current, {
      duration,
      scrambleText: {
        text,
        chars,
        speed,
        tweenLength: false,
      },
      ease: "power2.inOut",
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
      if (ref.current) ref.current.textContent = text;
    };
  }, [text, chars, speed, duration, trigger]);

  return <div ref={ref} className={className} />;
}

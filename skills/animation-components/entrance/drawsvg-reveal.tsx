"use client";

import { useRef, useEffect, ReactNode } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger, DrawSVGPlugin);
}

interface DrawSVGRevealProps {
  children: ReactNode;
  className?: string;
  duration?: number;
  ease?: string;
  scrub?: boolean;
}

export default function DrawSVGReveal({
  children,
  className = "",
  duration = 2,
  ease = "power2.inOut",
  scrub = false,
}: DrawSVGRevealProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const paths = ref.current.querySelectorAll<SVGPathElement>("path[stroke], path[stroke-width]");
    if (paths.length === 0) return;

    const vars: gsap.TweenVars = {
      duration: scrub ? 1 : duration,
      ease,
      drawSVG: "0% 100%",
    };

    if (scrub) {
      vars.scrollTrigger = {
        trigger: ref.current,
        start: "top 85%",
        end: "bottom 15%",
        scrub: true,
      };
    } else {
      vars.scrollTrigger = {
        trigger: ref.current,
        start: "top 85%",
        once: true,
      };
    }

    const tween = gsap.fromTo(
      paths,
      { drawSVG: "0% 0%" },
      vars
    );

    return () => {
      tween.kill();
      ScrollTrigger.getAll().forEach((st) => {
        if (st.trigger === ref.current) st.kill();
      });
    };
  }, [duration, ease, scrub]);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}

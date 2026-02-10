"use client";

import React, { useState, useEffect, useRef } from "react";

interface CountUpProps {
  /** Target number to count up to */
  target: number;
  /** Text appended after the number */
  suffix?: string;
  /** Text prepended before the number */
  prefix?: string;
  /** Animation duration in milliseconds */
  duration?: number;
  /** Number of decimal places */
  decimals?: number;
  /** Additional CSS classes */
  className?: string;
}

export function CountUp({
  target,
  suffix = "",
  prefix = "",
  duration = 2000,
  decimals = 0,
  className,
}: CountUpProps) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const hasAnimated = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true;
          const start = Date.now();
          const tick = () => {
            const elapsed = Date.now() - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setCount(
              decimals > 0
                ? parseFloat((eased * target).toFixed(decimals))
                : Math.round(eased * target)
            );
            if (progress < 1) requestAnimationFrame(tick);
          };
          requestAnimationFrame(tick);
        }
      },
      { threshold: 0.5 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [target, duration, decimals]);

  return (
    <span ref={ref} className={className}>
      {prefix}
      {decimals > 0 ? count.toFixed(decimals) : count}
      {suffix}
    </span>
  );
}

export default CountUp;

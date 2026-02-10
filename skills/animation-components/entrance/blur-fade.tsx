"use client";

import * as React from "react";
import { motion, useInView } from "framer-motion";

interface BlurRevealProps {
  /** Additional CSS classes */
  className?: string;
  /** Content to animate */
  children: React.ReactNode;
  /** Delay before animation starts (seconds) */
  delay?: number;
  /** Animation duration (seconds) */
  duration?: number;
}

export function BlurReveal({
  className,
  children,
  delay = 0,
  duration = 1,
}: BlurRevealProps) {
  const spanRef = React.useRef<HTMLSpanElement | null>(null);
  const isInView: boolean = useInView(spanRef, { once: true });

  return (
    <motion.span
      ref={spanRef}
      initial={{ opacity: 0, filter: "blur(10px)", y: "20%" }}
      animate={isInView ? { opacity: 1, filter: "blur(0px)", y: "0%" } : {}}
      transition={{ duration, delay }}
      className={className ? `inline-block ${className}` : "inline-block"}
    >
      {children}
    </motion.span>
  );
}

export default BlurReveal;

"use client";

import React from "react";
import { motion } from "framer-motion";

interface HoverLiftProps {
  /** Content to wrap with hover-lift effect */
  children: React.ReactNode;
  /** How many pixels to lift on hover (negative = up) */
  lift?: number;
  /** Shadow on hover */
  shadow?: string;
  /** Animation duration (seconds) */
  duration?: number;
  /** Additional CSS classes */
  className?: string;
  /** Inline styles */
  style?: React.CSSProperties;
}

export function HoverLift({
  children,
  lift = -6,
  shadow = "0 20px 40px -12px rgba(0, 0, 0, 0.15)",
  duration = 0.3,
  className,
  style,
}: HoverLiftProps) {
  return (
    <motion.div
      whileHover={{
        y: lift,
        boxShadow: shadow,
        transition: { duration, ease: [0.33, 1, 0.68, 1] },
      }}
      className={className}
      style={style}
    >
      {children}
    </motion.div>
  );
}

export default HoverLift;

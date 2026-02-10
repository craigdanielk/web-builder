"use client";

import React from "react";
import { motion } from "framer-motion";

interface WordRevealProps {
  /** The text to animate word-by-word */
  text: string;
  /** Additional CSS classes */
  className?: string;
  /** Delay before the animation starts (seconds) */
  delay?: number;
  /** Duration per word (seconds) */
  duration?: number;
  /** Stagger between words (seconds) */
  stagger?: number;
}

export function WordReveal({
  text,
  className = "",
  delay = 0,
  duration = 0.55,
  stagger = 0.06,
}: WordRevealProps) {
  const words = text.split(" ");
  return (
    <motion.span
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-60px" }}
      className={className}
    >
      {words.map((word, i) => (
        <span key={i} className="inline-block overflow-hidden mr-[0.25em]">
          <motion.span
            className="inline-block"
            variants={{
              hidden: { y: "110%", opacity: 0 },
              visible: {
                y: 0,
                opacity: 1,
                transition: {
                  duration,
                  delay: delay + i * stagger,
                  ease: [0.33, 1, 0.68, 1],
                },
              },
            }}
          >
            {word}
          </motion.span>
        </span>
      ))}
    </motion.span>
  );
}

export default WordReveal;

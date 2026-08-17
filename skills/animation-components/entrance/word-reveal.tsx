"use client";

import React from "react";
import { motion } from "framer-motion";

export interface WordRevealProps {
  /** The text to animate word-by-word. Ignored when `children` is given. */
  text?: string;
  /**
   * Arbitrary subtree. There are no words to split in a subtree, so children
   * get the same rise-and-fade the individual words get, applied once to the
   * whole block — and a block-level root, because the word-by-word path's
   * <motion.span> cannot legally contain a <section>.
   */
  children?: React.ReactNode;
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
  children,
  className = "",
  delay = 0,
  duration = 0.55,
  stagger = 0.06,
}: WordRevealProps) {
  // Block-wrap path first: this is also the return the injection pipeline's
  // root-tag check reads, and it must find a block element.
  if (children) {
    return (
      <motion.div
        initial={{ y: "8%", opacity: 0 }}
        whileInView={{ y: 0, opacity: 1 }}
        viewport={{ once: true, margin: "-60px" }}
        transition={{ duration, delay, ease: [0.33, 1, 0.68, 1] }}
        className={className}
      >
        {children}
      </motion.div>
    );
  }

  const words = (text ?? "").split(" ");
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

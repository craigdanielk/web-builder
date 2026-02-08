"use client";

import React from "react";
import { motion } from "framer-motion";

const Section07Testimonials: React.FC = () => {
  return (
    <section className="bg-amber-50 py-24">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="mx-auto max-w-3xl text-center"
        >
          {/* Quote Mark */}
          <div className="mb-8">
            <svg
              className="mx-auto w-12 h-12 text-amber-700/30"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10H14.017zM0 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151C7.546 6.068 5.983 8.789 5.983 11H10v10H0z" />
            </svg>
          </div>

          {/* Quote Text */}
          <blockquote
            className="text-2xl sm:text-3xl lg:text-4xl font-bold text-stone-950 leading-snug mb-8"
            style={{ fontFamily: "'DM Serif Display', serif" }}
          >
            I've tried every subscription out there. Turm Kaffee is the first
            one where I genuinely look forward to the delivery — every bag is a
            discovery.
          </blockquote>

          {/* Attribution */}
          <div className="flex flex-col items-center gap-4">
            {/* Avatar Placeholder */}
            <div
              className="w-16 h-16 rounded-full bg-gradient-to-br from-stone-400 to-stone-600"
              aria-label="Portrait of Lena Müller, Connoisseur subscriber"
            />
            <div>
              <p
                className="text-base font-medium text-stone-950"
                style={{ fontFamily: "'DM Sans', sans-serif" }}
              >
                Lena Müller
              </p>
              <p
                className="text-sm text-stone-500"
                style={{ fontFamily: "'DM Sans', sans-serif" }}
              >
                Connoisseur subscriber since 2023 — Zürich
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default Section07Testimonials;

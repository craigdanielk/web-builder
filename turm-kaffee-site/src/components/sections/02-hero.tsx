"use client";

import React from "react";
import { motion } from "framer-motion";

const Section02Hero: React.FC = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background Image Placeholder */}
      <div
        className="absolute inset-0 bg-gradient-to-br from-stone-900 via-stone-800 to-amber-950"
        aria-label="Dark moody photograph of Turm Kaffee roastery interior with warm lighting"
      />
      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/40 to-black/30" />

      <div className="relative z-10 mx-auto max-w-7xl px-6 lg:px-8 py-24 text-center">
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="mb-6 text-sm uppercase tracking-[0.25em] text-amber-400/90"
          style={{ fontFamily: "'DM Sans', sans-serif" }}
        >
          Specialty Coffee Roasters — Zürich
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
          className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold leading-tight text-white"
          style={{ fontFamily: "'DM Serif Display', serif" }}
        >
          Single Origin,
          <br />
          Roasted in Zürich
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
          className="mx-auto mt-6 max-w-2xl text-lg sm:text-xl text-white/80 leading-relaxed"
          style={{ fontFamily: "'DM Sans', sans-serif" }}
        >
          We travel to the source, build relationships with farmers, and roast
          every batch by hand. From Ethiopia to your cup — no shortcuts, no
          compromises.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.3 }}
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <a
            href="#products"
            className="rounded-lg bg-amber-700 px-8 py-4 text-base font-medium text-white shadow-lg transition-all duration-300 hover:bg-amber-800 hover:shadow-xl hover:-translate-y-0.5"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          >
            Explore Our Roasts
          </a>
          <a
            href="#pricing"
            className="rounded-lg border border-white/30 px-8 py-4 text-base font-medium text-white transition-all duration-300 hover:bg-white/10 hover:border-white/50"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          >
            Start a Subscription
          </a>
        </motion.div>
      </div>

      {/* Scroll Indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2, duration: 0.6 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
      >
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          className="w-6 h-10 rounded-full border-2 border-white/30 flex items-start justify-center p-1.5"
        >
          <div className="w-1.5 h-2.5 rounded-full bg-white/60" />
        </motion.div>
      </motion.div>
    </section>
  );
};

export default Section02Hero;

"use client";

import { motion } from "framer-motion";

/**
 * HERO | full-bleed-overlay
 * Parameterized section template — brand tokens injected at build time.
 *
 * Token placeholders (replaced by orchestrator):
 *   {{brand.bg_primary}}    → e.g. "stone-50"
 *   {{brand.text_heading}}  → e.g. "stone-950"
 *   {{brand.text_primary}}  → e.g. "stone-900"
 *   {{brand.accent}}        → e.g. "amber-700"
 *   {{brand.accent_hover}}  → e.g. "amber-800"
 *   {{brand.heading_font}}  → e.g. "DM Serif Display"
 *   {{brand.body_font}}     → e.g. "DM Sans"
 */

interface HeroProps {
  headline?: string;
  subheadline?: string;
  ctaText?: string;
  ctaHref?: string;
  backgroundImage?: string;
}

export default function Section01HERO({
  headline = "Crafted with Passion, Served with Purpose",
  subheadline = "Discover artisan products made with generations of expertise and the finest ingredients.",
  ctaText = "Explore Our Collection",
  ctaHref = "#collection",
  backgroundImage = "/images/hero-bg.jpg",
}: HeroProps) {
  return (
    <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden">
      {/* Background with overlay */}
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: `url(${backgroundImage})` }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/40 to-black/70" />

      {/* Content */}
      <div className="relative z-10 max-w-4xl mx-auto px-6 text-center">
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="text-4xl md:text-6xl lg:text-7xl font-bold text-white leading-tight tracking-tight"
          style={{ fontFamily: "var(--font-heading, '{{brand.heading_font}}')" }}
        >
          {headline}
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
          className="mt-6 text-lg md:text-xl text-white/90 max-w-2xl mx-auto leading-relaxed"
          style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
        >
          {subheadline}
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
          className="mt-10 flex flex-col sm:flex-row gap-4 justify-center"
        >
          <a
            href={ctaHref}
            className={`
              inline-flex items-center justify-center
              px-8 py-4 text-base font-semibold
              bg-{{brand.accent}} hover:bg-{{brand.accent_hover}}
              text-white rounded-lg
              transition-all duration-300 ease-out
              hover:shadow-lg hover:-translate-y-0.5
            `}
          >
            {ctaText}
          </a>
          <a
            href="#about"
            className="inline-flex items-center justify-center px-8 py-4 text-base font-semibold text-white border-2 border-white/30 hover:border-white/60 rounded-lg transition-all duration-300 backdrop-blur-sm"
          >
            Our Story
          </a>
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2, duration: 0.6 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
      >
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ repeat: Infinity, duration: 2 }}
          className="w-6 h-10 border-2 border-white/40 rounded-full flex justify-center pt-2"
        >
          <div className="w-1 h-2 bg-white/60 rounded-full" />
        </motion.div>
      </motion.div>
    </section>
  );
}

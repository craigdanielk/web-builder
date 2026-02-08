"use client";

import React from "react";
import { motion } from "framer-motion";

const Section03About: React.FC = () => {
  return (
    <section id="about" className="bg-stone-50 py-24">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Image Side */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          >
            <div
              className="aspect-[4/5] rounded-xl bg-gradient-to-br from-stone-800 via-stone-700 to-amber-900 shadow-2xl"
              aria-label="Interior of Turm Kaffee roastery — copper roasting drum with warm overhead lighting, raw brick walls, bags of green coffee beans stacked in the background"
            />
          </motion.div>

          {/* Text Side */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
            className="flex flex-col gap-6"
          >
            <p
              className="text-sm uppercase tracking-[0.2em] text-amber-700 font-medium"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            >
              Our Story
            </p>

            <h2
              className="text-3xl sm:text-4xl lg:text-5xl font-bold text-stone-950 leading-tight"
              style={{ fontFamily: "'DM Serif Display', serif" }}
            >
              Coffee Is a Craft.
              <br />
              We Treat It That Way.
            </h2>

            <div
              className="flex flex-col gap-4 text-stone-600 text-base sm:text-lg leading-relaxed"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            >
              <p>
                Turm Kaffee was born in a small Zürich workshop in 2018 with a
                simple conviction: great coffee starts at the source. We don't
                buy from brokers. We travel to Ethiopia, Colombia, and Guatemala
                to meet the farmers who grow our beans.
              </p>
              <p>
                Every relationship is direct. Every batch is small. We roast on a
                vintage Probat drum roaster — slow and careful — because rushing
                the process means losing the story each bean carries with it.
              </p>
              <p>
                Swiss precision meets artisan craft. We take coffee seriously so
                you can enjoy it simply.
              </p>
            </div>

            <div className="mt-2">
              <a
                href="#how-it-works"
                className="inline-flex items-center gap-2 text-amber-700 font-medium text-base transition-colors duration-300 hover:text-amber-800"
                style={{ fontFamily: "'DM Sans', sans-serif" }}
              >
                See how we source our beans
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 8l4 4m0 0l-4 4m4-4H3"
                  />
                </svg>
              </a>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};

export default Section03About;

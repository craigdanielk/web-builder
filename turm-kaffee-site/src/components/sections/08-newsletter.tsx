"use client";

import React from "react";
import { motion } from "framer-motion";

const Section08Newsletter: React.FC = () => {
  return (
    <section className="bg-stone-50 py-24">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="mx-auto max-w-2xl text-center"
        >
          <h2
            className="text-3xl sm:text-4xl font-bold text-stone-950 mb-4"
            style={{ fontFamily: "'DM Serif Display', serif" }}
          >
            Stay in the Loop
          </h2>

          <p
            className="text-stone-500 text-base sm:text-lg mb-8"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          >
            Roasting tips, origin stories, and first access to new beans.
            No spam — just coffee.
          </p>

          <form
            onSubmit={(e) => e.preventDefault()}
            className="flex flex-col sm:flex-row gap-3 max-w-lg mx-auto"
          >
            <input
              type="email"
              placeholder="your@email.com"
              required
              className="flex-1 rounded-lg border border-stone-200 bg-white px-5 py-3.5 text-base text-stone-900 placeholder:text-stone-400 outline-none transition-all duration-300 focus:border-amber-700 focus:ring-2 focus:ring-amber-700/20"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            />
            <button
              type="submit"
              className="rounded-lg bg-amber-700 px-8 py-3.5 text-base font-medium text-white transition-all duration-300 hover:bg-amber-800 hover:shadow-lg whitespace-nowrap"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            >
              Subscribe
            </button>
          </form>

          <p
            className="mt-4 text-xs text-stone-400"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          >
            Join 2,400+ coffee lovers. Unsubscribe anytime.
          </p>
        </motion.div>
      </div>
    </section>
  );
};

export default Section08Newsletter;

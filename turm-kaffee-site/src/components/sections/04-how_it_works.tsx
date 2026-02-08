"use client";

import React from "react";
import { motion } from "framer-motion";

const steps = [
  {
    number: "01",
    title: "We Travel to Origin",
    description:
      "Every year we visit our partner farms in Ethiopia, Colombia, and Guatemala. We taste, we learn, and we choose beans that tell a story. No brokers, no middlemen — just real relationships built over shared meals and long conversations.",
    detail: "Direct Trade",
  },
  {
    number: "02",
    title: "Small-Batch Roasting",
    description:
      "Back in our Zürich roastery, each lot is profiled and roasted on our Probat drum roaster. Small batches mean we can treat every origin differently — bringing out the blueberry in our Yirgacheffe, the caramel in our Huila, the chocolate in our Antigua.",
    detail: "Roasted Weekly",
  },
  {
    number: "03",
    title: "Fresh to Your Door",
    description:
      "We roast on Tuesdays and ship on Wednesdays. Your beans arrive within days of roasting — not weeks, not months. Subscribers get first access to seasonal lots and limited releases before they hit the shop.",
    detail: "Ships in 48h",
  },
];

const Section04HowItWorks: React.FC = () => {
  return (
    <section id="how-it-works" className="bg-white py-24">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="text-center mb-16 lg:mb-20"
        >
          <p
            className="text-sm uppercase tracking-[0.2em] text-amber-700 font-medium mb-4"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          >
            From Source to Cup
          </p>
          <h2
            className="text-3xl sm:text-4xl lg:text-5xl font-bold text-stone-950"
            style={{ fontFamily: "'DM Serif Display', serif" }}
          >
            The Journey of Every Bean
          </h2>
        </motion.div>

        {/* Timeline */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12 relative">
          {/* Connecting Line (desktop only) */}
          <div className="hidden md:block absolute top-12 left-[16.67%] right-[16.67%] h-px bg-stone-200" />

          {steps.map((step, index) => (
            <motion.div
              key={step.number}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{
                duration: 0.6,
                ease: [0.22, 1, 0.36, 1],
                delay: index * 0.1,
              }}
              className="relative flex flex-col items-center text-center"
            >
              {/* Step Number Circle */}
              <div className="relative z-10 flex h-24 w-24 items-center justify-center rounded-full bg-stone-50 border-2 border-stone-200 mb-8">
                <span
                  className="text-2xl font-bold text-amber-700"
                  style={{ fontFamily: "'DM Serif Display', serif" }}
                >
                  {step.number}
                </span>
              </div>

              {/* Detail Badge */}
              <span
                className="mb-4 inline-block rounded-lg bg-amber-50 px-3 py-1 text-xs font-medium uppercase tracking-wider text-amber-700"
                style={{ fontFamily: "'DM Sans', sans-serif" }}
              >
                {step.detail}
              </span>

              {/* Title */}
              <h3
                className="text-xl sm:text-2xl font-bold text-stone-950 mb-4"
                style={{ fontFamily: "'DM Serif Display', serif" }}
              >
                {step.title}
              </h3>

              {/* Description */}
              <p
                className="text-stone-500 text-base leading-relaxed max-w-sm"
                style={{ fontFamily: "'DM Sans', sans-serif" }}
              >
                {step.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Section04HowItWorks;

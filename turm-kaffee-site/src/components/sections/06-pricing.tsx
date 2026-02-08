"use client";

import React from "react";
import { motion } from "framer-motion";

const plans = [
  {
    name: "Explorer",
    price: "CHF 24",
    interval: "/ month",
    description:
      "A rotating single-origin bean, chosen by our roaster each month. The perfect way to discover new flavours without commitment.",
    features: [
      "250g freshly roasted beans",
      "New single-origin every month",
      "Roaster's tasting notes included",
      "Free shipping across Switzerland",
      "Pause or cancel anytime",
    ],
    cta: "Start Exploring",
    highlighted: false,
  },
  {
    name: "Connoisseur",
    price: "CHF 42",
    interval: "/ week",
    description:
      "For the dedicated coffee lover. A curated 500g bag every week — always fresh, always interesting. First access to limited lots.",
    features: [
      "500g freshly roasted beans",
      "Weekly curated selection",
      "First access to seasonal & limited lots",
      "Tasting notes + brewing guide",
      "Free express shipping",
      "10% off all shop purchases",
    ],
    cta: "Go Connoisseur",
    highlighted: true,
  },
];

const Section06Pricing: React.FC = () => {
  return (
    <section id="pricing" className="bg-white py-24">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="text-center mb-16"
        >
          <p
            className="text-sm uppercase tracking-[0.2em] text-amber-700 font-medium mb-4"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          >
            Subscriptions
          </p>
          <h2
            className="text-3xl sm:text-4xl lg:text-5xl font-bold text-stone-950 mb-4"
            style={{ fontFamily: "'DM Serif Display', serif" }}
          >
            Fresh Coffee, On Your Schedule
          </h2>
          <p
            className="mx-auto max-w-xl text-stone-500 text-base sm:text-lg"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          >
            No contracts, no minimums. Pause or cancel with a click.
          </p>
        </motion.div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {plans.map((plan, index) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{
                duration: 0.6,
                ease: [0.22, 1, 0.36, 1],
                delay: index * 0.1,
              }}
              className={`relative rounded-xl border-2 p-8 lg:p-10 transition-all duration-300 hover:shadow-xl hover:-translate-y-1 ${
                plan.highlighted
                  ? "border-amber-700 bg-amber-50/30"
                  : "border-stone-200 bg-white"
              }`}
            >
              {/* Recommended Badge */}
              {plan.highlighted && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                  <span
                    className="inline-block rounded-lg bg-amber-700 px-4 py-1.5 text-xs font-medium text-white uppercase tracking-wider"
                    style={{ fontFamily: "'DM Sans', sans-serif" }}
                  >
                    Most Popular
                  </span>
                </div>
              )}

              {/* Plan Header */}
              <div className="mb-8">
                <h3
                  className="text-xl font-bold text-stone-950 mb-2"
                  style={{ fontFamily: "'DM Serif Display', serif" }}
                >
                  {plan.name}
                </h3>
                <p
                  className="text-stone-500 text-sm leading-relaxed"
                  style={{ fontFamily: "'DM Sans', sans-serif" }}
                >
                  {plan.description}
                </p>
              </div>

              {/* Price */}
              <div className="mb-8 flex items-baseline gap-1">
                <span
                  className="text-4xl font-bold text-stone-950"
                  style={{ fontFamily: "'DM Serif Display', serif" }}
                >
                  {plan.price}
                </span>
                <span
                  className="text-stone-500 text-base"
                  style={{ fontFamily: "'DM Sans', sans-serif" }}
                >
                  {plan.interval}
                </span>
              </div>

              {/* Features */}
              <ul className="mb-8 flex flex-col gap-3">
                {plan.features.map((feature) => (
                  <li
                    key={feature}
                    className="flex items-start gap-3"
                  >
                    <svg
                      className="w-5 h-5 text-amber-700 mt-0.5 flex-shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    <span
                      className="text-stone-600 text-sm"
                      style={{ fontFamily: "'DM Sans', sans-serif" }}
                    >
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <a
                href="#"
                className={`block w-full rounded-lg px-6 py-4 text-center text-base font-medium transition-all duration-300 ${
                  plan.highlighted
                    ? "bg-amber-700 text-white hover:bg-amber-800 shadow-lg hover:shadow-xl"
                    : "bg-stone-900 text-white hover:bg-stone-800"
                }`}
                style={{ fontFamily: "'DM Sans', sans-serif" }}
              >
                {plan.cta}
              </a>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Section06Pricing;

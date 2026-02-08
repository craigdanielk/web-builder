"use client";

import React from "react";
import { motion } from "framer-motion";

const beans = [
  {
    name: "Yirgacheffe Kochere",
    origin: "Ethiopia",
    roast: "Light",
    notes: "Blueberry, jasmine, lemon zest",
    description:
      "Washed process from the Kochere district. Bright and floral with a clean, tea-like body. Our most delicate roast.",
    price: "CHF 18",
    weight: "250g",
  },
  {
    name: "Huila Supremo",
    origin: "Colombia",
    roast: "Medium",
    notes: "Caramel, red apple, hazelnut",
    description:
      "From the high-altitude farms of Huila. Sweet and balanced with a creamy mouthfeel. A crowd favourite.",
    price: "CHF 17",
    weight: "250g",
  },
  {
    name: "Antigua Pastoral",
    origin: "Guatemala",
    roast: "Medium-Dark",
    notes: "Dark chocolate, brown sugar, walnut",
    description:
      "Volcanic soil, shade-grown in the Antigua valley. Rich and full-bodied with a lingering cocoa finish.",
    price: "CHF 19",
    weight: "250g",
  },
  {
    name: "Sidamo Natural",
    origin: "Ethiopia",
    roast: "Light-Medium",
    notes: "Strawberry, wine, dark honey",
    description:
      "Natural process from Sidamo. Fruit-forward and complex — like no coffee you've tasted before.",
    price: "CHF 20",
    weight: "250g",
  },
  {
    name: "Nariño Microlot",
    origin: "Colombia",
    roast: "Medium",
    notes: "Mandarin, toffee, almond",
    description:
      "Single-farm microlot from Nariño. Citrus brightness with a sweet, syrupy body. Limited availability.",
    price: "CHF 22",
    weight: "250g",
  },
  {
    name: "Seasonal Blend",
    origin: "Rotating Origins",
    roast: "Medium",
    notes: "Balanced, approachable, evolving",
    description:
      "Our roaster's pick — a blend that changes with the seasons. Always balanced, always interesting, always fresh.",
    price: "CHF 15",
    weight: "250g",
  },
];

const Section05ProductShowcase: React.FC = () => {
  return (
    <section id="products" className="bg-stone-50 py-24">
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
            Our Beans
          </p>
          <h2
            className="text-3xl sm:text-4xl lg:text-5xl font-bold text-stone-950 mb-4"
            style={{ fontFamily: "'DM Serif Display', serif" }}
          >
            Every Bean Has a Story
          </h2>
          <p
            className="mx-auto max-w-xl text-stone-500 text-base sm:text-lg"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          >
            Single origin, direct trade, roasted fresh every Tuesday in Zürich.
          </p>
        </motion.div>

        {/* Product Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {beans.map((bean, index) => (
            <motion.div
              key={bean.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{
                duration: 0.6,
                ease: [0.22, 1, 0.36, 1],
                delay: index * 0.1,
              }}
              className="group relative"
            >
              <div className="rounded-xl bg-white border border-stone-200 overflow-hidden transition-all duration-300 hover:shadow-xl hover:-translate-y-1">
                {/* Product Image Placeholder */}
                <div
                  className="aspect-square bg-gradient-to-br from-stone-800 via-stone-700 to-amber-900 relative overflow-hidden"
                  aria-label={`${bean.name} coffee beans from ${bean.origin} — dark moody product photography`}
                >
                  {/* Origin Badge */}
                  <div className="absolute top-4 left-4">
                    <span
                      className="inline-block rounded-lg bg-black/50 backdrop-blur-sm px-3 py-1.5 text-xs font-medium text-white uppercase tracking-wider"
                      style={{ fontFamily: "'DM Sans', sans-serif" }}
                    >
                      {bean.origin}
                    </span>
                  </div>

                  {/* Hover Overlay */}
                  <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center p-6">
                    <div className="text-center">
                      <p
                        className="text-white/90 text-sm leading-relaxed mb-4"
                        style={{ fontFamily: "'DM Sans', sans-serif" }}
                      >
                        {bean.description}
                      </p>
                      <button
                        className="rounded-lg bg-amber-700 px-6 py-2.5 text-sm font-medium text-white transition-colors duration-300 hover:bg-amber-800"
                        style={{ fontFamily: "'DM Sans', sans-serif" }}
                      >
                        Add to Bag
                      </button>
                    </div>
                  </div>
                </div>

                {/* Card Content */}
                <div className="p-6">
                  <div className="flex items-start justify-between mb-2">
                    <h3
                      className="text-lg font-bold text-stone-950"
                      style={{ fontFamily: "'DM Serif Display', serif" }}
                    >
                      {bean.name}
                    </h3>
                    <span
                      className="text-amber-700 font-medium text-sm whitespace-nowrap ml-4"
                      style={{ fontFamily: "'DM Sans', sans-serif" }}
                    >
                      {bean.price}
                    </span>
                  </div>

                  <p
                    className="text-stone-500 text-sm mb-3"
                    style={{ fontFamily: "'DM Sans', sans-serif" }}
                  >
                    {bean.notes}
                  </p>

                  <div className="flex items-center gap-3">
                    <span
                      className="inline-block rounded-lg bg-stone-100 px-2.5 py-1 text-xs font-medium text-stone-600"
                      style={{ fontFamily: "'DM Sans', sans-serif" }}
                    >
                      {bean.roast}
                    </span>
                    <span
                      className="text-xs text-stone-400"
                      style={{ fontFamily: "'DM Sans', sans-serif" }}
                    >
                      {bean.weight}
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Section05ProductShowcase;

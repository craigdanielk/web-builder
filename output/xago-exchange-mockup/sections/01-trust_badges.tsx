"use client";

Can't write file, no perm. Code below — copy as needed.

```tsx
import React from "react";
import { motion } from "framer-motion";
import { Shield, Lock, Globe, Layers } from "lucide-react";

const regulators = [
  { name: "FSCA Licensed", icon: Shield },
  { name: "FICA Compliant", icon: Lock },
  { name: "ISO 27001 Custody", icon: Layers },
  { name: "Cross-Border Authorized", icon: Globe },
];

const rails = [
  { label: "XRP Ledger" },
  { label: "USDC" },
  { label: "USDT" },
  { label: "ZAR / USD / GBP / EUR" },
];

const Section01TRUSTBADGES: React.FC = () => {
  return (
    <section className="bg-white py-20 px-6" aria-labelledby="trust-heading">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className="text-center mb-12"
        >
          <p className="text-sky-700 text-sm font-semibold tracking-wide uppercase mb-2">
            Custody-grade infrastructure
          </p>
          <h2 id="trust-heading" className="text-2xl sm:text-3xl font-bold text-sky-800">
            Regulated. Audited. Built for institutional volume.
          </h2>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={{ visible: { transition: { staggerChildren: 0.1 } } }}
          className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-14"
        >
          {regulators.map(({ name, icon: Icon }) => (
            <motion.div
              key={name}
              variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              whileHover={{ y: -2 }}
              className="flex flex-col items-center gap-3 rounded-xl border border-sky-100 bg-white px-4 py-6 text-center shadow-sm"
            >
              <Icon className="w-6 h-6 text-sky-700 transition-colors duration-200" />
              <span className="text-sm font-medium text-sky-800">{name}</span>
            </motion.div>
          ))}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.2, ease: "easeOut", delay: 0.1 }}
          className="rounded-2xl bg-sky-800 px-6 py-8 sm:px-10 sm:py-10"
        >
          <p className="text-sky-100 text-xs font-semibold uppercase tracking-wide mb-5 text-center">
            Settlement rails
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {rails.map((rail) => (
              <span
                key={rail.label}
                className="rounded-full bg-sky-700 px-5 py-2.5 text-sm font-medium text-white transition-colors duration-200 hover:bg-sky-700/80"
              >
                {rail.label}
              </span>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default Section01TRUSTBADGES;

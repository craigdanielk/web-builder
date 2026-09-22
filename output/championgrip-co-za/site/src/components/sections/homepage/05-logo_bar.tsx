"use client";

import React from 'react';
import { motion } from 'framer-motion';

const Section05LOGOBAR: React.FC = () => {
  const stockists = [
    'Bowls South Africa',
    'Cape Town Lawn Bowls',
    'Durban Sports Club',
    'Johannesburg Bowls',
    'Port Elizabeth Club',
    'Pretoria Bowls Centre',
    'Western Province Bowls',
    'Eastern Cape Sports',
    'KZN Bowls Association',
    'Gauteng Bowls League',
  ];

  const duplicatedStockists = [...stockists, ...stockists];

  return (
    <section className="py-20 bg-white border-t border-b border-slate-200 overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mb-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
          className="text-center"
        >
          <p className="text-sm font-bold text-blue-600 uppercase tracking-wider mb-2">
            Trusted by Leading Clubs
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-slate-900" style={{ fontFamily: 'Inter' }}>
            Available at Premium Stockists
          </h2>
        </motion.div>
      </div>

      <div className="relative">
        <div className="absolute left-0 top-0 bottom-0 w-32 bg-gradient-to-r from-white to-transparent z-10"></div>
        <div className="absolute right-0 top-0 bottom-0 w-32 bg-gradient-to-l from-white to-transparent z-10"></div>

        <motion.div
          className="flex"
          animate={{
            x: [0, -50 * stockists.length],
          }}
          transition={{
            x: {
              repeat: Infinity,
              repeatType: "loop",
              duration: 40,
              ease: "linear",
            },
          }}
        >
          {duplicatedStockists.map((stockist, index) => (
            <div
              key={index}
              className="flex-shrink-0 mx-8 flex items-center justify-center"
              style={{ minWidth: '200px' }}
            >
              <div className="text-lg font-bold text-slate-400 whitespace-nowrap" style={{ fontFamily: 'Inter' }}>
                {stockist}
              </div>
            </div>
          ))}
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1], delay: 0.2 }}
        className="mt-12 text-center"
      >
        <a
          href="#"
          className="inline-flex items-center gap-2 text-blue-600 font-bold hover:text-slate-900 transition-colors duration-300"
          style={{ fontFamily: 'Inter' }}
        >
          Become a Stockist
          <svg
            className="w-5 h-5"
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
      </motion.div>
    </section>
  );
};

export default Section05LOGOBAR;
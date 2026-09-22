"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Sparkles, Play } from 'lucide-react';

const Section01HERO: React.FC = () => {
  const fadeUpVariant = {
    hidden: { opacity: 0, y: 30 },
    visible: { opacity: 1, y: 0 }
  };

  const staggerContainer = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2
      }
    }
  };

  return (
    <section className="relative bg-gradient-to-br from-slate-50 to-white overflow-hidden">
      {/* Background Accent */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-[#0c8558]/5" />
      
      {/* Decorative Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(12,133,88,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(12,133,88,0.03)_1px,transparent_1px)] bg-[size:4rem_4rem]" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          
          {/* Left Content */}
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            className="space-y-6"
          >
            {/* Kicker */}
            <motion.div 
              variants={fadeUpVariant}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg shadow-sm"
            >
              <Sparkles className="w-4 h-4 text-[#0c8558]" />
              <span className="text-sm font-medium text-slate-900" style={{ fontFamily: 'Inter, sans-serif' }}>
                Elevate your game
              </span>
            </motion.div>

            {/* Headline */}
            <motion.h1
              variants={fadeUpVariant}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="text-5xl sm:text-6xl lg:text-7xl font-bold text-slate-900 leading-tight tracking-tight"
              style={{ fontFamily: 'Raleway, sans-serif' }}
            >
              Champion Grip<br />& Polish
            </motion.h1>

            {/* Claim */}
            <motion.p
              variants={fadeUpVariant}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="text-xl sm:text-2xl text-slate-900 font-medium"
              style={{ fontFamily: 'Open Sans, sans-serif' }}
            >
              The world's first aerosol bowls grip enhancer
            </motion.p>

            {/* Features List */}
            <motion.div
              variants={fadeUpVariant}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="space-y-3 pt-4"
            >
              {[
                'Confident Control',
                'Safety-first aerosol formula',
                'Professional-grade performance'
              ].map((feature, index) => (
                <div key={index} className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-[#0c8558] rounded-full" />
                  <span className="text-lg text-slate-900" style={{ fontFamily: 'Open Sans, sans-serif' }}>
                    {feature}
                  </span>
                </div>
              ))}
            </motion.div>

            {/* CTA Buttons */}
            <motion.div
              variants={fadeUpVariant}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-wrap gap-4 pt-6"
            >
              <motion.button
                whileHover={{ scale: 1.02, y: -2, boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)' }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="inline-flex items-center gap-2 px-8 py-4 bg-[#0c8558] text-white rounded-lg font-semibold shadow-lg hover:bg-[#0a6f48] transition-colors"
                style={{ fontFamily: 'Inter, sans-serif' }}
              >
                Shop Now
                <ArrowRight className="w-5 h-5" />
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02, y: -2 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="inline-flex items-center gap-2 px-8 py-4 bg-white text-slate-900 border-2 border-slate-200 rounded-lg font-semibold hover:border-slate-300 transition-colors"
                style={{ fontFamily: 'Inter, sans-serif' }}
              >
                <Play className="w-5 h-5" />
                Watch Demo
              </motion.button>
            </motion.div>
          </motion.div>

          {/* Right Product Showcase */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.3 }}
            className="relative"
          >
            {/* Product Card */}
            <motion.div
              whileHover={{ y: -8 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="relative bg-white rounded-xl shadow-xl p-8 border border-slate-200"
            >
              {/* Price Badge */}
              <div className="absolute top-6 right-6 bg-[#eac61e] text-slate-900 px-4 py-2 rounded-lg font-bold shadow-lg z-10">
                <span className="text-2xl" style={{ fontFamily: 'Raleway, sans-serif' }}>R85.00</span>
              </div>

              {/* Product Image */}
              <div className="aspect-square bg-gradient-to-br from-slate-50 to-white rounded-xl overflow-hidden mb-6 flex items-center justify-center">
                <img
                  src="https://championgrip.co.za/wp-content/uploads/2023/09/0001-1733163681977838814_png-4.png"
                  alt="Champion Grip Spray 120ml"
                  className="w-full h-full object-contain p-8"
                />
              </div>

              {/* Product Info */}
              <div className="space-y-4">
                <h3 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Raleway, sans-serif' }}>
                  Champion Grip Spray
                </h3>
                <p className="text-slate-900 text-lg" style={{ fontFamily: 'Open Sans, sans-serif' }}>
                  120ml professional formula
                </p>

                {/* Specs */}
                <div className="grid grid-cols-2 gap-4 pt-4">
                  <div className="text-center p-4 bg-slate-50 rounded-lg">
                    <div className="text-3xl font-bold text-[#0c8558]" style={{ fontFamily: 'Raleway, sans-serif' }}>120ml</div>
                    <div className="text-sm text-slate-900 mt-1" style={{ fontFamily: 'Open Sans, sans-serif' }}>Volume</div>
                  </div>
                  <div className="text-center p-4 bg-slate-50 rounded-lg">
                    <div className="text-3xl font-bold text-[#0c8558]" style={{ fontFamily: 'Raleway, sans-serif' }}>Aerosol</div>
                    <div className="text-sm text-slate-900 mt-1" style={{ fontFamily: 'Open Sans, sans-serif' }}>Format</div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Floating Badge */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.6 }}
              className="absolute -bottom-6 -left-6 bg-blue-600 text-white px-6 py-4 rounded-xl shadow-xl"
            >
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                <span className="font-bold" style={{ fontFamily: 'Inter, sans-serif' }}>World's First</span>
              </div>
            </motion.div>
          </motion.div>

        </div>
      </div>
    </section>
  );
};

export default Section01HERO;
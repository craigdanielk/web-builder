"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Check, X, Sparkles, Shield, Zap } from 'lucide-react';

const Section03COMPARISON: React.FC = () => {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        duration: 0.5,
        ease: [0.25, 0.1, 0.25, 1]
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
        ease: [0.25, 0.1, 0.25, 1]
      }
    }
  };

  const features = [
    { name: 'Aerosol Delivery', icon: Sparkles },
    { name: 'Safety-First Formula', icon: Shield },
    { name: 'Quick Drying', icon: Zap },
    { name: 'Professional Grade', icon: Check },
    { name: 'Non-Sticky Finish', icon: Check },
    { name: 'Weather Resistant', icon: Shield }
  ];

  return (
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={containerVariants}
          className="text-center mb-12"
        >
          <motion.h2
            variants={itemVariants}
            className="text-4xl font-bold text-slate-900 mb-4"
            style={{ fontFamily: 'Raleway, sans-serif' }}
          >
            Why Choose Champion Grip?
          </motion.h2>
          <motion.p
            variants={itemVariants}
            className="text-lg text-slate-900 max-w-2xl mx-auto"
            style={{ fontFamily: 'Open Sans, sans-serif' }}
          >
            Compare the world's first aerosol bowls grip enhancer with traditional grip methods
          </motion.p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={containerVariants}
          className="grid md:grid-cols-3 gap-6"
        >
          <motion.div
            variants={itemVariants}
            className="bg-slate-50 rounded-xl p-6 border-2 border-slate-200"
          >
            <h3
              className="text-xl font-bold text-slate-900 mb-6 text-center"
              style={{ fontFamily: 'Raleway, sans-serif' }}
            >
              Traditional Methods
            </h3>
            <ul className="space-y-4" style={{ fontFamily: 'Open Sans, sans-serif' }}>
              <li className="flex items-start gap-6">
                <X className="w-6 h-6 text-slate-400 flex-shrink-0 mt-1" />
                <span className="text-slate-900">Messy application</span>
              </li>
              <li className="flex items-start gap-6">
                <X className="w-6 h-6 text-slate-400 flex-shrink-0 mt-1" />
                <span className="text-slate-900">Inconsistent coverage</span>
              </li>
              <li className="flex items-start gap-6">
                <X className="w-6 h-6 text-slate-400 flex-shrink-0 mt-1" />
                <span className="text-slate-900">Sticky residue</span>
              </li>
              <li className="flex items-start gap-6">
                <X className="w-6 h-6 text-slate-400 flex-shrink-0 mt-1" />
                <span className="text-slate-900">Long drying time</span>
              </li>
              <li className="flex items-start gap-6">
                <X className="w-6 h-6 text-slate-400 flex-shrink-0 mt-1" />
                <span className="text-slate-900">Difficult to control</span>
              </li>
              <li className="flex items-start gap-6">
                <X className="w-6 h-6 text-slate-400 flex-shrink-0 mt-1" />
                <span className="text-slate-900">Not weather resistant</span>
              </li>
            </ul>
          </motion.div>

          <motion.div
            variants={itemVariants}
            whileHover={{
              y: -8,
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
              transition: { duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }
            }}
            className="rounded-xl p-6 border-2 relative overflow-hidden"
            style={{
              backgroundColor: '#0c8558',
              borderColor: '#0c8558'
            }}
          >
            <div className="absolute top-0 right-0 px-4 py-2 rounded-bl-lg" style={{ backgroundColor: '#eac61e' }}>
              <span className="text-sm font-bold text-slate-900" style={{ fontFamily: 'Raleway, sans-serif' }}>
                RECOMMENDED
              </span>
            </div>
            <h3
              className="text-xl font-bold text-white mb-2 text-center mt-8"
              style={{ fontFamily: 'Raleway, sans-serif' }}
            >
              Champion Grip Spray
            </h3>
            <p className="text-center text-white mb-6" style={{ fontFamily: 'Open Sans, sans-serif' }}>
              120ml | R85.00
            </p>
            <ul className="space-y-4" style={{ fontFamily: 'Open Sans, sans-serif' }}>
              {features.map((feature, index) => {
                const IconComponent = feature.icon;
                return (
                  <li key={index} className="flex items-start gap-6">
                    <IconComponent className="w-6 h-6 flex-shrink-0 mt-1" style={{ color: '#eac61e' }} />
                    <span className="text-white">{feature.name}</span>
                  </li>
                );
              })}
            </ul>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="mt-6 w-full py-3 rounded-lg font-bold text-slate-900"
              style={{
                backgroundColor: '#eac61e',
                fontFamily: 'Raleway, sans-serif'
              }}
            >
              Get Champion Grip
            </motion.button>
          </motion.div>

          <motion.div
            variants={itemVariants}
            className="bg-slate-50 rounded-xl p-6 border-2 border-slate-200"
          >
            <h3
              className="text-xl font-bold text-slate-900 mb-6 text-center"
              style={{ fontFamily: 'Raleway, sans-serif' }}
            >
              Other Sprays
            </h3>
            <ul className="space-y-4" style={{ fontFamily: 'Open Sans, sans-serif' }}>
              <li className="flex items-start gap-6">
                <Check className="w-6 h-6 flex-shrink-0 mt-1" style={{ color: '#0c8558' }} />
                <span className="text-slate-900">Spray application</span>
              </li>
              <li className="flex items-start gap-6">
                <X className="w-6 h-6 text-slate-400 flex-shrink-0 mt-1" />
                <span className="text-slate-900">Generic formulas</span>
              </li>
              <li className="flex items-start gap-6">
                <X className="w-6 h-6 text-slate-400 flex-shrink-0 mt-1" />
                <span className="text-slate-900">Variable quality</span>
              </li>
              <li className="flex items-start gap-6">
                <X className="w-6 h-6 text-slate-400 flex-shrink-0 mt-1" />
                <span className="text-slate-900">Not bowls-specific</span>
              </li>
              <li className="flex items-start gap-6">
                <X className="w-6 h-6 text-slate-400 flex-shrink-0 mt-1" />
                <span className="text-slate-900">Untested ingredients</span>
              </li>
              <li className="flex items-start gap-6">
                <X className="w-6 h-6 text-slate-400 flex-shrink-0 mt-1" />
                <span className="text-slate-900">Inconsistent results</span>
              </li>
            </ul>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1], delay: 0.3 }}
          className="mt-12 text-center"
        >
          <p
            className="text-lg text-slate-900 max-w-3xl mx-auto"
            style={{ fontFamily: 'Open Sans, sans-serif' }}
          >
            Developed by industrial chemist Werner Kunte, Champion Grip combines decades of chemical expertise with 
            bowls-specific innovation. The world's first aerosol bowls grip enhancer designed for confident control.
          </p>
        </motion.div>
      </div>
    </section>
  );
};

export default Section03COMPARISON;
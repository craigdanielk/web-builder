"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Shield, Zap, Check, X } from 'lucide-react';

const Section03COMPARISON: React.FC = () => {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        duration: 0.5,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: 'easeOut' },
    },
  };

  const features = [
    { label: 'Aerosol Technology', traditional: false, champion: true },
    { label: 'Quick Application', traditional: false, champion: true },
    { label: 'Safety-First Design', traditional: false, champion: true },
    { label: 'Consistent Grip', traditional: false, champion: true },
    { label: 'No Residue Buildup', traditional: false, champion: true },
    { label: 'Professional Grade', traditional: true, champion: true },
  ];

  return (
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          variants={containerVariants}
          className="space-y-6"
        >
          <motion.div variants={itemVariants} className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-slate-50 rounded-lg mb-4">
              <Sparkles className="w-5 h-5 text-blue-600" />
              <span className="text-sm font-semibold text-slate-900" style={{ fontFamily: 'Inter' }}>
                Why Champion Grip?
              </span>
            </div>
            <h2 className="text-4xl lg:text-5xl font-bold text-slate-900 mb-4" style={{ fontFamily: 'Inter' }}>
              Innovation vs. Traditional
            </h2>
            <p className="text-lg text-slate-900" style={{ fontFamily: 'Inter' }}>
              See how our aerosol technology compares to conventional grip solutions
            </p>
          </motion.div>

          <motion.div variants={itemVariants} className="overflow-x-auto">
            <div className="min-w-[600px]">
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="col-span-1"></div>
                <div className="bg-slate-50 rounded-xl p-6 text-center">
                  <h3 className="text-xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Inter' }}>
                    Traditional Methods
                  </h3>
                  <Shield className="w-8 h-8 text-slate-900 mx-auto" />
                </div>
                <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl p-6 text-center">
                  <h3 className="text-xl font-bold text-white mb-2" style={{ fontFamily: 'Inter' }}>
                    Champion Grip
                  </h3>
                  <Zap className="w-8 h-8 text-yellow-400 mx-auto" />
                </div>
              </div>

              <div className="space-y-3">
                {features.map((feature, index) => (
                  <motion.div
                    key={index}
                    variants={itemVariants}
                    className="grid grid-cols-3 gap-4 items-center bg-slate-50 rounded-lg p-4"
                  >
                    <div className="font-semibold text-slate-900" style={{ fontFamily: 'Inter' }}>
                      {feature.label}
                    </div>
                    <div className="text-center">
                      {feature.traditional ? (
                        <Check className="w-6 h-6 text-blue-600 mx-auto" />
                      ) : (
                        <X className="w-6 h-6 text-slate-900 mx-auto" />
                      )}
                    </div>
                    <div className="text-center">
                      <Check className="w-6 h-6 text-blue-600 mx-auto" />
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
};

export default Section03COMPARISON;
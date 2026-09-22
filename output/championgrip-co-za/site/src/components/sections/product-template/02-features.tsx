"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Shield, Gauge, Zap, Lock, Eye, Sparkles } from 'lucide-react';

const Section02FEATURES: React.FC = () => {
  const specs = [
    { icon: Shield, label: 'Formula Type', value: 'Safety-First Aerosol' },
    { icon: Gauge, label: 'Volume', value: '120ml' },
    { icon: Zap, label: 'Application', value: 'Instant Spray Delivery' },
    { icon: Lock, label: 'Grip Duration', value: 'Extended Control' },
    { icon: Eye, label: 'Finish', value: 'Clear, Non-Residue' },
    { icon: Sparkles, label: 'Innovation', value: "World's First Aerosol Bowls Grip" }
  ];

  const features = [
    {
      title: 'Confident Control',
      description: 'Enhanced grip for precision delivery and consistent performance in all conditions'
    },
    {
      title: 'Safety-First Aerosol',
      description: 'Easy application with controlled spray that ensures even coverage without waste'
    },
    {
      title: 'Polish & Protection',
      description: 'Dual-action formula that grips and polishes for optimal bowl performance'
    }
  ];

  return (
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="font-bold text-3xl sm:text-4xl lg:text-5xl text-slate-900 mb-4" style={{ fontFamily: 'Inter' }}>
            How Champion Grip Elevates Your Game
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto" style={{ fontFamily: 'Inter' }}>
            Precision-engineered specifications for professional bowlers who demand the best
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="bg-slate-50 rounded-xl p-8 mb-12 border border-slate-200"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {specs.map((spec, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="flex items-start gap-4"
              >
                <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-blue-600 flex items-center justify-center">
                  <spec.icon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 mb-1" style={{ fontFamily: 'Inter' }}>
                    {spec.label}
                  </h3>
                  <p className="text-slate-600 text-sm" style={{ fontFamily: 'Inter' }}>
                    {spec.value}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ y: -4, boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1)' }}
              className="bg-white p-6 rounded-xl border border-slate-200 transition-all"
            >
              <h3 className="font-bold text-xl text-slate-900 mb-3" style={{ fontFamily: 'Inter' }}>
                {feature.title}
              </h3>
              <p className="text-slate-600" style={{ fontFamily: 'Inter' }}>
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Section02FEATURES;
"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Shield, Lock, Gauge, Globe, Layers, Cpu } from 'lucide-react';

const Section08TRUSTBADGES: React.FC = () => {
  const badges = [
    {
      icon: Shield,
      label: 'Safe Formulation',
      description: 'Tested & Certified'
    },
    {
      icon: Gauge,
      label: 'Premium Quality',
      description: 'Laboratory Standard'
    },
    {
      icon: Globe,
      label: 'Shipped Nationwide',
      description: 'South Africa Wide'
    },
    {
      icon: Lock,
      label: 'Secure Payments',
      description: 'Protected Checkout'
    },
    {
      icon: Layers,
      label: 'German Heritage',
      description: 'Since 1957'
    },
    {
      icon: Cpu,
      label: 'Innovative Formula',
      description: 'First Aerosol Grip'
    }
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 0.5,
        ease: [0.25, 0.1, 0.25, 1],
        staggerChildren: 0.1
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

  return (
    <section className="py-20 bg-slate-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="border-y border-slate-200 py-12"
        >
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 lg:gap-8">
            {badges.map((badge, index) => {
              const IconComponent = badge.icon;
              return (
                <motion.div
                  key={index}
                  variants={itemVariants}
                  whileHover={{
                    y: -4,
                    transition: { duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }
                  }}
                  className="flex flex-col items-center text-center gap-3"
                >
                  <div className="w-12 h-12 rounded-lg bg-white border border-slate-200 flex items-center justify-center">
                    <IconComponent className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <div className="font-bold text-sm text-slate-900 mb-1">
                      {badge.label}
                    </div>
                    <div className="text-xs text-slate-600">
                      {badge.description}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default Section08TRUSTBADGES;
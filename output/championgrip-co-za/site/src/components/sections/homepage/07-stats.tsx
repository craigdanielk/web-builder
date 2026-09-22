"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Target, BarChart3, Activity } from 'lucide-react';

const Section07STATS: React.FC = () => {
  const stats = [
    {
      icon: TrendingUp,
      value: '98',
      suffix: '%',
      label: 'Player Satisfaction',
      description: 'Bowlers trust Champion Grip'
    },
    {
      icon: Target,
      value: '3',
      suffix: 'x',
      label: 'Improved Control',
      description: 'Enhanced grip performance'
    },
    {
      icon: BarChart3,
      value: '120',
      suffix: 'ml',
      label: 'Per Bottle',
      description: 'Long-lasting application'
    },
    {
      icon: Activity,
      value: '65',
      suffix: '+',
      label: 'Years Experience',
      description: 'Chemical expertise since 1957'
    }
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2
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
        ease: [0.25, 0.4, 0.25, 1]
      }
    }
  };

  return (
    <section className="relative py-20 bg-white overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-blue-50 opacity-60" />
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.5, ease: [0.25, 0.4, 0.25, 1] }}
          className="text-center mb-16"
        >
          <h2 className="font-bold text-4xl md:text-5xl text-slate-900 mb-6" style={{ fontFamily: 'Inter' }}>
            Proven Performance
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto" style={{ fontFamily: 'Inter' }}>
            Trusted by bowlers across South Africa for championship-level grip enhancement
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"
        >
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={index}
                variants={itemVariants}
                whileHover={{ 
                  y: -8,
                  boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
                  transition: { duration: 0.5, ease: [0.25, 0.4, 0.25, 1] }
                }}
                className="bg-white rounded-xl border border-slate-200 p-8 text-center shadow-sm"
              >
                <div className="flex justify-center mb-6">
                  <div className="w-14 h-14 rounded-lg bg-blue-50 flex items-center justify-center">
                    <Icon className="w-7 h-7 text-blue-600" />
                  </div>
                </div>
                
                <div className="mb-4">
                  <div className="flex items-baseline justify-center">
                    <span className="font-bold text-5xl text-slate-900" style={{ fontFamily: 'Inter' }}>
                      {stat.value}
                    </span>
                    <span className="font-bold text-3xl text-blue-600 ml-1" style={{ fontFamily: 'Inter' }}>
                      {stat.suffix}
                    </span>
                  </div>
                </div>

                <h3 className="font-bold text-lg text-slate-900 mb-2" style={{ fontFamily: 'Inter' }}>
                  {stat.label}
                </h3>
                
                <p className="text-slate-600 text-sm" style={{ fontFamily: 'Inter' }}>
                  {stat.description}
                </p>
              </motion.div>
            );
          })}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.5, ease: [0.25, 0.4, 0.25, 1], delay: 0.4 }}
          className="mt-16 text-center"
        >
          <p className="text-slate-600 text-sm" style={{ fontFamily: 'Inter' }}>
            Backed by decades of chemical expertise and trusted by professional bowlers
          </p>
        </motion.div>
      </div>
    </section>
  );
};

export default Section07STATS;
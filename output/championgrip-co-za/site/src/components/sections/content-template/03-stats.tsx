"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Target, BarChart3, TrendingUp, Hash } from 'lucide-react';

const Section03STATS: React.FC = () => {
  const stats = [
    {
      icon: Target,
      value: '120ml',
      label: 'Optimized Formula',
      description: 'Perfect application size'
    },
    {
      icon: Hash,
      value: 'R85',
      label: 'Affordable Excellence',
      description: 'Premium quality grip'
    },
    {
      icon: TrendingUp,
      value: '1st',
      label: 'World Innovation',
      description: 'Aerosol bowls grip enhancer'
    },
    {
      icon: BarChart3,
      value: '65+',
      label: 'Years Experience',
      description: 'Industrial chemistry heritage'
    }
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        duration: 0.5,
        ease: [0.4, 0, 0.2, 1]
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
        ease: [0.4, 0, 0.2, 1]
      }
    }
  };

  return (
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
          className="text-center mb-12"
        >
          <h2 className="font-bold text-4xl text-slate-900 mb-4" style={{ fontFamily: 'Inter' }}>
            Proven Performance
          </h2>
          <p className="text-lg text-slate-900 max-w-2xl mx-auto" style={{ fontFamily: 'Inter' }}>
            Champion Grip combines decades of chemical expertise with innovative aerosol technology
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
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
                  transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] }
                }}
                className="bg-slate-50 rounded-xl p-8 text-center border border-slate-200 shadow-sm"
              >
                <div className="flex justify-center mb-4">
                  <div className="w-16 h-16 rounded-lg flex items-center justify-center" style={{ backgroundColor: '#0c8558' }}>
                    <Icon className="w-8 h-8 text-white" />
                  </div>
                </div>
                <div className="mb-2">
                  <div className="text-4xl font-bold text-slate-900 mb-1" style={{ fontFamily: 'Inter', color: '#0c8558' }}>
                    {stat.value}
                  </div>
                  <div className="text-xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Inter' }}>
                    {stat.label}
                  </div>
                </div>
                <p className="text-slate-900" style={{ fontFamily: 'Inter' }}>
                  {stat.description}
                </p>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
};

export default Section03STATS;
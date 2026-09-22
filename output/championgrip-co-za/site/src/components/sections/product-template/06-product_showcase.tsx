"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Zap, Star } from 'lucide-react';

const Section06PRODUCTSHOWCASE: React.FC = () => {
  const accessories = [
    {
      icon: Sparkles,
      title: 'Microfiber Polish Cloth',
      description: 'Premium cloth designed specifically for Champion Grip maintenance. Keep your bowls gleaming between applications.',
      price: 'R45.00',
      gradient: 'from-blue-50 to-slate-50',
      iconColor: 'text-blue-600',
      iconBg: 'bg-blue-100',
      hoverScale: 1.05,
      hoverRotate: 2
    },
    {
      icon: Zap,
      title: 'Travel Carry Case',
      description: 'Compact protective case fits your 120ml Champion Grip spray perfectly. Tournament-ready portability.',
      price: 'R125.00',
      gradient: 'from-emerald-50 to-slate-50',
      iconColor: 'text-emerald-600',
      iconBg: 'bg-emerald-100',
      hoverScale: 1.03,
      hoverRotate: -2
    },
    {
      icon: Star,
      title: 'Club Pack Bundle',
      description: '6x Champion Grip 120ml cans at a special rate. Perfect for clubs and serious players who demand consistent performance.',
      price: 'R450.00',
      gradient: 'from-yellow-50 to-slate-50',
      iconColor: 'text-yellow-600',
      iconBg: 'bg-yellow-100',
      hoverScale: 1.04,
      hoverRotate: 1
    }
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        duration: 0.5
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
    <section className="py-20 bg-white relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-slate-50 to-white pointer-events-none" />
      
      <div className="container mx-auto px-4 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
          className="text-center mb-12"
        >
          <h2 className="font-bold text-4xl md:text-5xl text-slate-900 mb-4" style={{ fontFamily: 'Inter' }}>
            Complete Your Kit
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto" style={{ fontFamily: 'Inter' }}>
            Essential accessories to maximize your Champion Grip experience and maintain peak performance
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {accessories.map((accessory, index) => {
            const Icon = accessory.icon;
            return (
              <motion.article
                key={index}
                variants={itemVariants}
                whileHover={{
                  scale: accessory.hoverScale,
                  rotate: accessory.hoverRotate,
                  y: -8,
                  boxShadow: '0 20px 40px -12px rgba(0, 0, 0, 0.15)',
                  transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] }
                }}
                className={`bg-gradient-to-br ${accessory.gradient} rounded-xl p-8 border border-slate-200 shadow-sm`}
              >
                <motion.div
                  whileHover={{ rotate: 360 }}
                  transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
                  className={`${accessory.iconBg} w-16 h-16 rounded-lg flex items-center justify-center mb-6`}
                >
                  <Icon className={`w-8 h-8 ${accessory.iconColor}`} />
                </motion.div>
                
                <h3 className="font-bold text-2xl text-slate-900 mb-3" style={{ fontFamily: 'Inter' }}>
                  {accessory.title}
                </h3>
                
                <p className="text-slate-600 mb-6 leading-relaxed" style={{ fontFamily: 'Inter' }}>
                  {accessory.description}
                </p>
                
                <div className="flex items-center justify-between">
                  <span className="text-3xl font-bold text-slate-900" style={{ fontFamily: 'Inter' }}>
                    {accessory.price}
                  </span>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
                    style={{ fontFamily: 'Inter' }}
                  >
                    Add to Cart
                  </motion.button>
                </div>
              </motion.article>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
};

export default Section06PRODUCTSHOWCASE;
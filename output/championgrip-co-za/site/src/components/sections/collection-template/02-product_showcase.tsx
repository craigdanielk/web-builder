"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Eye, Sparkles, Zap } from 'lucide-react';

const Section02PRODUCTSHOWCASE: React.FC = () => {
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

  return (
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
          className="text-center mb-12"
        >
          <h2 className="text-4xl lg:text-5xl font-bold text-slate-900 mb-4" style={{ fontFamily: 'Raleway, sans-serif' }}>
            Champion Grip Products
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto" style={{ fontFamily: 'Open Sans, sans-serif' }}>
            Discover the world's first aerosol bowls grip enhancer designed to elevate your game
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          <motion.article
            variants={itemVariants}
            whileHover={{ y: -8, transition: { duration: 0.3 } }}
            className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm hover:shadow-xl transition-shadow duration-500"
          >
            <div className="relative h-64 bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center overflow-hidden">
              <motion.div
                initial={{ scale: 1 }}
                whileHover={{ scale: 1.05 }}
                transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
                className="relative w-full h-full flex items-center justify-center"
              >
                <img
                  src="https://championgrip.co.za/wp-content/uploads/2023/09/0001-1733163681977838814_png-4.png"
                  alt="Champion Grip Spray 120ml"
                  className="w-auto h-full object-contain p-6"
                />
              </motion.div>
              <motion.div
                className="absolute top-4 right-4 bg-white/90 backdrop-blur-sm rounded-lg px-3 py-1 flex items-center gap-2"
                initial={{ opacity: 0, x: 10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.3, duration: 0.5 }}
              >
                <Sparkles className="w-4 h-4" style={{ color: '#0c8558' }} />
                <span className="text-sm font-semibold text-slate-900" style={{ fontFamily: 'Raleway, sans-serif' }}>Featured</span>
              </motion.div>
            </div>
            <div className="p-6">
              <h3 className="text-2xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Raleway, sans-serif' }}>
                Champion Grip Spray 120ml
              </h3>
              <p className="text-slate-600 mb-4" style={{ fontFamily: 'Open Sans, sans-serif' }}>
                The world's first aerosol bowls grip enhancer for confident control and elevated performance
              </p>
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-3xl font-bold text-slate-900" style={{ fontFamily: 'Raleway, sans-serif' }}>
                    R85.00
                  </span>
                </div>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="px-6 py-3 rounded-lg font-semibold text-white transition-all duration-300"
                  style={{ 
                    backgroundColor: '#0c8558',
                    fontFamily: 'Raleway, sans-serif'
                  }}
                >
                  View Details
                </motion.button>
              </div>
            </div>
          </motion.article>

          <motion.article
            variants={itemVariants}
            whileHover={{ y: -8, transition: { duration: 0.3 } }}
            className="bg-gradient-to-br from-blue-50 to-slate-50 border border-slate-200 rounded-xl p-8 shadow-sm hover:shadow-xl transition-shadow duration-500"
          >
            <motion.div
              className="w-16 h-16 rounded-xl flex items-center justify-center mb-6"
              style={{ backgroundColor: '#0c8558' }}
              whileHover={{ rotate: 360 }}
              transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
            >
              <Eye className="w-8 h-8 text-white" />
            </motion.div>
            <h3 className="text-2xl font-bold text-slate-900 mb-3" style={{ fontFamily: 'Raleway, sans-serif' }}>
              Confident Control
            </h3>
            <p className="text-slate-600 leading-relaxed" style={{ fontFamily: 'Open Sans, sans-serif' }}>
              Experience unmatched precision and control with our scientifically formulated grip enhancer that adapts to every condition
            </p>
          </motion.article>

          <motion.article
            variants={itemVariants}
            whileHover={{ y: -8, transition: { duration: 0.3 } }}
            className="bg-gradient-to-br from-slate-50 to-blue-50 border border-slate-200 rounded-xl p-8 shadow-sm hover:shadow-xl transition-shadow duration-500"
          >
            <motion.div
              className="w-16 h-16 rounded-xl flex items-center justify-center mb-6"
              style={{ backgroundColor: '#295c49' }}
              whileHover={{ scale: 1.1 }}
              transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
            >
              <Zap className="w-8 h-8 text-white" />
            </motion.div>
            <h3 className="text-2xl font-bold text-slate-900 mb-3" style={{ fontFamily: 'Raleway, sans-serif' }}>
              Safety-First Aerosol
            </h3>
            <p className="text-slate-600 leading-relaxed" style={{ fontFamily: 'Open Sans, sans-serif' }}>
              Innovative aerosol technology ensures even application, quick drying, and safe use for all bowlers at every level
            </p>
          </motion.article>
        </motion.div>
      </div>
    </section>
  );
};

export default Section02PRODUCTSHOWCASE;
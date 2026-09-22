"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Zap, Eye } from 'lucide-react';

const Section10NEWSLETTER: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitted(true);
    setTimeout(() => setIsSubmitted(false), 3000);
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 0.5,
        ease: [0.4, 0, 0.2, 1],
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
        ease: [0.4, 0, 0.2, 1]
      }
    }
  };

  return (
    <section className="py-20 bg-slate-50 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-[#0c8558]/5"></div>
      
      <div className="max-w-4xl mx-auto px-6 relative z-10">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="bg-white rounded-xl p-8 md:p-12 shadow-lg border border-slate-200"
        >
          <div className="flex flex-col md:flex-row items-start md:items-center gap-6 mb-8">
            <motion.div
              variants={itemVariants}
              className="flex-shrink-0"
            >
              <div className="w-16 h-16 rounded-lg bg-gradient-to-br from-[#0c8558] to-[#295c49] flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
            </motion.div>

            <div className="flex-grow">
              <motion.h2
                variants={itemVariants}
                className="font-bold text-3xl md:text-4xl text-slate-900 mb-2"
                style={{ fontFamily: 'Inter' }}
              >
                Stay in the Game
              </motion.h2>
              <motion.p
                variants={itemVariants}
                className="text-lg text-slate-900"
                style={{ fontFamily: 'Inter' }}
              >
                Get product updates, tips from pro bowlers, and early access to new Champion Grip innovations
              </motion.p>
            </div>
          </div>

          <motion.div
            variants={itemVariants}
            className="flex flex-wrap gap-4 mb-8"
          >
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-lg bg-blue-600/10 flex items-center justify-center flex-shrink-0">
                <Zap className="w-5 h-5 text-blue-600" />
              </div>
              <span className="text-slate-900" style={{ fontFamily: 'Inter' }}>New product launches</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-lg bg-blue-600/10 flex items-center justify-center flex-shrink-0">
                <Eye className="w-5 h-5 text-blue-600" />
              </div>
              <span className="text-slate-900" style={{ fontFamily: 'Inter' }}>Exclusive discounts</span>
            </div>
          </motion.div>

          <motion.form
            variants={itemVariants}
            onSubmit={handleSubmit}
            className="flex flex-col sm:flex-row gap-3"
          >
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email address"
              required
              className="flex-grow px-6 py-4 rounded-lg border border-slate-200 text-slate-900 placeholder:text-slate-900/50 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all duration-300"
              style={{ fontFamily: 'Inter' }}
            />
            <motion.button
              type="submit"
              whileHover={{
                y: -2,
                boxShadow: '0 10px 25px -5px rgba(8, 133, 88, 0.3)',
                transition: { duration: 0.3, ease: [0.4, 0, 0.2, 1] }
              }}
              whileTap={{ scale: 0.98 }}
              className="px-8 py-4 bg-[#0c8558] text-white font-bold rounded-lg shadow-md hover:bg-[#295c49] transition-colors duration-500"
              style={{ fontFamily: 'Inter' }}
              disabled={isSubmitted}
            >
              {isSubmitted ? 'Subscribed!' : 'Subscribe'}
            </motion.button>
          </motion.form>

          <motion.p
            variants={itemVariants}
            className="text-sm text-slate-900/60 mt-4"
            style={{ fontFamily: 'Inter' }}
          >
            We respect your privacy. Unsubscribe at any time. No spam, just grip.
          </motion.p>
        </motion.div>
      </div>
    </section>
  );
};

export default Section10NEWSLETTER;
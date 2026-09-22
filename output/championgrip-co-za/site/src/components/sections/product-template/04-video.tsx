"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Play, CheckCircle, Sparkles, Eye } from 'lucide-react';

const Section04VIDEO: React.FC = () => {
  const [isPlaying, setIsPlaying] = React.useState(false);

  const features = [
    {
      icon: Sparkles,
      title: 'Quick Application',
      description: 'Apply in seconds before your game'
    },
    {
      icon: Eye,
      title: 'Visual Guide',
      description: 'See exactly how to achieve perfect grip'
    },
    {
      icon: CheckCircle,
      title: 'Pro Tips',
      description: 'Learn from expert bowlers'
    }
  ];

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
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid lg:grid-cols-2 gap-6 lg:gap-12 items-center"
        >
          <motion.div variants={itemVariants} className="order-2 lg:order-1">
            <div className="space-y-6">
              <div>
                <motion.p
                  variants={itemVariants}
                  className="text-sm font-bold tracking-wider uppercase mb-2"
                  style={{ color: '#0c8558' }}
                >
                  Watch & Learn
                </motion.p>
                <motion.h2
                  variants={itemVariants}
                  className="text-4xl sm:text-5xl font-bold text-slate-900 mb-4"
                  style={{ fontFamily: 'Inter' }}
                >
                  How to Apply Champion Grip
                </motion.h2>
                <motion.p
                  variants={itemVariants}
                  className="text-lg text-slate-600"
                  style={{ fontFamily: 'Inter' }}
                >
                  Watch our quick demonstration to see how easy it is to enhance your grip and elevate your game. Perfect application every time.
                </motion.p>
              </div>

              <motion.div variants={itemVariants} className="space-y-4">
                {features.map((feature, index) => (
                  <motion.div
                    key={index}
                    variants={itemVariants}
                    whileHover={{ x: 4 }}
                    className="flex items-start gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200 transition-all duration-500"
                  >
                    <div
                      className="p-2 rounded-lg flex-shrink-0"
                      style={{ backgroundColor: '#0c8558' }}
                    >
                      <feature.icon className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900 mb-1" style={{ fontFamily: 'Inter' }}>
                        {feature.title}
                      </h3>
                      <p className="text-sm text-slate-600" style={{ fontFamily: 'Inter' }}>
                        {feature.description}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </motion.div>

              <motion.div variants={itemVariants} className="pt-2">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="px-6 py-3 rounded-lg font-bold text-white transition-all duration-500"
                  style={{ backgroundColor: '#0c8558', fontFamily: 'Inter' }}
                >
                  Book A Demo
                </motion.button>
              </motion.div>
            </div>
          </motion.div>

          <motion.div variants={itemVariants} className="order-1 lg:order-2">
            <div className="relative aspect-video rounded-xl overflow-hidden bg-slate-900 shadow-2xl">
              <div className="absolute inset-0 bg-gradient-to-br from-slate-800 via-slate-900 to-slate-950">
                <div className="absolute inset-0 opacity-20">
                  <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-blue-600 via-transparent to-transparent animate-pulse"></div>
                </div>
              </div>
              
              <div className="absolute inset-0 flex items-center justify-center">
                <img
                  src="https://championgrip.co.za/wp-content/uploads/2023/09/0001-1733163681977838814_png-4.png"
                  alt="Champion Grip Spray"
                  className="w-48 h-auto object-contain opacity-40"
                />
              </div>

              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsPlaying(!isPlaying)}
                className="absolute inset-0 flex items-center justify-center group cursor-pointer"
                aria-label="Play video"
              >
                <div className="relative">
                  <motion.div
                    animate={{
                      scale: [1, 1.2, 1],
                      opacity: [0.5, 0, 0.5]
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: "easeInOut"
                    }}
                    className="absolute inset-0 rounded-full"
                    style={{ backgroundColor: '#0c8558' }}
                  ></motion.div>
                  <div
                    className="relative w-20 h-20 rounded-full flex items-center justify-center shadow-xl transition-all duration-500 group-hover:shadow-2xl"
                    style={{ backgroundColor: '#0c8558' }}
                  >
                    <Play className="w-8 h-8 text-white ml-1" fill="white" />
                  </div>
                </div>
              </motion.button>

              <div className="absolute bottom-4 left-4 right-4 flex items-center gap-4">
                <div className="h-1 flex-1 bg-slate-700 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ backgroundColor: '#0c8558' }}
                    initial={{ width: '0%' }}
                    animate={{ width: isPlaying ? '100%' : '0%' }}
                    transition={{ duration: 30, ease: 'linear' }}
                  ></motion.div>
                </div>
                <span className="text-xs text-white font-medium" style={{ fontFamily: 'Inter' }}>
                  2:15
                </span>
              </div>
            </div>

            <motion.p
              variants={itemVariants}
              className="mt-4 text-sm text-slate-600 text-center"
              style={{ fontFamily: 'Inter' }}
            >
              Step-by-step application guide for optimal results
            </motion.p>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
};

export default Section04VIDEO;
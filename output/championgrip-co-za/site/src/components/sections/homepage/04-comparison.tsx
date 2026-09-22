"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Check, X, Sparkles, Shield, Zap } from 'lucide-react';
import BorderBeam from '@/components/animations/border-beam';

const Section04COMPARISON: React.FC = () => {
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

  const features = [
    {
      name: 'Application Method',
      icon: Sparkles,
      championGrip: 'Safety-first aerosol spray',
      traditional: 'Messy hand application',
      sticky: 'Sticky residue buildup'
    },
    {
      name: 'Grip Enhancement',
      icon: Zap,
      championGrip: 'Instant superior grip',
      traditional: 'Inconsistent coverage',
      sticky: 'Temporary grip only'
    },
    {
      name: 'Polish Effect',
      icon: Sparkles,
      championGrip: 'Dual-action grip & polish',
      traditional: 'No polishing properties',
      sticky: 'Dulls bowl finish'
    },
    {
      name: 'Hygiene',
      icon: Shield,
      championGrip: 'No-touch application',
      traditional: 'Direct hand contact required',
      sticky: 'Unhygienic application'
    },
    {
      name: 'Consistency',
      icon: Zap,
      championGrip: 'Even, controlled coating',
      traditional: 'Uneven results',
      sticky: 'Variable performance'
    },
    {
      name: 'Residue',
      icon: Shield,
      championGrip: 'Clean, residue-free',
      traditional: 'Requires cleanup',
      sticky: 'Sticky buildup over time'
    }
  ];

  return (
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={containerVariants}
          className="space-y-6"
        >
          <motion.div variants={itemVariants} className="text-center max-w-3xl mx-auto mb-12">
            <h2 className="text-4xl sm:text-5xl font-bold text-slate-900 mb-4" style={{ fontFamily: 'Inter' }}>
              Why Champion Grip Wins
            </h2>
            <p className="text-lg text-slate-600" style={{ fontFamily: 'Inter' }}>
              Compare Champion Grip's innovative aerosol formula against traditional grip enhancers and sticky sprays
            </p>
          </motion.div>

          <motion.div variants={itemVariants} className="relative">
            <div className="overflow-x-auto">
              <div className="inline-block min-w-full align-middle">
                <div className="overflow-hidden rounded-xl border border-slate-200 relative">
                  <BorderBeam />
                  <table className="min-w-full divide-y divide-slate-200">
                    <thead className="bg-slate-50">
                      <tr>
                        <th scope="col" className="py-6 px-6 text-left text-sm font-bold text-slate-900" style={{ fontFamily: 'Inter' }}>
                          Feature
                        </th>
                        <th scope="col" className="py-6 px-6 text-center text-sm font-bold text-white bg-gradient-to-br from-[#0c8558] to-[#295c49]" style={{ fontFamily: 'Inter' }}>
                          <div className="flex items-center justify-center gap-2">
                            <Sparkles className="w-5 h-5" />
                            <span>Champion Grip</span>
                          </div>
                        </th>
                        <th scope="col" className="py-6 px-6 text-center text-sm font-bold text-slate-900" style={{ fontFamily: 'Inter' }}>
                          Traditional Methods
                        </th>
                        <th scope="col" className="py-6 px-6 text-center text-sm font-bold text-slate-900" style={{ fontFamily: 'Inter' }}>
                          Sticky Sprays
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 bg-white">
                      {features.map((feature, index) => {
                        const Icon = feature.icon;
                        return (
                          <motion.tr
                            key={feature.name}
                            initial={{ opacity: 0, x: -20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true, margin: "-50px" }}
                            transition={{
                              duration: 0.5,
                              delay: index * 0.1,
                              ease: [0.4, 0, 0.2, 1]
                            }}
                            className="hover:bg-slate-50 transition-colors duration-300"
                          >
                            <td className="py-6 px-6 text-sm font-semibold text-slate-900" style={{ fontFamily: 'Inter' }}>
                              <div className="flex items-center gap-3">
                                <Icon className="w-5 h-5 text-[#0c8558]" />
                                <span>{feature.name}</span>
                              </div>
                            </td>
                            <td className="py-6 px-6 text-center text-sm text-slate-900 bg-gradient-to-br from-[#0c8558]/5 to-[#295c49]/5" style={{ fontFamily: 'Inter' }}>
                              <div className="flex items-center justify-center gap-2">
                                <Check className="w-5 h-5 text-[#0c8558] flex-shrink-0" />
                                <span className="font-medium">{feature.championGrip}</span>
                              </div>
                            </td>
                            <td className="py-6 px-6 text-center text-sm text-slate-600" style={{ fontFamily: 'Inter' }}>
                              <div className="flex items-center justify-center gap-2">
                                <X className="w-5 h-5 text-slate-400 flex-shrink-0" />
                                <span>{feature.traditional}</span>
                              </div>
                            </td>
                            <td className="py-6 px-6 text-center text-sm text-slate-600" style={{ fontFamily: 'Inter' }}>
                              <div className="flex items-center justify-center gap-2">
                                <X className="w-5 h-5 text-slate-400 flex-shrink-0" />
                                <span>{feature.sticky}</span>
                              </div>
                            </td>
                          </motion.tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div
            variants={itemVariants}
            className="mt-12 text-center"
          >
            <motion.div
              whileHover={{ y: -4, boxShadow: '0 10px 30px rgba(12, 133, 88, 0.2)' }}
              transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
            >
              <a
                href="#contact"
                className="inline-flex items-center gap-2 bg-gradient-to-r from-[#0c8558] to-[#295c49] text-white px-8 py-4 rounded-lg font-bold text-lg shadow-lg"
                style={{ fontFamily: 'Inter' }}
              >
                <Zap className="w-5 h-5" />
                Get Champion Grip Today
              </a>
            </motion.div>
            <p className="mt-6 text-sm text-slate-600" style={{ fontFamily: 'Inter' }}>
              Only R85.00 for 120ml • The world's first aerosol bowls grip enhancer
            </p>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
};

export default Section04COMPARISON;
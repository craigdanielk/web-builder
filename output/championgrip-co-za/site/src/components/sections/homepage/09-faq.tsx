"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, HelpCircle } from 'lucide-react';

interface FAQItem {
  question: string;
  answer: string;
}

const Section09FAQ: React.FC = () => {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const faqs: FAQItem[] = [
    {
      question: "What surfaces is Champion Grip compatible with?",
      answer: "Champion Grip is specifically formulated for lawn bowls and is compatible with all bowl compositions including phenolic resin, melamine, and composite materials. It's safe for use on all manufacturers' bowls including Henselite, Drakes Pride, Taylor, and Aero."
    },
    {
      question: "How long does one 120ml can last?",
      answer: "A single 120ml can of Champion Grip provides approximately 150-200 applications depending on usage. For regular bowlers playing 2-3 times per week, one can typically lasts 3-4 months. The aerosol format ensures consistent application and minimal product waste."
    },
    {
      question: "Is Champion Grip safe for indoor and outdoor use?",
      answer: "Yes, Champion Grip is formulated with a safety-first approach and is suitable for both indoor and outdoor bowling greens. The aerosol formula is non-toxic, odorless, and leaves no residue on greens. It meets all international bowling federation regulations for grip enhancers."
    },
    {
      question: "What is the warranty policy?",
      answer: "Champion Grip comes with a full satisfaction guarantee. If you're not completely satisfied with the product's performance within 30 days of purchase, we offer a full refund. Simply contact us with your proof of purchase. The product has a shelf life of 3 years from manufacture date when stored properly."
    },
    {
      question: "Does Champion Grip leave residue on bowls or greens?",
      answer: "No, Champion Grip is formulated to enhance grip without leaving any sticky residue on your bowls or the green. It absorbs quickly into your hands and evaporates cleanly, leaving only improved grip performance. Regular use will not cause buildup or require special cleaning."
    },
    {
      question: "Can I use Champion Grip in tournament play?",
      answer: "Yes, Champion Grip complies with World Bowls regulations and is approved for use in sanctioned tournament play. The formula contains no banned substances and has been tested to ensure it doesn't alter bowl bias or green characteristics. Many professional bowlers use Champion Grip in competitive play."
    },
    {
      question: "What are the technical specifications?",
      answer: "Champion Grip Spray: 120ml aerosol can, propellant: compressed air (CFC-free), active grip agent: proprietary polymer blend, pH neutral, storage temperature: 5-30°C, flammability: non-flammable, weight: 145g, dimensions: 15cm height × 5cm diameter. Made in South Africa."
    },
    {
      question: "How should I store Champion Grip?",
      answer: "Store Champion Grip in a cool, dry place away from direct sunlight and heat sources. Keep the can upright when not in use. Do not store above 30°C or below 5°C. Keep out of reach of children. Do not puncture or incinerate the can, even when empty."
    }
  ];

  const toggleFAQ = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

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
        ease: [0.4, 0, 0.2, 1]
      }
    }
  };

  return (
    <section className="relative py-20 bg-white overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-50 opacity-60"></div>
      
      <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-full mb-6">
            <HelpCircle className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-4xl sm:text-5xl font-bold text-slate-900 mb-4" style={{ fontFamily: 'Inter' }}>
            Frequently Asked Questions
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto" style={{ fontFamily: 'Inter' }}>
            Everything you need to know about Champion Grip compatibility, warranty, and technical specifications
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="space-y-4"
        >
          {faqs.map((faq, index) => (
            <motion.article
              key={index}
              variants={itemVariants}
              className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-500"
            >
              <button
                onClick={() => toggleFAQ(index)}
                className="w-full text-left px-6 py-5 flex items-center justify-between gap-4 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 transition-colors duration-500"
                aria-expanded={openIndex === index}
              >
                <span className="text-lg font-bold text-slate-900 flex-1" style={{ fontFamily: 'Inter' }}>
                  {faq.question}
                </span>
                <motion.div
                  animate={{ rotate: openIndex === index ? 180 : 0 }}
                  transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
                  className="flex-shrink-0"
                >
                  <ChevronDown className="w-6 h-6 text-slate-600" />
                </motion.div>
              </button>
              
              <AnimatePresence initial={false}>
                {openIndex === index && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="px-6 pb-5 pt-2">
                      <p className="text-slate-600 leading-relaxed" style={{ fontFamily: 'Inter' }}>
                        {faq.answer}
                      </p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.article>
          ))}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1], delay: 0.3 }}
          className="mt-12 text-center bg-slate-50 border border-slate-200 rounded-xl p-8"
        >
          <h3 className="text-xl font-bold text-slate-900 mb-3" style={{ fontFamily: 'Inter' }}>
            Still have questions?
          </h3>
          <p className="text-slate-600 mb-6" style={{ fontFamily: 'Inter' }}>
            Our team is here to help you get the most out of Champion Grip
          </p>
          <motion.a
            href="/contact"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white font-bold rounded-lg shadow-sm hover:bg-blue-700 transition-colors duration-500"
            style={{ fontFamily: 'Inter' }}
          >
            Contact Us
          </motion.a>
        </motion.div>
      </div>
    </section>
  );
};

export default Section09FAQ;
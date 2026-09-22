"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Quote, Star, ChevronLeft, ChevronRight } from 'lucide-react';

const testimonials = [
  {
    id: 1,
    quote: "Champion Grip has transformed my game completely. The aerosol delivery is genius - consistent application every time without the mess of traditional methods.",
    author: "David Mitchell",
    role: "Professional Bowls Player",
    rating: 5,
    location: "Cape Town"
  },
  {
    id: 2,
    quote: "As a coach, I recommend Champion Grip to all my students. The safety-first formula and precise control it provides makes it perfect for players at any level.",
    author: "Sarah Thompson",
    role: "Bowls Coach & Instructor",
    rating: 5,
    location: "Johannesburg"
  },
  {
    id: 3,
    quote: "Werner Kunte's expertise as an industrial chemist really shows. This isn't just another grip product - it's a scientifically engineered solution that actually works.",
    author: "James Robertson",
    role: "Tournament Organizer",
    rating: 5,
    location: "Durban"
  },
  {
    id: 4,
    quote: "The 120ml aerosol format is perfect. Lasts ages, easy to carry in my bowls bag, and the application is so much cleaner than alternatives. Absolute game-changer.",
    author: "Margaret Williams",
    role: "Club Champion",
    rating: 5,
    location: "Pretoria"
  },
  {
    id: 5,
    quote: "I was skeptical at first, but Champion Grip delivers on every promise. Confident control in all weather conditions - it's now an essential part of my kit.",
    author: "Peter van der Merwe",
    role: "Regional Champion",
    rating: 5,
    location: "Port Elizabeth"
  }
];

const Section06TESTIMONIALS: React.FC = () => {
  const [currentIndex, setCurrentIndex] = useState(0);

  const handlePrevious = () => {
    setCurrentIndex((prev) => (prev === 0 ? testimonials.length - 1 : prev - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev === testimonials.length - 1 ? 0 : prev + 1));
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
            What Players Say
          </h2>
          <p className="text-lg text-slate-900 max-w-2xl mx-auto" style={{ fontFamily: 'Inter' }}>
            Trusted by champions across South Africa
          </p>
        </motion.div>

        <div className="max-w-4xl mx-auto relative">
          <AnimatePresence mode="wait">
            <motion.article
              key={currentIndex}
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
              className="bg-white rounded-xl border border-slate-200 p-8 md:p-12 shadow-lg"
            >
              <div className="flex justify-center mb-6">
                <Quote className="w-12 h-12 text-blue-600" />
              </div>

              <div className="flex justify-center gap-1 mb-6">
                {[...Array(testimonials[currentIndex].rating)].map((_, i) => (
                  <Star key={i} className="w-5 h-5 text-yellow-400 fill-yellow-400" />
                ))}
              </div>

              <blockquote className="text-xl md:text-2xl text-slate-900 text-center mb-8 leading-relaxed" style={{ fontFamily: 'Inter' }}>
                "{testimonials[currentIndex].quote}"
              </blockquote>

              <div className="text-center">
                <div className="font-bold text-lg text-slate-900 mb-1" style={{ fontFamily: 'Inter' }}>
                  {testimonials[currentIndex].author}
                </div>
                <div className="text-slate-900" style={{ fontFamily: 'Inter' }}>
                  {testimonials[currentIndex].role}
                </div>
                <div className="text-sm text-slate-900 mt-1" style={{ fontFamily: 'Inter' }}>
                  {testimonials[currentIndex].location}
                </div>
              </div>
            </motion.article>
          </AnimatePresence>

          <div className="flex items-center justify-center gap-4 mt-8">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handlePrevious}
              className="w-12 h-12 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-900 hover:bg-blue-600 hover:text-white hover:border-blue-600 transition-colors"
              aria-label="Previous testimonial"
            >
              <ChevronLeft className="w-6 h-6" />
            </motion.button>

            <div className="flex gap-2">
              {testimonials.map((_, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentIndex(index)}
                  className={`w-2 h-2 rounded-full transition-all ${
                    index === currentIndex
                      ? 'bg-blue-600 w-8'
                      : 'bg-slate-200 hover:bg-slate-900'
                  }`}
                  aria-label={`Go to testimonial ${index + 1}`}
                />
              ))}
            </div>

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleNext}
              className="w-12 h-12 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-900 hover:bg-blue-600 hover:text-white hover:border-blue-600 transition-colors"
              aria-label="Next testimonial"
            >
              <ChevronRight className="w-6 h-6" />
            </motion.button>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1], delay: 0.2 }}
          className="text-center mt-12"
        >
          <p className="text-slate-900 mb-4" style={{ fontFamily: 'Inter' }}>
            Join hundreds of satisfied players across South Africa
          </p>
          <motion.a
            href="/book-a-demo"
            whileHover={{ scale: 1.05, boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)' }}
            whileTap={{ scale: 0.95 }}
            className="inline-block px-8 py-3 bg-blue-600 text-white rounded-lg font-bold transition-shadow"
            style={{ fontFamily: 'Inter' }}
          >
            Try Champion Grip Today
          </motion.a>
        </motion.div>
      </div>
    </section>
  );
};

export default Section06TESTIMONIALS;
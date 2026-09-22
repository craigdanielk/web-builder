"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Star, Quote, ThumbsUp } from 'lucide-react';

const Section05TESTIMONIALS: React.FC = () => {
  const reviews = [
    {
      name: "Johan van der Merwe",
      location: "Cape Town",
      rating: 5,
      date: "2 weeks ago",
      text: "Champion Grip has completely transformed my game. The aerosol application is so convenient and the grip enhancement is immediate. No more slippery bowls!",
      helpful: 12
    },
    {
      name: "Susan Marais",
      location: "Durban",
      rating: 5,
      date: "1 month ago",
      text: "Finally, a grip enhancer that actually works! The spray is easy to apply and dries quickly. My control has improved dramatically since switching to Champion Grip.",
      helpful: 8
    },
    {
      name: "Peter Kowalski",
      location: "Johannesburg",
      rating: 5,
      date: "3 weeks ago",
      text: "As a club champion, I've tried many products. Champion Grip stands out for its consistency and ease of use. The 120ml can lasts ages too.",
      helpful: 15
    },
    {
      name: "Margaret Smith",
      location: "Pretoria",
      rating: 4,
      date: "2 months ago",
      text: "Great product! Works well in all weather conditions. My only wish is that it came in a larger size for frequent users.",
      helpful: 6
    },
    {
      name: "David Naidoo",
      location: "Port Elizabeth",
      rating: 5,
      date: "1 week ago",
      text: "The world's first aerosol grip enhancer lives up to its reputation. Clean application, fantastic grip, and the polish keeps my bowls looking pristine.",
      helpful: 9
    },
    {
      name: "Linda Botha",
      location: "Bloemfontein",
      rating: 5,
      date: "3 weeks ago",
      text: "I was skeptical at first, but Champion Grip exceeded my expectations. The safety-first design and quality results make it worth every cent.",
      helpful: 11
    }
  ];

  const starBreakdown = [
    { stars: 5, count: 142, percentage: 85 },
    { stars: 4, count: 18, percentage: 11 },
    { stars: 3, count: 5, percentage: 3 },
    { stars: 2, count: 2, percentage: 1 },
    { stars: 1, count: 0, percentage: 0 }
  ];

  const averageRating = 4.8;
  const totalReviews = 167;

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
      <div className="container mx-auto px-4 max-w-7xl">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          variants={containerVariants}
          className="grid md:grid-cols-12 gap-6 lg:gap-12"
        >
          {/* Left Column - Star Breakdown */}
          <motion.div variants={itemVariants} className="md:col-span-4">
            <div className="bg-slate-50 rounded-xl p-6 lg:p-8 sticky top-8">
              <div className="flex items-center gap-2 mb-4">
                <Quote className="w-8 h-8 text-blue-600" />
                <h2 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Inter' }}>
                  Customer Reviews
                </h2>
              </div>
              
              <div className="mb-6">
                <div className="flex items-end gap-2 mb-2">
                  <span className="text-5xl font-bold text-slate-900" style={{ fontFamily: 'Inter' }}>
                    {averageRating}
                  </span>
                  <span className="text-slate-600 mb-2" style={{ fontFamily: 'Inter' }}>
                    out of 5
                  </span>
                </div>
                <div className="flex gap-1 mb-2">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className="w-5 h-5 fill-current text-blue-600"
                    />
                  ))}
                </div>
                <p className="text-sm text-slate-600" style={{ fontFamily: 'Inter' }}>
                  Based on {totalReviews} reviews
                </p>
              </div>

              <div className="space-y-3">
                {starBreakdown.map((item) => (
                  <div key={item.stars} className="flex items-center gap-3">
                    <span className="text-sm font-medium text-slate-700 w-8" style={{ fontFamily: 'Inter' }}>
                      {item.stars} <Star className="w-3 h-3 inline" />
                    </span>
                    <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        whileInView={{ width: `${item.percentage}%` }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.5, delay: 0.2, ease: [0.4, 0, 0.2, 1] }}
                        className="h-full bg-blue-600 rounded-full"
                      />
                    </div>
                    <span className="text-sm text-slate-600 w-12 text-right" style={{ fontFamily: 'Inter' }}>
                      {item.percentage}%
                    </span>
                  </div>
                ))}
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="w-full mt-6 bg-blue-600 text-white px-6 py-3 rounded-lg font-bold transition-all duration-300"
                style={{ fontFamily: 'Inter' }}
              >
                Write a Review
              </motion.button>
            </div>
          </motion.div>

          {/* Right Column - Reviews */}
          <div className="md:col-span-8">
            <motion.div variants={containerVariants} className="space-y-6">
              {reviews.map((review, index) => (
                <motion.article
                  key={index}
                  variants={itemVariants}
                  whileHover={{ 
                    y: -4,
                    boxShadow: "0 10px 30px -10px rgba(0, 0, 0, 0.1)",
                    transition: { duration: 0.3 }
                  }}
                  className="bg-slate-50 rounded-xl p-6 border border-slate-200"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold" style={{ fontFamily: 'Inter' }}>
                          {review.name.charAt(0)}
                        </div>
                        <div>
                          <h3 className="font-bold text-slate-900" style={{ fontFamily: 'Inter' }}>
                            {review.name}
                          </h3>
                          <p className="text-sm text-slate-600" style={{ fontFamily: 'Inter' }}>
                            {review.location}
                          </p>
                        </div>
                      </div>
                      <div className="flex gap-1 mb-2">
                        {[...Array(5)].map((_, i) => (
                          <Star
                            key={i}
                            className={`w-4 h-4 ${
                              i < review.rating
                                ? 'fill-current text-blue-600'
                                : 'text-slate-300'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                    <span className="text-sm text-slate-500" style={{ fontFamily: 'Inter' }}>
                      {review.date}
                    </span>
                  </div>

                  <p className="text-slate-700 mb-4 leading-relaxed" style={{ fontFamily: 'Inter' }}>
                    {review.text}
                  </p>

                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      className="flex items-center gap-1 hover:text-blue-600 transition-colors"
                      style={{ fontFamily: 'Inter' }}
                    >
                      <ThumbsUp className="w-4 h-4" />
                      Helpful ({review.helpful})
                    </motion.button>
                  </div>
                </motion.article>
              ))}
            </motion.div>

            <motion.div
              variants={itemVariants}
              className="mt-8 text-center"
            >
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="bg-slate-900 text-white px-8 py-3 rounded-lg font-bold hover:bg-slate-800 transition-colors"
                style={{ fontFamily: 'Inter' }}
              >
                Load More Reviews
              </motion.button>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default Section05TESTIMONIALS;
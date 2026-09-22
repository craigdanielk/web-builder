"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Zap, Eye } from 'lucide-react';

const Section02PRODUCTSHOWCASE: React.FC<{ products?: Array<{ title: string; handle: string; priceRange?: { minVariantPrice: { amount: string; currencyCode: string } }; images?: { edges: Array<{ node: { url: string; altText: string | null } }> } }>; collections?: Array<{ handle: string; title: string; description?: string; image?: { url: string } }> }> = ({ products, collections }) => {
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

  const cardVariants = {
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

  const fallbackProducts = [
    {
      icon: Sparkles,
      title: 'Champion Grip Spray',
      description: 'The world\'s first aerosol bowls grip enhancer. Confident control in a safety-first aerosol format.',
      price: 'R85.00',
      size: '120ml',
      gradient: 'from-emerald-50 to-teal-50',
      iconColor: 'text-emerald-600',
      borderColor: 'border-emerald-200',
      hoverBg: 'hover:bg-emerald-100/50',
      image: 'https://championgrip.co.za/wp-content/uploads/2023/09/0001-1733163681977838814_png-4.png'
    },
    {
      icon: Zap,
      title: 'Professional Formula',
      description: 'Developed by industrial chemist Werner Kunte, combining decades of chemical expertise with bowls performance.',
      gradient: 'from-blue-50 to-slate-100',
      iconColor: 'text-blue-600',
      borderColor: 'border-blue-200',
      hoverBg: 'hover:bg-blue-100/50'
    },
    {
      icon: Eye,
      title: 'Polish & Protect',
      description: 'Dual-action formula that enhances grip while maintaining bowl shine and protecting the surface.',
      gradient: 'from-amber-50 to-yellow-50',
      iconColor: 'text-amber-600',
      borderColor: 'border-amber-200',
      hoverBg: 'hover:bg-amber-100/50'
    }
  ];
  const mappedProducts = products?.length ? Array.from(products, p => ({ name: p.title, price: `${parseFloat(p.priceRange?.minVariantPrice?.amount || '0').toFixed(2)} ${p.priceRange?.minVariantPrice?.currencyCode || ''}`.trim(), image: p.images?.edges?.[0]?.node?.url || '/placeholder.jpg', alt: p.images?.edges?.[0]?.node?.altText || p.title, url: `/products/${p.handle}`, tag: '' })) : null;
  const displayProducts = mappedProducts || fallbackProducts;

  return (
    <section className="py-20 bg-slate-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
          className="text-center mb-12"
        >
          <p className="text-blue-600 font-semibold mb-2 tracking-wide uppercase text-sm">
            Elevate your game
          </p>
          <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-4" style={{ fontFamily: 'Raleway, sans-serif' }}>
            Champion Grip & Polish
          </h2>
          <p className="text-xl text-slate-900 max-w-2xl mx-auto" style={{ fontFamily: 'Open Sans, sans-serif' }}>
            How Champion Grip Elevates Your Game
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {displayProducts.map((product, index) => {
            const Icon = product.icon;
            return (
              <motion.article
                key={index}
                variants={cardVariants}
                whileHover={{
                  y: -8,
                  boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
                  transition: { duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }
                }}
                className={`bg-white rounded-xl border ${product.borderColor} p-6 transition-all duration-500`}
              >
                {product.image && (
                  <div className="mb-6 rounded-lg overflow-hidden bg-gradient-to-br from-slate-100 to-white p-4">
                    <img
                      src={product.image}
                      alt={product.title}
                      className="w-full h-48 object-contain"
                    />
                  </div>
                )}
                
                <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${product.gradient} flex items-center justify-center mb-4`}>
                  <Icon className={`w-6 h-6 ${product.iconColor}`} />
                </div>

                <h3 className="text-2xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Raleway, sans-serif' }}>
                  {product.title}
                </h3>

                {product.price && (
                  <div className="flex items-baseline gap-2 mb-3">
                    <span className="text-3xl font-bold" style={{ color: '#0c8558' }}>
                      {product.price}
                    </span>
                    {product.size && (
                      <span className="text-slate-900 text-sm">
                        / {product.size}
                      </span>
                    )}
                  </div>
                )}

                <p className="text-slate-900 leading-relaxed" style={{ fontFamily: 'Open Sans, sans-serif' }}>
                  {product.description}
                </p>

                {index === 0 && (
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="mt-6 w-full py-3 px-6 rounded-lg font-semibold text-white transition-all duration-500"
                    style={{ backgroundColor: '#0c8558' }}
                  >
                    Shop Now
                  </motion.button>
                )}
              </motion.article>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
};

export default Section02PRODUCTSHOWCASE;
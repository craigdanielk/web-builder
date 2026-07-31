"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Shield, Globe, Coins, HelpCircle } from "lucide-react";
import { FadeText } from "@/components/animations/fade-up-single";

interface FAQItem {
  icon: React.ReactNode;
  question: string;
  answer: string;
}

const FAQS: FAQItem[] = [
  {
    icon: <Shield className="w-5 h-5 text-sky-700" />,
    question: "How long does verification (KYC) take?",
    answer:
      "Standard individual verification completes in 10–30 minutes once documents are submitted. Enhanced due-diligence for high-value accounts typically clears within 1 business day, with a compliance specialist assigned to your file.",
  },
  {
    icon: <Coins className="w-5 h-5 text-sky-700" />,
    question: "Which currencies and rails do you support?",
    answer:
      "Fiat: ZAR, USD, GBP, EUR and more via regulated banking partners. Crypto rails: XRP Ledger and major stablecoins including USDT and USDC, settled directly to your linked institutional or personal wallets.",
  },
  {
    icon: <Globe className="w-5 h-5 text-sky-700" />,
    question: "Are fees and rates transparent before I confirm?",
    answer:
      "Yes. Every transaction shows the exact exchange rate, network fee, and Xago fee before you confirm — no spread surprises. Rates lock for 30 seconds at review so the number you see is the number you get.",
  },
  {
    icon: <HelpCircle className="w-5 h-5 text-sky-700" />,
    question: "What if my transfer is above the daily limit?",
    answer:
      "High-net-worth accounts can request elevated limits via your relationship manager. Approved increases apply instantly to your account with no re-verification needed for future transfers.",
  },
];

const Section02FAQ: React.FC = () => {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="bg-white py-20 px-4 sm:px-6" aria-labelledby="faq-heading">
      <div className="max-w-2xl mx-auto">
        <FadeText
          text="Frequently asked questions"
          className="block text-2xl sm:text-3xl font-bold text-sky-800 text-center mb-3"
        />
        <h2 id="faq-heading" className="sr-only">
          Frequently asked questions
        </h2>
        <p className="text-center text-slate-500 mb-10 text-sm sm:text-base">
          Due-diligence answers for high-value cross-border transfers.
        </p>

        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-100px" }}
          transition={{ staggerChildren: 0.1 }}
          className="space-y-3"
        >
          {FAQS.map((item, i) => {
            const isOpen = openIndex === i;
            return (
              <motion.div
                key={item.question}
                variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="border border-slate-200 rounded-xl overflow-hidden bg-white"
              >
                <button
                  type="button"
                  onClick={() => setOpenIndex(isOpen ? null : i)}
                  aria-expanded={isOpen}
                  className="w-full flex items-center justify-between gap-3 px-4 py-4 min-h-[44px] text-left transition-colors duration-200 hover:bg-sky-50"
                >
                  <span className="flex items-center gap-3">
                    {item.icon}
                    <span className="font-semibold text-sky-800 text-sm sm:text-base">
                      {item.question}
                    </span>
                  </span>
                  <motion.span
                    animate={{ rotate: isOpen ? 180 : 0 }}
                    transition={{ duration: 0.2, ease: "easeOut" }}
                  >
                    <ChevronDown className="w-5 h-5 text-sky-700 shrink-0" />
                  </motion.span>
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2, ease: "easeOut" }}
                    >
                      <p className="px-4 pb-4 text-sm text-slate-600 leading-relaxed tabular-nums">
                        {item.answer}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
};

export default Section02FAQ;

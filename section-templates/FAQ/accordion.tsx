"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * FAQ | accordion
 * Token-driven section template — tenant content filled at build time.
 *
 * The Supabase template this replaces shipped "Questions? We've got answers"
 * with a subtitle and NOTHING ELSE: the harvest supplied 2 of its 14 slots, so
 * the heading filled and every question row came out blank. It survived the
 * omission rule because that rule drops a section with ZERO sourced slots, and
 * this one had two — a heading over empty space, which is precisely the failure
 * the rule is named after.
 *
 * The fix belongs in the template, not in the omission rule: a section whose
 * BODY is empty renders nothing, whatever its title managed to fill. A title is
 * not content.
 *
 * Everything is a token — no Tailwind palette literal — so the section takes
 * the market benchmark's palette, rhythm and type weights. See
 * FEATURES/icon-grid for the full reasoning.
 *
 * Slots:
 *   {section_title}     → "Questions? We've got answers"
 *   {section_subtitle}  → "Visit our help centre…"
 *   {faqs[].question}   → "How do I fund my account?"
 *   {faqs[].answer}     → "Deposit Rands directly from your bank…"
 */

// The machine-read declaration. `slot_contract.declared_slots()` reads ONLY a
// `// Tokens:` line or a `Slot placeholders` block — the prose "Slots:" list
// above is neither, so without this line the contract falls back to a
// permissive brace sweep and substitutes this file's own JS identifiers away.
// Tokens: {section_title} {section_subtitle} {faqs[].question} {faqs[].answer}

interface Faq {
  question: string;
  answer: string;
}

interface FaqAccordionProps {
  sectionTitle?: string;
  sectionSubtitle?: string;
  faqs?: Faq[];
}

const harvestedFaqs: Faq[] = [
  /* repeat:faqs */
  { question: "{faqs[].question}", answer: "{faqs[].answer}" },
  /* /repeat */
];

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";

export default function FaqAccordion({
  sectionTitle = "{section_title}",
  sectionSubtitle = "{section_subtitle}",
  faqs = harvestedFaqs,
}: FaqAccordionProps) {
  const [open, setOpen] = useState<number | null>(0);

  // A title is not content. No questions, no section.
  if (!faqs.length) return null;

  return (
    <section
      className="w-full"
      style={{
        background: "var(--background)",
        color: "var(--foreground)",
        paddingTop: "var(--section-py, 96px)",
        paddingBottom: "var(--section-py, 96px)",
      }}
    >
      <div className="mx-auto grid w-full max-w-6xl gap-12 px-6 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        <div>
          {sectionTitle && (
            <h2
              className="text-3xl md:text-[2.5rem] leading-[1.12] tracking-tight"
              style={{
                fontFamily: "var(--font-heading, inherit)",
                fontWeight: "var(--heading-weight, 400)" as unknown as number,
              }}
            >
              {sectionTitle}
            </h2>
          )}
          {sectionSubtitle && (
            <p
              className="mt-5 text-base leading-relaxed"
              style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
            >
              {sectionSubtitle}
            </p>
          )}
        </div>

        <ul className="border-t" style={{ borderColor: HAIRLINE }}>
          {faqs.map((faq, index) => {
            const isOpen = open === index;
            return (
              <li key={index} className="border-b" style={{ borderColor: HAIRLINE }}>
                <button
                  type="button"
                  onClick={() => setOpen(isOpen ? null : index)}
                  aria-expanded={isOpen}
                  className="flex w-full items-start justify-between gap-6 py-6 text-left"
                >
                  <span
                    className="text-lg leading-snug"
                    style={{
                      fontFamily: "var(--font-heading, inherit)",
                      fontWeight: 500,
                      color: isOpen ? ACCENT : "inherit",
                    }}
                  >
                    {faq.question}
                  </span>
                  <span
                    aria-hidden="true"
                    className="mt-2 shrink-0 transition-transform duration-300"
                    style={{
                      transform: isOpen ? "rotate(45deg)" : "none",
                      color: ACCENT,
                      lineHeight: 1,
                      fontSize: "1.25rem",
                    }}
                  >
                    +
                  </span>
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && faq.answer && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.32, ease: "easeOut" }}
                      className="overflow-hidden"
                    >
                      <p
                        className="max-w-2xl pb-6 pr-10 text-base leading-relaxed"
                        style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                      >
                        {faq.answer}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

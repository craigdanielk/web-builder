"use client";

import { motion } from "framer-motion";

/**
 * FAQ | two-column
 * Token-driven section template — tenant content filled at build time.
 *
 * Every answer visible, in a compact two-column grid of question/answer
 * pairs. For a short list of purchase facts (what it is, how many, why
 * pre-order) an accordion hides exactly what a buyer came to read; this shows
 * all of it in less vertical space than the accordion's open state.
 *
 *   1. A title is not content: no questions, no section (as FAQ/accordion).
 *   2. Every colour, size and rhythm is a token. The question reads
 *      --type-h4, the section title --type-h2.
 *   3. Hairline above each pair; no boxes, no icons.
 *
 * Slots:
 *   {section_title}     → section heading
 *   {section_subtitle}  → intro line (optional)
 *   {faqs[].question}   → question
 *   {faqs[].answer}     → answer
 */

// Tokens: {section_title} {section_subtitle} {faqs[].question} {faqs[].answer}

// Art: none

interface Faq {
  question: string;
  answer: string;
}

interface FaqTwoColumnProps {
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

/** A slot value that survived the fill; an unsubstituted placeholder is empty. */
function resolved(value: string | undefined): string {
  if (!value) return "";
  const trimmed = value.trim();
  if (!trimmed || trimmed.startsWith("{")) return "";
  return trimmed;
}

export default function FaqTwoColumn({
  sectionTitle = "{section_title}",
  sectionSubtitle = "{section_subtitle}",
  faqs = harvestedFaqs,
}: FaqTwoColumnProps) {
  const pairs = faqs.filter((faq) => resolved(faq.question));
  if (!pairs.length) return null;
  const title = resolved(sectionTitle);
  const intro = resolved(sectionSubtitle);

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
      <div className="aurelix-container mx-auto w-full max-w-6xl px-6">
        {(title || intro) && (
          <div className="max-w-2xl" style={{ marginBottom: "var(--block-gap, 48px)" }}>
            {title && (
              <h2
                className="leading-[1.1] tracking-tight"
                style={{
                  fontSize: "var(--type-h2, 3rem)",
                  fontFamily: "var(--font-heading, inherit)",
                  fontWeight: "var(--heading-weight, 400)" as unknown as number,
                }}
              >
                {title}
              </h2>
            )}
            {intro && (
              <p
                className="mt-5 text-base leading-relaxed"
                style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
              >
                {intro}
              </p>
            )}
          </div>
        )}

        <dl className="grid gap-x-16 md:grid-cols-2">
          {pairs.map((faq, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.45, delay: (index % 2) * 0.06, ease: "easeOut" }}
              className="border-t py-7"
              style={{ borderColor: HAIRLINE }}
            >
              <dt>
                <h3
                  className="leading-snug"
                  style={{
                    fontSize: "var(--type-h4, 1.25rem)",
                    fontFamily: "var(--font-heading, inherit)",
                    fontWeight: "var(--heading-weight, 400)" as unknown as number,
                  }}
                >
                  {faq.question}
                </h3>
              </dt>
              {resolved(faq.answer) && (
                <dd
                  className="mt-3 text-base leading-relaxed"
                  style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                >
                  {faq.answer}
                </dd>
              )}
            </motion.div>
          ))}
        </dl>
      </div>
    </section>
  );
}

"use client";

import { motion } from "framer-motion";

/**
 * CTA | dark-band
 * Parameterized section template — brand tokens injected at build time.
 *
 * A full-width call-to-action on a dark background with WCAG-AA-safe
 * contrast ratios. All text, buttons, and surfaces use intentionally
 * paired light-on-dark tokens so no tenant hand-fixes contrast.
 *
 * Token placeholders (replaced by orchestrator):
 *   {{brand.bg_dark}}             → e.g. "gray-950" / "stone-950"  (dark section bg)
 *   {{brand.text_on_dark}}        → e.g. "gray-100" / "stone-100"  (primary text on dark)
 *   {{brand.text_muted_on_dark}}  → e.g. "gray-400" / "stone-400"  (muted text on dark)
 *   {{brand.accent_on_dark}}      → e.g. "amber-400"               (CTA bg — passes AA on dark)
 *   {{brand.accent_text_on_dark}} → e.g. "black" / "stone-950"     (CTA label — passes AA on accent)
 *   {{brand.accent_hover_on_dark}}→ e.g. "amber-300"               (CTA hover)
 *   {{brand.heading_font}}        → e.g. "DM Serif Display"
 *   {{brand.body_font}}           → e.g. "DM Sans"
 *
 * Slot placeholders (filled by tenant data):
 *   {headline}           → "Ready to Transform Your Business?"
 *   {subheadline}        → "Join thousands of companies already using our platform."
 *   {cta_text}           → "Get Started Free"
 *   {cta_href}           → "/signup"
 *   {secondary_cta_text} → "Learn More"
 *   {secondary_cta_href} → "/features"
 *   {disclaimer}         → "No credit card required. Cancel anytime."
 */

interface DarkBandCTAProps {
  headline?: string;
  subheadline?: string;
  ctaText?: string;
  ctaHref?: string;
  secondaryCtaText?: string;
  secondaryCtaHref?: string;
  disclaimer?: string;
}

export default function SectionDarkBandCTA({
  headline = "{headline}",
  subheadline = "{subheadline}",
  ctaText = "{cta_text}",
  ctaHref = "{cta_href}",
  secondaryCtaText = "{secondary_cta_text}",
  secondaryCtaHref = "{secondary_cta_href}",
  disclaimer = "{disclaimer}",
}: DarkBandCTAProps) {
  return (
    <section className="bg-{{brand.bg_dark}} py-16 md:py-24 lg:py-28">
      <div className="container mx-auto px-4 max-w-5xl text-center">
        {/* Headline — WCAG AA: white/light text on dark bg */}
        <motion.h2
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="text-3xl md:text-4xl lg:text-5xl font-bold text-{{brand.text_on_dark}} leading-tight tracking-tight"
          style={{ fontFamily: "var(--font-heading, '{{brand.heading_font}}')" }}
        >
          {headline}
        </motion.h2>

        {/* Subheadline — WCAG AA: muted-light text on dark bg */}
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.7, delay: 0.15, ease: "easeOut" }}
          className="mt-5 text-lg md:text-xl text-{{brand.text_muted_on_dark}} max-w-3xl mx-auto leading-relaxed"
          style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
        >
          {subheadline}
        </motion.p>

        {/* CTA buttons */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.7, delay: 0.3, ease: "easeOut" }}
          className="mt-8 md:mt-10 flex flex-col sm:flex-row gap-4 justify-center items-center"
        >
          {/* Primary CTA — WCAG AA: accent bg passes contrast on dark bg, label passes on accent bg */}
          <a
            href={ctaHref}
            className={`
              inline-flex items-center justify-center
              px-8 py-4 text-base font-semibold rounded-lg
              bg-{{brand.accent_on_dark}} text-{{brand.accent_text_on_dark}}
              hover:bg-{{brand.accent_hover_on_dark}}
              transition-all duration-300 ease-out
              hover:shadow-lg hover:-translate-y-0.5
              focus-visible:outline-2 focus-visible:outline-offset-2
              focus-visible:outline-{{brand.accent_on_dark}}
            `}
            style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
          >
            {ctaText}
          </a>

          {/* Secondary CTA — outline style on dark bg, WCAG AA */}
          {secondaryCtaText && (
            <a
              href={secondaryCtaHref}
              className={`
                inline-flex items-center justify-center
                px-8 py-4 text-base font-semibold rounded-lg
                border-2 border-{{brand.text_muted_on_dark}}/40
                text-{{brand.text_on_dark}}
                hover:border-{{brand.text_on_dark}}/70 hover:bg-white/5
                transition-all duration-300 ease-out
                hover:-translate-y-0.5
                focus-visible:outline-2 focus-visible:outline-offset-2
                focus-visible:outline-{{brand.text_on_dark}}
              `}
              style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
            >
              {secondaryCtaText}
            </a>
          )}
        </motion.div>

        {/* Disclaimer — smallest text, WCAG AA compliant on dark bg */}
        {disclaimer && (
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="mt-8 text-sm text-{{brand.text_muted_on_dark}}/70 max-w-xl mx-auto leading-relaxed"
            style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
          >
            {disclaimer}
          </motion.p>
        )}
      </div>
    </section>
  );
}

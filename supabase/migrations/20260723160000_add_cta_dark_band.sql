-- ═══════════════════════════════════════════════════════════════
-- CTA/dark-band — reusable dark-section CTA with slot_schema
-- ═══════════════════════════════════════════════════════════════
-- Inserts a parameterized CTA/dark-band row into section_archetypes
-- with a WCAG-safe contrast template and self-describing slot_schema.
--
-- New brand tokens introduced (for orchestrator resolution):
--   {{brand.bg_dark}}              → e.g. "gray-950"
--   {{brand.text_on_dark}}         → e.g. "gray-100"
--   {{brand.text_muted_on_dark}}   → e.g. "gray-400"
--   {{brand.accent_on_dark}}       → e.g. "amber-400"
--   {{brand.accent_hover_on_dark}} → e.g. "amber-300"
--   {{brand.accent_text_on_dark}}  → e.g. "black"
-- ═══════════════════════════════════════════════════════════════

INSERT INTO section_archetypes (
    archetype,
    variant,
    description,
    animation_engine,
    has_template,
    template_path,
    code_template,
    slot_schema
)
VALUES (
    'CTA',
    'dark-band',
    'Full-width call-to-action on dark background with WCAG-AA-safe contrast ratios — no hard-coded copy, all content driven by slot_schema',
    'framer-motion',
    TRUE,
    'section-templates/CTA/dark-band.tsx',
    $$"use client";

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
 *   {{brand.bg_dark}}              -> e.g. "gray-950" / "stone-950"
 *   {{brand.text_on_dark}}         -> e.g. "gray-100" / "stone-100"
 *   {{brand.text_muted_on_dark}}   -> e.g. "gray-400" / "stone-400"
 *   {{brand.accent_on_dark}}       -> e.g. "amber-400"
 *   {{brand.accent_hover_on_dark}} -> e.g. "amber-300"
 *   {{brand.accent_text_on_dark}}  -> e.g. "black"
 *   {{brand.heading_font}}         -> e.g. "DM Serif Display"
 *   {{brand.body_font}}            -> e.g. "DM Sans"
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
        {/* Headline — WCAG AA: light text on dark bg */}
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
          {/* Primary CTA — WCAG AA: accent_on_dark on bg_dark */}
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

          {/* Secondary CTA — outline style, WCAG AA on dark */}
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

        {/* Disclaimer — smallest text, WCAG AA on dark */}
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
}$$,
    '{
      "slots": [
        {
          "name": "headline",
          "source_path": "content.headline",
          "required": true,
          "default": "Ready to Transform Your Business?",
          "fill_prompt": "Compelling, benefit-driven headline for a CTA section (2-8 words, active voice, no punctuation at end)",
          "description": "Primary call-to-action headline — the main hook"
        },
        {
          "name": "subheadline",
          "source_path": "content.subheadline",
          "required": true,
          "default": "Join thousands of companies already using our platform.",
          "fill_prompt": "Supporting subheadline that expands on the headline value prop (1-2 sentences, 10-25 words)",
          "description": "Secondary descriptive text beneath the headline"
        },
        {
          "name": "cta_text",
          "source_path": "content.cta.primary.text",
          "required": true,
          "default": "Get Started Free",
          "fill_prompt": "Short action-oriented CTA button label (2-4 words, imperative mood, e.g. \"Get Started\", \"Claim Your Spot\", \"Book a Demo\")",
          "description": "Primary CTA button label"
        },
        {
          "name": "cta_href",
          "source_path": "content.cta.primary.href",
          "required": true,
          "default": "/signup",
          "fill_prompt": "URL path or absolute URL for the primary CTA destination",
          "description": "Primary CTA link destination"
        },
        {
          "name": "secondary_cta_text",
          "source_path": "content.cta.secondary.text",
          "required": false,
          "default": "Learn More",
          "fill_prompt": "Optional secondary CTA button label (2-4 words, imperative mood). Omit if no secondary action",
          "description": "Secondary (outline) CTA button label"
        },
        {
          "name": "secondary_cta_href",
          "source_path": "content.cta.secondary.href",
          "required": false,
          "default": "/features",
          "fill_prompt": "URL path or absolute URL for the secondary CTA destination. Omitted if secondary_cta_text is omitted",
          "description": "Secondary CTA link destination"
        },
        {
          "name": "disclaimer",
          "source_path": "content.disclaimer",
          "required": false,
          "default": "No credit card required. Cancel anytime.",
          "fill_prompt": "Small print / disclaimer text below the CTA buttons. 1 sentence, builds trust. Omit if no disclaimer needed",
          "description": "Optional fine-print or trust-building disclaimer"
        }
      ]
    }'::jsonb
)
ON CONFLICT (archetype, variant) DO UPDATE SET
    description = EXCLUDED.description,
    animation_engine = EXCLUDED.animation_engine,
    has_template = EXCLUDED.has_template,
    template_path = EXCLUDED.template_path,
    code_template = EXCLUDED.code_template,
    slot_schema = EXCLUDED.slot_schema;

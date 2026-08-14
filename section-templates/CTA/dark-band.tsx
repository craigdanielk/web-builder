"use client";

import { motion } from "framer-motion";

/**
 * CTA | dark-band
 * Token-driven section template — tenant content filled at build time.
 *
 * Replaces the `{{brand.*}}` mustache version, which asked the orchestrator to
 * hand it eight Tailwind palette names (`gray-950`, `amber-400`, `stone-100`)
 * and, when nothing supplied them, shipped class strings like `bg-{{brand.
 * bg_dark}}` that Tailwind cannot resolve — a section with no background at
 * all. Four deliberate departures:
 *
 *   1. EVERY COLOUR, SIZE AND RHYTHM IS A TOKEN. The build compiles the market
 *      benchmark into CSS custom properties and this reads them, so one file
 *      renders a navy fintech and a warm food brand without edits.
 *
 *   2. "DARK" IS NOW "INVERTED", AND THAT IS THE POINT. The band's job is to
 *      break the page by reversing ground and ink — it cannot know whether the
 *      compiled palette is light-on-dark or dark-on-light. So the ground is
 *      --foreground and the ink is --background: the same pair the compiler
 *      already contrast-checked for body text, used the other way round. A
 *      literal `bg-gray-950` would have been dark on a dark palette too, i.e.
 *      invisible. The old `hover:bg-white/5` wash had the same bug in
 *      miniature — it assumed a dark ground. It is now mixed from the band's
 *      own ink, so it lightens a dark band and darkens a light one.
 *
 *   3. ARITY COMES FROM THE HARVEST. The old file hardcoded exactly two
 *      buttons and invented a "Learn More" for the second. Actions are a
 *      repeat block: one harvested CTA renders one button, three render three,
 *      none renders no button row. The first action is the primary; the rest
 *      are outlines, so hierarchy survives any count.
 *
 *   4. NO INVENTED COPY. Every default is its own slot placeholder. Cape
 *      Crypto is an FSCA-licensed FSP — a hardcoded "Join thousands of
 *      companies" is a regulatory liability, not a placeholder.
 *
 * Slots:
 *   {headline}         → "Start trading in minutes"
 *   {subheadline}      → "Open an account and fund it in your own currency"
 *   {disclaimer}       → "Cape Crypto is a licensed FSP. Terms apply."
 *   {actions[].cta}    → "Create an account"
 *   {actions[].href}   → "/register"
 */

// Tokens: {headline} {subheadline} {disclaimer} {actions[].cta} {actions[].href}

interface CtaAction {
  cta: string;
  href: string;
}

interface CtaDarkBandProps {
  ctaHeadline?: string;
  ctaSubheadline?: string;
  ctaDisclaimer?: string;
  ctaActions?: CtaAction[];
}

const harvestedActions: CtaAction[] = [
  /* repeat:actions */
  { cta: "{actions[].cta}", href: "{actions[].href}" },
  /* /repeat */
];

// The band inverts the page: ground is the page's ink, ink is the page's
// ground. Both derived, so the pair inverts with the palette (see note 2).
const BAND_BG = "var(--foreground)";
const BAND_INK = "var(--background)";
const BAND_MUTED = "color-mix(in srgb, var(--background) 72%, var(--foreground))";
const BAND_HAIRLINE = "color-mix(in srgb, var(--background) 38%, transparent)";
const BAND_WASH = "color-mix(in srgb, var(--background) 10%, transparent)";
const ACCENT = "var(--accent, var(--background))";
const ON_ACCENT = "var(--on-accent, var(--foreground))";

export default function SectionDarkBandCTA({
  ctaHeadline = "{headline}",
  ctaSubheadline = "{subheadline}",
  ctaDisclaimer = "{disclaimer}",
  ctaActions = harvestedActions,
}: CtaDarkBandProps) {
  // A disclaimer under nothing is not a call to action.
  if (!ctaHeadline && !ctaSubheadline && !ctaActions.length) return null;

  return (
    <section
      className="w-full"
      style={{
        background: BAND_BG,
        color: BAND_INK,
        paddingTop: "var(--section-py, 96px)",
        paddingBottom: "var(--section-py, 96px)",
      }}
    >
      <div className="mx-auto w-full max-w-4xl px-6 text-center">
        {/* Decorative accent rule — content-free, and the one place the brand
            accent carries no legibility risk on an unknown ground. */}
        <span
          aria-hidden="true"
          className="mx-auto mb-8 block h-[3px] w-12"
          style={{ background: ACCENT, borderRadius: "var(--radius-button, 4px)" }}
        />

        {ctaHeadline && (
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="text-3xl md:text-[3rem] leading-[1.1] tracking-tight"
            style={{
              fontFamily: "var(--font-heading, inherit)",
              fontWeight: "var(--heading-weight, 400)" as unknown as number,
            }}
          >
            {ctaHeadline}
          </motion.h2>
        )}

        {ctaSubheadline && (
          <motion.p
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, delay: 0.12, ease: "easeOut" }}
            className="mx-auto mt-5 max-w-2xl text-lg leading-relaxed"
            style={{ color: BAND_MUTED, fontFamily: "var(--font-body, inherit)" }}
          >
            {ctaSubheadline}
          </motion.p>
        )}

        {ctaActions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, delay: 0.24, ease: "easeOut" }}
            className="flex flex-col items-center justify-center gap-4 sm:flex-row"
            style={{ marginTop: "var(--block-gap, 48px)" }}
          >
            {ctaActions.map((ctaAction, actionIndex) =>
              ctaAction.cta ? (
                <a
                  key={actionIndex}
                  href={ctaAction.href || undefined}
                  className="inline-flex items-center justify-center px-8 py-4 text-base transition-transform duration-300 ease-out hover:-translate-y-0.5"
                  style={
                    actionIndex === 0
                      ? {
                          // Primary. --accent / --on-accent are a pair the
                          // compiler emits together, so the label is safe on
                          // the fill; the hairline ring keeps the button's
                          // EDGE readable if the accent sits close to the band.
                          background: ACCENT,
                          color: ON_ACCENT,
                          boxShadow: `0 0 0 1px ${BAND_HAIRLINE}`,
                          borderRadius: "var(--radius-button, 6px)",
                          fontFamily: "var(--font-body, inherit)",
                          fontWeight: 500,
                        }
                      : {
                          // Secondary. Outline in the band's own ink — no
                          // palette literal, so it reads on either polarity.
                          background: BAND_WASH,
                          color: BAND_INK,
                          boxShadow: `inset 0 0 0 1px ${BAND_HAIRLINE}`,
                          borderRadius: "var(--radius-button, 6px)",
                          fontFamily: "var(--font-body, inherit)",
                          fontWeight: 500,
                        }
                  }
                >
                  {ctaAction.cta}
                </a>
              ) : null
            )}
          </motion.div>
        )}

        {ctaDisclaimer && (
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="mx-auto mt-8 max-w-xl text-sm leading-relaxed"
            style={{ color: BAND_MUTED, fontFamily: "var(--font-body, inherit)" }}
          >
            {ctaDisclaimer}
          </motion.p>
        )}
      </div>
    </section>
  );
}

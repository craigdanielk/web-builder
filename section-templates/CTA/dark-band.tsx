"use client";

import { motion } from "framer-motion";

/**
 * CTA | dark-band
 * Token-driven section template — tenant content filled at build time.
 *
 * The design authority is benchmarks/enterprise-payments-bvnk.json, which is a
 * LIGHT benchmark (bg_primary is white). This section stays dark anyway, and
 * that is a decision rather than an oversight. Five deliberate departures:
 *
 *   1. EVERY COLOUR, SIZE AND RHYTHM IS A TOKEN. Not one palette literal. The
 *      build compiles the benchmark into CSS custom properties and this reads
 *      them, so the same file renders a navy fintech and a warm food brand
 *      without edits. Fallbacks are the benchmark's own measured numbers.
 *
 *   2. THE BAND IS A DELIBERATE ACCENT SURFACE, NOT AN INVERSION. An earlier
 *      revision made the ground --foreground on the theory that the band's job
 *      was to reverse the page's polarity. That is wrong in one specific way:
 *      it makes the section's identity a side effect of the palette, so a dark
 *      compiled palette would silently produce a WHITE "dark-band". The band
 *      is dark on purpose, so it asks for a dark surface by name:
 *      --surface-inverse, falling back to --foreground. The fallback is not a
 *      coincidence — the benchmark's text_primary is a real dark
 *      surface on that reference, measured as the pill/button emphasis stroke,
 *      and at 13.98:1 under bg_primary it is the darkest ground the compiled
 *      vocabulary can supply. See the report note on --surface-inverse.
 *
 *   3. ON A DARK BAND THE PRIMARY BUTTON IS THE LIGHT PILL, NOT THE ACCENT.
 *      --accent against the band ground separates at 1.63:1 — the button
 *      would read as a smudge, and only a hairline ring would describe its
 *      shape. So the primary is filled in the band's ink (13.98:1 label
 *      contrast, and the strongest possible shape separation) and the accent
 *      keeps the decorative rule, where it carries no legibility duty. This is
 *      the reference's own dark-pill-on-light pattern, run the other way.
 *
 *   4. ARITY COMES FROM THE HARVEST. Actions are a repeat block: one harvested
 *      CTA renders one button, three render three, none renders no button row.
 *      The first action is primary; the rest are outlines, so hierarchy
 *      survives any count.
 *
 *   5. NO INVENTED COPY. Every default is its own slot placeholder. Cape Crypto
 *      is an FSCA-licensed FSP (No. 53746) — a hardcoded "Join thousands of
 *      companies" is a regulatory liability, not a placeholder.
 */

// The machine-read declaration. `slot_contract.declared_slots()` reads ONLY a
// `// Tokens:` line or a `Slot placeholders` block — a prose "Slots:" list is
// neither, and without this line the contract falls back to a permissive brace
// sweep and substitutes this file's own JS identifiers away.
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

// The band asks for a dark surface by name; --foreground is the darkest ground
// the compiled vocabulary can supply and is a measured surface on the
// reference, so it is the fallback rather than a literal (see note 2).
const BAND_BG = "var(--surface-inverse, var(--foreground))";
// Ink on that ground. --background is the page ground, the one colour the
// compiler has already contrast-checked against --foreground for body text.
const BAND_INK = "var(--background)";
const BAND_MUTED = "color-mix(in srgb, var(--background) 72%, var(--foreground))";
const BAND_HAIRLINE = "color-mix(in srgb, var(--background) 38%, transparent)";
const BAND_WASH = "color-mix(in srgb, var(--background) 10%, transparent)";
const ACCENT = "var(--accent, var(--background))";

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
        paddingTop: "var(--section-py, 120px)",
        paddingBottom: "var(--section-py, 120px)",
      }}
    >
      <div className="mx-auto w-full max-w-4xl px-6 text-center">
        {/* Decorative accent rule — content-free, and the one place the brand
            accent carries no legibility duty on a dark ground (see note 3). */}
        <span
          aria-hidden="true"
          className="mx-auto mb-8 block h-[3px] w-12"
          style={{ background: ACCENT, borderRadius: "var(--radius-button, 100px)" }}
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
              fontWeight: "var(--heading-weight, 500)" as unknown as number,
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
            className="flex flex-col items-center justify-center sm:flex-row"
            style={{ marginTop: "var(--block-gap, 24px)", gap: "var(--block-gap, 24px)" }}
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
                          // Primary: the light pill. Ground and ink are the
                          // page pair used the other way round, so the label
                          // clears the same ratio the compiler already checked
                          // for body text, and the pill separates maximally
                          // from the band. Accent cannot do this job here —
                          // note 3.
                          background: BAND_INK,
                          color: BAND_BG,
                          borderRadius: "var(--radius-button, 100px)",
                          fontFamily: "var(--font-body, inherit)",
                          fontWeight: 500,
                        }
                      : {
                          // Secondary: outline in the band's own ink. No
                          // palette literal, so it survives any compiled
                          // palette without going invisible.
                          background: BAND_WASH,
                          color: BAND_INK,
                          boxShadow: `inset 0 0 0 1px ${BAND_HAIRLINE}`,
                          borderRadius: "var(--radius-button, 100px)",
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

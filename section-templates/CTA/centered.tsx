"use client";

import { motion } from "framer-motion";

/**
 * CTA | centered
 * Token-driven section template — tenant content filled at build time.
 *
 * The Supabase template this replaces was 37 lines and resolved on five of this
 * site's twenty-one sections — about, developers, merchants ×2 and wealth. It
 * hardcoded a near-black ground, white heading ink, grey body ink and a white
 * pill as Tailwind palette literals — the same failure the whole design-token
 * chain was rebuilt to end (no such literal appears below, deliberately): the
 * compiled palette reached `globals.css` and this section ignored it, so the
 * tenant's accent (#004e89) appeared nowhere on five of its own calls to action.
 *
 * Decisions:
 *
 *   1. EVERY COLOUR, RHYTHM AND RADIUS IS A TOKEN. Not one palette literal. The
 *      fallbacks are the benchmark's own measured numbers, so the file renders a
 *      navy fintech and a warm food brand without edits.
 *
 *   2. CENTERED IS A PANEL, NOT A BAND. `dark-band` already owns full-bleed
 *      inversion — a second variant that also spans edge to edge on a contrasting
 *      ground is the same section twice under two names. This one composes an
 *      inset panel on `--surface` (the benchmark's measured pale secondary
 *      surface, #f1f7ff there) sitting on the page ground, bounded by
 *      `--border` and `--radius-card`. Two CTA sections on one page therefore
 *      read as two different gestures rather than one repeated.
 *
 *   3. ON A LIGHT PANEL THE PRIMARY BUTTON IS THE ACCENT. The inverse of
 *      `dark-band` note 3, and for the same measured reason run the other way:
 *      `--accent` on `--surface` separates strongly, and `--on-accent` is
 *      compiled at 8.57:1 against it. On the dark band the accent would have been
 *      a smudge; here it is the one element that should be loudest.
 *
 *   4. THE ACTIONS ARE A HIERARCHY, NOT AN ITEM LIST — AND THAT DISTINCTION IS
 *      LOAD-BEARING. `dark-band` spells its buttons as a `{actions[].cta}`
 *      repeater, and writing this one the same way broke three live tests.
 *      `archetype_item_capacity()` (orchestrate.py:1546) reads ANY repeater in a
 *      template body as unbounded *item* capacity, and
 *      `reclassify_sections_by_arity()` only moves a block when its current
 *      archetype cannot hold the harvested arity. So a CTA declaring a repeater
 *      claims it can hold six feature cards, and the six-card block this site's
 *      merchants page harvests under CTA/centered stops being reclassified to
 *      FEATURES/icon-grid — a real classification loss, caused by a template
 *      declaring a capacity it does not have. A call to action has no item list:
 *      it has a primary action and at most a secondary one. Both are declared as
 *      scalars, the secondary disappears when the harvest carries only one CTA
 *      (which is every one of this site's five), and the button row disappears
 *      when it carries none. Arity still comes from the harvest; the ceiling is
 *      two because two is what the section means.
 *
 *   5. NO IMAGE SLOT AND NO ART DEMAND. `centered` means the words are the
 *      subject. A backdrop here would also raise this build's art demand by five
 *      jobs for decoration the panel does not need — the composed ground is
 *      mixed from `--accent`, so it costs nothing and adapts to any tenant.
 *
 *   6. FOCUS IS VISIBLE. The template it replaces shipped bare anchors: keyboard
 *      focus on the only actionable element in the section was whatever the UA
 *      happened to draw over a dark ground. The ring is drawn in `--accent` at a
 *      2px offset, which is a token, so it cannot go invisible on a repaint.
 *
 *   7. NO INVENTED COPY. Every default is its own slot placeholder and every
 *      block is guarded on its value. Cape Crypto is an FSCA-licensed FSP
 *      (No. 53746) — a hardcoded "Join thousands of traders" is a regulatory
 *      liability, not a placeholder.
 */

// The machine-read declaration. `slot_contract.declared_slots()` reads ONLY a
// `// Tokens:` line or a `Slot placeholders` block — the prose above is neither,
// and without this line the contract falls back to a permissive brace sweep and
// substitutes this file's own JS identifiers away.
// Tokens: {headline} {subheadline} {disclaimer} {primary_cta_text} {primary_cta_url} {secondary_cta_text} {secondary_cta_url}

// The DEMAND declaration, read by `asset_resolver.art_declarations()`. An
// explicit absence, not an omission — see note 5. The panel's ground is mixed
// from `--accent`, so it is composed rather than fetched, and declaring a
// backdrop here would raise this build's art demand by five commissioned jobs
// for decoration the section reads exactly as well without.
// Art: none

interface CtaCenteredProps {
  ctaHeadline?: string;
  ctaSubheadline?: string;
  ctaDisclaimer?: string;
  primaryCtaText?: string;
  primaryCtaUrl?: string;
  secondaryCtaText?: string;
  secondaryCtaUrl?: string;
}

const SURFACE = "var(--surface, color-mix(in srgb, var(--accent) 6%, var(--background)))";
const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";
// Ink on the accent fill. Always emitted, and compiled for 8.57:1 on the tenant
// accent; the fallback is the page ground the accent sits on, never a literal
// white, so an uncompiled palette degrades to a measured pair rather than a bet.
const ON_ACCENT = "var(--on-accent, var(--background))";
// The wash inside the panel. Mixed from ACCENT into transparent, so it tints
// whatever surface it lands on instead of naming a second colour.
const WASH = `color-mix(in srgb, ${ACCENT} 10%, transparent)`;

// Shape, rhythm and focus ring are identical on both actions; only ground and
// ink differ, so hierarchy is carried by colour rather than by size. The ring is
// drawn in ACCENT via `outlineColor` in each action's style — a token, so it
// cannot go invisible on a repaint (note 6).
const BUTTON_CLASS =
  "inline-flex items-center justify-center px-8 py-4 text-base transition-transform " +
  "duration-300 ease-out hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2";

export default function SectionCenteredCTA({
  ctaHeadline = "{headline}",
  ctaSubheadline = "{subheadline}",
  ctaDisclaimer = "{disclaimer}",
  primaryCtaText = "{primary_cta_text}",
  primaryCtaUrl = "{primary_cta_url}",
  secondaryCtaText = "{secondary_cta_text}",
  secondaryCtaUrl = "{secondary_cta_url}",
}: CtaCenteredProps) {
  // A disclaimer under nothing is not a call to action.
  if (!ctaHeadline && !ctaSubheadline && !primaryCtaText) return null;

  return (
    <section
      className="relative w-full"
      style={{
        background: "var(--background)",
        color: "var(--foreground)",
        paddingTop: "var(--section-py, 120px)",
        paddingBottom: "var(--section-py, 120px)",
      }}
    >
      <div className="mx-auto w-full max-w-5xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="relative overflow-hidden text-center"
          style={{
            background: SURFACE,
            boxShadow: `inset 0 0 0 1px ${HAIRLINE}`,
            borderRadius: "var(--radius-card, 32px)",
            paddingTop: "calc(var(--card-pad, 40px) * 1.6)",
            paddingBottom: "calc(var(--card-pad, 40px) * 1.6)",
            paddingLeft: "var(--card-pad, 40px)",
            paddingRight: "var(--card-pad, 40px)",
          }}
        >
          {/* Composed ground — a single soft rise from the panel's foot, derived
              from the accent token. The benchmark states elevation is carried by
              surface tint and radius rather than by shadow, so there is no drop
              shadow anywhere in this section. */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0"
            style={{
              background: `radial-gradient(70% 60% at 50% 100%, ${WASH} 0%, transparent 72%)`,
            }}
          />

          <div className="relative mx-auto flex w-full max-w-3xl flex-col items-center">
            {ctaHeadline && (
              <h2
                // 32 → 44 → 56px in discrete steps. A type scale is a closed
                // set, so the ramp is breakpoints; a clamp() would render sizes
                // between the rungs at most real viewport widths.
                className="text-balance text-[2rem] md:text-[2.75rem] lg:text-[3.5rem]"
                style={{
                  fontFamily: "var(--font-heading, inherit)",
                  fontWeight: "var(--heading-weight, 500)" as unknown as number,
                  lineHeight: 1.1,
                  letterSpacing: "-0.02em",
                }}
              >
                {ctaHeadline}
              </h2>
            )}

            {ctaSubheadline && (
              <p
                className="text-pretty leading-relaxed"
                style={{
                  color: MUTED,
                  fontFamily: "var(--font-body, inherit)",
                  fontSize: "1.125rem",
                  marginTop: "var(--block-gap, 24px)",
                  // A typographic constant, not a taste call: the longest
                  // harvested supporting line on this site runs 190 characters
                  // and at panel width would wrap mid-phrase without a cap.
                  maxWidth: "58ch",
                }}
              >
                {ctaSubheadline}
              </p>
            )}

            {/* A label is what makes a button a button: each action is guarded
                on its own text, so a CTA harvested with an href and no words
                renders nothing rather than an unlabelled target — which is what
                merchants/02-cta shipped as an empty white pill to `href=""`. */}
            {(primaryCtaText || secondaryCtaText) && (
              <div
                className="flex w-full flex-col items-stretch justify-center sm:w-auto sm:flex-row sm:items-center"
                style={{
                  marginTop: "calc(var(--block-gap, 24px) * 2)",
                  gap: "var(--block-gap, 24px)",
                }}
              >
                {primaryCtaText && (
                  <a
                    href={primaryCtaUrl || undefined}
                    className={BUTTON_CLASS}
                    style={{
                      // Primary: the accent fill. See note 3 — this is the
                      // measured pair, and the one element in the section that
                      // should be loudest.
                      background: ACCENT,
                      color: ON_ACCENT,
                      borderRadius: "var(--radius-button, 100px)",
                      fontFamily: "var(--font-body, inherit)",
                      fontWeight: 500,
                      outlineColor: ACCENT,
                    }}
                  >
                    {primaryCtaText}
                  </a>
                )}
                {secondaryCtaText && (
                  <a
                    href={secondaryCtaUrl || undefined}
                    className={BUTTON_CLASS}
                    style={{
                      // Secondary: outline on the page ground, inset into the
                      // panel. Ink is the page foreground, so the label clears
                      // the ratio the compiler already checked for body text.
                      background: "var(--background)",
                      color: "var(--foreground)",
                      boxShadow: `inset 0 0 0 1px ${HAIRLINE}`,
                      borderRadius: "var(--radius-button, 100px)",
                      fontFamily: "var(--font-body, inherit)",
                      fontWeight: 500,
                      outlineColor: ACCENT,
                    }}
                  >
                    {secondaryCtaText}
                  </a>
                )}
              </div>
            )}

            {ctaDisclaimer && (
              <p
                className="mx-auto max-w-xl text-sm leading-relaxed"
                style={{
                  color: MUTED,
                  fontFamily: "var(--font-body, inherit)",
                  marginTop: "calc(var(--block-gap, 24px) * 1.5)",
                }}
              >
                {ctaDisclaimer}
              </p>
            )}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

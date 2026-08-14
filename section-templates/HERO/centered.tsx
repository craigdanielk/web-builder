"use client";

import { motion } from "framer-motion";

/**
 * HERO | centered
 * Token-driven section template — tenant content filled at build time.
 *
 * The Supabase template this replaces put a bold headline, a subtitle and one
 * dark button in the middle of an empty white page — the first thing a visitor
 * sees, and the weakest thing on the site. It also left roughly a screen of
 * dead space below the button, because its padding was a fixed `py-24` with
 * nothing to fill it.
 *
 * This variant carries NO image slot: `centered` means the words are the
 * subject. That is a legitimate hero — but only if the words are treated as the
 * subject, which means real display scale, controlled measure, and a background
 * that is composed rather than merely blank.
 *
 * Decisions:
 *
 *   1. A COMPOSED GROUND, NOT A VOID. Two very soft accent-tinted radial
 *      washes, built from the accent token via color-mix, sit behind the copy.
 *      No image, no asset, nothing fabricated — pure CSS derived from the
 *      palette, so it adapts to any tenant and cannot break.
 *
 *   2. DISPLAY SCALE, LIGHT WEIGHT. The benchmark's headlines are 300-400 at
 *      large sizes; hierarchy comes from size and space. clamp() lets the
 *      headline actually behave as display type instead of a big paragraph.
 *
 *   3. MEASURE IS CAPPED. The old subtitle ran the full container and wrapped
 *      awkwardly mid-phrase ("XRP and / USDT"). Prose is capped near 60ch,
 *      which is a typographic constant, not a taste call.
 *
 *   4. THE SECONDARY ACTION DISAPPEARS WHEN UNSOURCED. This build harvested one
 *      CTA, not two; `{secondary_cta_text}` comes back empty and the button is
 *      simply not rendered, rather than shipping a ghost button to nowhere.
 *
 * Slots:
 *   {eyebrow}            → "Licensed FSP"              (optional)
 *   {headline}           → "Buy Bitcoin South Africa"
 *   {subheadline}        → "Lowest trade fees in SA…"
 *   {primary_cta_text}   → "Sign up"
 *   {primary_cta_url}    → "https://trade.capecrypto.com/signup"
 *   {secondary_cta_text} → optional
 *   {secondary_cta_url}  → optional
 */

// The machine-read declaration. `slot_contract.declared_slots()` reads ONLY a
// line beginning `// Tokens:` (or a bracketed placeholder block) — the prose
// list above is neither, so without this line the contract falls back to a
// permissive brace sweep and substitutes this file's own JS identifiers away.
// Tokens: {eyebrow} {headline} {subheadline} {primary_cta_text} {primary_cta_url} {secondary_cta_text} {secondary_cta_url}

interface HeroCenteredProps {
  eyebrow?: string;
  headline?: string;
  subheadline?: string;
  primaryCtaText?: string;
  primaryCtaUrl?: string;
  secondaryCtaText?: string;
  secondaryCtaUrl?: string;
}

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";
const WASH_A = "color-mix(in srgb, var(--accent, #444) 9%, transparent)";
const WASH_B = "color-mix(in srgb, var(--accent, #444) 5%, transparent)";

export default function HeroCentered({
  eyebrow = "{eyebrow}",
  headline = "{headline}",
  subheadline = "{subheadline}",
  primaryCtaText = "{primary_cta_text}",
  primaryCtaUrl = "{primary_cta_url}",
  secondaryCtaText = "{secondary_cta_text}",
  secondaryCtaUrl = "{secondary_cta_url}",
}: HeroCenteredProps) {
  if (!headline && !subheadline) return null;

  return (
    <section
      className="relative w-full overflow-hidden"
      style={{
        background: "var(--background)",
        color: "var(--foreground)",
        paddingTop: "calc(var(--section-py, 96px) * 1.4)",
        paddingBottom: "calc(var(--section-py, 96px) * 1.4)",
      }}
    >
      {/* Composed ground — derived from the accent token, no asset. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background: `radial-gradient(58% 46% at 50% 0%, ${WASH_A} 0%, transparent 70%), radial-gradient(42% 38% at 82% 88%, ${WASH_B} 0%, transparent 72%)`,
        }}
      />

      <div className="relative mx-auto flex w-full max-w-4xl flex-col items-center px-6 text-center">
        {eyebrow && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="mb-7 inline-flex items-center gap-2.5 rounded-full border px-4 py-1.5"
            style={{ borderColor: HAIRLINE, background: "var(--background)" }}
          >
            <span
              aria-hidden="true"
              className="block h-1.5 w-1.5 rounded-full"
              style={{ background: ACCENT }}
            />
            <span
              className="text-xs uppercase tracking-[0.14em]"
              style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
            >
              {eyebrow}
            </span>
          </motion.div>
        )}

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="text-balance"
          style={{
            fontFamily: "var(--font-heading, inherit)",
            fontWeight: "var(--heading-weight, 400)" as unknown as number,
            fontSize: "clamp(2.6rem, 6.2vw, 4.5rem)",
            lineHeight: 1.03,
            letterSpacing: "-0.03em",
          }}
        >
          {headline}
        </motion.h1>

        {subheadline && (
          <motion.p
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.08, ease: "easeOut" }}
            className="mt-7 text-pretty text-lg leading-relaxed md:text-xl"
            style={{
              color: MUTED,
              fontFamily: "var(--font-body, inherit)",
              maxWidth: "58ch",
            }}
          >
            {subheadline}
          </motion.p>
        )}

        {(primaryCtaText || secondaryCtaText) && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.16, ease: "easeOut" }}
            className="mt-11 flex flex-wrap items-center justify-center gap-4"
          >
            {primaryCtaText && (
              <a
                href={primaryCtaUrl || "#"}
                className="inline-flex items-center px-8 py-4 text-base transition-opacity hover:opacity-90"
                style={{
                  background: ACCENT,
                  color: "var(--on-accent, #fff)",
                  borderRadius: "var(--radius-button, 4px)",
                  fontFamily: "var(--font-body, inherit)",
                  fontWeight: 500,
                  boxShadow:
                    "0 20px 40px -28px color-mix(in srgb, var(--accent, #000) 70%, transparent)",
                }}
              >
                {primaryCtaText}
              </a>
            )}
            {secondaryCtaText && (
              <a
                href={secondaryCtaUrl || "#"}
                className="inline-flex items-center border px-8 py-4 text-base transition-colors"
                style={{
                  borderColor: HAIRLINE,
                  borderRadius: "var(--radius-button, 4px)",
                  fontFamily: "var(--font-body, inherit)",
                  fontWeight: 500,
                }}
              >
                {secondaryCtaText}
              </a>
            )}
          </motion.div>
        )}
      </div>
    </section>
  );
}

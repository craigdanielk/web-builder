"use client";

import Image from "next/image";
import { motion } from "framer-motion";

/**
 * HERO | centered
 * Token-driven section template — tenant content filled at build time.
 *
 * The Supabase template this replaces put a bold headline, a subtitle and one
 * flat dark button in the middle of an empty page — the first thing a visitor
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
 *   1. THE REFERENCE'S GRADIENT GROUND, DERIVED NOT COPIED. The ratified
 *      benchmark's hero is a white-to-pale-blue gradient over the page ground.
 *      The token vocabulary carries no pale-blue token (bg_secondary was not
 *      compiled), so rather than invent a hex the wash is mixed from tokens
 *      that do exist: a few percent of --accent into --background. The tenant
 *      accent IS blue (#004e89), so this lands in the same family while staying
 *      tenant-derived on any future palette. One soft radial sits over the
 *      linear ramp for depth. No image, no asset, nothing fabricated — pure CSS
 *      derived from the palette, so it adapts to any tenant and cannot break.
 *      It is deliberately the same gradient language as HERO |
 *      full-bleed-overlay, so a site using either reads as one design.
 *
 *   2. DISPLAY SCALE, WEIGHT CAPPED AT 500. Every measured H1/H2 in the
 *      reference renders at 500 and none above it; 700 appears on inline text
 *      only. Hierarchy comes from size and space, and clamp() ramps the
 *      headline across the two display sizes the reference actually uses —
 *      64px and 96px — instead of letting it behave like a big paragraph.
 *
 *   3. MEASURE IS CAPPED. The old subtitle ran the full container and wrapped
 *      awkwardly mid-phrase ("XRP and / USDT"). Prose is capped near 60ch,
 *      which is a typographic constant, not a taste call.
 *
 *   4. THE SECONDARY ACTION DISAPPEARS WHEN UNSOURCED. This build harvested one
 *      CTA, not two; `{secondary_cta_text}` comes back empty and the button is
 *      simply not rendered, rather than shipping a ghost button to nowhere.
 *
 *   5. NO GLOW UNDER THE BUTTON. The primary action previously carried a 40px
 *      accent-tinted drop shadow — a dark-system device, where a coloured bloom
 *      reads as light emitted onto a black ground. The ratified benchmark
 *      measured a single soft 0.1-alpha layer on five elements and states
 *      outright that elevation is carried by surface tint and radius, not by
 *      shadow. On a white ground that bloom is a smear, so it is removed; the
 *      button's presence comes from the accent fill and the full-pill radius.
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
// Tokens: {eyebrow} {headline} {subheadline} {primary_cta_text} {primary_cta_url} {secondary_cta_text} {secondary_cta_url} {backdrop_url}

// The DEMAND declaration, read by `asset_resolver.art_declarations()`.
//
// `centered` means the words are the subject, and note 1 composes a ground out
// of the palette so the section never depends on an asset. That stays true —
// but "never depends on" became "never has": this variant opened all five
// routes of the last build and the whole site carried five images. The backdrop
// is the design ASKING, which is the one thing that was missing.
//
// `texture`, not `scene`: it sits behind display type at low alpha under the
// radial wash, so it must carry no subject of its own to compete with the
// headline and no detail that survives being dimmed. Decorative in the strict
// sense — the section renders identically well with nothing here, which is why
// an empty slot is not a defect and a missing generation is not a blocked build.
// Art: slot=backdrop_url intent=texture aspect=16:9 role=decorative

interface HeroCenteredProps {
  eyebrow?: string;
  headline?: string;
  subheadline?: string;
  primaryCtaText?: string;
  primaryCtaUrl?: string;
  secondaryCtaText?: string;
  secondaryCtaUrl?: string;
  backdropUrl?: string;
}

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";
//: See note 1. Both washes mix the ACCENT token — whose own fallback is
//: --foreground — into --background, so no opaque literal is ever named and the
//: ground follows the palette on any tenant rather than one grey.
const GROUND = `linear-gradient(180deg, var(--background) 0%, color-mix(in srgb, ${ACCENT} 6%, var(--background)) 100%)`;
const WASH = `color-mix(in srgb, ${ACCENT} 9%, transparent)`;

export default function HeroCentered({
  eyebrow = "{eyebrow}",
  headline = "{headline}",
  subheadline = "{subheadline}",
  primaryCtaText = "{primary_cta_text}",
  primaryCtaUrl = "{primary_cta_url}",
  secondaryCtaText = "{secondary_cta_text}",
  secondaryCtaUrl = "{secondary_cta_url}",
  backdropUrl = "{backdrop_url}",
}: HeroCenteredProps) {
  if (!headline && !subheadline) return null;

  // `<Image src="">` THROWS in next/image, so an unresolved slot must never
  // reach the DOM — the guard is the value being falsy, never a fallback path.
  const backdrop = backdropUrl && backdropUrl.trim() ? backdropUrl : null;

  return (
    <section
      className="relative w-full overflow-hidden"
      style={{
        background: GROUND,
        color: "var(--foreground)",
        // 120px * 1.5 = the 180px hero-specific top padding the benchmark
        // measured on 25 elements; the 120px default carries the bottom.
        paddingTop: "calc(var(--section-py, 120px) * 1.5)",
        paddingBottom: "var(--section-py, 120px)",
      }}
    >
      {/* Commissioned texture, when one exists. It sits BENEATH the radial
          wash and at low alpha deliberately: the contrast pair this section is
          measured on is --foreground on --background, and an image at full
          strength behind display type would put the headline over an unmeasured
          ground. At 0.14 over the opaque gradient the composited ground stays
          within a few percent of --background, so the measured ratio holds for
          any picture — including one that comes back brighter than intended. */}
      {backdrop && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0"
          style={{ opacity: 0.14 }}
        >
          <Image src={backdrop} alt="" fill sizes="100vw" className="object-cover" />
        </div>
      )}

      {/* Composed ground — derived from the accent token, no asset. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background: `radial-gradient(58% 46% at 50% 0%, ${WASH} 0%, transparent 70%)`,
        }}
      />

      <div className="relative mx-auto flex w-full max-w-4xl flex-col items-center px-6 text-center">
        {eyebrow && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="inline-flex items-center gap-2.5 rounded-full border px-4 py-1.5"
            style={{
              borderColor: HAIRLINE,
              background: "var(--background)",
              marginBottom: "var(--block-gap, 24px)",
            }}
          >
            <span
              aria-hidden="true"
              className="block h-1.5 w-1.5 rounded-full"
              style={{ background: ACCENT }}
            />
            <span
              className="uppercase tracking-[0.14em]"
              style={{
                color: MUTED,
                fontFamily: "var(--font-body, inherit)",
                fontSize: "0.75rem",
              }}
            >
              {eyebrow}
            </span>
          </motion.div>
        )}

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          // 48 → 64 → 96px in DISCRETE steps. This was a clamp() across the
          // same endpoints, which reads as the same intent but is not: clamp
          // interpolates, so every viewport between ~750px and 1500px rendered
          // a size that is on no step of the declared scale — at the 1440px
          // audit viewport, 92px. A type scale is a closed set, not a
          // continuum, so the ramp is breakpoints and every rung is a
          // scale_px value.
          className="text-balance text-[3rem] md:text-[4rem] lg:text-[6rem]"
          style={{
            fontFamily: "var(--font-heading, inherit)",
            fontWeight: "var(--heading-weight, 500)" as unknown as number,
            lineHeight: 1.05,
            letterSpacing: "-0.025em",
          }}
        >
          {headline}
        </motion.h1>

        {subheadline && (
          <motion.p
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.08, ease: "easeOut" }}
            className="text-pretty leading-relaxed"
            style={{
              color: MUTED,
              fontFamily: "var(--font-body, inherit)",
              fontSize: "1.25rem",
              marginTop: "var(--block-gap, 24px)",
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
            className="flex flex-wrap items-center justify-center gap-4"
            style={{ marginTop: "calc(var(--block-gap, 24px) * 2)" }}
          >
            {primaryCtaText && (
              <a
                href={primaryCtaUrl || "#"}
                className="inline-flex items-center px-8 py-4 text-base transition-opacity hover:opacity-90"
                style={{
                  background: ACCENT,
                  // --on-accent is always emitted and is compiled for 8.57:1 on
                  // the tenant accent; the fallback is the ground the accent
                  // sits on, never a literal white. No boxShadow — see note 5.
                  color: "var(--on-accent, var(--background))",
                  borderRadius: "var(--radius-button, 100px)",
                  fontFamily: "var(--font-body, inherit)",
                  fontWeight: 500,
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
                  borderRadius: "var(--radius-button, 100px)",
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

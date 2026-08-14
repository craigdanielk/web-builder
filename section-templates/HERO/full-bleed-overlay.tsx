"use client";

import Image from "next/image";
import { motion } from "framer-motion";

/**
 * HERO | full-bleed-overlay
 * Token-driven section template — tenant content filled at build time.
 *
 * What this replaces: a hero whose entire visual identity was three literals —
 * `text-white`, `bg-white/60` and a `from-black/60 via-black/40 to-black/70`
 * scrim — plus `bg-{{brand.accent}}` Tailwind class interpolation that only
 * resolves if the accent happens to be a Tailwind palette name. Every tenant
 * got the same dark-photo look whatever the compiled palette said, and the
 * accent button silently lost its colour whenever the benchmark produced a hex.
 *
 * Decisions:
 *
 *   1. THE SCRIM IS THE PAGE GROUND, NOT BLACK. A full-bleed hero's hard part
 *      is legibility: text sits on an image nobody chose for contrast. The
 *      benchmark compiles --foreground to be legible on --background, so the
 *      scrim re-creates --background over the photo
 *      (`color-mix(in srgb, var(--background) N%, transparent)`) and the copy
 *      keeps using --foreground. That contrast pair is the one the compiler
 *      already guarantees — on a light tenant the veil is pale and the text
 *      dark, on a dark tenant the reverse, with no branch in this file. A
 *      black scrim + `text-white` guarantees it for exactly one palette.
 *      Density ramps downward (55% → 92%) because the copy stacks toward the
 *      bottom and the top of the frame is where the image is worth seeing.
 *
 *   2. NO IMAGE MEANS NO IMAGE. `<Image src="">` THROWS in next/image, and a
 *      `bg-cover` div with `url(undefined)` renders a broken frame that every
 *      string check passes. When the harvest resolved nothing, no <img> and no
 *      background-image is emitted at all: the section falls back to a
 *      token-coloured ground and the scrim is skipped (it would only mute the
 *      copy against a flat ground it was never needed for).
 *
 *   3. ACCENT IS PUNCTUATION. Eyebrow rule and primary action only — matching
 *      HERO | split-image and FEATURES | icon-grid, so a page carrying two of
 *      them reads as one design rather than two.
 *
 *   4. HIERARCHY BY SIZE, NOT WEIGHT. Weight comes from --heading-weight (400
 *      under this benchmark); nothing here reaches for font-bold.
 *
 * There is no repeated array in this template — a full-bleed hero has one
 * headline, one subheadline and at most two actions — so there are no fixed-N
 * slots to convert to a repeat block, and none are invented to have some. Every
 * slot below is a slot the harvest can actually source.
 *
 * Slots:
 *   {eyebrow}            → "Licensed FSP 53746"        (optional)
 *   {headline}           → "Buy Bitcoin South Africa"
 *   {subheadline}        → "Lowest trade fees in SA…"  (optional)
 *   {primary_cta_text}   → "Sign up"                   (optional)
 *   {primary_cta_url}    → "/signup"
 *   {secondary_cta_text} → "See fees"                  (optional)
 *   {secondary_cta_url}  → "/fees"
 *   {bg_image_url}       → resolved local asset        (optional)
 *   {bg_image_alt}       → alt text for the above
 */

// The prose block above is documentation. THIS line is the contract:
// `slot_contract.declared_slots()` reads only `// Tokens:` (and the one legacy
// `Slot placeholders:` block). With neither, `no_declaration` is true and every
// non-reserved brace token in the body is treated as fillable — that is how a
// JSX prop holding a loop variable had its value substituted away and took a
// build down with `Expected '</', got 'ident'`. Declared, the sweep never runs
// and only the nine names below are ever substituted.
// Tokens: {eyebrow} {headline} {subheadline} {primary_cta_text} {primary_cta_url} {secondary_cta_text} {secondary_cta_url} {bg_image_url} {bg_image_alt}

interface HeroFullBleedOverlayProps {
  eyebrow?: string;
  headline?: string;
  subheadline?: string;
  primaryCtaText?: string;
  primaryCtaUrl?: string;
  secondaryCtaText?: string;
  secondaryCtaUrl?: string;
  bgImageUrl?: string;
  bgImageAlt?: string;
}

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";

//: The scrim. See note 1 — this is --background re-laid over the photograph,
//: never a black wash, so the --foreground/--background contrast the compiler
//: guarantees is the contrast the copy actually gets on either polarity.
const SCRIM =
  "linear-gradient(to bottom," +
  " color-mix(in srgb, var(--background) 55%, transparent) 0%," +
  " color-mix(in srgb, var(--background) 78%, transparent) 45%," +
  " color-mix(in srgb, var(--background) 92%, transparent) 100%)";

export default function HeroFullBleedOverlay({
  eyebrow = "{eyebrow}",
  headline = "{headline}",
  subheadline = "{subheadline}",
  primaryCtaText = "{primary_cta_text}",
  primaryCtaUrl = "{primary_cta_url}",
  secondaryCtaText = "{secondary_cta_text}",
  secondaryCtaUrl = "{secondary_cta_url}",
  bgImageUrl = "{bg_image_url}",
  bgImageAlt = "{bg_image_alt}",
}: HeroFullBleedOverlayProps) {
  // A hero is its headline. A section carrying only a subheadline is an orphan
  // line of body copy above the fold — worse than no hero at all.
  if (!headline || !headline.trim()) return null;

  // An unresolved src must never reach next/image — it throws, and the whole
  // route errors while every string and brace check passes.
  const bgImage = bgImageUrl && bgImageUrl.trim() ? bgImageUrl : null;

  return (
    <section
      className="relative flex w-full items-center justify-center overflow-hidden"
      style={{
        background: "var(--background)",
        color: "var(--foreground)",
        paddingTop: "calc(var(--section-py, 96px) * 1.5)",
        paddingBottom: "calc(var(--section-py, 96px) * 1.5)",
        minHeight: "min(88vh, 900px)",
      }}
    >
      {bgImage && (
        <>
          <Image
            src={bgImage}
            alt={bgImageAlt && bgImageAlt.trim() ? bgImageAlt : ""}
            fill
            priority
            sizes="100vw"
            className="object-cover"
          />
          {/* Scrim only exists to rescue text from a photograph; over a flat
              token ground it would only mute the copy, so it is not rendered. */}
          <div aria-hidden="true" className="absolute inset-0" style={{ background: SCRIM }} />
        </>
      )}

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
        className="relative z-10 mx-auto w-full max-w-3xl px-6 text-center"
      >
        {eyebrow && (
          <div className="mb-6 flex items-center justify-center gap-3">
            <span
              aria-hidden="true"
              className="block h-[3px] w-8"
              style={{ background: ACCENT, borderRadius: "var(--radius-button, 4px)" }}
            />
            <span
              className="text-xs uppercase tracking-[0.16em]"
              style={{ color: ACCENT, fontFamily: "var(--font-body, inherit)" }}
            >
              {eyebrow}
            </span>
          </div>
        )}

        <h1
          className="text-[2.75rem] leading-[1.05] tracking-[-0.025em] md:text-[4rem]"
          style={{
            fontFamily: "var(--font-heading, inherit)",
            fontWeight: "var(--heading-weight, 400)" as unknown as number,
          }}
        >
          {headline}
        </h1>

        {subheadline && (
          <p
            className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed md:text-xl"
            style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
          >
            {subheadline}
          </p>
        )}

        {(primaryCtaText || secondaryCtaText) && (
          <div
            className="flex flex-wrap items-center justify-center gap-4"
            style={{ marginTop: "var(--block-gap, 48px)" }}
          >
            {primaryCtaText && (
              <a
                href={primaryCtaUrl || "#"}
                className="inline-flex items-center px-7 py-3.5 text-base transition-opacity hover:opacity-90"
                style={{
                  background: ACCENT,
                  // --on-accent is always emitted; the fallback is the ground
                  // the accent sits on, not a literal white, so a pale accent
                  // on a dark tenant still yields legible label text.
                  color: "var(--on-accent, var(--background))",
                  borderRadius: "var(--radius-button, 4px)",
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
                className="inline-flex items-center border px-7 py-3.5 text-base transition-colors"
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
          </div>
        )}
      </motion.div>
    </section>
  );
}

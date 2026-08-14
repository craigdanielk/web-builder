"use client";

import Image from "next/image";
import { motion } from "framer-motion";

/**
 * HERO | full-bleed-overlay
 * Token-driven section template — tenant content filled at build time.
 *
 * What this replaces: a hero whose entire visual identity was three literals —
 * a hardcoded white text colour, a translucent white pill and a three-stop
 * black wash — plus Tailwind class interpolation on the accent that only
 * resolved if the accent happened to be a Tailwind palette name. Every tenant
 * got the same dark-photo look whatever the compiled palette said, and the
 * accent button silently lost its colour whenever the benchmark produced a hex.
 *
 * Decisions:
 *
 *   1. THE SCRIM IS GONE. NO TEXT SITS ON THE PHOTOGRAPH AT ALL.
 *
 *      A darkening scrim is a dark-system device: it exists so white text can
 *      survive an image nobody chose for contrast. The ratified benchmark is
 *      light — ground #ffffff, copy #242d35 — so the premise inverts, and the
 *      obvious inversion (a pale veil instead of a black one) is arithmetically
 *      unsafe. A white veil at the previous 55% top stop over a black
 *      photograph composites to roughly a 57%-grey; #242d35 on that grey is
 *      4.37:1 and FAILS AA. The veil would need to be opaque before the ratio
 *      is guaranteed, at which point it is no longer a scrim.
 *
 *      So the contrast problem is designed out rather than tuned. The copy sits
 *      on an OPAQUE --surface plane laid over the full-bleed image. The pair is
 *      then the one the benchmark measured directly — text_primary on surface,
 *      12.55:1 — and it holds for every photograph, including a blown-out white
 *      sky, which is the exact failure a light-system scrim cannot survive.
 *      The image stays full-bleed around the plane; it is composition, not a
 *      contrast substrate. Cape Crypto is an FSP (No. 53746); "usually legible"
 *      is not a standard.
 *
 *   2. THE GROUND IS THE REFERENCE'S GRADIENT, DERIVED NOT COPIED. The
 *      reference hero is a white-to-pale-blue gradient over the page ground.
 *      The token vocabulary carries no pale-blue token (the benchmark's
 *      bg_secondary was not compiled), so rather than invent a hex the wash is
 *      mixed from the tokens that do exist: 6% --accent into --background. The
 *      tenant accent IS blue (#004e89), so this lands in the same family while
 *      staying tenant-derived on any future palette.
 *
 *   3. HIERARCHY BY SIZE, NOT WEIGHT. --heading-weight is 500 under this
 *      benchmark and every measured H1/H2 renders at 500; 700 appears on inline
 *      text only. The headline clamps 48px → 96px, the two display sizes the
 *      reference actually uses. Nothing here reaches for font-bold.
 *
 *   4. NO IMAGE MEANS NO IMAGE. `<Image src="">` THROWS in next/image, and a
 *      `bg-cover` div with an undefined url renders a broken frame that every
 *      string check passes. When the harvest resolved nothing, no <img> is
 *      emitted at all — and the plane drops its surface, border and shadow so
 *      the copy reads as a hero on the gradient ground rather than as a card
 *      floating in a void.
 *
 *   5. ACCENT IS PUNCTUATION. Eyebrow rule and primary action only — matching
 *      HERO | split-image and FEATURES | icon-grid, so a page carrying two of
 *      them reads as one design rather than two.
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

//: The reference's white-to-pale-blue hero ground. See note 2 — the pale stop
//: is 6% of the accent mixed into the background, because the vocabulary has no
//: bg_secondary token and a hex invented to fill that gap is fabrication.
const GROUND =
  "linear-gradient(180deg," +
  " var(--background) 0%," +
  ` color-mix(in srgb, ${ACCENT} 6%, var(--background)) 100%)`;

//: The copy plane's lift. The benchmark measured max_layers = 1 — a single soft
//: layer at 0.1 alpha — and elevation carried by surface tint and radius rather
//: than by shadow. The colour is derived from --foreground, not the measured
//: navy: a fixed navy is a shadow for ONE palette on ONE ground.
const PANEL_SHADOW = "0 1px 8px color-mix(in srgb, var(--foreground) 10%, transparent)";

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

  // With a photograph behind it the plane must be opaque (note 1). Without one
  // there is nothing to lift off, and a bordered card on a bare gradient is
  // decoration pretending to be structure.
  const panelStyle = bgImage
    ? {
        background: "var(--surface, var(--background))",
        border: `1px solid ${HAIRLINE}`,
        borderRadius: "var(--radius-card, 16px)",
        boxShadow: PANEL_SHADOW,
        padding: "calc(var(--card-pad, 40px) * 1.5)",
      }
    : { padding: "0px" };

  return (
    <section
      className="relative flex w-full items-center justify-center overflow-hidden px-6"
      style={{
        background: GROUND,
        color: "var(--foreground)",
        // 120px * 1.5 = the 180px hero-specific top padding the benchmark
        // measured on 25 elements; the 120px default carries the bottom.
        paddingTop: "calc(var(--section-py, 120px) * 1.5)",
        paddingBottom: "var(--section-py, 120px)",
        minHeight: "min(88vh, 900px)",
      }}
    >
      {bgImage && (
        <Image
          src={bgImage}
          alt={bgImageAlt && bgImageAlt.trim() ? bgImageAlt : ""}
          fill
          priority
          sizes="100vw"
          className="object-cover"
        />
      )}

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="relative z-10 mx-auto w-full max-w-3xl text-center"
        style={panelStyle}
      >
        {eyebrow && (
          <div
            className="flex items-center justify-center gap-3"
            style={{ marginBottom: "var(--block-gap, 24px)" }}
          >
            <span
              aria-hidden="true"
              className="block h-[3px] w-8"
              style={{ background: ACCENT, borderRadius: "var(--radius-button, 100px)" }}
            />
            <span
              className="uppercase tracking-[0.16em]"
              style={{
                color: ACCENT,
                fontFamily: "var(--font-body, inherit)",
                fontSize: "0.75rem",
              }}
            >
              {eyebrow}
            </span>
          </div>
        )}

        <h1
          className="text-balance"
          style={{
            fontFamily: "var(--font-heading, inherit)",
            fontWeight: "var(--heading-weight, 500)" as unknown as number,
            // 48px → 96px: the display sizes the reference actually renders.
            fontSize: "clamp(3rem, 6.4vw, 6rem)",
            lineHeight: 1.05,
            letterSpacing: "-0.025em",
          }}
        >
          {headline}
        </h1>

        {subheadline && (
          <p
            className="mx-auto text-pretty leading-relaxed"
            style={{
              color: MUTED,
              fontFamily: "var(--font-body, inherit)",
              fontSize: "1.25rem",
              marginTop: "var(--block-gap, 24px)",
              maxWidth: "58ch",
            }}
          >
            {subheadline}
          </p>
        )}

        {(primaryCtaText || secondaryCtaText) && (
          <div
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
                  // sits on, never a literal white.
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
          </div>
        )}
      </motion.div>
    </section>
  );
}

"use client";

import Image from "next/image";
import { motion } from "framer-motion";

/**
 * HERO | product-hero
 * Token-driven section template — tenant content filled at build time.
 *
 * The product photograph is the subject: it fills the section, and the copy
 * sits on the side the art direction leaves clear (left). Fills the library
 * gap a declared `data-variant="product-hero"` names; no tenant literals.
 *
 *   1. THE IMAGE IS SEEN, NOT TEXTURED. Full opacity, object-position right,
 *      so the product lands on the side away from the copy.
 *   2. CONTRAST IS DESIGNED IN. The copy side is a ramp from the section's own
 *      --background (solid behind the text) to transparent — derived from the
 *      tone the section declares, so it holds on a dark or a light ground.
 *   3. MOBILE STACKS. Below md the image is its own block above the copy; no
 *      text ever sits on an unscrimmed photograph.
 *   4. NO IMAGE, NO FRAME. An unfilled image slot renders a plain copy hero.
 *   5. HEADINGS READ THE TYPE TIERS (--type-h1 / --type-h2).
 *
 * Slots:
 *   {eyebrow}            → section kicker (optional)
 *   {headline}           → h1
 *   {tagline}            → second heading (optional)
 *   {subheadline}        → lead paragraph (optional)
 *   {supporting_text}    → second paragraph (optional)
 *   {primary_cta_text} {primary_cta_url} {secondary_cta_text} {secondary_cta_url}
 *   {image_url} {image_alt}
 */

// Tokens: {eyebrow} {headline} {tagline} {subheadline} {supporting_text} {primary_cta_text} {primary_cta_url} {secondary_cta_text} {secondary_cta_url} {image_url} {image_alt}

// Art: slot=image_url intent=product aspect=16:9 role=load-bearing

interface HeroProductHeroProps {
  eyebrow?: string;
  headline?: string;
  tagline?: string;
  subheadline?: string;
  supportingText?: string;
  primaryCtaText?: string;
  primaryCtaUrl?: string;
  secondaryCtaText?: string;
  secondaryCtaUrl?: string;
  imageUrl?: string;
  imageAlt?: string;
}

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";
// The section is sized to the image's own 16:9 on desktop (see minHeight),
// so the photograph is never cropped and the product stays in the half the
// art direction placed it; the ramp only clears the copy side.
const SCRIM = "linear-gradient(90deg, var(--background) 0%, var(--background) 22%, color-mix(in srgb, var(--background) 55%, transparent) 34%, transparent 46%)";

/** A slot value that survived the fill; an unsubstituted placeholder is empty. */
function resolved(value: string | undefined): string {
  if (!value) return "";
  const trimmed = value.trim();
  if (!trimmed || trimmed.startsWith("{")) return "";
  return trimmed;
}

export default function HeroProductHero({
  eyebrow = "{eyebrow}",
  headline = "{headline}",
  tagline = "{tagline}",
  subheadline = "{subheadline}",
  supportingText = "{supporting_text}",
  primaryCtaText = "{primary_cta_text}",
  primaryCtaUrl = "{primary_cta_url}",
  secondaryCtaText = "{secondary_cta_text}",
  secondaryCtaUrl = "{secondary_cta_url}",
  imageUrl = "{image_url}",
  imageAlt = "{image_alt}",
}: HeroProductHeroProps) {
  const title = resolved(headline);
  if (!title) return null;
  const kickerText = resolved(eyebrow);
  const secondLine = resolved(tagline);
  const lead = resolved(subheadline);
  const note = resolved(supportingText);
  const primaryLabel = resolved(primaryCtaText);
  const secondaryLabel = resolved(secondaryCtaText);
  const heroImage = resolved(imageUrl);
  const heroAlt = resolved(imageAlt);

  return (
    <section
      className="relative w-full overflow-hidden"
      style={{
        background: "var(--background)",
        color: "var(--foreground)",
        paddingTop: "var(--section-py, 96px)",
        paddingBottom: "var(--section-py, 96px)",
      }}
    >
      {heroImage && (
        <div className="relative aspect-[16/9] w-full md:absolute md:inset-0 md:aspect-auto">
          <Image
            src={heroImage}
            alt={heroAlt}
            fill
            priority
            sizes="100vw"
            className="object-cover"
            style={{ objectPosition: "right center" }}
          />
          <div aria-hidden="true" className="absolute inset-0 hidden md:block" style={{ background: SCRIM }} />
        </div>
      )}

      <div
        className="relative mx-auto flex w-full max-w-6xl items-center px-6"
        style={{
          // 16:9 overall = 56.25vw minus the section padding above and below.
          minHeight: heroImage ? "calc(56.25vw - 2 * var(--section-py, 96px))" : undefined,
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="w-full max-w-md"
        >
          {kickerText && (
            <p
              className="mb-6 text-xs uppercase tracking-[0.18em]"
              style={{ color: MUTED, fontFamily: "var(--font-body, inherit)", fontWeight: 500 }}
            >
              {kickerText}
            </p>
          )}
          <h1
            className="text-balance"
            style={{
              fontSize: "var(--type-h1, 4rem)",
              fontFamily: "var(--font-heading, inherit)",
              fontWeight: "var(--heading-weight, 400)" as unknown as number,
              lineHeight: 1.1,
              letterSpacing: "-0.02em",
            }}
          >
            {title}
          </h1>
          {secondLine && (
            <h2
              className="text-balance"
              style={{
                fontSize: "var(--type-h2, 2rem)",
                fontFamily: "var(--font-heading, inherit)",
                fontWeight: "var(--heading-weight, 400)" as unknown as number,
                lineHeight: 1.2,
                marginTop: "calc(var(--block-gap, 24px) * 0.5)",
              }}
            >
              {secondLine}
            </h2>
          )}
          {lead && (
            <p
              className="text-pretty text-lg leading-relaxed"
              style={{ color: MUTED, fontFamily: "var(--font-body, inherit)", marginTop: "var(--block-gap, 24px)" }}
            >
              {lead}
            </p>
          )}
          {note && (
            <p
              className="text-pretty text-base leading-relaxed"
              style={{ color: MUTED, fontFamily: "var(--font-body, inherit)", marginTop: "calc(var(--block-gap, 24px) * 0.5)" }}
            >
              {note}
            </p>
          )}
          {(primaryLabel || secondaryLabel) && (
            <div className="flex flex-wrap items-center gap-4" style={{ marginTop: "calc(var(--block-gap, 24px) * 1.5)" }}>
              {primaryLabel && (
                <a
                  href={resolved(primaryCtaUrl) || "#"}
                  className="inline-flex items-center px-8 py-4 text-sm transition-opacity hover:opacity-90"
                  style={{
                    background: ACCENT,
                    color: "var(--on-accent, var(--background))",
                    borderRadius: "var(--radius-button, 6px)",
                    fontFamily: "var(--font-body, inherit)",
                    fontWeight: 500,
                  }}
                >
                  {primaryLabel}
                </a>
              )}
              {secondaryLabel && (
                <a
                  href={resolved(secondaryCtaUrl) || "#"}
                  className="inline-flex items-center border px-8 py-4 text-sm transition-colors hover:[border-color:var(--accent)]"
                  style={{
                    borderColor: HAIRLINE,
                    borderRadius: "var(--radius-button, 6px)",
                    fontFamily: "var(--font-body, inherit)",
                    fontWeight: 500,
                  }}
                >
                  {secondaryLabel}
                </a>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </section>
  );
}

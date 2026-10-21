"use client";

import Image from "next/image";
import { motion } from "framer-motion";

/**
 * CTA | split-with-image
 * Token-driven section template — tenant content filled at build time.
 *
 * A closing band where the image carries one side and the call to action the
 * other (copy right). Mirror of HERO | product-hero, same rules: the image is
 * shown at full strength, the copy side sits on a ramp from the section's own
 * --background, mobile stacks, and an unfilled image renders a plain band.
 *
 * Slots:
 *   {headline} {subheadline} {disclaimer}
 *   {primary_cta_text} {primary_cta_url} {secondary_cta_text} {secondary_cta_url}
 *   {image_url} {image_alt}
 */

// Tokens: {headline} {subheadline} {disclaimer} {primary_cta_text} {primary_cta_url} {secondary_cta_text} {secondary_cta_url} {image_url} {image_alt}

// Art: slot=image_url intent=product aspect=16:9 role=load-bearing

interface CtaSplitWithImageProps {
  ctaHeadline?: string;
  ctaSubheadline?: string;
  ctaDisclaimer?: string;
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
const SCRIM = "linear-gradient(270deg, var(--background) 0%, var(--background) 22%, color-mix(in srgb, var(--background) 55%, transparent) 34%, transparent 46%)";

function resolved(value: string | undefined): string {
  if (!value) return "";
  const trimmed = value.trim();
  if (!trimmed || trimmed.startsWith("{")) return "";
  return trimmed;
}

export default function CtaSplitWithImage({
  ctaHeadline = "{headline}",
  ctaSubheadline = "{subheadline}",
  ctaDisclaimer = "{disclaimer}",
  primaryCtaText = "{primary_cta_text}",
  primaryCtaUrl = "{primary_cta_url}",
  secondaryCtaText = "{secondary_cta_text}",
  secondaryCtaUrl = "{secondary_cta_url}",
  imageUrl = "{image_url}",
  imageAlt = "{image_alt}",
}: CtaSplitWithImageProps) {
  const title = resolved(ctaHeadline);
  const primaryLabel = resolved(primaryCtaText);
  if (!title && !primaryLabel) return null;
  const lead = resolved(ctaSubheadline);
  const fine = resolved(ctaDisclaimer);
  const secondaryLabel = resolved(secondaryCtaText);
  const bandImage = resolved(imageUrl);

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
      {bandImage && (
        <div className="relative aspect-[16/9] w-full md:absolute md:inset-0 md:aspect-auto">
          <Image
            src={bandImage}
            alt={resolved(imageAlt)}
            fill
            sizes="100vw"
            className="object-cover"
            style={{ objectPosition: "left center" }}
          />
          <div aria-hidden="true" className="absolute inset-0 hidden md:block" style={{ background: SCRIM }} />
        </div>
      )}

      <div
        className="relative mx-auto flex w-full max-w-6xl items-center justify-end px-6"
        style={{
          // 16:9 overall = 56.25vw minus the section padding above and below.
          minHeight: bandImage ? "calc(56.25vw - 2 * var(--section-py, 96px))" : undefined,
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="w-full max-w-sm"
        >
          {title && (
            <h2
              className="text-balance"
              style={{
                fontSize: "var(--type-h1, 3rem)",
                fontFamily: "var(--font-heading, inherit)",
                fontWeight: "var(--heading-weight, 400)" as unknown as number,
                lineHeight: 1.1,
                letterSpacing: "-0.02em",
              }}
            >
              {title}
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
          {fine && (
            <p className="mt-6 text-xs leading-relaxed" style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}>
              {fine}
            </p>
          )}
        </motion.div>
      </div>
    </section>
  );
}

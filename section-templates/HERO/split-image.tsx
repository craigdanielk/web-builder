"use client";

import Image from "next/image";
import { motion } from "framer-motion";

/**
 * HERO | split-image
 * Token-driven section template — tenant content filled at build time.
 *
 * The Supabase template this replaces rendered a centred headline, a subtitle
 * and a button floating in white space with no image, no accent and no
 * structure — the weakest thing on the page and the first thing a visitor sees.
 *
 * Decisions:
 *
 *   1. THE IMAGE IS OPTIONAL AND HONEST. If the harvest resolved no hero image,
 *      the media column does not render an empty box, a placeholder or a
 *      stretched logo — the copy column takes the full width and the layout
 *      still reads deliberately. `<Image src="">` THROWS in next/image, so an
 *      unresolved src must never reach the DOM; the guard is `heroImage` being
 *      falsy, not a fallback path.
 *
 *   2. ACCENT IS USED ONCE. The benchmark caps unique colours and treats the
 *      accent as punctuation, not decoration: it appears on the eyebrow rule
 *      and the primary action, nowhere else.
 *
 *   3. HIERARCHY BY SIZE, NOT WEIGHT. --heading-weight is 400 under this
 *      benchmark. The headline is large and light with tight leading; the old
 *      template's bold-everything is what made the page read as a template.
 *
 * Slots:
 *   {eyebrow}            → "Licensed FSP 53746"        (optional)
 *   {headline}           → "Buy Bitcoin South Africa"
 *   {subheadline}        → "Lowest trade fees in SA…"
 *   {primary_cta_text}   → "Sign up"
 *   {primary_cta_url}    → "/signup"
 *   {secondary_cta_text} → "See fees"                  (optional)
 *   {secondary_cta_url}  → "/fees"
 *   {image_url}          → resolved local asset        (optional)
 *   {image_alt}          → alt text for the above
 */

interface HeroSplitImageProps {
  eyebrow?: string;
  headline?: string;
  subheadline?: string;
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

export default function HeroSplitImage({
  eyebrow = "{eyebrow}",
  headline = "{headline}",
  subheadline = "{subheadline}",
  primaryCtaText = "{primary_cta_text}",
  primaryCtaUrl = "{primary_cta_url}",
  secondaryCtaText = "{secondary_cta_text}",
  secondaryCtaUrl = "{secondary_cta_url}",
  imageUrl = "{image_url}",
  imageAlt = "{image_alt}",
}: HeroSplitImageProps) {
  if (!headline && !subheadline) return null;

  // An unresolved src must never reach next/image — it throws, and the whole
  // route errors while every string and brace check passes.
  const heroImage = imageUrl && imageUrl.trim() ? imageUrl : null;

  return (
    <section
      className="w-full overflow-hidden"
      style={{
        background: "var(--background)",
        color: "var(--foreground)",
        paddingTop: "calc(var(--section-py, 96px) * 1.15)",
        paddingBottom: "calc(var(--section-py, 96px) * 1.15)",
      }}
    >
      <div
        className={`mx-auto grid w-full max-w-6xl items-center gap-14 px-6 ${
          heroImage ? "lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]" : ""
        }`}
      >
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className={heroImage ? "" : "max-w-3xl"}
        >
          {eyebrow && (
            <div className="mb-6 flex items-center gap-3">
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
            className="text-[2.75rem] leading-[1.05] tracking-[-0.025em] md:text-[3.5rem]"
            style={{
              fontFamily: "var(--font-heading, inherit)",
              fontWeight: "var(--heading-weight, 400)" as unknown as number,
            }}
          >
            {headline}
          </h1>

          {subheadline && (
            <p
              className="mt-6 max-w-xl text-lg leading-relaxed md:text-xl"
              style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
            >
              {subheadline}
            </p>
          )}

          {(primaryCtaText || secondaryCtaText) && (
            <div className="mt-10 flex flex-wrap items-center gap-4">
              {primaryCtaText && (
                <a
                  href={primaryCtaUrl || "#"}
                  className="inline-flex items-center px-7 py-3.5 text-base transition-opacity hover:opacity-90"
                  style={{
                    background: ACCENT,
                    color: "var(--on-accent, #fff)",
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

        {heroImage && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, delay: 0.1, ease: "easeOut" }}
            className="relative aspect-[4/3] w-full overflow-hidden"
            style={{
              borderRadius: "var(--radius-card, 8px)",
              border: `1px solid ${HAIRLINE}`,
              boxShadow:
                "0 30px 60px -40px rgba(15,27,45,0.28), 0 12px 28px -18px rgba(15,27,45,0.16)",
            }}
          >
            <Image
              src={heroImage}
              alt={imageAlt && imageAlt.trim() ? imageAlt : ""}
              fill
              priority
              sizes="(min-width: 1024px) 45vw, 100vw"
              className="object-cover"
            />
          </motion.div>
        )}
      </div>
    </section>
  );
}

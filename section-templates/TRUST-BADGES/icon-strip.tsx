"use client";

import { motion } from "framer-motion";

/**
 * TRUST-BADGES | icon-strip
 * Parameterized section template — tenant content filled at build time.
 *
 * A hairline-separated strip of credibility statements: a short label (a
 * figure, a licence, a capability) over a one-line qualifier. The library had
 * `horizontal-strip` and `inline-strip` but not this variant, so every page
 * carrying it fell through to the LLM.
 *
 * Three decisions worth stating, because each is a deliberate departure:
 *
 *   1. ARITY IS NOT FIXED. The badge row is written once, between the
 *      `/* repeat:badges *\/` markers, and emitted once per harvested item —
 *      three on a page with three, six on a page with six, none on a page with
 *      none. The 17 archetypes that spell out `{badge_1_label} … {badge_6_label}`
 *      cap the render at whatever number their author typed, which is what
 *      keeps the fabrication tables alive; this one has no such number.
 *
 *   2. NO ICON IS SOURCED. The archetype is named "icon-strip", but the
 *      harvest carries headings, body text, CTAs and images and nothing else —
 *      an icon NAME is unfillable, and filling it from the heading list is how
 *      `icon: 'Lowest trading fees in South Africa'` happened. The mark beside
 *      each badge is therefore a CSS rule, decorative and content-free, not a
 *      slot pretending to hold an icon.
 *
 *   3. COLOUR COMES FROM THE PAGE. `{{brand.*}}` tokens are only substituted
 *      on the `--industry` path, where a BuildCache carries a style config; a
 *      harvest-driven build has none, and a template written against them
 *      ships `bg-{{brand.bg_dark}}` as a literal class. Everything here reads
 *      the CSS custom properties the generated `globals.css` actually defines,
 *      with muted and hairline tones derived from them via `color-mix`, so the
 *      section takes the tenant's palette without naming a single brand value.
 *
 * Slot placeholders (filled by tenant data):
 *   {section_title}     → "Everything you need to integrate"  (may be empty)
 *   {section_subtitle}  → "Trusted by South Africans since 2020"
 *   {badges[].label}    → "R1B+" / "REST API"
 *   {badges[].detail}   → "Trading volume" / "Clean, predictable JSON endpoints."
 */

interface Badge {
  label: string;
  detail: string;
}

interface TrustBadgesIconStripProps {
  sectionTitle?: string;
  sectionSubtitle?: string;
  badges?: Badge[];
}

const harvestedBadges: Badge[] = [
  /* repeat:badges */
  { label: "{badges[].label}", detail: "{badges[].detail}" },
  /* /repeat */
];

const MUTED = "color-mix(in srgb, var(--foreground) 62%, var(--background))";
const HAIRLINE = "color-mix(in srgb, var(--foreground) 14%, var(--background))";
const MARK = "color-mix(in srgb, var(--accent, var(--foreground)) 55%, var(--background))";

export default function TrustBadgesIconStrip({
  sectionTitle = "{section_title}",
  sectionSubtitle = "{section_subtitle}",
  badges = harvestedBadges,
}: TrustBadgesIconStripProps) {
  if (!badges.length && !sectionTitle && !sectionSubtitle) return null;

  return (
    <section
      className="w-full py-14 md:py-20"
      style={{ background: "var(--background)", color: "var(--foreground)" }}
    >
      <div className="mx-auto w-full max-w-6xl px-6">
        {(sectionTitle || sectionSubtitle) && (
          <div className="mb-10 max-w-3xl">
            {sectionTitle && (
              <h2
                className="text-2xl md:text-3xl font-semibold tracking-tight leading-tight"
                style={{ fontFamily: "var(--font-heading, inherit)" }}
              >
                {sectionTitle}
              </h2>
            )}
            {sectionSubtitle && (
              <p
                className="mt-3 text-base md:text-lg leading-relaxed"
                style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
              >
                {sectionSubtitle}
              </p>
            )}
          </div>
        )}

        <ul
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 border-t"
          style={{ borderColor: HAIRLINE }}
        >
          {badges.map((badge, index) => (
            <motion.li
              key={index}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: index * 0.06, ease: "easeOut" }}
              className="flex gap-4 border-b py-6 pr-6 sm:py-7"
              style={{ borderColor: HAIRLINE }}
            >
              {/* Decorative mark — deliberately content-free; see note 2 above. */}
              <span
                aria-hidden="true"
                className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: MARK, boxShadow: `0 0 0 4px ${HAIRLINE}` }}
              />
              <div className="min-w-0">
                <p
                  className="text-lg md:text-xl font-semibold leading-snug"
                  style={{ fontFamily: "var(--font-heading, inherit)" }}
                >
                  {badge.label}
                </p>
                {badge.detail && (
                  <p
                    className="mt-1.5 text-sm md:text-base leading-relaxed"
                    style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                  >
                    {badge.detail}
                  </p>
                )}
              </div>
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  );
}

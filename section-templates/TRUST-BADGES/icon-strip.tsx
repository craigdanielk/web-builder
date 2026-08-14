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
 *   3. COLOUR, RHYTHM AND WEIGHT COME FROM THE PAGE. `{{brand.*}}` tokens are
 *      only substituted on the `--industry` path, where a BuildCache carries a
 *      style config; a harvest-driven build has none, and a template written
 *      against them ships `bg-{{brand.bg_dark}}` as a literal class. Everything
 *      here reads the CSS custom properties the generated `globals.css`
 *      actually defines — `--accent`, `--foreground`, `--background`,
 *      `--muted`, `--border`, `--section-py`, `--block-gap`, `--card-pad`,
 *      `--heading-weight` — with translucent tones derived via `color-mix` off
 *      those same properties so they hold on light AND dark ground. Nothing
 *      here reaches for `font-bold`: weight is `--heading-weight`, because the
 *      benchmark's defining observation is that reference headlines are LIGHT.
 *
 *      The section band is `--section-py` scaled, not `py-14 md:py-20`. A
 *      credibility strip is deliberately tighter than a content section, so it
 *      DERIVES from the rhythm token rather than opting out of it — a literal
 *      pair cannot follow a tenant whose sections breathe wider or narrower.
 *
 * Slot placeholders (filled by tenant data):
 *   {section_title}     → "Everything you need to integrate"  (may be empty)
 *   {section_subtitle}  → "Trusted by South Africans since 2020"
 *   {badges[].label}    → "R1B+" / "REST API"
 *   {badges[].detail}   → "Trading volume" / "Clean, predictable JSON endpoints."
 */

// Tokens: {section_title} {section_subtitle} {badges[].label} {badges[].detail}

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

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 14%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";
// The mark's halo is foreground-derived, never a fixed rgba — a translucent
// white ring vanishes on a light ground and a black one on a dark one.
const HALO = "color-mix(in srgb, var(--foreground) 10%, transparent)";


export default function TrustBadgesIconStrip({
  sectionTitle = "{section_title}",
  sectionSubtitle = "{section_subtitle}",
  badges = harvestedBadges,
}: TrustBadgesIconStripProps) {
  // A heading over an empty strip is worse than no section.
  if (!badges.length) return null;

  return (
    <section
      className="w-full"
      style={{
        background: "var(--background)",
        color: "var(--foreground)",
        // A strip is a tighter band than a content section, but the tightness
        // is a RATIO of the tenant's rhythm, never a number typed here.
        paddingTop: "calc(var(--section-py, 96px) * 0.7)",
        paddingBottom: "calc(var(--section-py, 96px) * 0.7)",
      }}
    >
      <div className="mx-auto w-full max-w-6xl px-6">
        {(sectionTitle || sectionSubtitle) && (
          <div className="max-w-3xl" style={{ marginBottom: "var(--block-gap, 48px)" }}>
            {sectionTitle && (
              <h2
                className="text-2xl md:text-3xl tracking-tight leading-tight"
                style={{
                  fontFamily: "var(--font-heading, inherit)",
                  fontWeight: "var(--heading-weight, 400)" as unknown as number,
                }}
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
              className="flex gap-4 border-b"
              style={{
                borderColor: HAIRLINE,
                paddingTop: "calc(var(--card-pad, 32px) * 0.75)",
                paddingBottom: "calc(var(--card-pad, 32px) * 0.75)",
                paddingRight: "var(--card-pad, 32px)",
              }}
            >
              {/* Decorative mark — deliberately content-free; see note 2 above. */}
              <span
                aria-hidden="true"
                className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: ACCENT, boxShadow: `0 0 0 4px ${HALO}` }}
              />
              <div className="min-w-0">
                <p
                  className="text-lg md:text-xl leading-snug"
                  style={{
                    fontFamily: "var(--font-heading, inherit)",
                    fontWeight: 500,
                  }}
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

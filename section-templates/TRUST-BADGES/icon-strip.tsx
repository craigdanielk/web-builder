"use client";

import { motion } from "framer-motion";

/**
 * TRUST-BADGES | icon-strip
 * Token-driven section template — tenant content filled at build time.
 *
 * A separated strip of credibility statements: a short label (a figure, a
 * licence, a capability) over a one-line qualifier. The library had
 * `horizontal-strip` and `inline-strip` but not this variant, so every page
 * carrying it fell through to the LLM.
 *
 * Four decisions worth stating, because each is a deliberate departure:
 *
 *   1. ARITY IS NOT FIXED. The badge row is written once, between the
 *      `/* repeat:badges *\/` markers, and emitted once per harvested item —
 *      three on a page with three, six on a page with six, none on a page with
 *      none. The 17 archetypes that spell out `badge_1_label … badge_6_label`
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
 *   3. COLOUR, RHYTHM AND WEIGHT COME FROM THE PAGE. Mustache brand tokens are
 *      only substituted on the `--industry` path, where a BuildCache carries a
 *      style config; a harvest-driven build has none, and a template written
 *      against them ships the unsubstituted mustache as a literal class name.
 *      Everything here reads the CSS custom properties the generated
 *      `globals.css` actually defines — --accent, --foreground, --background,
 *      --surface, --muted, --border, --section-py, --block-gap, --card-pad,
 *      --radius-card, --heading-weight — with translucent tones derived via
 *      `color-mix` off those same properties so they hold on light AND dark
 *      ground. Fallbacks carry the ratified light benchmark
 *      (benchmarks/enterprise-payments-bvnk.json), which supersedes the dark
 *      Robinhood capture. Nothing here reaches for font-bold: display weight is
 *      --heading-weight, and the benchmark measures every H1/H2 at 500.
 *
 *      The section band is --section-py itself — not a Tailwind step, and not a
 *      ratio of the token either. This file historically carried the library's
 *      one real rhythm literal — a hardcoded Tailwind padding pair — which
 *      silently overrode the benchmark's 120px; a 0.7 multiplier overrode it
 *      just as silently, to 84px. The band is the tenant's rhythm, unscaled.
 *
 *   4. THE BADGE SURFACE IS A TOKEN, THE BADGE ARTWORK IS UNTOUCHED. Regulator,
 *      licence and compliance marks on an FSP-regulated site are evidentiary
 *      imagery; recolouring them to suit a ground is a misrepresentation, not a
 *      style fix. So the cell's ground is --surface and the marks themselves are
 *      never filtered, inverted or tinted. See the note in the header of the
 *      cell block for the residual risk this leaves.
 *
 * Slot placeholders (filled by tenant data):
 *   {section_title}     → "Everything you need to integrate"  (may be empty)
 *   {section_subtitle}  → "Trusted by South Africans since 2020"
 *   {badges[].label}    → "R1B+" / "REST API"
 *   {badges[].detail}   → "Trading volume" / "Clean, predictable JSON endpoints."
 */

// The machine-read declaration. `slot_contract.declared_slots()` reads ONLY a
// `// Tokens:` line or a `Slot placeholders` block — the prose list above is
// neither, so without this line the contract falls back to a permissive brace
// sweep and substitutes this file's own JS identifiers away.
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

const mutedColor = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const hairlineColor = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const accentColor = "var(--accent, var(--foreground))";
// The mark's halo is foreground-derived, never a fixed rgba — a translucent
// white ring vanishes on a light ground and a black one on a dark one.
const haloColor = "color-mix(in srgb, var(--foreground) 10%, transparent)";

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
        paddingTop: "var(--section-py, 120px)",
        paddingBottom: "var(--section-py, 120px)",
      }}
    >
      <div className="mx-auto w-full max-w-6xl px-6">
        {(sectionTitle || sectionSubtitle) && (
          <div className="max-w-3xl" style={{ marginBottom: "var(--block-gap, 24px)" }}>
            {sectionTitle && (
              <h2
                className="text-3xl md:text-[2.75rem] leading-[1.1] tracking-tight"
                style={{
                  fontFamily: "var(--font-heading, inherit)",
                  fontWeight: "var(--heading-weight, 500)" as unknown as number,
                }}
              >
                {sectionTitle}
              </h2>
            )}
            {sectionSubtitle && (
              <p
                className="mt-5 text-lg leading-relaxed"
                style={{ color: mutedColor, fontFamily: "var(--font-body, inherit)" }}
              >
                {sectionSubtitle}
              </p>
            )}
          </div>
        )}

        {/* Hairline separation is the grid's own background showing through a
            1px gap, so the cells need no borders and the strip needs no rules
            that would have to be recoloured per ground. */}
        <ul
          className="grid grid-cols-1 gap-px overflow-hidden sm:grid-cols-2 lg:grid-cols-3"
          style={{
            background: hairlineColor,
            borderRadius: "var(--radius-card, 16px)",
          }}
        >
          {badges.map((badge, index) => (
            <motion.li
              key={index}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: index * 0.06, ease: "easeOut" }}
              className="flex gap-4"
              style={{
                // Badge marks are supplied artwork and are never restyled — the
                // GROUND moves instead of the mark. --surface is the benchmark's
                // neutral card tint, so a mark reads against a tinted panel
                // rather than floating on raw page white.
                background: "var(--surface, var(--background))",
                padding: "var(--card-pad, 40px)",
              }}
            >
              {/* Decorative mark — deliberately content-free; see note 2 above. */}
              <span
                aria-hidden="true"
                className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: accentColor, boxShadow: `0 0 0 4px ${haloColor}` }}
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
                    style={{ color: mutedColor, fontFamily: "var(--font-body, inherit)" }}
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

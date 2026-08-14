"use client";

import { motion } from "framer-motion";

/**
 * FEATURES | icon-grid
 * Token-driven section template — tenant content filled at build time.
 *
 * Replaces the Supabase template that shipped `bg-white text-gray-900 py-24`
 * and an empty grey rounded square where an icon should be. Three deliberate
 * departures:
 *
 *   1. EVERY COLOUR, SIZE AND RHYTHM IS A TOKEN. Not one Tailwind palette
 *      literal. The build compiles the market benchmark into CSS custom
 *      properties (--accent, --foreground, --muted, --border, --section-py,
 *      --heading-weight …) and this reads them, so the same file renders a
 *      navy fintech and a warm food brand without edits. A template that
 *      hardcodes `text-gray-900` cannot carry a design system, which is why 74
 *      Supabase templates produced one identical look for every tenant.
 *
 *   2. NO FAKE ICON. `{feature[].icon}` classifies as `data` and is
 *      unfillable from a harvest of headings, body text, CTAs and images — so
 *      the old template rendered an empty box on every card. The mark here is
 *      a rule in the accent colour: decorative, content-free, honest about
 *      carrying no meaning. An icon is a design decision belonging to the
 *      library, not a slot pretending to hold harvested data.
 *
 *   3. HIERARCHY BY SIZE AND SPACE, NOT WEIGHT. The benchmark's defining
 *      observation is that reference headlines are LIGHT (300-400) and large.
 *      Weight comes from --heading-weight; nothing here reaches for font-bold.
 *
 * Arity is the harvest's, via the repeat block — three features render three
 * cards, six render six, none renders nothing at all.
 *
 * Slots:
 *   {section_title}          → "Why Choose Cape Crypto"
 *   {section_subtitle}       → "Proudly South African, based in Cape Town"
 *   {features[].title}       → "Lowest trading fees in South Africa"
 *   {features[].description} → "We offer the most competitive trading fees…"
 */

// The machine-read declaration. `slot_contract.declared_slots()` reads ONLY a
// `// Tokens:` line or a `Slot placeholders` block — the prose "Slots:" list
// above is neither, so without this line the contract falls back to a
// permissive brace sweep and substitutes this file's own JS identifiers away.
// Tokens: {section_title} {section_subtitle} {features[].title} {features[].description}

interface Feature {
  title: string;
  description: string;
}

interface FeaturesIconGridProps {
  sectionTitle?: string;
  sectionSubtitle?: string;
  features?: Feature[];
}

const harvestedFeatures: Feature[] = [
  /* repeat:features */
  { title: "{features[].title}", description: "{features[].description}" },
  /* /repeat */
];

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";

export default function FeaturesIconGrid({
  sectionTitle = "{section_title}",
  sectionSubtitle = "{section_subtitle}",
  features = harvestedFeatures,
}: FeaturesIconGridProps) {
  // A heading over empty space is worse than no section.
  if (!features.length) return null;

  return (
    <section
      className="w-full"
      style={{
        background: "var(--surface, var(--background))",
        color: "var(--foreground)",
        paddingTop: "var(--section-py, 96px)",
        paddingBottom: "var(--section-py, 96px)",
      }}
    >
      <div className="mx-auto w-full max-w-6xl px-6">
        {(sectionTitle || sectionSubtitle) && (
          <div className="max-w-2xl" style={{ marginBottom: "var(--block-gap, 48px)" }}>
            {sectionTitle && (
              <h2
                className="text-3xl md:text-[2.75rem] leading-[1.1] tracking-tight"
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
                className="mt-5 text-lg leading-relaxed"
                style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
              >
                {sectionSubtitle}
              </p>
            )}
          </div>
        )}

        <ul className="grid grid-cols-1 gap-px sm:grid-cols-2 lg:grid-cols-3"
            style={{ background: HAIRLINE }}>
          {features.map((feature, index) => (
            <motion.li
              key={index}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: index * 0.07, ease: "easeOut" }}
              className="flex flex-col"
              style={{
                background: "var(--background)",
                padding: "var(--card-pad, 32px)",
              }}
            >
              {/* Decorative accent rule — content-free by design; see note 2. */}
              <span
                aria-hidden="true"
                className="mb-6 block h-[3px] w-10"
                style={{ background: ACCENT, borderRadius: "var(--radius-button, 4px)" }}
              />
              <h3
                className="text-xl leading-snug"
                style={{
                  fontFamily: "var(--font-heading, inherit)",
                  fontWeight: 500,
                }}
              >
                {feature.title}
              </h3>
              {feature.description && (
                <p
                  className="mt-3 text-base leading-relaxed"
                  style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                >
                  {feature.description}
                </p>
              )}
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  );
}

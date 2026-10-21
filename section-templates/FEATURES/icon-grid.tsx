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
 *   {features[].meta}        → a source-declared detail (data-field="meta"), optional
 */

// The machine-read declaration. `slot_contract.declared_slots()` reads ONLY a
// `// Tokens:` line or a `Slot placeholders` block — the prose "Slots:" list
// above is neither, so without this line the contract falls back to a
// permissive brace sweep and substitutes this file's own JS identifiers away.
// Tokens: {eyebrow} {section_title} {section_subtitle} {features[].title} {features[].description} {features[].meta} {supporting_text}

// No art demand, declared rather than omitted so a reader can tell
// "nothing wanted" from "nobody considered it":
// the visual vocabulary is Lucide icons, selected semantically. A generated picture per feature would depict capabilities that may not exist.
// Art: none

interface Feature {
  title: string;
  description: string;
  meta?: string;
}

interface FeaturesIconGridProps {
  eyebrow?: string;
  sectionTitle?: string;
  sectionSubtitle?: string;
  features?: Feature[];
  supportingText?: string;
}

const harvestedFeatures: Feature[] = [
  /* repeat:features */
  { title: "{features[].title}", description: "{features[].description}", meta: "{features[].meta}" },
  /* /repeat */
];

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
//: Secondary text set directly on the section's --surface ground. A palette
//: checks --muted against --background and its card surface, not against
//: bg_secondary — THURIS's Stone on Parchment measured 3.98:1. Derived from
//: the ink, weighted toward it, so it clears AA on any surface.
const MUTED_ON_SURFACE = "color-mix(in srgb, var(--foreground) 80%, var(--surface, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";

export default function FeaturesIconGrid({
  eyebrow = "{eyebrow}",
  sectionTitle = "{section_title}",
  sectionSubtitle = "{section_subtitle}",
  features = harvestedFeatures,
  supportingText = "{supporting_text}",
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
      <div className="aurelix-container mx-auto w-full max-w-6xl px-6">
        {(sectionTitle || sectionSubtitle) && (
          <div className="max-w-2xl" style={{ marginBottom: "var(--block-gap, 48px)" }}>
            {eyebrow && !eyebrow.startsWith("{") && (
              <p
                className="mb-4 text-xs uppercase tracking-[0.14em]"
                style={{ color: MUTED_ON_SURFACE, fontFamily: "var(--font-body, inherit)", fontWeight: 500 }}
              >
                {eyebrow}
              </p>
            )}
            {sectionTitle && (
              <h2
                className="leading-[1.1] tracking-tight"
                style={{
                  fontSize: "var(--type-h2, 3rem)",
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
                style={{ color: MUTED_ON_SURFACE, fontFamily: "var(--font-body, inherit)" }}
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
                className="leading-snug"
                style={{
                  fontSize: "var(--type-h4, 1.25rem)",
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
              {feature.meta && !feature.meta.startsWith("{") && (
                <p
                  className="mt-4 text-xs uppercase tracking-[0.14em]"
                  style={{ color: MUTED, fontFamily: "var(--font-body, inherit)", fontWeight: 500 }}
                >
                  {feature.meta}
                </p>
              )}
            </motion.li>
          ))}
        </ul>
        {supportingText && !supportingText.startsWith("{") && (
          <p
            className="text-lg leading-relaxed"
            style={{ marginTop: "var(--block-gap, 48px)", fontFamily: "var(--font-heading, inherit)" }}
          >
            {supportingText}
          </p>
        )}
      </div>
    </section>
  );
}

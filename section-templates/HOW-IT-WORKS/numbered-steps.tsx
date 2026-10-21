"use client";

import { motion } from "framer-motion";

/**
 * HOW-IT-WORKS | numbered-steps
 * Token-driven section template — tenant content filled at build time.
 *
 * Same three departures as FEATURES/icon-grid, plus one specific to this
 * archetype:
 *
 *   THE NUMBER IS THE ILLUSTRATION. A how-it-works section is where templates
 *   reach for an icon per step and render an empty box, because `{step[].icon}`
 *   classifies as `data` and no harvest of headings and body text can fill it.
 *   The ordinal is already the strongest signal a step has — it is derived from
 *   position, so it is never missing, never fabricated, and needs no asset.
 *   It is set large and light against a hairline connector, which is the
 *   sequence made visible without inventing anything.
 *
 * NEVER TWICE. When the source title already carries its ordinal ("01 —
 * Choose."), the derived ordinal is not drawn: the copy renders verbatim and
 * the number appears once.
 *
 * Arity is the harvest's, via the repeat block. Three steps render three,
 * five render five, none renders nothing at all.
 *
 * Slots:
 *   {section_title}       → "How to start trading"
 *   {section_subtitle}    → "Three steps, verified in minutes"
 *   {steps[].title}       → "Create your account"
 *   {steps[].description} → "Sign up with your email and verify your identity…"
 */

// Tokens: {eyebrow} {section_title} {section_subtitle} {steps[].title} {steps[].description}

// No art demand, declared rather than omitted so a reader can tell
// "nothing wanted" from "nobody considered it":
// the steps are numbered type; illustrating a step means depicting the product doing it, which is a claim, not decoration.
// Art: none

interface Step {
  title: string;
  description: string;
}

interface HowItWorksNumberedStepsProps {
  eyebrow?: string;
  sectionTitle?: string;
  sectionSubtitle?: string;
  steps?: Step[];
}

const harvestedSteps: Step[] = [
  /* repeat:steps */
  { title: "{steps[].title}", description: "{steps[].description}" },
  /* /repeat */
];

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";

export default function HowItWorksNumberedSteps({
  eyebrow = "{eyebrow}",
  sectionTitle = "{section_title}",
  sectionSubtitle = "{section_subtitle}",
  steps = harvestedSteps,
}: HowItWorksNumberedStepsProps) {
  // A heading over empty space is worse than no section.
  if (!steps.length) return null;

  return (
    <section
      className="w-full"
      style={{
        background: "var(--background)",
        color: "var(--foreground)",
        paddingTop: "var(--section-py, 96px)",
        paddingBottom: "var(--section-py, 96px)",
      }}
    >
      <div className="mx-auto w-full max-w-6xl px-6">
        {(sectionTitle || sectionSubtitle) && (
          <div className="max-w-2xl" style={{ marginBottom: "var(--block-gap, 48px)" }}>
            {eyebrow && !eyebrow.startsWith("{") && (
              <p
                className="mb-4 text-xs uppercase tracking-[0.14em]"
                style={{ color: MUTED, fontFamily: "var(--font-body, inherit)", fontWeight: 500 }}
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
                style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
              >
                {sectionSubtitle}
              </p>
            )}
          </div>
        )}

        <ol className="relative grid grid-cols-1 md:grid-cols-3 gap-x-10 gap-y-12">
          {steps.map((step, index) => {
            const stepOrdinal = String(index + 1).padStart(2, "0");
            const titleCarriesOrdinal = step.title.trim().startsWith(stepOrdinal);
            return (
            <motion.li
              key={index}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: index * 0.09, ease: "easeOut" }}
              className="relative flex flex-col"
            >
              {/* The connector runs between steps, never past the last one. */}
              {!titleCarriesOrdinal && index < steps.length - 1 && (
                <span
                  aria-hidden="true"
                  className="absolute left-0 top-[1.35rem] hidden h-px w-full md:block"
                  style={{
                    background: HAIRLINE,
                    transform: "translateX(3.5rem)",
                  }}
                />
              )}

              {!titleCarriesOrdinal && (
              <div className="relative flex items-baseline gap-4">
                <span
                  className="text-[2rem] leading-none tabular-nums"
                  style={{
                    color: ACCENT,
                    fontFamily: "var(--font-heading, inherit)",
                    fontWeight: "var(--heading-weight, 400)" as unknown as number,
                  }}
                >
                  {stepOrdinal}
                </span>
              </div>
              )}

              <h3
                className={`${titleCarriesOrdinal ? "" : "mt-6 "}text-xl leading-snug`}
                style={{ fontFamily: "var(--font-heading, inherit)", fontWeight: 500 }}
              >
                {step.title}
              </h3>
              {step.description && (
                <p
                  className="mt-3 text-base leading-relaxed"
                  style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                >
                  {step.description}
                </p>
              )}
            </motion.li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}

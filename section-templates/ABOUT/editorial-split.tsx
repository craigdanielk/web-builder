"use client";

import Image from "next/image";
import { motion } from "framer-motion";

/**
 * ABOUT | editorial-split
 * Token-driven section template — tenant content filled at build time.
 *
 * Replaces the Supabase template that shipped `bg-white text-gray-900 py-16`,
 * a hardcoded 4:5 image frame with no fallback, and a `{highlight_stat}` /
 * `{highlight_label}` pair under a rule. Four deliberate departures:
 *
 *   1. EVERY COLOUR, SIZE AND RHYTHM IS A TOKEN. Not one Tailwind palette
 *      literal. The build compiles the market benchmark into CSS custom
 *      properties (--accent, --foreground, --muted, --border, --section-py,
 *      --heading-weight …) and this reads them, so the same file renders a
 *      navy fintech and a warm food brand without edits.
 *
 *   2. NO STAT SLOT. The old template's `{highlight_stat}` is classified `data`
 *      by `slot_contract.infer_type` — the harvest carries headings, body text,
 *      CTAs and images and nothing else, so nothing can ever source it. It
 *      rendered as a large placeholder number under a placeholder label. For an
 *      FSCA-licensed FSP a fabricated figure is a regulatory liability, not a
 *      cosmetic defect, so the slot is gone rather than defaulted.
 *
 *   3. THE PROSE HAS NO FIXED LENGTH. The old template spelled out exactly two
 *      paragraphs. The three ABOUT sections in the cape-crypto capture carry
 *      3, 5 and 1 body strings — two of them lose copy against a fixed pair.
 *      The lead paragraph is a scalar; every paragraph after it comes from the
 *      repeat block, so the render count is the harvest count in both
 *      directions.
 *
 *   4. THE IMAGE IS OPTIONAL AND HONEST. If the harvest resolved no image the
 *      media column does not render an empty frame or a placeholder — the prose
 *      takes the full measure and the layout still reads deliberately.
 *      `<Image src="">` THROWS in next/image, so an unresolved src must never
 *      reach the DOM.
 *
 * Slots:
 *   {section_title}      → "Our story"
 *   {section_body}       → the lead paragraph
 *   {paragraphs[].body}  → every paragraph after the lead, arity from harvest
 *   {image_url}          → resolved local asset                     (optional)
 *   {image_alt}          → alt text for the above
 *   {cta_text}           → "Read more"                              (optional)
 *   {cta_url}            → "/about"
 */

// The prose block above is documentation. THIS line is the contract:
// `slot_contract.declared_slots()` reads only a `// Tokens:` line (plus one
// legacy prose dialect used by a single older template). With neither,
// `no_declaration` is true and every non-reserved brace token in the body is
// treated as fillable — which is how a JSX loop variable in a `key=` position
// was substituted away and took a build down with
// `Expected '</', got 'ident'`. Declared, the sweep never runs.
//
// The legacy dialect is matched by a regex that runs to the NEXT `*/`, so
// naming it verbatim above a block comment silently annexes the code between
// them into the declaration. Hence the paraphrase.
// Tokens: {section_title} {section_body} {paragraphs[].body} {image_url} {image_alt} {cta_text} {cta_url}

// The DEMAND declaration, read by `asset_resolver.art_declarations()`. An
// editorial split is prose beside a picture; note 4 keeps it honest when there
// is none, but "honest and half-empty" is what the last five builds shipped.
// `scene`: place and atmosphere — this tenant is Cape Town-founded and says so
// in the copy. Never staff, never a customer, never the app.
// Art: slot=image_url intent=scene aspect=4:5 role=load-bearing

interface AboutEditorialSplitProps {
  sectionTitle?: string;
  sectionBody?: string;
  bodyParagraphs?: string[];
  imageUrl?: string;
  imageAlt?: string;
  ctaText?: string;
  ctaUrl?: string;
}

const harvestedParagraphs: string[] = [
  /* repeat:paragraphs */
  "{paragraphs[].body}",
  /* /repeat */
];

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";
//: The media panel's lift. Derived from --foreground, not from a fixed navy —
//: a literal rgba shadow is a shadow for ONE palette on ONE ground; on a dark
//: tenant it is an invisible smudge and on a warm one it reads blue.
//: ONE layer, not two. The benchmark declares shadow_system.max_layers = 1 and
//: states outright that elevation is carried by surface tint and radius, not by
//: shadow — the reference's five shadowed elements are all a single soft layer.
//: The stacked ambient+contact pair this replaces was a two-layer elevation ramp
//: borrowed from a different design system; the single layer keeps the lift.
const MEDIA_SHADOW =
  "0 18px 44px -30px color-mix(in srgb, var(--foreground) 26%, transparent)";

/** A slot value that survived the fill. Empty, whitespace, or an unsubstituted
 *  placeholder are all "the harvest had nothing here". */
function resolved(value: string | undefined): string {
  if (!value) return "";
  const trimmed = value.trim();
  if (!trimmed || trimmed.startsWith("{")) return "";
  return trimmed;
}

export default function AboutEditorialSplit({
  sectionTitle = "{section_title}",
  sectionBody = "{section_body}",
  bodyParagraphs = harvestedParagraphs,
  imageUrl = "{image_url}",
  imageAlt = "{image_alt}",
  ctaText = "{cta_text}",
  ctaUrl = "{cta_url}",
}: AboutEditorialSplitProps) {
  const title = resolved(sectionTitle);
  const lead = resolved(sectionBody);
  const rest = bodyParagraphs.map(resolved).filter(Boolean);

  // An ABOUT section IS its narrative. A heading over an image with no story
  // under it is a frame around nothing — worse than omitting the section.
  if (!lead && !rest.length) return null;

  // An unresolved src must never reach next/image — it throws, and the whole
  // route errors while every string and brace check passes.
  const storyImage = resolved(imageUrl);
  const storyImageAlt = resolved(imageAlt);
  const actionLabel = resolved(ctaText);
  const actionHref = resolved(ctaUrl);

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
      <div
        className={`mx-auto grid w-full max-w-6xl gap-14 px-6 ${
          storyImage ? "lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1fr)] lg:items-center" : ""
        }`}
      >
        {storyImage && (
          <motion.div
            initial={{ opacity: 0, x: -24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="relative aspect-[4/5] w-full overflow-hidden"
            style={{
              borderRadius: "var(--radius-card, 8px)",
              border: `1px solid ${HAIRLINE}`,
              boxShadow: MEDIA_SHADOW,
            }}
          >
            <Image
              src={storyImage}
              alt={storyImageAlt}
              fill
              sizes="(min-width: 1024px) 40vw, 100vw"
              className="object-cover"
            />
          </motion.div>
        )}

        <motion.div
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, delay: 0.12, ease: "easeOut" }}
          className={storyImage ? "" : "max-w-3xl"}
        >
          {title && (
            <>
              {/* Accent used once, as punctuation — see the benchmark note. */}
              <span
                aria-hidden="true"
                className="mb-6 block h-[3px] w-10"
                style={{ background: ACCENT, borderRadius: "var(--radius-button, 4px)" }}
              />
              <h2
                className="text-[2rem] leading-[1.1] tracking-tight md:text-[3rem]"
                style={{
                  fontFamily: "var(--font-heading, inherit)",
                  fontWeight: "var(--heading-weight, 400)" as unknown as number,
                }}
              >
                {title}
              </h2>
            </>
          )}

          {lead && (
            <p
              className="mt-7 text-lg leading-relaxed md:text-xl"
              style={{ color: "var(--foreground)", fontFamily: "var(--font-body, inherit)" }}
            >
              {lead}
            </p>
          )}

          {rest.length > 0 && (
            <div style={{ marginTop: "var(--block-gap, 48px)" }}>
              {/* `paraText`, not `paragraph`: declaring `{paragraphs[].body}`
                  contributes the base and its SINGULAR to the slot set, so a
                  local named `paragraph` is indistinguishable from a slot and
                  gets substituted away. A camelCase name cannot match the
                  `[a-z][a-z_0-9]*` slot pattern at all. */}
              {rest.map((paraText, index) => (
                <p
                  key={index}
                  className="mt-5 text-base leading-relaxed first:mt-0"
                  style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                >
                  {paraText}
                </p>
              ))}
            </div>
          )}

          {actionLabel && (
            <div
              className="border-t"
              style={{
                borderColor: HAIRLINE,
                marginTop: "var(--block-gap, 48px)",
                paddingTop: "var(--card-pad, 32px)",
              }}
            >
              <a
                href={actionHref || "#"}
                className="inline-flex items-center gap-2 text-base transition-opacity hover:opacity-70"
                style={{
                  color: ACCENT,
                  fontFamily: "var(--font-body, inherit)",
                  fontWeight: 500,
                }}
              >
                {actionLabel}
                <span aria-hidden="true">&rarr;</span>
              </a>
            </div>
          )}
        </motion.div>
      </div>
    </section>
  );
}

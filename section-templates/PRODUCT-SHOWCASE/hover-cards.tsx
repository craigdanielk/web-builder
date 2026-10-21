"use client";

import Image from "next/image";
import { motion } from "framer-motion";

/**
 * PRODUCT-SHOWCASE | hover-cards
 * Token-driven section template — tenant content filled at build time.
 *
 * Replaces the Supabase template, which hardcoded `bg-white` / `text-gray-900`
 * (defeating a section's declared `data-tone` ground), rendered an empty grey
 * image box per card when no image was supplied, and declared prices and
 * reserve links it could never fill from a harvest.
 *
 *   1. EVERY COLOUR, SIZE AND RHYTHM IS A TOKEN, so the section takes the
 *      ground its tone wrapper declares — dark or light — without edits.
 *   2. NO EMPTY IMAGE BOX. An unfilled image slot renders nothing at all; the
 *      card is name, description, price and action. `<Image src="">` throws
 *      in next/image, so the guard is the value being falsy.
 *   3. PRICE IS A DECLARED FIELD. `{products[].price}` classifies as `data`,
 *      which only a source-declared `data-field="price"` can supply. Absent,
 *      the price line is simply not rendered — never a placeholder figure.
 *   4. HOVER IS A HAIRLINE SHIFT. The border moves to the accent; no lift, no
 *      scale, no shadow.
 *
 * Arity is the harvest's, via the repeat block.
 *
 * Slots:
 *   {eyebrow}                  → section kicker (optional)
 *   {section_title}            → "Three essences. One collection."
 *   {section_subtitle}         → intro line (optional)
 *   {products[].name}          → item heading
 *   {products[].description}   → item paragraph (optional)
 *   {products[].price}         → declared data-field="price" (optional)
 *   {products[].cta_text}      → item link text (optional)
 *   {products[].cta_url}       → item link href
 *   {products[].image_url}     → item image (optional)
 *   {products[].image_alt}     → item image alt
 */

// Tokens: {eyebrow} {section_title} {section_subtitle} {products[].name} {products[].description} {products[].price} {products[].cta_text} {products[].cta_url} {products[].image_url} {products[].image_alt}

// Art: slot=products[].image_url intent=product aspect=4:5 role=load-bearing

interface ProductCard {
  name: string;
  description: string;
  price: string;
  ctaText: string;
  ctaUrl: string;
  imageUrl: string;
  imageAlt: string;
}

interface ProductShowcaseHoverCardsProps {
  eyebrow?: string;
  sectionTitle?: string;
  sectionSubtitle?: string;
  products?: ProductCard[];
}

const harvestedProducts: ProductCard[] = [
  /* repeat:products */
  {
    name: "{products[].name}",
    description: "{products[].description}",
    price: "{products[].price}",
    ctaText: "{products[].cta_text}",
    ctaUrl: "{products[].cta_url}",
    imageUrl: "{products[].image_url}",
    imageAlt: "{products[].image_alt}",
  },
  /* /repeat */
];

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";

/** A slot value that survived the fill; an unsubstituted placeholder is empty. */
function resolved(value: string | undefined): string {
  if (!value) return "";
  const trimmed = value.trim();
  if (!trimmed || trimmed.startsWith("{")) return "";
  return trimmed;
}

export default function ProductShowcaseHoverCards({
  eyebrow = "{eyebrow}",
  sectionTitle = "{section_title}",
  sectionSubtitle = "{section_subtitle}",
  products = harvestedProducts,
}: ProductShowcaseHoverCardsProps) {
  const cards = products.filter((card) => resolved(card.name));
  if (!cards.length) return null;
  const kickerText = resolved(eyebrow);
  const title = resolved(sectionTitle);
  const intro = resolved(sectionSubtitle);

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
      <div className="aurelix-container mx-auto w-full max-w-6xl px-6">
        {(kickerText || title || intro) && (
          <div className="mx-auto max-w-2xl text-center" style={{ marginBottom: "var(--block-gap, 48px)" }}>
            {kickerText && (
              <p
                className="mb-4 text-xs uppercase tracking-[0.14em]"
                style={{ color: MUTED, fontFamily: "var(--font-body, inherit)", fontWeight: 500 }}
              >
                {kickerText}
              </p>
            )}
            {title && (
              <h2
                className="leading-[1.1] tracking-tight"
                style={{
                  fontSize: "var(--type-h2, 3rem)",
                  fontFamily: "var(--font-heading, inherit)",
                  fontWeight: "var(--heading-weight, 400)" as unknown as number,
                }}
              >
                {title}
              </h2>
            )}
            {intro && (
              <p
                className="mt-5 text-lg leading-relaxed"
                style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
              >
                {intro}
              </p>
            )}
          </div>
        )}

        <ul
          className="grid gap-6"
          style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}
        >
          {cards.map((card, index) => {
            const cardImage = resolved(card.imageUrl);
            const cardPrice = resolved(card.price);
            const cardText = resolved(card.description);
            const actionLabel = resolved(card.ctaText);
            const actionHref = resolved(card.ctaUrl);
            return (
              <motion.li
                key={index}
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.5, delay: index * 0.07, ease: "easeOut" }}
                className="group flex flex-col border transition-colors duration-500 hover:[border-color:var(--accent)]"
                style={{
                  borderColor: HAIRLINE,
                  borderRadius: "var(--radius-card, 8px)",
                  background: "var(--surface, var(--background))",
                }}
              >
                {cardImage && (
                  <div className="relative aspect-[4/5] w-full overflow-hidden">
                    <Image
                      src={cardImage}
                      alt={resolved(card.imageAlt)}
                      fill
                      sizes="(min-width: 1024px) 25vw, (min-width: 640px) 50vw, 100vw"
                      className="object-cover"
                    />
                  </div>
                )}
                <div className="flex flex-1 flex-col" style={{ padding: "var(--card-pad, 32px)" }}>
                  <h3
                    className="text-xl leading-snug"
                    style={{
                      color: ACCENT,
                      fontFamily: "var(--font-heading, inherit)",
                      fontWeight: "var(--heading-weight, 400)" as unknown as number,
                    }}
                  >
                    {card.name}
                  </h3>
                  {cardText && (
                    <p
                      className="mt-3 text-sm leading-relaxed"
                      style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                    >
                      {cardText}
                    </p>
                  )}
                  {cardPrice && (
                    <p
                      className="mt-6 text-base"
                      style={{ fontFamily: "var(--font-body, inherit)", fontWeight: 500 }}
                    >
                      {cardPrice}
                    </p>
                  )}
                  {actionLabel && (
                    <div className="mt-auto" style={{ paddingTop: "var(--card-pad, 32px)" }}>
                    <a
                      href={actionHref || "#"}
                      className="inline-flex w-full items-center justify-center border px-5 py-3 text-xs uppercase tracking-[0.14em] transition-colors duration-500"
                      style={{
                        borderColor: ACCENT,
                        color: ACCENT,
                        borderRadius: "var(--radius-button, 6px)",
                        fontFamily: "var(--font-body, inherit)",
                        fontWeight: 500,
                      }}
                    >
                      {actionLabel}
                    </a>
                    </div>
                  )}
                </div>
              </motion.li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

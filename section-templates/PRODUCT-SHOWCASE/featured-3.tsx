"use client";

import Image from "next/image";
import { motion } from "framer-motion";

/**
 * PRODUCT-SHOWCASE | featured-3
 * Token-driven section template — tenant content filled at build time.
 *
 * Three products presented large, then everything after them as a distinct
 * full-width feature — the shape of a release with three items and a set
 * (or a bundle) that is not a fourth peer of the three.
 *
 *   1. THE FIRST THREE ITEMS ARE THE PRESENTATIONS. Portrait image, name,
 *      descriptor line, price and a quiet text action — no boxed card, so the
 *      photograph carries each one.
 *   2. ITEMS FOUR ONWARD ARE FEATURES. Each renders as an image/copy band on
 *      the section's surface, with a filled primary action. A source with
 *      three items renders no band at all.
 *   3. EVERY COLOUR, SIZE AND RHYTHM IS A TOKEN; headings read --type-h2 /
 *      --type-h3. Hover is colour only (an image dims a step, an action
 *      underlines) — no lift, no scale.
 *   4. PRICE IS A DECLARED FIELD (`data-field="price"`). An item that declares
 *      none renders no price line — never a placeholder figure.
 *   5. NO EMPTY IMAGE BOX. `<Image src="">` throws in next/image, so an
 *      unresolved image renders nothing.
 *
 * Slots:
 *   {eyebrow} {section_title} {section_subtitle}
 *   {products[].name} {products[].description} {products[].price}
 *   {products[].cta_text} {products[].cta_url}
 *   {products[].image_url} {products[].image_alt}
 */

// Tokens: {eyebrow} {section_title} {section_subtitle} {products[].name} {products[].description} {products[].price} {products[].cta_text} {products[].cta_url} {products[].image_url} {products[].image_alt}

// Art: slot=products[].image_url intent=product aspect=4:5 role=load-bearing

interface ProductItem {
  name: string;
  description: string;
  price: string;
  ctaText: string;
  ctaUrl: string;
  imageUrl: string;
  imageAlt: string;
}

interface ProductShowcaseFeatured3Props {
  eyebrow?: string;
  sectionTitle?: string;
  sectionSubtitle?: string;
  products?: ProductItem[];
}

const harvestedProducts: ProductItem[] = [
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
const EASE = [0.22, 1, 0.36, 1] as const;

/** A slot value that survived the fill; an unsubstituted placeholder is empty. */
function resolved(value: string | undefined): string {
  if (!value) return "";
  const trimmed = value.trim();
  if (!trimmed || trimmed.startsWith("{")) return "";
  return trimmed;
}

export default function ProductShowcaseFeatured3({
  eyebrow = "{eyebrow}",
  sectionTitle = "{section_title}",
  sectionSubtitle = "{section_subtitle}",
  products = harvestedProducts,
}: ProductShowcaseFeatured3Props) {
  const items = products.filter((item) => resolved(item.name));
  if (!items.length) return null;
  const presentations = items.slice(0, 3);
  const features = items.slice(3);
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
          <div
            className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:items-end"
            style={{ marginBottom: "var(--block-gap, 48px)" }}
          >
            <div>
              {kickerText && (
                <p
                  className="mb-4 text-xs uppercase tracking-[0.18em]"
                  style={{ color: MUTED, fontFamily: "var(--font-body, inherit)", fontWeight: 500 }}
                >
                  {kickerText}
                </p>
              )}
              {title && (
                <h2
                  className="leading-[1.08] tracking-tight"
                  style={{
                    fontSize: "var(--type-h2, 3rem)",
                    fontFamily: "var(--font-heading, inherit)",
                    fontWeight: "var(--heading-weight, 400)" as unknown as number,
                  }}
                >
                  {title}
                </h2>
              )}
            </div>
            {intro && (
              <p
                className="text-base leading-relaxed lg:text-right"
                style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
              >
                {intro}
              </p>
            )}
          </div>
        )}

        <ul className="grid gap-x-8 gap-y-14 sm:grid-cols-2 lg:grid-cols-3">
          {presentations.map((item, index) => {
            const itemImage = resolved(item.imageUrl);
            const itemPrice = resolved(item.price);
            const itemText = resolved(item.description);
            const actionLabel = resolved(item.ctaText);
            return (
              <motion.li
                key={index}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-80px" }}
                transition={{ duration: 0.5, delay: index * 0.08, ease: EASE }}
                className="group flex flex-col"
              >
                {itemImage && (
                  <div
                    className="relative aspect-[4/5] w-full overflow-hidden"
                    style={{ borderRadius: "var(--radius-card, 8px)" }}
                  >
                    <Image
                      src={itemImage}
                      alt={resolved(item.imageAlt)}
                      fill
                      sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                      className="object-cover transition-[filter] duration-500 group-hover:brightness-[0.92]"
                    />
                  </div>
                )}
                <div className="flex flex-1 flex-col pt-6">
                  <h3
                    className="leading-snug"
                    style={{
                      color: ACCENT,
                      fontSize: "var(--type-h3, 1.75rem)",
                      fontFamily: "var(--font-heading, inherit)",
                      fontWeight: "var(--heading-weight, 400)" as unknown as number,
                    }}
                  >
                    {item.name}
                  </h3>
                  {itemText && (
                    <p
                      className="mt-2 text-sm leading-relaxed"
                      style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                    >
                      {itemText}
                    </p>
                  )}
                  {(itemPrice || actionLabel) && (
                    <div
                      className="mt-auto flex items-center justify-between gap-4 border-t pt-4"
                      style={{ borderColor: HAIRLINE, marginTop: "1.5rem" }}
                    >
                      {itemPrice ? (
                        <p className="text-base tabular-nums" style={{ fontFamily: "var(--font-body, inherit)", fontWeight: 500 }}>
                          {itemPrice}
                        </p>
                      ) : (
                        <span />
                      )}
                      {actionLabel && (
                        <a
                          href={resolved(item.ctaUrl) || "#"}
                          className="inline-flex items-center gap-2 border-b border-transparent pb-0.5 text-xs uppercase tracking-[0.18em] transition-colors duration-300 hover:[border-color:var(--accent)]"
                          style={{ color: ACCENT, fontFamily: "var(--font-body, inherit)", fontWeight: 500 }}
                        >
                          {actionLabel}
                          <span aria-hidden="true">&rarr;</span>
                        </a>
                      )}
                    </div>
                  )}
                </div>
              </motion.li>
            );
          })}
        </ul>

        {features.map((item, index) => {
          const itemImage = resolved(item.imageUrl);
          const itemPrice = resolved(item.price);
          const itemText = resolved(item.description);
          const actionLabel = resolved(item.ctaText);
          return (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.6, ease: EASE }}
              className={`grid overflow-hidden border ${itemImage ? "lg:grid-cols-2" : ""}`}
              style={{
                marginTop: "calc(var(--block-gap, 48px) * 1.5)",
                borderColor: HAIRLINE,
                borderRadius: "var(--radius-card, 8px)",
                background: "var(--surface, var(--background))",
              }}
            >
              {itemImage && (
                <div className="relative aspect-square w-full lg:aspect-auto lg:min-h-[28rem]">
                  <Image
                    src={itemImage}
                    alt={resolved(item.imageAlt)}
                    fill
                    sizes="(min-width: 1024px) 50vw, 100vw"
                    className="object-cover"
                  />
                </div>
              )}
              <div className="flex flex-col justify-center p-6 sm:p-[calc(var(--card-pad,32px)*1.5)]">
                <h3
                  className="leading-[1.1] tracking-tight"
                  style={{
                    fontSize: "var(--type-h2, 2.5rem)",
                    fontFamily: "var(--font-heading, inherit)",
                    fontWeight: "var(--heading-weight, 400)" as unknown as number,
                  }}
                >
                  {item.name}
                </h3>
                {itemText && (
                  <p
                    className="mt-4 text-base leading-relaxed"
                    style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                  >
                    {itemText}
                  </p>
                )}
                {itemPrice && (
                  <p className="mt-6 text-lg tabular-nums" style={{ fontFamily: "var(--font-body, inherit)", fontWeight: 500 }}>
                    {itemPrice}
                  </p>
                )}
                {actionLabel && (
                  <div style={{ marginTop: "var(--block-gap, 48px)" }}>
                    <a
                      href={resolved(item.ctaUrl) || "#"}
                      className="flex min-h-12 w-full items-center justify-center px-4 py-3 text-center text-xs uppercase tracking-[0.12em] transition-opacity duration-300 hover:opacity-85 sm:inline-flex sm:w-auto sm:px-8 sm:tracking-[0.18em]"
                      style={{
                        background: ACCENT,
                        color: "var(--on-accent, var(--background))",
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
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}

"use client";

/**
 * FOOTER | mega
 * Token-driven layout component — tenant content filled at build time.
 *
 * Shared by every page, so it is the highest-multiplier template in the
 * library and the one where a hardcoded default is most expensive: a
 * fabricated link appears on all seven routes at once.
 *
 * Three departures:
 *
 *   ARITY IS DATA-DRIVEN AT BOTH LEVELS. Column count comes from the harvest,
 *   and each column's link count comes from that column. Cape Crypto's real
 *   footer harvests as three columns of 4, 6 and 2 — a template with a fixed
 *   arity has to either invent two links to square the third column or drop
 *   four from the second. Both are wrong; neither is visible once rendered.
 *
 *   NO FALLBACK LINK SET. A column whose links all resolved away renders no
 *   column, and a footer with no columns renders only its legal line. The
 *   previous behaviour — falling back to hardcoded Shop / About / Contact when
 *   a Shopify menu had columns with no children — put links to routes that may
 *   not exist on every page of the site.
 *
 *   LEGAL TEXT IS NEVER SYNTHESISED. `{legal_line}` renders only when the
 *   harvest supplied it. A licensed FSP's regulatory line is not something a
 *   builder may compose, and an invented registration number is a liability,
 *   not a placeholder.
 *
 * Slots:
 *   {columns[].heading}      → "Overview"
 *   {columns[].links[].text} → "Privacy policy"
 *   {columns[].links[].href} → resolved by lib/nav_harvest.localise_hrefs
 *   {legal_line}             → harvested regulatory line, or absent
 *   {brand_name}             → "Cape Crypto"
 */

// Tokens: {brand_name} {legal_line} {columns[].heading} {columns[].links[].text} {columns[].links[].href}

// No art demand, declared rather than omitted so a reader can tell
// "nothing wanted" from "nobody considered it":
// navigation furniture. Nothing to depict.
// Art: none

interface FooterLink {
  text: string;
  href: string;
}

interface FooterColumn {
  heading: string;
  links: FooterLink[];
}

interface FooterMegaProps {
  brandName?: string;
  columns?: FooterColumn[];
  legalLine?: string;
}

const harvestedColumns: FooterColumn[] = [
  /* repeat:columns */
  {
    heading: "{columns[].heading}",
    links: [
      /* repeat:columns[].links */
      { text: "{columns[].links[].text}", href: "{columns[].links[].href}" },
      /* /repeat */
    ],
  },
  /* /repeat */
];

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";

/** An unfilled slot is not content. */
const filled = (v?: string) => !!v && v.trim().length > 0 && !v.trim().startsWith("{");

export default function FooterMega({
  brandName = "{brand_name}",
  columns = harvestedColumns,
  legalLine = "{legal_line}",
}: FooterMegaProps) {
  const live = (columns || [])
    .map((c) => ({
      heading: filled(c?.heading) ? c.heading : "",
      links: (c?.links || []).filter((l) => filled(l?.text) && filled(l?.href)),
    }))
    // A heading with no links under it is a promise the footer cannot keep.
    .filter((c) => c.links.length > 0);

  // camelCase deliberately: the slot contract's token pattern is
  // `[a-z][a-z_0-9]*`, so a lowercase local rendered as `{brand}` is
  // indistinguishable from the `{brand_name}` slot and gets substituted away.
  const brandLabel = filled(brandName) ? brandName : "";
  const legalText = filled(legalLine) ? legalLine : "";

  // Nothing sourced at all — render nothing rather than a chrome-only footer.
  if (!live.length && !brandLabel && !legalText) return null;

  return (
    <footer
      className="w-full"
      style={{
        background: "var(--background)",
        color: "var(--foreground)",
        borderTop: `1px solid ${HAIRLINE}`,
        paddingTop: "var(--section-py, 96px)",
        paddingBottom: "calc(var(--section-py, 96px) / 2)",
      }}
    >
      <div className="mx-auto w-full max-w-6xl px-6">
        {live.length > 0 && (
          <div
            className="grid grid-cols-2 md:grid-cols-4"
            style={{ gap: "var(--block-gap, 48px)" }}
          >
            {brandLabel && (
              <div className="col-span-2 md:col-span-1">
                <p
                  className="text-lg leading-snug"
                  style={{
                    fontFamily: "var(--font-heading, inherit)",
                    fontWeight: "var(--heading-weight, 400)" as unknown as number,
                  }}
                >
                  {brandLabel}
                </p>
              </div>
            )}

            {live.map((column, ci) => (
              <nav key={ci} aria-label={column.heading || undefined}>
                {column.heading && (
                  <h3
                    className="text-xs uppercase tracking-[0.14em]"
                    style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                  >
                    {column.heading}
                  </h3>
                )}
                <ul className="mt-5 space-y-3">
                  {column.links.map((link, li) => (
                    <li key={li}>
                      <a
                        href={link.href}
                        className="text-sm leading-relaxed transition-opacity hover:opacity-70"
                        style={{ fontFamily: "var(--font-body, inherit)" }}
                      >
                        {link.text}
                      </a>
                    </li>
                  ))}
                </ul>
              </nav>
            ))}
          </div>
        )}

        {legalText && (
          <p
            className="mt-16 max-w-3xl text-xs leading-relaxed"
            style={{
              color: MUTED,
              fontFamily: "var(--font-body, inherit)",
              borderTop: `1px solid ${HAIRLINE}`,
              paddingTop: "var(--block-gap, 48px)",
            }}
          >
            {legalText}
          </p>
        )}
      </div>
    </footer>
  );
}

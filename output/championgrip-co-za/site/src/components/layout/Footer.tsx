'use client';

import Link from 'next/link';

const defaultColumns: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: "About",
    links: [
      { label: "About", href: "/#about" },
      { label: "Blog", href: "#" },
      { label: "Careers", href: "#" }
    ],
  },
  {
    title: "Services",
    links: [
      { label: "Services", href: "/#services" },
      { label: "FAQ", href: "/#faq" }
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy", href: "#" },
      { label: "Terms", href: "#" }
    ],
  },
];

// The footer ships on every route, so a hardcoded palette here outweighs every
// converted section template. These read the compiled design system, exactly as
// section-templates/FEATURES/icon-grid.tsx does.
const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 14%, var(--background)))";

export default function Footer({ menu, shopName }: {
  menu?: { title: string; items: Array<{ title: string; url: string; items?: Array<{ title: string; url: string }> }> };
  shopName?: string;
} = {}) {
  const displayColumns = menu?.items?.length
    ? menu.items.map(i => ({
        title: i.title,
        links: i.items?.map(sub => ({ label: sub.title, href: sub.url })) ?? [],
      }))
    : defaultColumns;

  return (
    <footer
      style={{
        background: "var(--surface, var(--background))",
        color: "var(--foreground)",
        paddingTop: "var(--section-py, 96px)",
        paddingBottom: "calc(var(--section-py, 96px) * 0.6)",
      }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {displayColumns.map((col, i) => (
            <div key={i}>
              <h3
                className="text-sm uppercase tracking-wider mb-4"
                style={{ fontFamily: "var(--font-heading, inherit)", fontWeight: 500 }}
              >
                {col.title}
              </h3>
              <ul className="space-y-2">
                {col.links.map((link, j) => (
                  <li key={j}>
                    <Link
                      href={link.href}
                      className="text-sm transition-opacity hover:opacity-70"
                      style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div
          className="mt-12 pt-8 border-t text-center text-sm"
          style={{ borderColor: HAIRLINE, color: MUTED, fontFamily: "var(--font-body, inherit)" }}
        >
          &copy; {new Date().getFullYear()} {shopName || 'Championgrip Co Za'}. All rights reserved.
        </div>
      </div>
    </footer>
  );
}

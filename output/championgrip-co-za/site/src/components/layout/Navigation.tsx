'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const defaultLinks: { label: string; url: string }[] = [
  { label: "Shop", url: "/collections" },
  { label: "About", url: "/pages/about" },
  { label: "Contact", url: "/pages/contact" },
];

export default function Navigation({ menu, logo, shopName }: {
  menu?: { title: string; items: Array<{ title: string; url: string; items?: Array<{ title: string; url: string }> }> };
  logo?: { url: string; altText: string | null; width?: number; height?: number };
  shopName?: string;
} = {}) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const displayLinks = menu?.items?.length
    ? menu.items.map(i => ({ label: i.title, url: i.url }))
    : defaultLinks;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <nav
      className="sticky top-0 left-0 right-0 z-50 transition-shadow duration-300"
      style={{
        background: 'var(--background)',
        color: 'var(--foreground)',
        borderBottom: '1px solid var(--border, transparent)',
        boxShadow: scrolled ? '0 8px 24px -20px rgba(0,0,0,0.45)' : 'none',
      }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 md:h-20">
          {/* Logo */}
          <Link href="/" className="flex-shrink-0">
            {logo?.url ? (
              <img
                src={logo.url}
                alt={logo.altText || shopName || 'Championgrip Co Za'}
                className="h-8 w-auto"
              />
            ) : (
              <span
                className="text-xl tracking-tight"
                style={{ fontFamily: 'var(--font-heading, inherit)', fontWeight: 600 }}
              >
                {shopName || 'Championgrip Co Za'}
              </span>
            )}
          </Link>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-8">
            {displayLinks.map((link, i) => (
              <Link
                key={i}
                href={link.url}
                className="text-sm transition-opacity hover:opacity-70"
                style={{ color: 'var(--foreground)', fontFamily: 'var(--font-body, inherit)' }}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden p-2"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            <svg
              className="h-6 w-6"
              style={{ color: 'var(--foreground)' }}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              {mobileOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div
          className="md:hidden border-t shadow-lg"
          style={{
            background: 'var(--surface, var(--background))',
            borderColor: 'var(--border, transparent)',
          }}
        >
          <div className="px-4 py-3 space-y-2">
            {displayLinks.map((link, i) => (
              <Link
                key={i}
                href={link.url}
                className="block py-2 transition-opacity hover:opacity-70"
                style={{ color: 'var(--foreground)', fontFamily: 'var(--font-body, inherit)' }}
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </nav>
  );
}

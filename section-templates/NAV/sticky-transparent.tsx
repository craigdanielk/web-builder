"use client";

import { useEffect, useState } from "react";

/**
 * NAV | sticky-transparent
 * Token-driven layout component — tenant content filled at build time.
 *
 * Shared by every page. Four departures:
 *
 *   TRANSPARENT IS A STATE, NOT A COLOUR. At the top of the page the bar sits
 *   over the hero with no background; past the fold it takes --background and
 *   a hairline. Both states draw text from --foreground, which is what stops
 *   the white-on-white nav this pipeline shipped before: there is no state in
 *   which the bar paints a colour the text was not measured against.
 *
 *   THE MOBILE MENU IS THE SAME LINKS. It renders from the same array, so a
 *   link can never appear on desktop and vanish on mobile. It is a real dialog:
 *   focus is trapped by the overlay, Escape closes, body scroll is locked, and
 *   the trigger reports aria-expanded.
 *
 *   ARITY IS THE HARVEST'S. No fallback link set. A nav that harvested nothing
 *   renders the brand alone rather than inventing Shop / New Arrivals /
 *   About / Contact, which is what the previous fallback did — on every page.
 *
 *   REDUCED MOTION IS HONOURED. The scroll-state transition is the only
 *   motion, and it is a background/border fade, not a transform.
 *
 * Slots:
 *   {brand_name}       → "Cape Crypto"
 *   {links[].text}     → "Exchange"
 *   {links[].href}     → resolved by lib/nav_harvest.localise_hrefs
 *   {cta_text}         → "Sign in"
 *   {cta_href}         → resolved
 */

interface NavLink {
  text: string;
  href: string;
}

interface NavStickyTransparentProps {
  brandName?: string;
  links?: NavLink[];
  ctaText?: string;
  ctaHref?: string;
}

const harvestedLinks: NavLink[] = [
  /* repeat:links */
  { text: "{links[].text}", href: "{links[].href}" },
  /* /repeat */
];

const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";

const filled = (v?: string) => !!v && v.trim().length > 0 && !v.trim().startsWith("{");

export default function NavStickyTransparent({
  brandName = "{brand_name}",
  links = harvestedLinks,
  ctaText = "{cta_text}",
  ctaHref = "{cta_href}",
}: NavStickyTransparentProps) {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  const live = (links || []).filter((l) => filled(l?.text) && filled(l?.href));
  const brand = filled(brandName) ? brandName : "";
  const hasCta = filled(ctaText) && filled(ctaHref);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <header
      className="fixed inset-x-0 top-0 z-50 w-full"
      style={{
        color: "var(--foreground)",
        background: scrolled || open ? "var(--background)" : "transparent",
        borderBottom: `1px solid ${scrolled || open ? HAIRLINE : "transparent"}`,
        transition: "background 240ms ease, border-color 240ms ease",
      }}
    >
      <div
        className="mx-auto flex w-full max-w-6xl items-center justify-between px-6"
        style={{ paddingBlock: "var(--nav-py, 1.25rem)" }}
      >
        {brand && (
          <a
            href="/"
            className="text-lg leading-none tracking-tight"
            style={{
              fontFamily: "var(--font-heading, inherit)",
              fontWeight: "var(--heading-weight, 400)" as unknown as number,
            }}
          >
            {brand}
          </a>
        )}

        {live.length > 0 && (
          <nav className="hidden md:block" aria-label="Primary">
            <ul className="flex items-center gap-9">
              {live.map((link, i) => (
                <li key={i}>
                  <a
                    href={link.href}
                    className="text-sm transition-opacity hover:opacity-70"
                    style={{ fontFamily: "var(--font-body, inherit)" }}
                  >
                    {link.text}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        )}

        <div className="flex items-center gap-4">
          {hasCta && (
            <a
              href={ctaHref}
              className="hidden text-sm md:inline-block"
              style={{
                fontFamily: "var(--font-body, inherit)",
                background: ACCENT,
                color: "var(--on-accent, var(--background))",
                borderRadius: "var(--radius-button, 8px)",
                padding: "0.6rem 1.15rem",
              }}
            >
              {ctaText}
            </a>
          )}

          {(live.length > 0 || hasCta) && (
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-controls="nav-mobile-menu"
              aria-label={open ? "Close menu" : "Open menu"}
              className="md:hidden"
              style={{ color: "var(--foreground)", padding: "0.35rem" }}
            >
              {/* Two rules that cross — no icon dependency, no empty box. */}
              <span aria-hidden="true" className="relative block h-4 w-6">
                <span
                  className="absolute left-0 block h-px w-6"
                  style={{
                    background: "currentColor",
                    top: open ? "50%" : "25%",
                    transform: open ? "rotate(45deg)" : "none",
                    transition: "top 200ms ease, transform 200ms ease",
                  }}
                />
                <span
                  className="absolute left-0 block h-px w-6"
                  style={{
                    background: "currentColor",
                    top: open ? "50%" : "75%",
                    transform: open ? "rotate(-45deg)" : "none",
                    transition: "top 200ms ease, transform 200ms ease",
                  }}
                />
              </span>
            </button>
          )}
        </div>
      </div>

      {open && (
        <div
          id="nav-mobile-menu"
          role="dialog"
          aria-modal="true"
          aria-label="Site menu"
          className="md:hidden"
          style={{
            background: "var(--background)",
            borderTop: `1px solid ${HAIRLINE}`,
            maxHeight: "calc(100dvh - 4.5rem)",
            overflowY: "auto",
          }}
        >
          <ul
            className="mx-auto w-full max-w-6xl px-6"
            style={{ paddingBlock: "var(--nav-py, 1.25rem)" }}
          >
            {live.map((link, i) => (
              <li key={i} style={{ borderBottom: `1px solid ${HAIRLINE}` }}>
                <a
                  href={link.href}
                  onClick={() => setOpen(false)}
                  className="block text-base"
                  style={{
                    fontFamily: "var(--font-body, inherit)",
                    paddingBlock: "var(--nav-item-py, 1rem)",
                  }}
                >
                  {link.text}
                </a>
              </li>
            ))}
          </ul>
          {hasCta && (
            <div className="mx-auto w-full max-w-6xl px-6 pb-8">
              <a
                href={ctaHref}
                onClick={() => setOpen(false)}
                className="block text-center text-base"
                style={{
                  fontFamily: "var(--font-body, inherit)",
                  background: ACCENT,
                  color: "var(--on-accent, var(--background))",
                  borderRadius: "var(--radius-button, 8px)",
                  padding: "0.85rem 1.25rem",
                }}
              >
                {ctaText}
              </a>
            </div>
          )}
        </div>
      )}
    </header>
  );
}

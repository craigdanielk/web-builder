"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useCart } from "@/lib/shopify/cart-context";

const PRODUCT =
  "/products/champion-grip-spray-120ml-can-elevate-your-bowling-game-with-confidence";

const NAV = [
  { href: PRODUCT, label: "Shop" },
  { href: "/features", label: "Features" },
  { href: "/about", label: "Story" },
  { href: "/find-a-stockist", label: "Stockists" },
  { href: "/book-a-demo", label: "Demo" },
  { href: "/blog", label: "Journal" },
  { href: "/contact", label: "Contact" },
];

const SOCIAL = [
  {
    label: "Instagram",
    href: "https://www.instagram.com/champion_grip/",
  },
  {
    label: "Facebook",
    href: "https://www.facebook.com/profile.php?id=100054611102140",
  },
  {
    label: "WhatsApp",
    href: "https://api.whatsapp.com/send?phone=27612602932",
  },
];

function SocialIcon({ label }: { label: string }) {
  const common = {
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.75,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true as const,
  };

  if (label === "Instagram") {
    return (
      <svg {...common}>
        <rect x="3" y="3" width="18" height="18" rx="5" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
      </svg>
    );
  }
  if (label === "Facebook") {
    return (
      <svg {...common}>
        <path d="M14 8h2V5h-2c-2.2 0-4 1.8-4 4v2H8v3h2v7h3v-7h2.2l.8-3H13V9c0-.6.4-1 1-1z" fill="currentColor" stroke="none" />
      </svg>
    );
  }
  // WhatsApp
  return (
    <svg {...common}>
      <path
        d="M20 11.5A8.5 8.5 0 0 1 7.6 18.3L4 20l1.8-3.5A8.5 8.5 0 1 1 20 11.5z"
        fill="none"
      />
      <path
        d="M9.2 9.1c.2-.5.4-.5.6-.5h.5c.2 0 .4 0 .5.4l.7 1.7c.1.2 0 .4-.1.5l-.4.5c-.1.1-.2.3 0 .5.3.5.8 1.1 1.4 1.5.5.4 1 .6 1.2.5.2-.1.4-.3.5-.4l.5-.3c.2-.1.4 0 .5.1l1.5.9c.2.1.3.3.2.5-.1.4-.6 1-1.1 1.1-.5.1-1.3.1-2.7-.5-1.7-.8-2.9-2.3-3.4-3.3-.4-.8-.5-1.4-.5-1.8 0-.4.5-.8.6-1z"
        fill="currentColor"
        stroke="none"
      />
    </svg>
  );
}

export function SiteHeader() {
  const { cart, openCart } = useCart();
  const [solid, setSolid] = useState(false);
  const [open, setOpen] = useState(false);
  const count = cart?.totalQuantity ?? 0;

  useEffect(() => {
    const onScroll = () => setSolid(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className={`cg-header${solid ? " is-solid" : ""}`}>
      <Link href="/" className="cg-wordmark">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/media/champion-grip/brand-logo.png" alt="" width={36} height={36} />
        <span>Champion Grip</span>
      </Link>
      <nav className={open ? "is-open" : ""} aria-label="Primary">
        {NAV.map((item) => (
          <Link key={item.href} href={item.href} onClick={() => setOpen(false)}>
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="cg-header-actions">
        <Link href={PRODUCT} className="cg-header-shop" onClick={() => setOpen(false)}>
          Buy
        </Link>
        <button type="button" className="cg-cart-btn" onClick={openCart} aria-label="Open cart">
          Cart
          {count > 0 ? <span>{count}</span> : null}
        </button>
        <button
          type="button"
          className="cg-menu-btn"
          aria-label="Toggle menu"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          Menu
        </button>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="cg-footer">
      <div>
        <strong>Champion Grip</strong>
        <p>Aerosol bowls grip enhancer. 120ml.</p>
        <p>14 Manning St, Colbyn, Pretoria</p>
        <p>
          <a href="tel:+27612602932">+27 61 260 2932</a>
        </p>
        <p>
          <a href="mailto:info@championgrip.co.za">info@championgrip.co.za</a>
        </p>
        <div className="cg-social" aria-label="Social">
          {SOCIAL.map((item) => (
            <a key={item.href} href={item.href} target="_blank" rel="noreferrer" aria-label={item.label}>
              <SocialIcon label={item.label} />
            </a>
          ))}
        </div>
      </div>
      <div>
        <Link href={PRODUCT}>Shop / PDP</Link>
        <Link href="/collections/champion-grip">Collection</Link>
        <Link href="/features">Features</Link>
        <Link href="/about">Story</Link>
        <Link href="/find-a-stockist">Stockists</Link>
        <Link href="/become-a-stockist">Trade enquiry</Link>
        <Link href="/book-a-demo">Demo</Link>
        <Link href="/blog">Journal</Link>
        <Link href="/in-the-media">In the media</Link>
        <Link href="/contact">Contact</Link>
      </div>
      <p className="cg-fine">
        Checkout runs on Shopify. Use outdoors or in a well-ventilated place. Spray away from yourself.
      </p>
    </footer>
  );
}

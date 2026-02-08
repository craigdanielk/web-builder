"use client";

import React from "react";

const footerLinks = [
  { label: "Shop", href: "#products" },
  { label: "Subscription", href: "#pricing" },
  { label: "Our Story", href: "#about" },
  { label: "Contact", href: "#contact" },
];

const Section09Footer: React.FC = () => {
  return (
    <footer className="bg-stone-950 py-16">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="flex flex-col items-center gap-8">
          {/* Logo */}
          <a
            href="#"
            className="text-2xl font-bold text-white"
            style={{ fontFamily: "'DM Serif Display', serif" }}
          >
            Turm Kaffee
          </a>

          {/* Links */}
          <nav className="flex flex-wrap items-center justify-center gap-6 sm:gap-8">
            {footerLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-sm text-stone-400 transition-colors duration-300 hover:text-white"
                style={{ fontFamily: "'DM Sans', sans-serif" }}
              >
                {link.label}
              </a>
            ))}
          </nav>

          {/* Social Icons */}
          <div className="flex items-center gap-5">
            {/* Instagram */}
            <a
              href="#"
              className="text-stone-400 transition-colors duration-300 hover:text-white"
              aria-label="Follow Turm Kaffee on Instagram"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" />
              </svg>
            </a>
            {/* Twitter/X */}
            <a
              href="#"
              className="text-stone-400 transition-colors duration-300 hover:text-white"
              aria-label="Follow Turm Kaffee on X"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </a>
          </div>

          {/* Divider */}
          <div className="w-full border-t border-stone-800" />

          {/* Bottom Row */}
          <div className="flex flex-col sm:flex-row items-center justify-between w-full gap-4">
            <p
              className="text-xs text-stone-500"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            >
              © {new Date().getFullYear()} Turm Kaffee. All rights reserved.
            </p>
            <p
              className="text-xs text-stone-500"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            >
              Roasted with care in Zürich, Switzerland.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Section09Footer;

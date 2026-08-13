"use client";

/**
 * LOGO-BAR | scrolling-marquee
 * Token-driven section template — tenant content filled at build time.
 *
 * Two departures specific to this archetype:
 *
 *   A LOGO IS AN ASSET, NOT A STRING. Every logo rendered here must come from
 *   a resolved asset. There is no text fallback that turns a partner name into
 *   a styled pill, because a pill reads as a logo the tenant does not have —
 *   which on a licensed FSP's site is a claimed relationship. Logos with no
 *   resolved src are dropped and counted, and if none resolve the section
 *   returns null rather than shipping an empty rail.
 *
 *   THE MARQUEE IS DECORATION, NOT STRUCTURE. The track duplicates its
 *   children so the loop is seamless; the duplicate is aria-hidden so screen
 *   readers hear each logo once. `prefers-reduced-motion` stops the animation
 *   entirely and the rail becomes a static, scrollable row — the content is
 *   never only reachable through motion.
 *
 * Arity is the harvest's, via the repeat block.
 *
 * Slots:
 *   {section_title}   → "Trusted by"
 *   {logos[].src}     → resolved asset path — REQUIRED, never a placeholder
 *   {logos[].alt}     → "Cape Town Chamber of Commerce"
 */

// Tokens: {section_title} {logos[].src} {logos[].alt}

interface Logo {
  src: string;
  alt: string;
}

interface LogoBarScrollingMarqueeProps {
  sectionTitle?: string;
  logos?: Logo[];
}

const harvestedLogos: Logo[] = [
  /* repeat:logos */
  { src: "{logos[].src}", alt: "{logos[].alt}" },
  /* /repeat */
];

const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";

/** Static, module-level, never interpolated. See the note at its use site. */
const MARQUEE_CSS = `
.logo-marquee__track {
  animation: logo-marquee-scroll var(--marquee-duration, 38s) linear infinite;
}
.logo-marquee:hover .logo-marquee__track { animation-play-state: paused; }
@keyframes logo-marquee-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}
@media (prefers-reduced-motion: reduce) {
  .logo-marquee { overflow-x: auto; }
  .logo-marquee__track { animation: none; }
}
`;

/** An unresolved slot is not an asset. Never render one. */
function isResolved(logo: Logo): boolean {
  const src = (logo?.src || "").trim();
  return src.length > 0 && !src.startsWith("{") && src !== "#";
}

export default function LogoBarScrollingMarquee({
  sectionTitle = "{section_title}",
  logos = harvestedLogos,
}: LogoBarScrollingMarqueeProps) {
  const resolved = (logos || []).filter(isResolved);

  // An empty rail claims a set of relationships that resolved to nothing.
  if (!resolved.length) return null;

  // camelCase deliberately — see FOOTER/mega: a lowercase local rendered as
  // `{title}` is indistinguishable from a slot and gets substituted away.
  const titleText = sectionTitle && !sectionTitle.startsWith("{") ? sectionTitle : "";

  return (
    <section
      className="w-full overflow-hidden"
      style={{
        background: "var(--background)",
        color: "var(--foreground)",
        borderTop: `1px solid ${HAIRLINE}`,
        borderBottom: `1px solid ${HAIRLINE}`,
        paddingTop: "calc(var(--section-py, 96px) / 2)",
        paddingBottom: "calc(var(--section-py, 96px) / 2)",
      }}
    >
      {titleText && (
        <p
          className="mx-auto mb-10 w-full max-w-6xl px-6 text-sm uppercase tracking-[0.14em]"
          style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
        >
          {titleText}
        </p>
      )}

      <div className="logo-marquee relative w-full">
        <div className="logo-marquee__track flex w-max items-center">
          {[0, 1].map((copy) => (
            <ul
              key={copy}
              aria-hidden={copy === 1 ? "true" : undefined}
              className="flex shrink-0 items-center"
              style={{ gap: "var(--block-gap, 48px)", paddingRight: "var(--block-gap, 48px)" }}
            >
              {resolved.map((logo, index) => (
                <li key={`${copy}-${index}`} className="flex shrink-0 items-center">
                  {/* Intrinsic sizing only — a logo box with a fixed aspect
                      distorts wordmarks of different widths. */}
                  <img
                    src={logo.src}
                    alt={copy === 1 ? "" : logo.alt}
                    loading="lazy"
                    decoding="async"
                    className="h-7 w-auto max-w-[10rem] object-contain md:h-8"
                    style={{ opacity: 0.72 }}
                  />
                </li>
              ))}
            </ul>
          ))}
        </div>
      </div>

      {/* Plain <style> with a static string child.
          Not styled-jsx: the generated scaffold does not carry it and
          `<style jsx>` type-errors there. Not dangerouslySetInnerHTML either —
          harvested content is untrusted, and an API that accepts raw HTML sat
          two edits away from someone interpolating a logo alt into it.
          MARQUEE_CSS is a module constant with no interpolation; keep it that
          way. The global `@keyframes marquee` is not usable here: orchestrate
          only emits it on the gsap engine, and this build resolves to css. */}
      <style>{MARQUEE_CSS}</style>
    </section>
  );
}

"use client";

import type { CSSProperties } from "react";

/**
 * LOGO-BAR | scrolling-marquee
 * Token-driven section template — tenant content filled at build time.
 *
 * Three departures specific to this archetype:
 *
 *   A LOGO IS AN ASSET, NOT A STRING. Every logo rendered here must come from
 *   a resolved asset. There is no text fallback that turns a partner name into
 *   a styled pill, because a pill reads as a logo the tenant does not have —
 *   which on a licensed FSP's site is a claimed relationship. Logos with no
 *   resolved src are dropped and counted, and if none resolve the section
 *   returns null rather than shipping an empty rail.
 *
 *   THE TRACK MUST OUTRUN THE VIEWPORT. A marquee reads as one continuous
 *   ribbon only while its track is wider than what the viewer can see. A
 *   harvest of four wordmarks is ~600px; duplicated once that is ~1200px, and
 *   on a 1440px screen the whole train plus the void behind it sits on screen
 *   at once — so the duplicate reads as a static repeat, not a loop. The run is
 *   therefore repeated to a floor of MIN_TRACK_ITEMS marks per half before the
 *   half is duplicated, and the duration scales with the run so the perceived
 *   speed stays constant no matter how many logos the harvest yielded.
 *
 *   THE MARQUEE IS DECORATION, NOT STRUCTURE. Exactly one run carries real alt
 *   text; every other run is an echo — aria-hidden, alt="", and flagged with
 *   data-marquee-echo. `prefers-reduced-motion` stops the animation AND drops
 *   every echo, leaving a single static, scrollable row of the real set. The
 *   content is never only reachable through motion, and a reader who has asked
 *   for stillness is not handed the same four logos eight times.
 *
 * Arity is the harvest's, via the repeat block.
 *
 * Slots:
 *   {section_title}   → "Trusted by"
 *   {logos[].src}     → resolved asset path — REQUIRED, never a placeholder
 *   {logos[].alt}     → "Cape Town Chamber of Commerce"
 */

// Tokens: {section_title} {logos[].src} {logos[].alt}

// Declared so it can be REFUSED. A partner logo is a third party's mark and an
// assertion that the relationship exists; generating one invents both. Harvested
// or absent.
// Art: slot=logos[].src intent=abstract aspect=1:1 role=load-bearing

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

/** Logo bars breathe wider than body rhythm; derived, never a bare pixel. */
const RAIL_GAP = "calc(var(--block-gap, 24px) * 2)";

/**
 * Marks per half before the half is duplicated. Sixteen narrow marks at the
 * rail gap still exceed a 1440px viewport, which is the condition for the
 * loop to read as continuous rather than as a visible repeat.
 */
const MIN_TRACK_ITEMS = 16;

/** Seconds of travel per mark — holds perceived speed constant across arities. */
const SECONDS_PER_ITEM = 3.2;

/**
 * Static, module-level, never interpolated. See the note at its use site.
 *
 * The edge mask is `currentColor`, not a colour literal: a CSS gradient mask
 * reads the alpha channel only, so an opaque token colour and `transparent`
 * are all it needs, and the palette stays in the tokens.
 */
const MARQUEE_CSS = `
.logo-marquee {
  overflow: hidden;
  -webkit-mask-image: linear-gradient(to right, transparent 0%, currentColor 7%, currentColor 93%, transparent 100%);
  mask-image: linear-gradient(to right, transparent 0%, currentColor 7%, currentColor 93%, transparent 100%);
}
.logo-marquee__track {
  animation: logo-marquee-scroll var(--marquee-duration, 38s) linear infinite;
  will-change: transform;
}
.logo-marquee:hover .logo-marquee__track,
.logo-marquee:focus-within .logo-marquee__track { animation-play-state: paused; }
@keyframes logo-marquee-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}
@media (prefers-reduced-motion: reduce) {
  .logo-marquee { overflow-x: auto; }
  .logo-marquee__track { animation: none; }
  .logo-marquee__run[data-marquee-echo="true"] { display: none; }
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
  const resolvedLogos = (logos || []).filter(isResolved);

  // An empty rail claims a set of relationships that resolved to nothing.
  if (!resolvedLogos.length) return null;

  // camelCase deliberately — see FOOTER/mega: a lowercase local rendered as
  // `{title}` is indistinguishable from a slot and gets substituted away.
  const titleText = sectionTitle && !sectionTitle.startsWith("{") ? sectionTitle : "";

  // Repeat the harvested run until a half outruns the viewport, then duplicate
  // the half — the -50% keyframe stays exact because the halves are identical.
  const runCount = Math.max(1, Math.ceil(MIN_TRACK_ITEMS / resolvedLogos.length));
  const runIndices = Array.from({ length: runCount }, (unusedValue, runIndex) => runIndex);
  const marqueeStyle = {
    "--marquee-duration": `${Math.round(runCount * resolvedLogos.length * SECONDS_PER_ITEM)}s`,
  } as CSSProperties;

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

      <div className="logo-marquee relative w-full" style={marqueeStyle}>
        <div className="logo-marquee__track flex w-max items-center">
          {[0, 1].map((halfIndex) =>
            runIndices.map((runIndex) => {
              // Exactly one run is real; every other is an echo, so a screen
              // reader hears the partner set once and reduced-motion can drop
              // the rest without losing content.
              const isEcho = halfIndex !== 0 || runIndex !== 0;
              return (
                <ul
                  key={`${halfIndex}-${runIndex}`}
                  data-marquee-echo={isEcho ? "true" : undefined}
                  aria-hidden={isEcho ? "true" : undefined}
                  className="logo-marquee__run flex shrink-0 items-center"
                  style={{ gap: RAIL_GAP, paddingRight: RAIL_GAP }}
                >
                  {resolvedLogos.map((logo, logoIndex) => (
                    <li
                      key={`${halfIndex}-${runIndex}-${logoIndex}`}
                      className="flex min-w-[6rem] shrink-0 items-center justify-center"
                    >
                      {/* Intrinsic sizing only — a logo box with a fixed aspect
                          distorts wordmarks of different widths. The min-width
                          sits on the cell, not the mark, so a narrow monogram
                          gets rhythm without being stretched. */}
                      <img
                        src={logo.src}
                        alt={isEcho ? "" : logo.alt}
                        loading="lazy"
                        decoding="async"
                        className="h-7 w-auto max-w-[10rem] object-contain md:h-8"
                        style={{ opacity: 0.72 }}
                      />
                    </li>
                  ))}
                </ul>
              );
            }),
          )}
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

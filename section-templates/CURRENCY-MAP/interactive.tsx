"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * CURRENCY-MAP | interactive
 * Token-driven section template — tenant content filled at build time.
 *
 * A plotted currency map: each node is a currency, positioned on a schematic
 * world canvas, with hover tooltip and click-through detail. Ported off the
 * brand-mustache scheme (31 references, zero of them resolvable by the token
 * filler) onto CSS custom properties. Four deliberate departures from what
 * shipped:
 *
 *   1. EVERY COLOUR IS A TOKEN. Not one Tailwind palette literal, not one hex.
 *      The build compiles the market benchmark into custom properties
 *      (--accent, --surface, --foreground, --muted, --border, --radius-card …)
 *      and this file reads them. A class like `bg-` plus a mustache brand key
 *      was never something Tailwind could compile, nor a token the filler could
 *      substitute — it was a class name that reached production as literal text.
 *
 *   2. THE MAP SCALE IS DERIVED, NOT INVENTED. An interactive map wants a
 *      colour ramp, and the obvious move — pick a saturated scale — bakes in a
 *      dark ground. Every fill here is a `color-mix` of --accent, --surface and
 *      --border, so the ramp is whatever the design system's accent is, at the
 *      contrast the light ground needs. See RAMP below.
 *
 *   3. DIRECTION IS CARRIED BY THE GLYPH, NOT BY COLOUR. Rise/fall reads from
 *      ▲ / ▼ / ◆ first. Colour reinforces it and is overridable via optional
 *      --positive / --negative, but falls back to accent/muted — both of which
 *      clear 4.5:1 on --background and on --surface. Nothing depends on a
 *      viewer distinguishing green from red.
 *
 *   4. NO FABRICATED RATES. The shipped default node set carried twelve
 *      invented exchange rates ("18.6415", "+0.31%") that would render on any
 *      page whose harvest supplied no `nodes`. On an FSP-regulated site an
 *      invented mid-rate is not placeholder copy, it is a false quote. `rate`,
 *      `change` and `direction` are now optional; the fallback set carries only
 *      ISO codes and map positions, which are facts, and the rate row renders
 *      only where real data was supplied.
 *
 * Hierarchy comes from size and space. Weight comes from --heading-weight and
 * never exceeds 500 — the benchmark reference uses no bold display type.
 *
 * Slots:
 *   {headline}    → "Global Currency Exchange Rates"
 *   {subheadline} → "Rates for major world currencies. Tap any node…"
 *   {disclaimer}  → "Rates shown are indicative market mid-rates…"
 *
 * `nodes` is structured data (code, rate, position), not page prose — it is a
 * prop sourced from `metrics.nodes`, never a `{token}`, because a harvest of
 * headings and body text cannot supply it.
 */

// The machine-read declaration. `slot_contract.declared_slots()` reads ONLY a
// `// Tokens:` line or a `Slot placeholders` block — the prose "Slots:" list
// above is neither, so without this line the contract falls back to a
// permissive brace sweep and substitutes this file's own JS identifiers away.
// Tokens: {headline} {subheadline} {disclaimer}

interface CurrencyNode {
  label: string;
  code: string;
  /** Omitted unless a real rate was supplied; never invented. */
  rate?: string;
  change?: string;
  direction?: "up" | "down" | "flat";
  /** Map position as a 0–100 percentage of the canvas. */
  x: number;
  y: number;
}

interface CurrencyMapInteractiveProps {
  headline?: string;
  subheadline?: string;
  nodes?: CurrencyNode[];
  disclaimer?: string;
}

/**
 * Fallback plot. ISO codes and approximate map positions only — no rate, no
 * change, no direction. See note 4: the section renders a geography, and the
 * numbers appear only when the fill supplies them.
 */
const fallbackNodes: CurrencyNode[] = [
  { label: "US Dollar", code: "USD", x: 22, y: 48 },
  { label: "Euro", code: "EUR", x: 52, y: 36 },
  { label: "British Pound", code: "GBP", x: 50, y: 32 },
  { label: "Japanese Yen", code: "JPY", x: 78, y: 28 },
  { label: "Swiss Franc", code: "CHF", x: 55, y: 40 },
  { label: "Canadian Dollar", code: "CAD", x: 18, y: 55 },
  { label: "Australian Dollar", code: "AUD", x: 76, y: 60 },
  { label: "Chinese Yuan", code: "CNY", x: 72, y: 34 },
  { label: "Indian Rupee", code: "INR", x: 62, y: 50 },
  { label: "Brazilian Real", code: "BRL", x: 28, y: 68 },
  { label: "South African Rand", code: "ZAR", x: 54, y: 62 },
  { label: "Singapore Dollar", code: "SGD", x: 70, y: 26 },
];

const FOREGROUND = "var(--foreground)";
const MUTED = "var(--muted, color-mix(in srgb, var(--foreground) 62%, var(--background)))";
const HAIRLINE = "var(--border, color-mix(in srgb, var(--foreground) 12%, var(--background)))";
const ACCENT = "var(--accent, var(--foreground))";
const ON_ACCENT = "var(--on-accent, var(--background))";
const CANVAS = "var(--surface, var(--background))";

/**
 * RAMP — the map's colour scale, derived rather than invented.
 *
 * A stock choropleth ramp assumes a dark ground; mixed against --surface these
 * stay legible on the benchmark's white page and pale-grey surface. Idle nodes
 * sit at --background with a hairline ring and --foreground text (≈13:1);
 * active nodes invert to --accent with --on-accent text (≈9:1 at the
 * benchmark's deep-blue accent). The connecting web is accent-at-low-alpha —
 * decorative, aria-hidden, and not load-bearing for contrast.
 */
const RAMP = {
  webIdle: "color-mix(in srgb, var(--accent) 22%, transparent)",
  webActive: "color-mix(in srgb, var(--accent) 55%, transparent)",
  graticule: "color-mix(in srgb, var(--muted, var(--foreground)) 20%, transparent)",
  nodeIdle: "var(--background)",
  nodeIdleRing: HAIRLINE,
  nodeHoverRing: "color-mix(in srgb, var(--accent) 45%, transparent)",
  nodeActive: ACCENT,
  nodeActiveRing: "color-mix(in srgb, var(--accent) 70%, var(--foreground))",
};

/**
 * Direction tone. --positive / --negative are honoured when the design system
 * defines them; the fallbacks are tokens already proven against both grounds,
 * so an undefined pair degrades to legible rather than to a guessed hex.
 */
const directionTones: Record<string, string> = {
  up: `var(--positive, ${ACCENT})`,
  down: `var(--negative, ${MUTED})`,
  flat: MUTED,
};

const directionGlyphs: Record<string, string> = {
  up: "▲",
  down: "▼",
  flat: "◆",
};

export default function SectionCurrencyMapInteractive({
  headline = "{headline}",
  subheadline = "{subheadline}",
  nodes = [],
  disclaimer = "{disclaimer}",
}: CurrencyMapInteractiveProps) {
  const [hoveredNode, setHoveredNode] = useState<number | null>(null);
  const [selectedNode, setSelectedNode] = useState<number | null>(null);
  const plottedNodes = nodes.length > 0 ? nodes : fallbackNodes;

  // A heading over an empty canvas is worse than no section.
  if (!plottedNodes.length) return null;

  const originNode = plottedNodes[0];
  const detailNode = selectedNode !== null ? plottedNodes[selectedNode] : null;

  return (
    <section
      className="w-full"
      style={{
        background: "var(--background)",
        color: FOREGROUND,
        paddingTop: "var(--section-py, 96px)",
        paddingBottom: "var(--section-py, 96px)",
      }}
    >
      <div className="mx-auto w-full max-w-6xl px-6">
        {(headline || subheadline) && (
          <div
            className="mx-auto max-w-3xl text-center"
            style={{ marginBottom: "var(--block-gap, 48px)" }}
          >
            {headline && (
              <motion.h2
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.6, ease: "easeOut" }}
                className="text-[2rem] md:text-[3rem] leading-[1.1] tracking-tight"
                style={{
                  fontFamily: "var(--font-heading, inherit)",
                  fontWeight: "var(--heading-weight, 400)" as unknown as number,
                }}
              >
                {headline}
              </motion.h2>
            )}
            {subheadline && (
              <motion.p
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.6, delay: 0.12, ease: "easeOut" }}
                className="mt-5 text-lg leading-relaxed"
                style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
              >
                {subheadline}
              </motion.p>
            )}
          </div>
        )}

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.15 }}
          className="relative w-full aspect-[2/1] overflow-hidden"
          style={{
            background: CANVAS,
            border: `1px solid ${HAIRLINE}`,
            borderRadius: "var(--radius-card, 16px)",
          }}
        >
          {/* Graticule — a dot lattice standing in for landmass; decorative. */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0"
            style={{
              backgroundImage: `radial-gradient(circle at 1px 1px, ${RAMP.graticule} 1px, transparent 0)`,
              backgroundSize: "32px 32px",
            }}
          />

          {/* Web of relations back to the base currency. */}
          <svg
            className="pointer-events-none absolute inset-0 h-full w-full"
            aria-hidden="true"
          >
            {plottedNodes.map((node, index) => {
              if (index === 0) return null;
              const isLit = hoveredNode === index || selectedNode === index;
              return (
                <line
                  key={`web-${index}`}
                  x1={`${originNode.x}%`}
                  y1={`${originNode.y}%`}
                  x2={`${node.x}%`}
                  y2={`${node.y}%`}
                  stroke={isLit ? RAMP.webActive : RAMP.webIdle}
                  strokeWidth={isLit ? 1.5 : 0.75}
                  className="transition-all duration-300"
                />
              );
            })}
          </svg>

          {plottedNodes.map((node, index) => {
            const isLit = hoveredNode === index || selectedNode === index;
            const isSelected = selectedNode === index;
            // camelCase, always: a lowercase local rendered as `{glyph}` is
            // indistinguishable from a `{headline}` slot to the token sweep.
            const directionTone = node.direction ? directionTones[node.direction] : MUTED;
            const directionGlyph = node.direction ? directionGlyphs[node.direction] : "";

            return (
              <motion.button
                key={`node-${index}`}
                type="button"
                initial={{ scale: 0, opacity: 0 }}
                whileInView={{ scale: 1, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.45, delay: 0.25 + index * 0.05, ease: "backOut" }}
                className={`absolute flex -translate-x-1/2 -translate-y-1/2 transform cursor-pointer flex-col items-center justify-center transition-all duration-300 ease-out focus-visible:outline-2 focus-visible:outline-offset-2 ${
                  isLit ? "z-20 scale-110" : "z-10 hover:scale-105"
                }`}
                style={{
                  left: `${node.x}%`,
                  top: `${node.y}%`,
                  borderRadius: "var(--radius-button, 100px)",
                  outlineColor: ACCENT,
                }}
                onMouseEnter={() => setHoveredNode(index)}
                onMouseLeave={() => setHoveredNode(null)}
                onFocus={() => setHoveredNode(index)}
                onBlur={() => setHoveredNode(null)}
                onClick={() => setSelectedNode(isSelected ? null : index)}
                aria-pressed={isSelected}
                aria-label={
                  node.rate
                    ? `${node.label} (${node.code}): ${node.rate}${node.change ? `, ${node.change}` : ""}`
                    : `${node.label} (${node.code})`
                }
              >
                <span
                  className="flex h-12 w-12 items-center justify-center rounded-full transition-all duration-300 md:h-14 md:w-14"
                  style={{
                    background: isLit ? RAMP.nodeActive : RAMP.nodeIdle,
                    color: isLit ? ON_ACCENT : FOREGROUND,
                    border: `1px solid ${
                      isLit
                        ? RAMP.nodeActiveRing
                        : hoveredNode === index
                          ? RAMP.nodeHoverRing
                          : RAMP.nodeIdleRing
                    }`,
                    fontFamily: "var(--font-body, inherit)",
                  }}
                >
                  <span className="text-sm md:text-base" style={{ fontWeight: 500 }}>
                    {node.code}
                  </span>
                </span>

                <AnimatePresence>
                  {hoveredNode === index && !isSelected && (
                    <motion.span
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 4 }}
                      transition={{ duration: 0.18 }}
                      className="absolute -bottom-2 block translate-y-full whitespace-nowrap px-3 py-2 text-xs"
                      style={{
                        background: "var(--background)",
                        color: FOREGROUND,
                        border: `1px solid ${HAIRLINE}`,
                        borderRadius: "var(--radius-card, 12px)",
                        fontFamily: "var(--font-body, inherit)",
                      }}
                    >
                      <span className="block" style={{ fontWeight: 500 }}>
                        {node.label}
                      </span>
                      {node.rate && (
                        <span className="mt-0.5 flex items-center gap-1.5">
                          <span className="font-mono">{node.rate}</span>
                          {node.change && (
                            <span style={{ color: directionTone }}>
                              {directionGlyph} {node.change}
                            </span>
                          )}
                        </span>
                      )}
                    </motion.span>
                  )}
                </AnimatePresence>
              </motion.button>
            );
          })}

          <AnimatePresence>
            {detailNode && (
              <motion.div
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 16 }}
                transition={{ duration: 0.28, ease: "easeOut" }}
                className="absolute bottom-4 right-4 z-30 max-w-[240px] px-5 py-4 md:bottom-6 md:right-6"
                style={{
                  background: "var(--background)",
                  border: `1px solid ${HAIRLINE}`,
                  borderRadius: "var(--radius-card, 16px)",
                  fontFamily: "var(--font-body, inherit)",
                }}
              >
                <button
                  type="button"
                  onClick={() => setSelectedNode(null)}
                  className="absolute right-2 top-2 text-sm leading-none transition-colors"
                  style={{ color: MUTED }}
                  aria-label="Close detail panel"
                >
                  ✕
                </button>
                <div className="text-sm" style={{ color: FOREGROUND, fontWeight: 500 }}>
                  {detailNode.label}
                </div>
                <div className="mt-0.5 text-xs" style={{ color: MUTED }}>
                  {detailNode.code}
                </div>
                {detailNode.rate && (
                  <div className="mt-3 flex items-baseline justify-between gap-3">
                    <span
                      className="font-mono text-lg"
                      style={{ color: FOREGROUND, fontWeight: 500 }}
                    >
                      {detailNode.rate}
                    </span>
                    {detailNode.change && (
                      <span
                        className="flex items-center gap-1 text-sm"
                        style={{
                          color: detailNode.direction
                            ? directionTones[detailNode.direction]
                            : MUTED,
                        }}
                      >
                        {detailNode.direction ? directionGlyphs[detailNode.direction] : ""}
                        {detailNode.change}
                      </span>
                    )}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {disclaimer && (
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.35 }}
            className="mx-auto mt-6 max-w-2xl text-center text-xs leading-relaxed"
            style={{ color: MUTED, fontFamily: "var(--font-body, inherit)" }}
          >
            {disclaimer}
          </motion.p>
        )}
      </div>
    </section>
  );
}

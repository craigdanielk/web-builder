"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * CURRENCY-MAP | interactive
 * Parameterized section template — brand tokens injected at build time.
 *
 * An interactive world currency visualization with plotted currency nodes.
 * Each node represents a currency pair with exchange data, marker position,
 * and interactive detail on hover/click. All text is driven by slot_schema
 * content — no hard-coded copy.
 *
 * Token placeholders (replaced by orchestrator):
 *   {{brand.bg_primary}}           -> e.g. "gray-50" / "stone-50"
 *   {{brand.bg_secondary}}         -> e.g. "white"
 *   {{brand.text_primary}}         -> e.g. "gray-900"
 *   {{brand.text_muted}}           -> e.g. "gray-500"
 *   {{brand.accent}}               -> e.g. "blue-600"
 *   {{brand.accent_hover}}         -> e.g. "blue-700"
 *   {{brand.heading_font}}         -> e.g. "DM Serif Display"
 *   {{brand.body_font}}            -> e.g. "DM Sans"
 */

interface CurrencyNode {
  label: string;
  code: string;
  rate: string;
  change: string;
  direction: "up" | "down" | "flat";
  x: number;
  y: number;
}

interface CurrencyMapInteractiveProps {
  headline?: string;
  subheadline?: string;
  nodes?: CurrencyNode[];
  disclaimer?: string;
}

const defaultNodes: CurrencyNode[] = [
  { label: "US Dollar", code: "USD", rate: "1.0000", change: "0.00%", direction: "flat", x: 22, y: 48 },
  { label: "Euro", code: "EUR", rate: "0.9213", change: "+0.14%", direction: "up", x: 52, y: 36 },
  { label: "British Pound", code: "GBP", rate: "0.7885", change: "-0.08%", direction: "down", x: 50, y: 32 },
  { label: "Japanese Yen", code: "JPY", rate: "149.72", change: "+0.22%", direction: "up", x: 78, y: 28 },
  { label: "Swiss Franc", code: "CHF", rate: "0.8761", change: "-0.03%", direction: "down", x: 55, y: 40 },
  { label: "Canadian Dollar", code: "CAD", rate: "1.3642", change: "+0.05%", direction: "up", x: 18, y: 55 },
  { label: "Australian Dollar", code: "AUD", rate: "1.5427", change: "-0.11%", direction: "down", x: 76, y: 60 },
  { label: "Chinese Yuan", code: "CNY", rate: "7.2431", change: "+0.01%", direction: "flat", x: 72, y: 34 },
  { label: "Indian Rupee", code: "INR", rate: "83.2810", change: "+0.07%", direction: "up", x: 62, y: 50 },
  { label: "Brazilian Real", code: "BRL", rate: "4.9735", change: "-0.18%", direction: "down", x: 28, y: 68 },
  { label: "South African Rand", code: "ZAR", rate: "18.6415", change: "+0.31%", direction: "up", x: 54, y: 62 },
  { label: "Singapore Dollar", code: "SGD", rate: "1.3284", change: "+0.03%", direction: "up", x: 70, y: 26 },
];

const directionColors: Record<string, string> = {
  up: "text-green-600",
  down: "text-red-500",
  flat: "text-{{brand.text_muted}}",
};

const directionIcons: Record<string, string> = {
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
  const [activeNode, setActiveNode] = useState<number | null>(null);
  const [selectedNode, setSelectedNode] = useState<number | null>(null);
  const displayNodes = nodes.length > 0 ? nodes : defaultNodes;

  return (
    <section className="bg-{{brand.bg_primary}} py-16 md:py-24 lg:py-28">
      <div className="container mx-auto px-4 max-w-6xl">
        {/* Header */}
        <div className="text-center mb-12 md:mb-16">
          <motion.h2
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.7, ease: "easeOut" }}
            className="text-3xl md:text-4xl lg:text-5xl font-bold text-{{brand.text_primary}} leading-tight tracking-tight"
            style={{ fontFamily: "var(--font-heading, '{{brand.heading_font}}')" }}
          >
            {headline}
          </motion.h2>
          {subheadline && (
            <motion.p
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.7, delay: 0.15, ease: "easeOut" }}
              className="mt-4 text-lg md:text-xl text-{{brand.text_muted}} max-w-3xl mx-auto leading-relaxed"
              style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
            >
              {subheadline}
            </motion.p>
          )}
        </div>

        {/* Map container */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="relative w-full aspect-[2/1] bg-{{brand.bg_secondary}} rounded-2xl border border-{{brand.text_muted}}/10 shadow-lg overflow-hidden"
        >
          {/* Background map pattern - subtle grid overlay for world-map feel */}
          <div className="absolute inset-0 opacity-[0.04] pointer-events-none"
            style={{
              backgroundImage:
                "radial-gradient(circle at 1px 1px, currentColor 1px, transparent 0)",
              backgroundSize: "32px 32px",
            }}
          />

          {/* Connecting lines between nodes */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none" aria-hidden="true">
            {displayNodes.map((node, i) => {
              const pctToSvg = (pct: number, dim: number) => (pct / 100) * dim;
              const parent = displayNodes[0]; // always lines to base (USD)
              if (i === 0) return null;
              const x1 = pctToSvg(parent.x, 100);
              const y1 = pctToSvg(parent.y, 100);
              const x2 = pctToSvg(node.x, 100);
              const y2 = pctToSvg(node.y, 100);
              const isActive = activeNode === i || selectedNode === i;
              return (
                <line
                  key={`line-${i}`}
                  x1={`${x1}%`}
                  y1={`${y1}%`}
                  x2={`${x2}%`}
                  y2={`${y2}%`}
                  stroke="currentColor"
                  strokeWidth={isActive ? 1.5 : 0.5}
                  className="text-{{brand.accent}}/30 transition-all duration-300"
                />
              );
            })}
          </svg>

          {/* Currency nodes */}
          {displayNodes.map((node, i) => {
            const isActive = activeNode === i;
            const isSelected = selectedNode === i;
            const isHighlighted = isActive || isSelected;

            return (
              <motion.button
                key={`node-${i}`}
                initial={{ scale: 0, opacity: 0 }}
                whileInView={{ scale: 1, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: 0.3 + i * 0.06, ease: "backOut" }}
                className={`
                  absolute transform -translate-x-1/2 -translate-y-1/2
                  flex flex-col items-center justify-center
                  rounded-full cursor-pointer
                  transition-all duration-300 ease-out
                  focus-visible:outline-2 focus-visible:outline-offset-2
                  focus-visible:outline-{{brand.accent}}
                  ${isHighlighted ? "z-20 scale-110" : "z-10 hover:scale-105"}
                `}
                style={{ left: `${node.x}%`, top: `${node.y}%` }}
                onMouseEnter={() => setActiveNode(i)}
                onMouseLeave={() => setActiveNode(null)}
                onClick={() => setSelectedNode(isSelected ? null : i)}
                aria-label={`${node.label} (${node.code}): ${node.rate} ${node.change}`}
              >
                {/* Node dot */}
                <span
                  className={`
                    flex items-center justify-center w-12 h-12 md:w-14 md:h-14 rounded-full
                    shadow-md border-2 transition-all duration-300
                    ${isHighlighted
                      ? "bg-{{brand.accent}} text-white border-{{brand.accent_hover}} shadow-lg"
                      : "bg-{{brand.bg_secondary}} text-{{brand.text_primary}} border-{{brand.text_muted}}/20 hover:border-{{brand.accent}}/50"
                    }
                  `}
                  style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
                >
                  <span className="text-sm md:text-base font-bold">{node.code}</span>
                </span>

                {/* Tooltip on hover */}
                <AnimatePresence>
                  {isActive && !isSelected && (
                    <motion.div
                      initial={{ opacity: 0, y: 4, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 4, scale: 0.95 }}
                      transition={{ duration: 0.2 }}
                      className={`
                        absolute -bottom-2 translate-y-full
                        px-3 py-2 rounded-lg shadow-lg text-xs whitespace-nowrap
                        bg-{{brand.bg_secondary}} border border-{{brand.text_muted}}/10
                        text-{{brand.text_primary}}
                      `}
                      style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
                    >
                      <div className="font-semibold">{node.label}</div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="font-mono">{node.rate}</span>
                        <span className={`flex items-center gap-0.5 text-xs ${directionColors[node.direction]}`}>
                          {directionIcons[node.direction]} {node.change}
                        </span>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.button>
            );
          })}

          {/* Selected node detail panel */}
          <AnimatePresence>
            {selectedNode !== null && displayNodes[selectedNode] && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                className="absolute bottom-4 right-4 md:bottom-6 md:right-6 px-5 py-4 rounded-xl shadow-xl bg-{{brand.bg_secondary}} border border-{{brand.text_muted}}/10 max-w-[240px]"
                style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
              >
                <button
                  onClick={() => setSelectedNode(null)}
                  className="absolute top-2 right-2 text-{{brand.text_muted}} hover:text-{{brand.text_primary}} transition-colors text-sm leading-none"
                  aria-label="Close detail panel"
                >
                  ✕
                </button>
                <div className="text-sm font-semibold text-{{brand.text_primary}}">
                  {displayNodes[selectedNode].label}
                </div>
                <div className="text-xs text-{{brand.text_muted}} mt-0.5">
                  {displayNodes[selectedNode].code}
                </div>
                <div className="mt-3 flex items-baseline justify-between">
                  <span className="text-lg font-mono font-bold text-{{brand.text_primary}}">
                    {displayNodes[selectedNode].rate}
                  </span>
                  <span className={`flex items-center gap-1 text-sm font-medium ${directionColors[displayNodes[selectedNode].direction]}`}>
                    {directionIcons[displayNodes[selectedNode].direction]}
                    {displayNodes[selectedNode].change}
                  </span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Disclaimer */}
        {disclaimer && (
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="mt-6 text-xs text-{{brand.text_muted}}/60 max-w-2xl mx-auto text-center leading-relaxed"
            style={{ fontFamily: "var(--font-body, '{{brand.body_font}}')" }}
          >
            {disclaimer}
          </motion.p>
        )}
      </div>
    </section>
  );
}

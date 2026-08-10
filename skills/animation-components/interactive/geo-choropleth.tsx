"use client";

import React, { useEffect, useRef, useState } from "react";
import { geoNaturalEarth1, geoPath, type GeoProjection, type ExtendedFeature } from "d3-geo";
import { feature } from "topojson-client";

/**
 * GeoChoropleth — interactive world map that highlights a set of regions and
 * shows a hover card with details and an optional call to action.
 *
 * TENANT-AGNOSTIC. The map ships no dataset and no copy. The caller supplies
 * `regions` (or `regionsUrl`), keyed by the geo id used in the topojson —
 * numeric ISO 3166-1 codes for the standard world-atlas file. Each region
 * carries its own label, detail rows and CTA, so the same component serves
 * "supported currencies", "shipping zones", "office locations" or anything else
 * that is a set of countries plus per-country facts.
 *
 * Generalised from a production fintech site's currency-coverage map. The
 * original hardcoded that tenant's palette, its two data files, its
 * currency/OTC field names and a "Send this currency?" signup CTA. All five are
 * now props; the d3-geo projection, hover behaviour and close-delay — the parts
 * that were actually engineering — are unchanged.
 *
 * REQUIRES a topojson file to be served (e.g. world-atlas `countries-110m.json`
 * in `public/`) and the `d3-geo` + `topojson-client` packages.
 */

export type GeoRegion = {
  /** Display name shown as the hover card title */
  name: string;
  /** Optional label/value rows, rendered in order */
  details?: Array<{ label: string; value: string }>;
  /** Optional call to action inside the hover card */
  cta?: { label: string; href: string };
};

export type GeoChoroplethColors = {
  /** Fill for regions present in `regions` */
  highlight?: string;
  /** Fill for the hovered region */
  active?: string;
  /** Fill for every other region */
  base?: string;
  /** Border between regions */
  stroke?: string;
  /** Map backdrop */
  background?: string;
  /** Hover card title colour */
  accent?: string;
  /** CTA button fill */
  ctaBackground?: string;
  /** CTA button text */
  ctaText?: string;
};

export type GeoChoroplethProps = {
  className?: string;
  /** Region data keyed by topojson feature id. */
  regions?: Record<string, GeoRegion>;
  /** Alternative to `regions`: fetch a JSON object of the same shape. */
  regionsUrl?: string;
  /** Key to read from the fetched JSON, when the payload is wrapped. */
  regionsKey?: string;
  /** URL of the topojson world file (default `/countries-110m.json`). */
  geoUrl?: string;
  /** Name of the object inside the topojson (default `countries`). */
  geoObjectName?: string;
  /** Projection factory; defaults to Natural Earth. */
  projectionFactory?: () => GeoProjection;
  /** Projection scale (default 178, tuned for the 960x560 viewBox). */
  scale?: number;
  colors?: GeoChoroplethColors;
  /** Accessible name for the map. */
  ariaLabel?: string;
};

type Active = GeoRegion & { id: string; cx: number; cy: number };

const VIEW_W = 960;
const VIEW_H = 560;

const DEFAULT_COLORS: Required<GeoChoroplethColors> = {
  highlight: "var(--brand-accent, #6366f1)",
  active: "var(--brand-accent-strong, #1e1b4b)",
  base: "var(--brand-muted, #e2e6ec)",
  stroke: "var(--brand-surface, #ffffff)",
  background: "var(--brand-surface-subtle, #f8fafc)",
  accent: "var(--brand-ink, #1e1b4b)",
  ctaBackground: "var(--brand-accent, #6366f1)",
  ctaText: "var(--brand-on-accent, #ffffff)",
};

export default function GeoChoropleth({
  className = "",
  regions,
  regionsUrl,
  regionsKey,
  geoUrl = "/countries-110m.json",
  geoObjectName = "countries",
  projectionFactory,
  scale = 178,
  colors,
  ariaLabel = "Regional coverage map",
}: GeoChoroplethProps = {}) {
  const [geo, setGeo] = useState<{ features: ExtendedFeature[] } | null>(null);
  const [fetched, setFetched] = useState<Record<string, GeoRegion>>({});
  const [active, setActive] = useState<Active | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const c = { ...DEFAULT_COLORS, ...(colors || {}) };
  const data = regions ?? fetched;

  useEffect(() => {
    let cancelled = false;
    fetch(geoUrl)
      .then((r) => r.json())
      .then((topo) => {
        if (cancelled) return;
        const obj = topo?.objects?.[geoObjectName];
        if (!obj) return;
        setGeo(feature(topo, obj) as unknown as { features: ExtendedFeature[] });
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [geoUrl, geoObjectName]);

  useEffect(() => {
    if (!regionsUrl) return;
    let cancelled = false;
    fetch(regionsUrl)
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return;
        setFetched((regionsKey ? d?.[regionsKey] : d) || {});
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [regionsUrl, regionsKey]);

  // The close timer outlives a single hover, so it has to be cleared on unmount
  // or a late setState lands on an unmounted tree.
  useEffect(() => () => { if (closeTimer.current) clearTimeout(closeTimer.current); }, []);

  const projection = (projectionFactory ? projectionFactory() : geoNaturalEarth1())
    .scale(scale)
    .translate([VIEW_W / 2, VIEW_H * 0.536]);
  const path = geoPath().projection(projection);

  const clearClose = () => { if (closeTimer.current) clearTimeout(closeTimer.current); };

  if (!geo) {
    return <div className={`h-[300px] w-full animate-pulse rounded-xl bg-gray-100 md:h-[520px] ${className}`} />;
  }

  return (
    <div className={`relative w-full ${className}`}>
      <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="block h-auto w-full" role="img" aria-label={ariaLabel}>
        <rect x="0" y="0" width={VIEW_W} height={VIEW_H} fill={c.background} rx="8" />
        {geo.features.map((f) => {
          const id = String(f.id ?? "");
          const region = data[id];
          const highlighted = !!region;
          const isActive = active?.id === id;
          return (
            <path
              key={id}
              d={path(f) || undefined}
              fill={highlighted ? (isActive ? c.active : c.highlight) : c.base}
              stroke={c.stroke}
              strokeWidth={0.4}
              style={{ cursor: highlighted ? "pointer" : "default", transition: "fill 0.2s" }}
              onMouseEnter={() => {
                if (!region) return;
                clearClose();
                const [cx, cy] = path.centroid(f);
                setActive({ id, ...region, cx, cy });
              }}
              onMouseLeave={() => {
                closeTimer.current = setTimeout(() => setActive(null), 140);
              }}
            />
          );
        })}
      </svg>

      {active && (
        <div
          className="pointer-events-auto absolute z-10 -translate-x-1/2 -translate-y-full"
          style={{ left: `${(active.cx / VIEW_W) * 100}%`, top: `${(active.cy / VIEW_H) * 100}%` }}
          onMouseEnter={clearClose}
          onMouseLeave={() => setActive(null)}
        >
          <div className="mb-2 w-52 rounded-lg border border-gray-200 bg-white p-3 shadow-[0_16px_40px_-12px_rgba(15,23,42,0.3)]">
            <p className="text-sm font-semibold" style={{ color: c.accent }}>{active.name}</p>
            {(active.details || []).map((row, i) => (
              <p key={i} className="mt-0.5 text-xs text-gray-500">
                {row.label}: <span className="font-medium text-gray-700">{row.value}</span>
              </p>
            ))}
            {active.cta && (
              <a
                href={active.cta.href}
                className="mt-2.5 flex items-center justify-center gap-1.5 rounded-md px-3 py-2 text-xs font-semibold transition-opacity hover:opacity-90"
                style={{ background: c.ctaBackground, color: c.ctaText }}
              >
                {active.cta.label}
                <span aria-hidden>&rarr;</span>
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

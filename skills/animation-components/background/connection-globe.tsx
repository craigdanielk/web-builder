"use client";

import React, { useEffect, useRef } from "react";

/**
 * ConnectionGlobe — continent-dotted rotating globe with animated connector
 * arcs between geographic nodes. Canvas 2D, DPR-aware, IntersectionObserver-
 * gated, respects prefers-reduced-motion. Falls back to a uniform sphere when
 * the land-point cloud is unavailable.
 *
 * TENANT-AGNOSTIC. Colours, nodes, node artwork and the land-cloud URL are all
 * props. Nothing about a particular brand or a particular set of countries is
 * baked in; with no props at all it renders a neutral network globe using CSS
 * custom properties for colour.
 *
 * ── The land cloud ────────────────────────────────────────────────────────────
 * Dots are sampled to land masses so the CONTINENTS read, rather than a uniform
 * fibonacci fill. Those points are computed at BUILD time by
 * `../assets/generate-globe-points.mjs` and shipped as a ~20 KB float32 binary.
 * They used to be computed in the browser, by 6,000 spherical point-in-polygon
 * tests against 177 country polygons in one un-yielded loop — measured at
 * 9,842 ms of a homepage's 9,845 ms Total Blocking Time, 99.97% of it, on every
 * load for every visitor. The input is a checked-in file and the output never
 * varied, so there was never anything to compute at runtime. If the binary is
 * absent the component degrades to the uniform sphere rather than failing.
 *
 * ── The render loop ───────────────────────────────────────────────────────────
 * `draw()` re-schedules itself in exactly one place, and only when the canvas is
 * on screen and the user has not asked for reduced motion. Under reduced motion
 * one frame is drawn and the loop ends — the picture is identical to the
 * animated one at rest, and the user who asked for less motion no longer pays
 * the identical CPU bill for it. Anything that changes what should be on screen
 * (the cloud arriving, an image decoding, a resize) must ask for a frame rather
 * than assume the next one is already coming.
 *
 * Ported from a production fintech site (Lighthouse 89-98) with its raf-gating
 * test — see `../__tests__/connection-globe.raf-gating.test.tsx`. Changes on the
 * way in: brand hexes and the eleven brand-chosen countries became props;
 * colours are resolved through the canvas so `var(--token)`, named colours, hsl
 * and hex all work; nodes without artwork now render as accent-filled coins so
 * the default needs no image assets at all.
 */

export type GlobeNode = {
  /** Latitude in degrees, -90..90 */
  lat: number;
  /** Longitude in degrees, -180..180 */
  lng: number;
  /** Optional image (flag, logo, avatar) drawn coin-clipped at the node */
  image?: string;
  /** Optional single character drawn when no image is supplied */
  initial?: string;
};

export type ConnectionGlobeProps = {
  className?: string;
  /**
   * Geographic nodes. Defaults to a neutral eight-point world spread with no
   * artwork, so the component ships zero assets of its own.
   */
  nodes?: GlobeNode[];
  /**
   * Connector arcs as index pairs into `nodes`. Defaults to a ring through
   * every node plus three chords across it.
   */
  links?: Array<[number, number]>;
  /** Arc, glow and node-fill colour. Any CSS colour, including `var(--token)`. */
  accentColor?: string;
  /** Travelling-dot glow; defaults to `accentColor`. */
  glowColor?: string;
  /** Continent dot colour. */
  dotColor?: string;
  /** Thin ring drawn around each node coin. */
  ringColor?: string;
  /** Backing disc behind image nodes. */
  nodeBackingColor?: string;
  /** URL of the float32 land-point binary. Absent => uniform sphere. */
  landPointsUrl?: string;
  /** Radians of rotation per frame (default 0.0016) */
  rotationSpeed?: number;
};

type V3 = { x: number; y: number; z: number };
type RGB = { r: number; g: number; b: number };

const D2R = Math.PI / 180;

const llToVec = (latDeg: number, lngDeg: number): V3 => {
  const lat = latDeg * D2R, lng = lngDeg * D2R;
  return { x: Math.cos(lat) * Math.cos(lng), y: Math.sin(lat), z: Math.cos(lat) * Math.sin(lng) };
};

/**
 * A neutral spread across the populated continents. Not a claim about anyone's
 * coverage — just eight points far enough apart to make legible arcs.
 */
const DEFAULT_NODES: GlobeNode[] = [
  { lat: 39.8, lng: -98.6 },   // North America
  { lat: -14.2, lng: -51.9 },  // South America
  { lat: 50.1, lng: 9.1 },     // Europe
  { lat: 9.1, lng: 8.7 },      // West Africa
  { lat: -29.0, lng: 24.0 },   // Southern Africa
  { lat: 25.3, lng: 55.3 },    // Middle East
  { lat: 1.35, lng: 103.8 },   // South-East Asia
  { lat: -25.0, lng: 133.8 },  // Oceania
];

const DEFAULTS = {
  accent: "var(--brand-accent, #6366f1)",
  dot: "var(--brand-globe-dot, #96b4f0)",
  ring: "var(--brand-globe-ring, #0f172a)",
  backing: "var(--brand-surface, #ffffff)",
};

/**
 * Normalise any CSS colour to RGB.
 *
 * The canvas needs `rgba(r,g,b,a)` strings with a per-draw alpha, which means it
 * needs the channels — and a caller passing `var(--brand-accent)` or `tomato`
 * has not given them. `var()` is resolved against the live element (the only
 * place the custom property is in scope), then the 2D context is used as the
 * parser: assigning any legal colour to `fillStyle` and reading it back yields
 * `#rrggbb` or `rgba(...)`, whatever went in.
 */
function resolveRgb(ctx: CanvasRenderingContext2D, el: Element, value: string, fallback: RGB): RGB {
  let raw = value.trim();
  const varMatch = raw.match(/^var\(\s*(--[\w-]+)\s*(?:,\s*([\s\S]+))?\)$/);
  if (varMatch) {
    const resolved = getComputedStyle(el).getPropertyValue(varMatch[1]).trim();
    raw = resolved || (varMatch[2] || "").trim();
  }
  if (!raw) return fallback;

  const prev = ctx.fillStyle;
  let out = fallback;
  try {
    ctx.fillStyle = "#000000";
    ctx.fillStyle = raw;
    const normalised = String(ctx.fillStyle);
    // An unparseable value leaves fillStyle at the sentinel; black-on-purpose
    // is indistinguishable from failure here, which is an acceptable trade for
    // not shipping a CSS colour parser.
    if (normalised === "#000000" && raw.toLowerCase() !== "#000" && raw.toLowerCase() !== "#000000" && raw.toLowerCase() !== "black") {
      out = fallback;
    } else if (normalised.startsWith("#")) {
      const hex = normalised.length === 4
        ? normalised[1] + normalised[1] + normalised[2] + normalised[2] + normalised[3] + normalised[3]
        : normalised.slice(1, 7);
      const n = parseInt(hex, 16);
      out = { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
    } else {
      const m = normalised.match(/rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/i);
      out = m ? { r: +m[1], g: +m[2], b: +m[3] } : fallback;
    }
  } catch {
    out = fallback;
  }
  ctx.fillStyle = prev;
  return out;
}

const rgba = (c: RGB, a: number) => `rgba(${c.r},${c.g},${c.b},${a})`;

export default function ConnectionGlobe({
  className = "",
  nodes: nodesProp,
  links: linksProp,
  accentColor = DEFAULTS.accent,
  glowColor,
  dotColor = DEFAULTS.dot,
  ringColor = DEFAULTS.ring,
  nodeBackingColor = DEFAULTS.backing,
  landPointsUrl = "/globe-land-points.bin",
  rotationSpeed = 0.0016,
}: ConnectionGlobeProps = {}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const landPtsRef = useRef<V3[] | null>(null);
  // Set by the render effect. The loop is not always running, so anything that
  // changes what should be on screen has to ask for a frame.
  const requestFrameRef = useRef<(() => void) | null>(null);

  const nodeSpec = nodesProp && nodesProp.length > 0 ? nodesProp : DEFAULT_NODES;
  // Identity of the node/link arrays drives the render effect; serialising them
  // keeps an inline array literal in JSX from tearing down the canvas every
  // render, which is how most callers will pass them.
  const nodeKey = JSON.stringify(nodeSpec);
  const linkKey = JSON.stringify(linksProp ?? null);

  // Build the continent dot cloud once (land-sampled), with uniform fallback.
  useEffect(() => {
    let cancelled = false;
    const uniform = (): V3[] => {
      const N = 700, gr = Math.PI * (3 - Math.sqrt(5)), out: V3[] = [];
      for (let i = 0; i < N; i++) {
        const y = 1 - (i / (N - 1)) * 2, r = Math.sqrt(1 - y * y), th = gr * i;
        out.push({ x: Math.cos(th) * r, y, z: Math.sin(th) * r });
      }
      return out;
    };
    if (!landPointsUrl) {
      landPtsRef.current = uniform();
      requestFrameRef.current?.();
      return;
    }
    // Little-endian float32 triples, 12 bytes per point. Emitted by
    // ../assets/generate-globe-points.mjs; format documented there.
    fetch(landPointsUrl)
      .then((r) => r.arrayBuffer())
      .then((buf) => {
        if (cancelled) return;
        const dv = new DataView(buf);
        const n = Math.floor(buf.byteLength / 12);
        const pts: V3[] = new Array(n);
        for (let i = 0; i < n; i++) {
          pts[i] = {
            x: dv.getFloat32(i * 12, true),
            y: dv.getFloat32(i * 12 + 4, true),
            z: dv.getFloat32(i * 12 + 8, true),
          };
        }
        landPtsRef.current = pts.length > 200 ? pts : uniform();
        requestFrameRef.current?.();
      })
      .catch(() => {
        if (cancelled) return;
        landPtsRef.current = uniform();
        requestFrameRef.current?.();
      });
    if (!landPtsRef.current) landPtsRef.current = uniform(); // immediate fallback until fetch resolves
    return () => { cancelled = true; };
  }, [landPointsUrl]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const spec: GlobeNode[] = JSON.parse(nodeKey);
    const linkSpec: Array<[number, number]> | null = JSON.parse(linkKey);

    const accent = resolveRgb(ctx, canvas, accentColor, { r: 99, g: 102, b: 241 });
    const glow = resolveRgb(ctx, canvas, glowColor ?? accentColor, accent);
    const dot = resolveRgb(ctx, canvas, dotColor, { r: 150, g: 180, b: 240 });
    const ring = resolveRgb(ctx, canvas, ringColor, { r: 15, g: 23, b: 42 });
    const backing = resolveRgb(ctx, canvas, nodeBackingColor, { r: 255, g: 255, b: 255 });

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    let visible = false;
    let disposed = false;
    let t = 0;
    const startMs = performance.now();
    let W = 0, H = 0, R = 0, cx = 0, cy = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    // Ask for exactly one frame. `draw()` decides whether another follows.
    // Hoisted (function declaration) because the image and observer callbacks
    // below are wired before `draw` exists; none of them can fire until the
    // effect body has finished running.
    function requestFrame() {
      if (disposed || raf !== 0) return;
      raf = requestAnimationFrame(draw);
    }

    type Node = { x: number; y: number; z: number; img: HTMLImageElement | null; loaded: boolean; delay: number; initial: string };
    const nodes: Node[] = spec.map((n, i) => {
      const v = llToVec(n.lat, n.lng);
      const node: Node = { x: v.x, y: v.y, z: v.z, img: null, loaded: false, delay: i * 130, initial: n.initial || "" };
      if (n.image) {
        const img = new Image();
        node.img = img;
        img.onload = () => { node.loaded = true; requestFrame(); };
        img.src = n.image;
      }
      return node;
    });

    const links: Array<{ a: number; b: number; speed: number; phase: number }> = [];
    if (linkSpec && linkSpec.length > 0) {
      linkSpec.forEach(([a, b], i) => {
        if (a < 0 || b < 0 || a >= nodes.length || b >= nodes.length) return;
        links.push({ a, b, speed: 0.18 + (i % 3) * 0.06, phase: (i % Math.max(1, linkSpec.length)) / Math.max(1, linkSpec.length) });
      });
    } else if (nodes.length > 1) {
      for (let i = 0; i < nodes.length; i++) {
        links.push({ a: i, b: (i + 1) % nodes.length, speed: 0.18 + (i % 3) * 0.06, phase: i / nodes.length });
      }
      // Three chords across the ring, clamped so a small node set stays valid.
      const n = nodes.length;
      ([[0, Math.floor(n / 2)], [Math.floor(n * 0.3), Math.floor(n * 0.8)], [1, Math.floor(n * 0.65)]] as Array<[number, number]>)
        .forEach(([a, b], i) => { if (a !== b) links.push({ a, b, speed: 0.22 + i * 0.05, phase: i / 3 }); });
    }

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      W = rect.width; H = rect.height;
      canvas.width = W * dpr; canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      R = Math.min(W, H) * 0.42; cx = W / 2; cy = H / 2;
    };
    resize();
    const ro = new ResizeObserver(() => { resize(); requestFrame(); });
    ro.observe(canvas);

    const rot = (p: V3, ay: number) => {
      const c = Math.cos(ay), s = Math.sin(ay);
      return { x: p.x * c + p.z * s, y: p.y, z: -p.x * s + p.z * c };
    };
    const slerp = (a: V3, b: V3, u: number): V3 => {
      let d = a.x * b.x + a.y * b.y + a.z * b.z;
      d = Math.max(-1, Math.min(1, d));
      const om = Math.acos(d);
      if (om < 1e-4) return a;
      const so = Math.sin(om), k0 = Math.sin((1 - u) * om) / so, k1 = Math.sin(u * om) / so;
      return { x: a.x * k0 + b.x * k1, y: a.y * k0 + b.y * k1, z: a.z * k0 + b.z * k1 };
    };
    const easeOut = (x: number) => 1 - Math.pow(1 - x, 3);

    const draw = () => {
      const now = performance.now();
      t += reduced ? 0 : rotationSpeed;
      const ay = t;
      ctx.clearRect(0, 0, W, H);

      const g = ctx.createRadialGradient(cx, cy, R * 0.2, cx, cy, R * 1.5);
      g.addColorStop(0, rgba(accent, 0.08));
      g.addColorStop(1, rgba(accent, 0));
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);

      // continent dots (land-sampled)
      const pts = landPtsRef.current || [];
      for (const p0 of pts) {
        const p = rot(p0, ay);
        if (p.z < -0.1) continue; // cull back hemisphere for crisp continents
        const depth = (p.z + 1) / 2;
        const x = cx + p.x * R, y = cy - p.y * R;
        ctx.beginPath();
        ctx.arc(x, y, 0.5 + depth * 1.2, 0, Math.PI * 2);
        ctx.fillStyle = rgba(dot, 0.10 + depth * 0.5);
        ctx.fill();
      }

      // connector arcs + travelling dots
      for (const lk of links) {
        const a = rot(nodes[lk.a], ay), b = rot(nodes[lk.b], ay);
        const midDepth = ((a.z + b.z) / 2 + 1) / 2;
        ctx.beginPath();
        for (let u = 0; u <= 1.0001; u += 0.05) {
          const m = slerp(a, b, u);
          const lift = 1 + 0.22 * Math.sin(Math.PI * u);
          const x = cx + m.x * R * lift, y = cy - m.y * R * lift;
          if (u === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = rgba(accent, 0.06 + midDepth * 0.16);
        ctx.lineWidth = 1;
        ctx.stroke();
        const u = reduced ? 0.5 : (t * lk.speed + lk.phase) % 1;
        const m = slerp(a, b, u);
        const lift = 1 + 0.22 * Math.sin(Math.PI * u);
        const x = cx + m.x * R * lift, y = cy - m.y * R * lift;
        const dotGlow = ctx.createRadialGradient(x, y, 0, x, y, 6);
        dotGlow.addColorStop(0, rgba(glow, 1));
        dotGlow.addColorStop(1, rgba(glow, 0));
        ctx.fillStyle = dotGlow;
        ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fill();
      }

      // nodes — coin-clipped, pop-in, depth-scaled, painter-ordered
      const ordered = nodes.map((n) => ({ n, r: rot(n, ay) })).sort((p, q) => p.r.z - q.r.z);
      for (const { n, r } of ordered) {
        if (r.z < -0.15) continue;
        const hasArt = !!n.img && n.loaded;
        const depth = (r.z + 1) / 2;
        const pop = reduced ? 1 : easeOut(Math.max(0, Math.min(1, (now - startMs - n.delay) / 650)));
        if (pop <= 0) continue;
        const x = cx + r.x * R, y = cy - r.y * R;
        const rad = Math.max(11, R * 0.065) * (0.6 + depth * 0.5) * (0.7 + 0.3 * pop);
        const alpha = (0.3 + depth * 0.7) * pop;
        ctx.globalAlpha = alpha;

        // backing disc + soft accent glow
        ctx.beginPath(); ctx.arc(x, y, rad + 2, 0, Math.PI * 2);
        ctx.fillStyle = hasArt ? rgba(backing, 1) : rgba(accent, 0.9);
        ctx.shadowColor = rgba(accent, 0.4); ctx.shadowBlur = 12 * depth;
        ctx.fill(); ctx.shadowBlur = 0;

        if (hasArt) {
          ctx.save();
          ctx.beginPath(); ctx.arc(x, y, rad, 0, Math.PI * 2); ctx.clip();
          const img = n.img as HTMLImageElement;
          const iw = img.width || 3, ih = img.height || 2;
          const scale = Math.max((rad * 2) / iw, (rad * 2) / ih);
          const dw = iw * scale, dh = ih * scale;
          try { ctx.drawImage(img, x - dw / 2, y - dh / 2, dw, dh); } catch { /* decoding */ }
          ctx.restore();
        } else if (n.initial) {
          ctx.save();
          ctx.fillStyle = rgba(backing, 1);
          ctx.font = `600 ${Math.round(rad)}px system-ui, sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(n.initial.slice(0, 1), x, y);
          ctx.restore();
        }

        // thin ring
        ctx.beginPath(); ctx.arc(x, y, rad, 0, Math.PI * 2);
        ctx.strokeStyle = rgba(ring, 0.15); ctx.lineWidth = 1; ctx.stroke();
        ctx.globalAlpha = 1;
      }

      // THE ONLY PLACE THE LOOP CONTINUES. It used to re-schedule
      // unconditionally: 60 fps of clearing, a full-canvas radial gradient,
      // 1,737 arc fills and a slerped arc plus radial gradient per link, for the
      // whole session, with the hero scrolled a page and a half off screen. And
      // `prefers-reduced-motion` froze only `t`, so a user who asked for less
      // motion paid the identical CPU bill for a picture that never changed — an
      // accessibility defect, not just a slow one. Under reduced motion one
      // frame is drawn and the loop ends; the result is pixel-identical.
      raf = 0;
      if (!reduced && visible) raf = requestAnimationFrame(draw);
    };

    requestFrameRef.current = requestFrame;

    // Off-screen means no frames. `draw` is otherwise unreachable: nothing else
    // starts the loop, so if IntersectionObserver never reports intersection the
    // globe simply never paints — which is correct, it is not on screen.
    let io: IntersectionObserver | null = null;
    if (typeof IntersectionObserver === "function") {
      io = new IntersectionObserver((entries) => {
        visible = entries.some((e) => e.isIntersecting);
        if (!visible) {
          if (raf) cancelAnimationFrame(raf);
          raf = 0;
          return;
        }
        requestFrame();
      });
      io.observe(canvas);
    } else {
      // No observer (very old browser, or a test environment that did not stub
      // one): draw rather than leave a blank canvas.
      visible = true;
      requestFrame();
    }

    return () => {
      disposed = true;
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
      ro.disconnect();
      io?.disconnect();
      requestFrameRef.current = null;
    };
  }, [nodeKey, linkKey, accentColor, glowColor, dotColor, ringColor, nodeBackingColor, rotationSpeed]);

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}

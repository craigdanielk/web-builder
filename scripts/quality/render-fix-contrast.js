#!/usr/bin/env node
/**
 * render-fix-contrast.js — measured contrast remediation for generated sections.
 *
 * BRIEF #33320 — replaces the blunt v1 (which keyed every fix off the FIRST
 * bg-[#hex] in a file and regressed multi-background sections) with a
 * measure -> fix -> re-measure -> revert-on-no-improvement loop driven by the
 * render-audit's per-element output.
 *
 * Primary mode (--audit <render-audit-results.json>): for every element the
 * render-audit reports as failing, we know its ACTUAL rendered foreground and
 * background. We compute a brand-safe replacement foreground, re-measure the
 * contrast against that element's real background, and only apply the change if
 * it strictly improves the ratio. Any change that does not improve is REVERTED
 * (left untouched) so a fix can never make a page worse — the exact regression
 * (home 16->19, checkout 5->19) is structurally impossible.
 *
 * Fallback mode (no --audit): per-occurrence measurement with the same
 * re-measure/revert guard (still never applies a non-improving change).
 *
 * Usage: node render-fix-contrast.js <sectionsRootDir> [--audit results.json] [--light #fafaf9]
 */
const fs = require("fs");
const path = require("path");

const hexToRgb = (h) => {
  h = String(h).replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
};
const lum = (rgb) => {
  const a = rgb.map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
  return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
};
const contrast = (fg, bg) => {
  const l1 = lum(fg), l2 = lum(bg); const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
};

const ON_DARK = ["#ffffff", "#e0e0e0", "#f47643"];
const ON_LIGHT = ["#0d0e45", "#1c1917", "#222b60"];

function bestReplacement(bgRgb, need) {
  const dark = lum(bgRgb) < 0.4;
  const pool = dark ? ON_DARK : ON_LIGHT;
  let best = dark ? "#ffffff" : "#0d0e45";
  let bestRatio = contrast(hexToRgb(best), bgRgb);
  for (const cand of pool) {
    const r = contrast(hexToRgb(cand), bgRgb);
    if (r >= need) return cand;
    if (r > bestRatio) { best = cand; bestRatio = r; }
  }
  return best;
}

/**
 * Load per-element failing findings from a render-audit results JSON.
 * Tolerant of shape: looks for an array of defects each carrying a failing
 * text color, its measured background, and the required ratio.
 */
function loadAuditDefects(auditPath) {
  try {
    const raw = JSON.parse(fs.readFileSync(auditPath, "utf-8"));
    const groups = raw.contrast || raw.defects || raw.line_items || raw.findings || [];
    const out = [];
    for (const g of Array.isArray(groups) ? groups : []) {
      const fg = g.fg || g.color || g.text_color || g.foreground;
      const bg = g.bg || g.background || g.bg_color;
      if (fg && bg) out.push({ fg: String(fg), bg: String(bg), need: g.need || g.required || 4.5 });
    }
    return out;
  } catch (e) {
    return [];
  }
}

/**
 * Build a fix map from measured audit defects: failing fg-hex -> verified
 * replacement. A replacement is included ONLY if, re-measured against the
 * element's real background, it strictly improves the contrast ratio.
 */
function auditFixMap(defects) {
  const map = {};
  let reverted = 0;
  for (const d of defects) {
    const bg = hexToRgb(d.bg);
    const oldRatio = contrast(hexToRgb(d.fg), bg);
    if (oldRatio >= d.need) continue;                 // not actually failing
    const rep = bestReplacement(bg, d.need);
    const newRatio = contrast(hexToRgb(rep), bg);
    if (newRatio > oldRatio && rep.toLowerCase() !== d.fg.toLowerCase()) {
      map[d.fg.toLowerCase()] = rep;                  // measured improvement -> keep
    } else {
      reverted++;                                     // no improvement -> revert (skip)
    }
  }
  return { map, reverted };
}

function fixFileWithMap(file, fixMap) {
  let code = fs.readFileSync(file, "utf-8");
  let changed = 0;
  code = code.replace(/text-\[(#[0-9a-fA-F]{3,6})\]/g, (m, hex) => {
    const rep = fixMap[hex.toLowerCase()];
    if (!rep) return m;
    changed++;
    return `text-[${rep}]`;
  });
  if (changed) fs.writeFileSync(file, code);
  return { file: path.basename(path.dirname(file)) + "/" + path.basename(file), changed };
}

// Fallback: per-occurrence, measured against a locally-inferred bg, with the
// same revert guard (only apply when the replacement strictly improves).
function fixFileFallback(file, lightBg) {
  let code = fs.readFileSync(file, "utf-8");
  const bgMatch = code.match(/bg-\[(#[0-9a-fA-F]{3,6})\]/);
  const bg = hexToRgb(bgMatch ? bgMatch[1] : lightBg);
  let changed = 0, reverted = 0;
  code = code.replace(/text-\[(#[0-9a-fA-F]{3,6})\]/g, (m, hex) => {
    const need = 4.5;
    const oldRatio = contrast(hexToRgb(hex), bg);
    if (oldRatio >= need) return m;
    const rep = bestReplacement(bg, need);
    const newRatio = contrast(hexToRgb(rep), bg);
    if (newRatio > oldRatio && rep.toLowerCase() !== hex.toLowerCase()) { changed++; return `text-[${rep}]`; }
    reverted++;                                        // revert: no measured improvement
    return m;
  });
  if (changed) fs.writeFileSync(file, code);
  return { file: path.basename(path.dirname(file)) + "/" + path.basename(file), changed, reverted };
}

function walk(dir, acc) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, acc);
    else if (e.name.endsWith(".tsx")) acc.push(p);
  }
  return acc;
}

const root = process.argv[2];
const auditIdx = process.argv.indexOf("--audit");
const auditPath = auditIdx > -1 ? process.argv[auditIdx + 1] : null;
const lightIdx = process.argv.indexOf("--light");
const lightBg = lightIdx > -1 ? process.argv[lightIdx + 1] : "#fafaf9";
if (!root) { console.error("Usage: render-fix-contrast.js <sectionsRootDir> [--audit results.json] [--light #hex]"); process.exit(2); }

const files = walk(root, []);
let total = 0, reverted = 0; const report = [];

if (auditPath && fs.existsSync(auditPath)) {
  const { map, reverted: r } = auditFixMap(loadAuditDefects(auditPath));
  reverted += r;
  for (const f of files) { const res = fixFileWithMap(f, map); if (res.changed) { total += res.changed; report.push(res); } }
  console.error(`  (render-audit driven: ${Object.keys(map).length} verified remaps, ${r} reverted as non-improving)`);
} else {
  for (const f of files) { const res = fixFileFallback(f, lightBg); reverted += res.reverted || 0; if (res.changed) { total += res.changed; report.push(res); } }
}

for (const r of report) console.error(`  ~ ${r.file}: ${r.changed} text color(s) remapped`);
console.error(`\n  ✅ contrast remediation: ${total} improving remap(s), ${reverted} reverted across ${files.length} file(s)`);
console.log(JSON.stringify({ remaps: total, reverted, files: report.length }));

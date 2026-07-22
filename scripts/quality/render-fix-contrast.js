#!/usr/bin/env node
/**
 * render-fix-contrast.js — deterministic contrast remediation for generated sections.
 *
 * Driven by the render-audit's contrast findings. Sections are generated with raw
 * brand-hex Tailwind classes (bg-[#0d0e45], text-[#b5b7ba]) applied decoratively,
 * with no guaranteed foreground/background contrast. This pass parses each section
 * file, determines the dominant background it renders on, and for any text color
 * that fails WCAG against that background, remaps it to the nearest brand-safe
 * shade that passes — white/near-white on dark, ink-navy on light. Conservative:
 * only touches text-[#hex] classes that measurably fail; leaves passing text alone.
 *
 * Usage: node render-fix-contrast.js <sectionsRootDir> [--light #fafaf9]
 */
const fs = require("fs");
const path = require("path");

const hexToRgb = (h) => {
  h = h.replace("#", "");
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

// Brand-safe replacement candidates, tried in order (readable + on-brand).
const ON_DARK = ["#ffffff", "#e0e0e0", "#f47643"];   // light + accent for dark bgs
const ON_LIGHT = ["#0d0e45", "#1c1917", "#222b60"];  // ink navy for light bgs

function bestReplacement(bgRgb, need) {
  const dark = lum(bgRgb) < 0.4;
  const pool = dark ? ON_DARK : ON_LIGHT;
  for (const cand of pool) if (contrast(hexToRgb(cand), bgRgb) >= need) return cand;
  return dark ? "#ffffff" : "#0d0e45";
}

function fixFile(file, lightBg) {
  let code = fs.readFileSync(file, "utf-8");
  // Dominant section background: first bg-[#hex] in the file, else the light body bg.
  const bgMatch = code.match(/bg-\[(#[0-9a-fA-F]{3,6})\]/);
  const bg = hexToRgb(bgMatch ? bgMatch[1] : lightBg);
  let changed = 0;
  const seen = {};
  code = code.replace(/text-\[(#[0-9a-fA-F]{3,6})\]/g, (m, hex) => {
    const need = 4.5;                                // treat body text conservatively
    const ratio = contrast(hexToRgb(hex), bg);
    if (ratio >= need) return m;
    const rep = bestReplacement(bg, need);
    if (rep.toLowerCase() === hex.toLowerCase()) return m;
    changed++;
    seen[`${hex}->${rep}`] = (seen[`${hex}->${rep}`] || 0) + 1;
    return `text-[${rep}]`;
  });
  if (changed) fs.writeFileSync(file, code);
  return { file: path.basename(path.dirname(file)) + "/" + path.basename(file), changed, map: seen };
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
const lightIdx = process.argv.indexOf("--light");
const lightBg = lightIdx > -1 ? process.argv[lightIdx + 1] : "#fafaf9";
if (!root) { console.error("Usage: render-fix-contrast.js <sectionsRootDir> [--light #hex]"); process.exit(2); }

const files = walk(root, []);
let total = 0; const report = [];
for (const f of files) { const r = fixFile(f, lightBg); if (r.changed) { total += r.changed; report.push(r); } }
for (const r of report) console.error(`  ~ ${r.file}: ${r.changed} text color(s) remapped ${JSON.stringify(r.map)}`);
console.error(`\n  ✅ contrast remediation: ${total} remap(s) across ${report.length} file(s)`);
console.log(JSON.stringify({ remaps: total, files: report.length }));

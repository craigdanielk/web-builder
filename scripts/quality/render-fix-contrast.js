#!/usr/bin/env node
/**
 * render-fix-contrast.js — measured contrast remediation at the TOKEN layer.
 *
 * Task C6 (docs/superpowers/plans/2026-08-17-aurelix-complete-dag.md), rewritten
 * from the X5 census (docs/census/2026-08-17-render-probe-facts.md §2).
 *
 * WHAT CHANGED AND WHY. The previous version keyed its fix map by hex literal and
 * applied it by rewriting `text-[#hex]` Tailwind arbitrary values. Measured
 * 2026-08-17: there are ZERO `text-[#hex]` occurrences in the 14 local templates
 * and ZERO in the 21 built cape-crypto sections. Colour reaches the DOM as
 * `var(--foreground)` / `var(--background)` (140 occurrences in the built
 * sections) or as a hardcoded Tailwind utility (21: text-gray-900, text-white,
 * text-gray-300). The old write path could therefore repair nothing at all, while
 * printing "0 verified remaps ✅" — a gate that can only say yes.
 *
 * So the remediation target is the token DECLARATION. A contrast failure is
 * resolved back to the palette role whose compiled value the probe measured, and
 * repaired by changing that role in globals.css and site-spec.style.palette.
 * PIPELINE_ARCHITECTURE.md §11.4–§11.5 precedence is preserved because:
 *
 *   - the replacement is drawn ONLY from values already in the compiled
 *     benchmark palette — nothing is invented, and a palette whose
 *     `design_source` is not "benchmark" is refused outright;
 *   - a candidate is accepted only if it repairs every failing measurement bound
 *     to that role AND regresses no currently-passing one (possible now that C2
 *     records passes as well as failures — commit 3ccf9444);
 *   - if no palette value reaches the required ratio, the run FAILS naming the
 *     ratio rather than inventing a colour;
 *   - a failure whose colour is not token-driven (a Tailwind literal) is reported
 *     as unrepairable with its route and selector, and exits non-zero. It is
 *     never counted as repaired and never silently passed.
 *
 * Outcomes are three, never two: PASS · REPAIRED (0) · FAIL (1) · NOT_MEASURED (3).
 *
 * Usage:
 *   node render-fix-contrast.js --report <render-audit-results/report.json> \
 *        --site-spec <output/<p>/site-spec.json> --globals <site/src/app/globals.css> [--apply]
 */
const fs = require("fs");
const path = require("path");

const hexToRgb = (h) => {
  h = String(h).replace("#", "").trim();
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
};
const isHex = (v) => typeof v === "string" && /^#[0-9a-fA-F]{3}$|^#[0-9a-fA-F]{6}$/.test(v.trim());
const lum = (rgb) => {
  const a = rgb.map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
  return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
};
const contrast = (fg, bg) => {
  const l1 = lum(fg), l2 = lum(bg); const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
};
const ratioOf = (fgHex, bgHex) => contrast(hexToRgb(fgHex), hexToRgb(bgHex));
const r2 = (n) => Math.round(n * 100) / 100;

/**
 * Palette role -> the CSS custom property orchestrate.py emits for it
 * (orchestrate.py:6400-6414). `--surface` is fed by bg_secondary with a fallback
 * to `surface`, so both roles map to it and the fallback is only used when
 * bg_secondary is absent.
 */
const ROLE_TO_VAR = {
  bg_primary: "--background",
  bg_secondary: "--surface",
  surface: "--surface",
  text_primary: "--foreground",
  text_muted: "--muted",
  accent: "--accent",
  on_accent: "--on-accent",
  border: "--border",
  surface_inverse: "--surface-inverse",
};

function cssVarForRole(role, palette) {
  if (role === "surface" && palette.bg_secondary) return null;   // --surface is bg_secondary's
  return ROLE_TO_VAR[role] || null;
}

/** Every contrast measurement in the report, flattened and route-stamped. */
function loadMeasurements(report) {
  const routes = Array.isArray(report && report.routes) ? report.routes : [];
  const entries = [];
  let anyContrastArray = false;
  for (const r of routes) {
    const facts = r && r.facts;
    if (!facts || !Array.isArray(facts.contrast)) continue;
    anyContrastArray = true;
    for (const c of facts.contrast) {
      if (!isHex(c.fg) || !isHex(c.bg)) continue;              // pre-C2 shape: rgb arrays
      entries.push({
        route: r.route || "(unknown)",
        selector: c.selector || c.tag || "(unidentified)",
        text: c.text || "",
        fg: c.fg.toLowerCase(),
        bg: c.bg.toLowerCase(),
        need: typeof c.need === "number" ? c.need : 4.5,
        ratio: typeof c.ratio === "number" ? c.ratio : r2(ratioOf(c.fg, c.bg)),
        pass: c.pass === true,
      });
    }
  }
  return { entries, measured: anyContrastArray };
}

/** hex -> [roles]. A hex owned by two roles cannot be attributed to either. */
function paletteIndex(palette) {
  const idx = new Map();
  for (const [role, hex] of Object.entries(palette || {})) {
    if (!isHex(hex)) continue;
    const k = hex.toLowerCase();
    idx.set(k, (idx.get(k) || []).concat(role));
  }
  return idx;
}

/**
 * Choose a replacement for `role` (current value `value`) from the palette.
 * Throws — naming the ratio — when no palette value can serve every measurement
 * bound to this role.
 */
function chooseReplacement({ role, value, palette, entries }) {
  // Every measurement this token participates in, on either side.
  const bound = entries.filter((e) => e.fg === value || e.bg === value);
  const failing = bound.filter((e) => !e.pass);

  const withCandidate = (e, cand) =>
    ratioOf(e.fg === value ? cand : e.fg, e.bg === value ? cand : e.bg);

  const candidates = [...new Set(
    Object.entries(palette)
      .filter(([, hex]) => isHex(hex) && hex.toLowerCase() !== value)
      .map(([, hex]) => hex.toLowerCase())
  )];

  const rejected = [];
  let best = null;
  for (const cand of candidates) {
    let worst = Infinity, regression = null;
    for (const e of bound) {
      const got = withCandidate(e, cand);
      if (got < e.need) {
        // A measurement that already passed and would stop passing is a
        // regression; one that was already failing is simply not repaired.
        regression = { entry: e, got, wasPassing: e.pass };
        break;
      }
      worst = Math.min(worst, got);
    }
    if (regression) { rejected.push({ cand, ...regression }); continue; }
    if (!best || worst > best.worst) best = { cand, worst };
  }

  if (best) {
    const roleOf = Object.entries(palette).find(([, h]) => isHex(h) && h.toLowerCase() === best.cand);
    return {
      to: best.cand,
      from: value,
      drawn_from: `site-spec.style.palette.${roleOf ? roleOf[0] : "?"}`,
      failing,
      worst: r2(best.worst),
    };
  }

  const worstFail = failing.reduce((a, b) => (a && a.need >= b.need ? a : b), null) || bound[0];
  const parts = [
    `no benchmark palette value reaches ${worstFail.need}:1 for role ${role}`,
    `current ${value} measures ${worstFail.ratio}:1 at "${worstFail.selector}" on ${worstFail.route}`,
  ];
  for (const rj of rejected.slice(0, 4)) {
    parts.push(
      rj.wasPassing
        ? `candidate ${rj.cand} would regress "${rj.entry.selector}" on ${rj.entry.route} to ${r2(rj.got)}:1 (needs ${rj.entry.need}:1)`
        : `candidate ${rj.cand} still fails "${rj.entry.selector}" on ${rj.entry.route} at ${r2(rj.got)}:1 (needs ${rj.entry.need}:1)`
    );
  }
  const err = new Error(parts.join("; "));
  err.code = "CONTRAST_UNREACHABLE";
  err.role = role;
  throw err;
}

function rewriteCssVar(css, cssVar, to) {
  const re = new RegExp(`(${cssVar}\\s*:\\s*)([^;]+)(;)`);
  if (!re.test(css)) {
    const err = new Error(`globals.css declares no ${cssVar} — cannot repair a token that is not emitted`);
    err.code = "TOKEN_NOT_DECLARED";
    throw err;
  }
  return css.replace(re, (_m, a, _old, c) => `${a}${to}${c}`);
}

/**
 * The whole decision. Reads the three measured artifacts, returns a verdict, and
 * (with apply) writes the token repair. Never writes on a failing verdict.
 */
function repairContrast({ reportPath, siteSpecPath, globalsPath, apply = false }) {
  const report = JSON.parse(fs.readFileSync(reportPath, "utf-8"));
  const { entries, measured } = loadMeasurements(report);

  if (!measured) {
    return {
      status: "NOT_MEASURED", exitCode: 3, measured: 0, failed: 0, adjustments: [], unrepairable: [],
      note: "report carries no facts.contrast[] — probe predates C2 (commit 3ccf9444) or crashed",
    };
  }

  const failures = entries.filter((e) => !e.pass);
  if (failures.length === 0) {
    return {
      status: "PASS", exitCode: 0, measured: entries.length, passed: entries.length,
      failed: 0, adjustments: [], unrepairable: [],
    };
  }

  const siteSpec = JSON.parse(fs.readFileSync(siteSpecPath, "utf-8"));
  const style = siteSpec.style || {};
  const palette = style.palette || {};
  if (style.design_source !== "benchmark") {
    const err = new Error(
      `palette provenance is "${style.design_source || "undeclared"}", not "benchmark" — ` +
      `refusing to draw a replacement colour from it`
    );
    err.code = "PROVENANCE";
    throw err;
  }

  const idx = paletteIndex(palette);
  const unrepairable = [];
  const byRole = new Map();

  for (const f of failures) {
    const roles = idx.get(f.fg);
    if (!roles) {
      // The failing text colour is not any token's compiled value — a Tailwind
      // utility or a literal. Unreachable from globals.css; say so.
      unrepairable.push({ reason: "colour-not-token-driven", route: f.route, selector: f.selector, fg: f.fg, bg: f.bg, ratio: f.ratio, need: f.need });
      continue;
    }
    if (roles.length > 1) {
      unrepairable.push({ reason: "ambiguous-role", roles, route: f.route, selector: f.selector, fg: f.fg, bg: f.bg, ratio: f.ratio, need: f.need });
      continue;
    }
    const role = roles[0];
    if (!cssVarForRole(role, palette)) {
      unrepairable.push({ reason: "role-not-emitted", roles, route: f.route, selector: f.selector, fg: f.fg, bg: f.bg, ratio: f.ratio, need: f.need });
      continue;
    }
    byRole.set(role, (byRole.get(role) || []).concat(f));
  }

  // Decide every role BEFORE writing anything: an unreachable ratio must leave
  // the artifacts untouched, not half-repaired.
  const decisions = [];
  for (const role of byRole.keys()) {
    decisions.push({ role, ...chooseReplacement({ role, value: palette[role].toLowerCase(), palette, entries }) });
  }

  if (unrepairable.length) {
    return {
      status: "FAIL", exitCode: 1, measured: entries.length, passed: entries.length - failures.length,
      failed: failures.length, adjustments: [], unrepairable,
      note: "contrast failures exist that no token change can reach",
    };
  }

  const adjustments = decisions.map((d) => {
    const worstBefore = d.failing.reduce((a, b) => (a && a.ratio <= b.ratio ? a : b), null);
    return {
      role: `palette.${d.role}`,
      from: d.from,
      to: d.to,
      source: "benchmark",
      drawn_from: d.drawn_from,
      reason:
        `measured contrast ${worstBefore.ratio}:1 at "${worstBefore.selector}" on ${worstBefore.route} ` +
        `is below ${worstBefore.need}:1; replaced from the compiled benchmark palette`,
      ratio_before: worstBefore.ratio,
      ratio_after: d.worst,
      route: worstBefore.route,
      selector: worstBefore.selector,
    };
  });

  if (apply) {
    let css = fs.readFileSync(globalsPath, "utf-8");
    for (const d of decisions) css = rewriteCssVar(css, cssVarForRole(d.role, palette), d.to);
    for (const d of decisions) palette[d.role] = d.to;
    style.palette = palette;
    style.adjustments = (style.adjustments || []).concat(adjustments);
    siteSpec.style = style;
    fs.writeFileSync(globalsPath, css);
    fs.writeFileSync(siteSpecPath, JSON.stringify(siteSpec, null, 2));
  }

  return {
    status: "REPAIRED", exitCode: 0, measured: entries.length, passed: entries.length - failures.length,
    failed: failures.length, adjustments, unrepairable: [], applied: apply,
  };
}

function parseArgs(argv) {
  const get = (flag) => { const i = argv.indexOf(flag); return i > -1 ? argv[i + 1] : null; };
  return {
    reportPath: get("--report"),
    siteSpecPath: get("--site-spec"),
    globalsPath: get("--globals"),
    apply: argv.includes("--apply"),
  };
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (!opts.reportPath || !opts.siteSpecPath || !opts.globalsPath) {
    console.error(
      "Usage: render-fix-contrast.js --report <report.json> --site-spec <site-spec.json> " +
      "--globals <globals.css> [--apply]"
    );
    process.exit(2);
  }
  let res;
  try {
    res = repairContrast(opts);
  } catch (e) {
    console.error(`  ✖ contrast remediation FAILED (${e.code || "error"}): ${e.message}`);
    console.log(JSON.stringify({ status: "FAIL", reason: e.code || "error", message: e.message }));
    process.exit(1);
  }
  if (res.status === "NOT_MEASURED") {
    console.error(`  ? contrast NOT_MEASURED: ${res.note}`);
  } else if (res.status === "PASS") {
    console.error(`  ✓ contrast PASS: ${res.passed}/${res.measured} measurements at or above threshold`);
  } else if (res.status === "REPAIRED") {
    for (const a of res.adjustments)
      console.error(`  ~ ${a.role}: ${a.from} -> ${a.to} (${a.ratio_before}:1 -> ${a.ratio_after}:1) [${a.source}]`);
    console.error(
      `  ✓ contrast REPAIRED: ${res.adjustments.length} token(s) adjusted for ` +
      `${res.failed}/${res.measured} failing measurement(s)${res.applied ? "" : " (dry run — pass --apply to write)"}`
    );
  } else {
    for (const u of res.unrepairable)
      console.error(`  ✖ ${u.route} "${u.selector}" ${u.fg} on ${u.bg} = ${u.ratio}:1 (needs ${u.need}:1) — ${u.reason}`);
    console.error(`  ✖ contrast FAIL: ${res.unrepairable.length} failure(s) no token change can reach`);
  }
  console.log(JSON.stringify(res));
  process.exit(res.exitCode);
}

if (require.main === module) main();

module.exports = {
  repairContrast, chooseReplacement, loadMeasurements, paletteIndex,
  cssVarForRole, rewriteCssVar, parseArgs, contrast, hexToRgb, ROLE_TO_VAR,
};

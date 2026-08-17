/**
 * render-fix-contrast.test.js — Task C6.
 *
 * The repair target is the TOKEN DECLARATION, not a Tailwind arbitrary hex.
 * Measured on 2026-08-17: 0 of 14 local templates and 0 of 21 built cape-crypto
 * sections contain a `text-[#hex]` literal, so the old rewrite path could repair
 * nothing. Colour reaches the DOM through `var(--foreground)` / `var(--background)`
 * (140 occurrences in the built sections) or through a hardcoded Tailwind utility
 * (21 occurrences) — and only the first of those is reachable from a token.
 *
 * Every fixture here is a MEASURED-SHAPE artifact triple: report.json
 * (schema aurelix.render_audit.v2, as C2 now writes it), site-spec.json and
 * globals.css. No browser is involved: C2's own suite covers the probe, this
 * suite covers the repair decision.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

const { repairContrast, contrast, hexToRgb } = require("./render-fix-contrast.js");

const ratio = (fg, bg) => contrast(hexToRgb(fg), hexToRgb(bg));

/** Write a report/site-spec/globals triple into a fresh temp dir. */
function fixture({ palette, measurements, designSource = "benchmark", route = "/" }) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "c6-contrast-"));
  const entries = measurements.map((m) => ({
    text: m.text || "sample",
    selector: m.selector || "p",
    tag: "p",
    cls: "",
    fg: m.fg,
    bg: m.bg,
    fontSize: 16,
    fontWeight: 400,
    ratio: Math.round(ratio(m.fg, m.bg) * 100) / 100,
    need: m.need || 4.5,
    pass: ratio(m.fg, m.bg) >= (m.need || 4.5),
  }));
  const failed = entries.filter((e) => !e.pass);
  const report = {
    schema: "aurelix.render_audit.v2",
    routes: [
      {
        route,
        facts: {
          sections: [],
          images: [],
          navLinks: [],
          contrast: entries,
          lowContrast: failed,
          contrastSummary: {
            measured: entries.length,
            passed: entries.length - failed.length,
            failed: failed.length,
          },
        },
      },
    ],
  };
  const cssVar = {
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
  const css = [
    '@import "tailwindcss";',
    "",
    ":root {",
    ...Object.entries(palette).map(([role, hex]) => `  ${cssVar[role]}: ${hex};`),
    "  --font-body: \"Poppins\", sans-serif;",
    "}",
    "",
  ].join("\n");
  const siteSpec = { version: "2", project: "fx", style: { design_source: designSource, palette, adjustments: [] } };

  const paths = {
    dir,
    report: path.join(dir, "report.json"),
    siteSpec: path.join(dir, "site-spec.json"),
    globals: path.join(dir, "globals.css"),
  };
  fs.writeFileSync(paths.report, JSON.stringify(report, null, 2));
  fs.writeFileSync(paths.siteSpec, JSON.stringify(siteSpec, null, 2));
  fs.writeFileSync(paths.globals, css);
  return paths;
}

const run = (p, apply = true) =>
  repairContrast({ reportPath: p.report, siteSpecPath: p.siteSpec, globalsPath: p.globals, apply });

const readSpec = (p) => JSON.parse(fs.readFileSync(p.siteSpec, "utf-8"));

// The BVNK-derived compiled palette, as it stands in output/cape-crypto/site-spec.json.
const BVNK = {
  bg_primary: "#ffffff",
  bg_secondary: "#f1f7ff",
  surface: "#f0f3f5",
  text_muted: "#465869",
  accent: "#004e89",
  on_accent: "#ffffff",
  border: "#dee3e8",
};

test("a low-contrast section is corrected from benchmark palette values only", () => {
  const p = fixture({
    palette: { ...BVNK, text_primary: "#cccccc" },          // ink too light against the ground
    measurements: [{ fg: "#cccccc", bg: "#ffffff", selector: "h2.headline" }],
  });

  const res = run(p);

  assert.equal(res.status, "REPAIRED");
  const adj = readSpec(p).style.adjustments.filter((a) => a.role.startsWith("palette."));
  assert.equal(adj.length, 1);
  assert.equal(adj[0].role, "palette.text_primary");
  assert.equal(adj[0].from, "#cccccc");
  assert.equal(adj[0].source, "benchmark");                 // nothing invented
  assert.ok(
    Object.values(BVNK).includes(adj[0].to),
    `replacement ${adj[0].to} must already be a palette value`
  );
  assert.ok(adj[0].ratio_before < 4.5 && adj[0].ratio_after >= 4.5, "both ratios recorded");
  assert.match(fs.readFileSync(p.globals, "utf-8"), new RegExp(`--foreground:\\s*${adj[0].to};`));
});

test("when no benchmark value reaches 4.5:1 it fails naming the ratio", () => {
  const p = fixture({
    palette: { bg_primary: "#ffffff", on_accent: "#ffffff", border: "#dddddd", text_primary: "#cccccc" },
    measurements: [{ fg: "#cccccc", bg: "#ffffff", selector: "h2.headline" }],
  });

  assert.throws(() => run(p), /4\.5:1/);
  assert.match(fs.readFileSync(p.globals, "utf-8"), /--foreground:\s*#cccccc;/, "nothing written on failure");
});

test("a replacement that would regress a currently-passing measurement is refused", () => {
  // #b0b0b0 fails on the white ground and passes on the dark one. No single
  // token value can serve both, so the honest answer is a named failure — not
  // a repair that silently breaks the dark band.
  const p = fixture({
    palette: { ...BVNK, text_primary: "#b0b0b0", surface_inverse: "#242d35" },
    measurements: [
      { fg: "#b0b0b0", bg: "#ffffff", selector: "h2.on-light" },
      { fg: "#b0b0b0", bg: "#242d35", selector: "p.on-dark" },
    ],
  });

  assert.throws(() => run(p), (e) => /4\.5:1/.test(e.message) && /regress/i.test(e.message));
  assert.match(fs.readFileSync(p.globals, "utf-8"), /--foreground:\s*#b0b0b0;/);
});

test("a failure whose colour is not token-driven is reported, never silently passed", () => {
  // text-gray-300 (#d1d5db) — 21 such literals exist in the built sections today.
  const p = fixture({
    palette: { ...BVNK, text_primary: "#242d35" },
    measurements: [{ fg: "#d1d5db", bg: "#ffffff", selector: "p.text-gray-300" }],
  });

  const res = run(p);

  assert.equal(res.status, "FAIL");
  assert.equal(res.exitCode, 1);
  assert.equal(res.unrepairable.length, 1);
  assert.equal(res.unrepairable[0].reason, "colour-not-token-driven");
  assert.equal(res.unrepairable[0].selector, "p.text-gray-300");
  assert.equal(res.unrepairable[0].route, "/");
  assert.equal(readSpec(p).style.adjustments.length, 0);
});

test("an ambiguous colour shared by two roles is reported, not guessed", () => {
  // Real shape: cape-crypto's text_primary and surface_inverse are both #242d35.
  const p = fixture({
    palette: { ...BVNK, text_primary: "#242d35", surface_inverse: "#242d35", bg_primary: "#2b3540" },
    measurements: [{ fg: "#242d35", bg: "#2b3540", selector: "h2.headline" }],
  });

  const res = run(p);

  assert.equal(res.status, "FAIL");
  assert.equal(res.unrepairable[0].reason, "ambiguous-role");
  assert.deepEqual(res.unrepairable[0].roles.sort(), ["surface_inverse", "text_primary"]);
});

test("zero contrast failures is PASS and writes nothing", () => {
  const p = fixture({
    palette: { ...BVNK, text_primary: "#242d35" },
    measurements: [{ fg: "#242d35", bg: "#ffffff", selector: "h1.text-balance" }],
  });
  const before = fs.readFileSync(p.globals, "utf-8");

  const res = run(p);

  assert.equal(res.status, "PASS");
  assert.equal(res.exitCode, 0);
  assert.equal(res.measured, 1);
  assert.equal(res.failed, 0);
  assert.equal(fs.readFileSync(p.globals, "utf-8"), before);
});

test("a report carrying no contrast measurements is NOT_MEASURED, never PASS", () => {
  const p = fixture({ palette: { ...BVNK, text_primary: "#242d35" }, measurements: [] });
  const raw = JSON.parse(fs.readFileSync(p.report, "utf-8"));
  delete raw.routes[0].facts.contrast;                      // a pre-C2 probe
  delete raw.routes[0].facts.contrastSummary;
  fs.writeFileSync(p.report, JSON.stringify(raw));

  const res = run(p);

  assert.equal(res.status, "NOT_MEASURED");
  assert.equal(res.exitCode, 3);
  assert.notEqual(res.status, "PASS");
});

test("a palette whose provenance is not the benchmark is refused, not repaired", () => {
  const p = fixture({
    palette: { ...BVNK, text_primary: "#cccccc" },
    measurements: [{ fg: "#cccccc", bg: "#ffffff", selector: "h2.headline" }],
    designSource: "crawled",
  });

  assert.throws(() => run(p), /provenance/i);
});

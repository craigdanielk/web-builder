#!/usr/bin/env node
/**
 * render-audit.js — Post-build visual render audit.
 *
 * The symmetric twin of the pre-build UI/UX audit: instead of auditing the OLD
 * site to produce a Bill of Sale, this audits the NEWLY BUILT site (deployed or
 * locally served) to prove it actually RENDERS. "HTTP 200 / deploy READY" does
 * not mean a page is visible, has images, or is navigable — this catches that.
 *
 * For every route it loads the page in headless Chromium, screenshots it, and
 * asserts:
 *   - visibility   : major sections actually render (not stuck at opacity:0 /
 *                    collapsed / invisible) — the #1 generation failure mode
 *   - images       : every <img> and CSS background image resolves and paints
 *                    (naturalWidth > 0, no 4xx), and flags a page with ZERO
 *                    images where content implies imagery
 *   - contrast     : prominent text has adequate contrast against its backdrop
 *   - navigation   : header nav links resolve to real in-site routes, not "#"
 *                    or generic placeholders, so pages are reachable
 *   - console      : no runtime console errors / exceptions
 *   - http         : the route itself and its assets don't 4xx/5xx
 *
 * Defects are emitted in a Bill-of-Sale-aligned schema so they feed the same
 * fix loop as the pre-build audit. Re-run after fixes until defects === 0.
 *
 * Usage:
 *   node render-audit.js --base <url> --routes "/,/pricing,/signup" --out <dir>
 *   node render-audit.js --base <url> --manifest <site-manifest.json> --out <dir>
 */

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const { describe } = require("./lib/capability");

/** What this instrument is, in its own words. Compiled into the capability
 *  register by `scripts/capability_register.py`; see that file for why it lives
 *  here rather than in a separate document. */
const CAPABILITY = {
  id: "aurelix.probe.render-audit",
  name: "Post-build render audit (headless Chromium probe)",
  kind: "probe",
  invocation:
    "node scripts/quality/render-audit.js --base <url> (--routes <a,b,c> | --manifest <site-manifest.json>) --out <dir> [--viewport 1440x900] [--settle 2500]",
  preconditions: [
    "the site is already SERVED at --base (a local `npm run start` or a deployed URL) — this probe neither builds nor deploys",
    "playwright with a chromium browser installed (`npx playwright install chromium`); its absence is a launch failure, not a measurement",
  ],
  inputs: ["every route reachable at <base><route>, from --routes or the non-dynamic pages of --manifest"],
  outputs: [
    "<out>/render-audit.json — the DEFECT SUMMARY (counts by severity/category, per-page totals); `facts` are discarded here",
    "<out>/report.json — schema aurelix.render_audit.v2, the raw per-route `facts` the summary throws away",
    "<out>/render-<route>.png — one full-page screenshot per route",
    "stdout: one JSON line {report, total_defects, by_severity} for the Python caller",
  ],
  outcome:
    "what the built site actually paints per route: section boxes, image load state, nav reachability, measured contrast with a denominator, console errors and 4xx/5xx requests",
  exit_contract: {
    0: "the audit RAN and both reports were written. It exits 0 whatever the defect count — this is a probe, not a gate, and the exit code carries no verdict",
    1: "the probe itself failed (chromium would not launch, or an unhandled error)",
    2: "usage — --base or --out missing",
  },
  measures: [
    "per-section geometry and paint: height/width, opacity, visibility, textLen, a djb2 text fingerprint, own/child background image, per-section overflowX",
    "page box: scrollWidth vs clientWidth with a 1px tolerance — the horizontal-overflow measurement",
    "every <img>: naturalWidth/Height, rendered box, objectFit, load state; CSS background-image URLs are listed but their load state is recorded as null",
    "contrast on up to 400 text elements that own their text node, alpha-compositing every background layer up to the first opaque ancestor, with measured/passed/failed counts so a failure count has a denominator",
    "header/nav hrefs against the known route set, console errors, and every response with status >= 400",
  ],
  cannot_see: [
    "any route it was not given: --manifest deliberately drops dynamic [handle] routes and not-found, so a broken product page is outside its world",
    "a permanently invisible reveal — before probing it injects `[style*=\"opacity\"]{opacity:1!important}` to settle framer entrance animations, which also forces a genuinely stuck-at-0 element visible",
    "zero-height sections as defects: blocks under 40px are recorded with belowThreshold=true and countedSections() keeps them out of every count and check",
    "whether a CSS background-image resolves — kind:'bg' records are pushed with loaded:null and nothing ever fetches them",
    "contrast of text inside a fixed/sticky overlay whose backdrop resolves light: those elements are SKIPPED, because the DOM-ancestor walk cannot see what is visually behind them",
    "whether the content is TRUE. It measures paint, not provenance — a fabricated statistic renders perfectly and scores zero defects",
    "anything that needs interaction: hover, modals, form states, authenticated pages. It loads, scrolls, and measures",
  ],
  reachable_from: [
    "orchestrate.py:10002 (Stage 6 resolves the path) and orchestrate.py:10090 (subprocess.run, 180s timeout)",
    "standalone CLI",
  ],
  cost: "roughly 10-20s per route (45s navigation timeout, --settle 2500ms, a scroll pass at 250ms per viewport, plus a full-page screenshot); requires a served site and a chromium download",
};

function parseArgs(argv) {
  const a = { base: null, routes: null, manifest: null, out: null, viewport: "1440x900", settle: 2500 };
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    if (k === "--base") a.base = argv[++i];
    else if (k === "--routes") a.routes = argv[++i];
    else if (k === "--manifest") a.manifest = argv[++i];
    else if (k === "--out") a.out = argv[++i];
    else if (k === "--viewport") a.viewport = argv[++i];
    else if (k === "--settle") a.settle = parseInt(argv[++i], 10);
  }
  return a;
}

function routesFromManifest(manifestPath) {
  const m = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
  const out = [];
  for (const p of m.pages || []) {
    if (p.dynamic) continue;              // skip [handle] template routes
    if (p.id === "not-found") continue;
    const r = p.route || "/";
    if (!r.includes("[")) out.push(r);
  }
  return out.length ? out : ["/"];
}

// In-page probe: runs in the browser, returns structured render facts.
const PROBE = () => {
  const facts = {
    sections: [], images: [], navLinks: [], lowContrast: [],
    contrast: [], contrastSummary: { measured: 0, passed: 0, failed: 0 },
    page: null, textLen: 0,
  };

  const lum = (rgb) => {
    const [r, g, b] = rgb.map((v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  // Canvas-based color parser: resolves ANY CSS color the browser understands
  // (rgb/rgba, hsl, named, and Tailwind v4's oklch()) to straight {rgb, a}.
  // A regex that only matched rgb() silently failed on oklch and fell through to
  // a white default, producing phantom "white-on-white" contrast flags.
  const _cv = document.createElement("canvas");
  _cv.width = _cv.height = 1;
  const _cx = _cv.getContext("2d", { willReadFrequently: true });
  const parseRGB = (s) => {
    if (!s) return null;
    try {
      _cx.clearRect(0, 0, 1, 1);
      _cx.fillStyle = "#000";      // reset so an invalid value can't inherit prior color
      _cx.fillStyle = s;
      if (_cx.fillStyle === "#000" && !/^(#000000|black|rgb\(0, 0, 0\)|oklch\(0)/i.test(s.trim()))
        return null;               // browser rejected the value
      _cx.fillRect(0, 0, 1, 1);
      const d = _cx.getImageData(0, 0, 1, 1).data;
      return { rgb: [d[0], d[1], d[2]], a: d[3] / 255 };
    } catch (e) {
      return null;
    }
  };
  // Alpha-composite every background layer from the element up to the first
  // opaque ancestor, over a white base. Returning a semi-transparent layer's raw
  // rgb (e.g. a 10%-opacity orange pill) as if opaque produced false "same-color"
  // contrast flags — the real visual backdrop is that layer composited over what
  // is behind it.
  const effectiveBg = (el) => {
    const layers = [];
    let node = el;
    while (node && node !== document.documentElement) {
      const p = parseRGB(getComputedStyle(node).backgroundColor);
      if (p && p.a > 0.001) {
        layers.push(p);
        if (p.a >= 0.999) break;   // opaque — nothing behind it matters
      }
      node = node.parentElement;
    }
    let base = [255, 255, 255];
    for (let i = layers.length - 1; i >= 0; i--) {
      const { rgb, a } = layers[i];
      base = [0, 1, 2].map((k) => Math.round(rgb[k] * a + base[k] * (1 - a)));
    }
    return base;
  };
  const contrast = (fg, bg) => {
    const l1 = lum(fg), l2 = lum(bg);
    const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
    return (hi + 0.05) / (lo + 0.05);
  };
  // Emit colours as #rrggbb. render-fix-contrast.js's hexToRgb (:26-30) parses
  // ONLY #rgb/#rrggbb — reporting the native {rgb:[r,g,b],a} would leave the
  // contrast repair loop unable to read its own input.
  const toHex = (rgb) =>
    "#" + rgb.map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("");
  // Enough identity to trace a finding back to a source file.
  const identify = (el) => {
    const cls = (el.className || "").toString().trim().split(/\s+/).filter(Boolean).slice(0, 3);
    return el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + cls.map((c) => "." + c).join("");
  };
  // Stable content fingerprint (djb2 over whitespace-normalised text). Two
  // sections with equal text LENGTH are otherwise indistinguishable, so
  // cross-route duplication cannot be detected from lengths alone.
  const fingerprint = (s) => {
    const norm = s.toLowerCase().replace(/\s+/g, " ").trim();
    let h = 5381;
    for (let i = 0; i < norm.length; i++) h = ((h * 33) ^ norm.charCodeAt(i)) >>> 0;
    return h.toString(16).padStart(8, "0");
  };

  facts.textLen = (document.body.innerText || "").trim().length;

  // ── Page box: horizontal overflow was not measurable at all before this ──
  const de = document.documentElement;
  facts.page = {
    scrollWidth: de.scrollWidth,
    clientWidth: de.clientWidth,
    innerWidth: window.innerWidth,
    scrollHeight: de.scrollHeight,
    // 1px tolerance: sub-pixel layout rounding is not an overflow defect.
    overflowX: de.scrollWidth > de.clientWidth + 1,
  };

  // ── Sections: top-level content blocks under <main> (or body) ──
  const main = document.querySelector("main") || document.body;
  const blocks = Array.from(main.querySelectorAll(":scope > *, :scope > * > section, section"));
  const seen = new Set();
  let sectionIdx = 0;
  for (const el of blocks) {
    if (seen.has(el)) continue;
    seen.add(el);
    const r = el.getBoundingClientRect();
    // Blocks under 40px are wrapper noise for every EXISTING check — but a 0px
    // section is precisely the zero-dimension defect, and dropping the record
    // here made that defect unmeasurable. Record it, flag it, and let
    // countedSections() keep it out of the counts and the defect list.
    const below = r.height < 40;
    const cs = getComputedStyle(el);
    const op = parseFloat(cs.opacity);
    const vis = cs.visibility !== "hidden" && cs.display !== "none";
    const txt = (el.innerText || "").trim();
    const bgOwn = cs.backgroundImage && cs.backgroundImage !== "none";
    const bgChild = !bgOwn && Array.from(el.querySelectorAll("*")).slice(0, 300)
      .some((c) => { const b = getComputedStyle(c).backgroundImage; return b && b !== "none"; });
    facts.sections.push({
      i: sectionIdx++,
      tag: el.tagName.toLowerCase(),
      id: el.id || "",
      cls: (el.className || "").toString().slice(0, 60),
      selector: identify(el),
      h: Math.round(r.height),
      w: Math.round(r.width),
      height: Math.round(r.height),   // kept for existing toDefects() readers
      x: Math.round(r.left),
      y: Math.round(r.top + window.scrollY),
      opacity: isNaN(op) ? 1 : op,
      visible: vis,
      textLen: txt.length,
      textFp: fingerprint(txt),
      // Empty-section check needs BOTH: no text and nothing painted.
      imgCount: el.querySelectorAll("img").length,
      hasBg: Boolean(bgOwn || bgChild),
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
      overflowX: el.scrollWidth > el.clientWidth + 1,
      belowThreshold: below,
      // "invisible" = takes vertical space but is opacity~0 / hidden / paints nothing
      invisible: !below && (op < 0.05 || !vis) && r.height > 80,
    });
  }

  // ── Images: <img> + CSS background-image ──
  for (const img of Array.from(document.images)) {
    const r = img.getBoundingClientRect();
    facts.images.push({
      kind: "img",
      src: img.currentSrc || img.src || "",
      alt: img.alt || "",
      selector: identify(img),
      loaded: img.complete && img.naturalWidth > 0,
      w: img.naturalWidth, h: img.naturalHeight,
      // Rendered box. Natural-vs-rendered is the aspect-distortion measurement;
      // collapsing it to `onscreen` threw the numerator away.
      rw: Math.round(r.width), rh: Math.round(r.height),
      // An object-cover image is cropped BY INTENT — without this every cover
      // image reads as distorted.
      objectFit: getComputedStyle(img).objectFit || "fill",
      onscreen: r.width > 0 && r.height > 0,
    });
  }
  for (const el of Array.from(document.querySelectorAll("*")).slice(0, 4000)) {
    const bg = getComputedStyle(el).backgroundImage;
    if (bg && bg !== "none" && bg.includes("url(")) {
      const url = (bg.match(/url\(["']?([^"')]+)["']?\)/) || [])[1] || "";
      if (url && !url.startsWith("data:")) facts.images.push({ kind: "bg", src: url, loaded: null });
    }
  }

  // ── Nav links (header / nav) ──
  const navScope = document.querySelector("header, nav") || document;
  for (const a of Array.from(navScope.querySelectorAll("a[href]"))) {
    facts.navLinks.push({ text: (a.innerText || "").trim().slice(0, 40), href: a.getAttribute("href") });
  }

  // ── Contrast on prominent text ──
  // Only measure elements that render their OWN text (a direct non-whitespace
  // text node). A container like <li> whose text lives in a coloured child <span>
  // otherwise gets measured with its inherited body colour, producing false
  // "invisible container" flags even though the visible text is fine.
  const hasOwnText = (el) =>
    Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim().length > 3);
  const textEls = Array.from(document.querySelectorAll("h1,h2,h3,p,a,button,li,span"))
    .filter((e) => (e.innerText || "").trim().length > 4 && hasOwnText(e)).slice(0, 400);
  // Is the element inside a position:fixed/sticky overlay? Such elements (e.g. a
  // transparent header over a hero) render over whatever is visually behind them,
  // which the DOM-ancestor walk cannot see — measuring them against the page
  // default background yields false flags. Skip when their bg is unresolved.
  const inOverlay = (el) => {
    let n = el;
    while (n && n !== document.body) {
      const p = getComputedStyle(n).position;
      if (p === "fixed" || p === "sticky") return true;
      n = n.parentElement;
    }
    return false;
  };
  for (const el of textEls) {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    const cs = getComputedStyle(el);
    const fg = parseRGB(cs.color);
    if (!fg) continue;
    const bg = effectiveBg(el);
    // Overlay text (fixed/sticky) whose backdrop resolves to the light page default
    // is unmeasurable — a transparent header renders over whatever is visually
    // behind it, which the DOM-ancestor walk cannot see. Skip rather than false-flag.
    if (inOverlay(el) && lum(bg) > 0.8) continue;
    const ratio = contrast(fg.rgb, bg);
    const size = parseFloat(cs.fontSize);
    const weight = parseInt(cs.fontWeight) || 400;
    const need = size >= 24 || (size >= 18.66 && weight >= 700) ? 3 : 4.5;
    const entry = {
      text: (el.innerText || "").trim().slice(0, 40),
      selector: identify(el),
      tag: el.tagName.toLowerCase(),
      cls: (el.className || "").toString().slice(0, 60),
      fg: toHex(fg.rgb),          // hex — see toHex()
      bg: toHex(bg),
      fontSize: size,
      fontWeight: weight,
      ratio: Math.round(ratio * 100) / 100,
      need,
      pass: ratio >= need,
    };
    // Record every measurement, not only the failures: "3 failures" without a
    // denominator cannot be read as better or worse than the last run.
    facts.contrast.push(entry);
    facts.contrastSummary.measured++;
    if (entry.pass) facts.contrastSummary.passed++;
    else { facts.contrastSummary.failed++; facts.lowContrast.push(entry); }
  }
  return facts;
};

async function auditRoute(context, base, route, outDir, settle) {
  const page = await context.newPage();
  const consoleErrors = [];
  const badRequests = [];
  page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text().slice(0, 200)); });
  page.on("pageerror", (e) => consoleErrors.push(String(e).slice(0, 200)));
  page.on("response", (resp) => {
    const s = resp.status();
    if (s >= 400) badRequests.push({ url: resp.url().slice(0, 160), status: s, type: resp.request().resourceType() });
  });

  const url = base.replace(/\/$/, "") + route;
  let httpStatus = null;
  try {
    const resp = await page.goto(url, { waitUntil: "load", timeout: 45000 });
    httpStatus = resp ? resp.status() : null;
  } catch (e) {
    consoleErrors.push("navigation: " + String(e).slice(0, 160));
  }
  await page.waitForTimeout(settle);              // let entrance animations resolve

  // Scroll the full page in viewport steps so IntersectionObserver-driven
  // reveals (framer `whileInView`) actually fire. Without this every
  // viewport-triggered section probes as empty and reads as a render defect.
  // A single scrollTo(0, bottom) jump does NOT work — elements passed over in
  // one jump never intersect the viewport and their observers never fire.
  const pageHeight = await page.evaluate(() => document.body.scrollHeight).catch(() => 0);
  const step = await page.evaluate(() => window.innerHeight).catch(() => 900);
  for (let y = 0; y < pageHeight; y += step) {
    await page.evaluate((yy) => window.scrollTo(0, yy), y).catch(() => {});
    await page.waitForTimeout(250);
  }
  await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
  await page.waitForTimeout(500);

  // Neutralize scroll-entrance animations (framer-motion sets inline opacity/transform).
  // Without this, below-fold whileInView elements are still opacity:0 at measure time and
  // read as false-positive "contrast ~1.0". This forces final visible state so the contrast
  // probe measures real fg/bg colors (genuine fg==bg bugs still surface).
  await page.addStyleTag({
    content: '[style*="opacity"]{opacity:1 !important} [style*="transform"]{transform:none !important}',
  }).catch(() => {});
  await page.waitForTimeout(150);

  const facts = await page.evaluate(PROBE).catch(() => null);
  const shotName = "render-" + (route === "/" ? "home" : route.replace(/[\/]/g, "_").replace(/^_/, "")) + ".png";
  const shotPath = path.join(outDir, shotName);
  try { await page.screenshot({ path: shotPath, fullPage: true }); } catch (e) { /* ignore */ }
  await page.close();
  return { route, url, httpStatus, facts, consoleErrors, badRequests, screenshot: shotPath };
}

function toDefects(res, knownRoutes) {
  const D = [];
  const pid = res.route === "/" ? "home" : res.route.replace(/\//g, "");
  let n = 0;
  const add = (category, severity, finding, evidence, fix_locus) =>
    D.push({ id: `RA-${pid}-${++n}`, page: res.route, category, severity, finding, evidence, fix_locus });

  if (res.httpStatus && res.httpStatus >= 400)
    add("http", "critical", `Route returns HTTP ${res.httpStatus}`, res.url, "web_builder");

  const f = res.facts;
  if (!f) { add("render", "critical", "Page produced no render facts (crashed/blank)", res.url, "web_builder"); return D; }

  if (f.textLen < 40)
    add("render_visibility", "critical", "Page renders almost no visible text", `body innerText len=${f.textLen}`, "web_builder");

  const invisible = countedSections(f).filter((s) => s.invisible);
  if (invisible.length)
    add("render_visibility", "critical",
      `${invisible.length} major section(s) render invisible (opacity~0/hidden but occupy space)`,
      invisible.slice(0, 6).map((s) => `${s.tag}.${s.cls} h=${s.height} op=${s.opacity}`).join(" | "),
      "web_builder");

  const brokenImgs = (f.images || []).filter((i) => i.kind === "img" && i.loaded === false);
  if (brokenImgs.length)
    add("render_image", "high", `${brokenImgs.length} image(s) fail to load (naturalWidth 0)`,
      brokenImgs.slice(0, 6).map((i) => i.src || "(empty src)").join(" | "), "web_builder");
  const imgCount = (f.images || []).filter((i) => i.kind === "img").length;
  if (imgCount === 0)
    add("render_image", "high", "Page renders ZERO images (no <img> elements)",
      "no image elements found — trust icons/media/hero imagery absent", "web_builder");

  const imgReq404 = (res.badRequests || []).filter((b) => b.type === "image");
  if (imgReq404.length)
    add("render_image", "high", `${imgReq404.length} image request(s) 4xx/5xx`,
      imgReq404.slice(0, 6).map((b) => `${b.status} ${b.url}`).join(" | "), "web_builder");

  if (f.lowContrast && f.lowContrast.length >= 3)
    add("render_contrast", "high", `${f.lowContrast.length} text element(s) below WCAG contrast`,
      f.lowContrast.slice(0, 6).map((c) => `"${c.text}" ${c.ratio}<${c.need}`).join(" | "), "web_builder");

  // Nav reachability: header links must resolve to real in-site routes.
  const nav = f.navLinks || [];
  const realTargets = nav.filter((l) => l.href && l.href.startsWith("/") && !l.href.startsWith("//"));
  const knownSet = new Set(knownRoutes.map((r) => r.replace(/\/$/, "") || "/"));
  const resolvable = realTargets.filter((l) => knownSet.has(l.href.replace(/\/$/, "") || "/") || l.href.startsWith("/#"));
  const placeholders = nav.filter((l) => !l.href || l.href === "#" || l.href === "");
  if (nav.length && resolvable.length === 0)
    add("render_nav", "critical", "Header nav has no links to real in-site routes (pages unreachable)",
      nav.slice(0, 6).map((l) => `"${l.text}"→${l.href}`).join(" | ") + ` | knownRoutes=${[...knownSet].join(",")}`,
      "web_builder");
  else if (placeholders.length >= 2)
    add("render_nav", "medium", `${placeholders.length} nav link(s) are placeholders ("#")`,
      placeholders.slice(0, 6).map((l) => `"${l.text}"`).join(" | "), "web_builder");

  const realConsole = (res.consoleErrors || []).filter((e) => !/extension|favicon|third-party/i.test(e));
  if (realConsole.length)
    add("console_error", "high", `${realConsole.length} console error(s)`,
      realConsole.slice(0, 4).join(" || "), "web_builder");

  return D;
}

// Sections the summary counts and the defect checks are allowed to see. Blocks
// below the wrapper-noise threshold are RECORDED (so a zero-height section is
// visible to a downstream check) but never counted as page sections.
function countedSections(facts) {
  return (facts?.sections || []).filter((s) => !s.belowThreshold);
}

async function main() {
  if (describe(CAPABILITY)) return 0;
  const args = parseArgs(process.argv);
  if (!args.base || !args.out) {
    console.error("Usage: render-audit.js --base <url> (--routes a,b,c | --manifest path) --out <dir>");
    process.exit(2);
  }
  let routes = ["/"];
  if (args.routes) routes = args.routes.split(",").map((s) => s.trim()).filter(Boolean);
  else if (args.manifest) routes = routesFromManifest(args.manifest);
  fs.mkdirSync(args.out, { recursive: true });
  const [vw, vh] = args.viewport.split("x").map((n) => parseInt(n, 10));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: 1 });

  const results = [];
  for (const route of routes) {
    process.stderr.write(`  🔎 auditing ${route} ...\n`);
    results.push(await auditRoute(context, args.base, route, args.out, args.settle));
  }
  await browser.close();

  const defects = [];
  for (const res of results) defects.push(...toDefects(res, routes));

  const bySeverity = defects.reduce((a, d) => ((a[d.severity] = (a[d.severity] || 0) + 1), a), {});
  const report = {
    base_url: args.base,
    audited_at_routes: routes,
    total_defects: defects.length,
    by_severity: bySeverity,
    by_category: defects.reduce((a, d) => ((a[d.category] = (a[d.category] || 0) + 1), a), {}),
    pages: results.map((r) => ({
      route: r.route, httpStatus: r.httpStatus, screenshot: r.screenshot,
      sections: countedSections(r.facts).length,
      invisibleSections: countedSections(r.facts).filter((s) => s.invisible).length,
      images: (r.facts?.images || []).filter((i) => i.kind === "img").length,
      textLen: r.facts?.textLen ?? 0,
    })),
    defects,
  };
  const outFile = path.join(args.out, "render-audit.json");
  fs.writeFileSync(outFile, JSON.stringify(report, null, 2));

  // Raw per-route facts report (aurelix.render_audit.v2). This is the report
  // consumed by scripts/quality/render-audit.smoke.js and by later pipeline
  // phases that assert against `facts` directly rather than summary counts.
  // Written alongside render-audit.json (not a replacement) so the existing
  // orchestrate.py Stage 6 consumer, which reads render-audit.json's summary
  // shape, keeps working unchanged.
  const rawReport = {
    schema: "aurelix.render_audit.v2",
    generated: new Date().toISOString(),
    routes: results.map((r) => ({
      route: r.route,
      url: r.url,
      httpStatus: r.httpStatus,
      facts: r.facts,
      consoleErrors: r.consoleErrors,
      badRequests: r.badRequests,
      screenshot: r.screenshot,
      summary: {
        sections: countedSections(r.facts).length,
        invisibleSections: countedSections(r.facts).filter((s) => s.invisible).length,
        subThresholdBlocks: (r.facts?.sections || []).filter((s) => s.belowThreshold).length,
        contrast: r.facts?.contrastSummary || null,
        overflowX: r.facts?.page?.overflowX ?? null,
        images: (r.facts?.images || []).filter((i) => i.kind === "img").length,
        textLen: r.facts?.textLen ?? 0,
      },
    })),
    defects,
  };
  const rawOutFile = path.join(args.out, "report.json");
  fs.writeFileSync(rawOutFile, JSON.stringify(rawReport, null, 2));

  process.stderr.write(`\n  📋 ${defects.length} defect(s) across ${routes.length} route(s) — ${JSON.stringify(bySeverity)}\n`);
  process.stderr.write(`  → ${outFile}\n`);
  process.stderr.write(`  → ${rawOutFile}\n`);
  // stdout = machine-readable report path + summary for the Python wrapper
  console.log(JSON.stringify({ report: outFile, total_defects: defects.length, by_severity: bySeverity }));
  process.exit(0);
}

module.exports = { PROBE, toDefects, countedSections, routesFromManifest, parseArgs };

if (require.main === module) {
  main().catch((e) => { console.error("render-audit failed:", e); process.exit(1); });
}

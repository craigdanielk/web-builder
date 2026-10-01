#!/usr/bin/env node
/**
 * device-matrix — headless Device & Media Compatibility gate (canonical; origin: Trend Digital 2026-10-01).
 * Shared verbatim by trend-digital-website and Aurelix AG. HEADLESS ONLY (never opens a visible browser).
 *
 * For every route x device profile it asserts:
 *  D1 page loads (HTTP < 400)            D2 no page errors / same-origin console errors
 *  D3 no failed same-origin requests      D4 no horizontal overflow
 *  D5 every on-screen <video> asked to play actually advances (or ended) — not stuck (reduced-motion exempt)
 *  D6 no loading indicator still visible after the settle budget
 *  D7 no clipped text in interactive/heading elements
 *  D8 every role=tablist: clicking each tab selects exactly that tab
 *  D9 route change lands at the TOP of the new page (scroll is reset), tested from the bottom of the page
 *  D10 phones: a menu control exists in the header and opening it exposes navigation links
 *  D11 the page's H1 is visible within the first viewport after the settle budget (no hero pushed off-screen)
 * Devices: desktop-1440@2x, desktop-1280@1x, android (Galaxy S24 Ultra UA), iphone, reduced-motion.
 *
 * LIMIT (stated, not hidden): emulation uses desktop Chrome's decoders. Real hardware decoder failures (the
 * 2026-10-01 Android incident passed emulation) are caught by media-policy.mjs + the manual real-device checklist.
 *
 * Usage: node device-matrix.mjs --base <url> [--routes /,/pricing] [--devices a,b] [--out dir] [--settle 7000]
 *                               [--override "<reason>"]   (or QA_OVERRIDE env)
 * Exit: 0 PASS · 1 FAIL · 3 NOT_MEASURED (base unreachable). Override turns 1 into 0, logged loudly.
 */
import { chromium, devices } from "playwright"; import fs from "node:fs"; import path from "node:path"; import os from "node:os";
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const base = (arg("--base", process.env.QA_BASE || "http://localhost:3000")).replace(/\/$/, "");
const routes = arg("--routes", "/").split(",").filter(Boolean);
const out = arg("--out", "qa-report"); const settle = +arg("--settle", "7000");
const override = arg("--override", process.env.QA_OVERRIDE || "");
const S24 = "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36";
const ALL = {
  "desktop-1440@2x": { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, screen: { width: 1440, height: 900 } },
  "desktop-1280@1x": { viewport: { width: 1280, height: 800 } },
  "android-s24": { ...devices["Pixel 7"], userAgent: S24 },
  "iphone": { ...devices["iPhone 14 Pro"] },
  "reduced-motion": { viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" },
};
const pick = arg("--devices", Object.keys(ALL).join(",")).split(",");
fs.mkdirSync(out, { recursive: true });
try { const r = await fetch(base + routes[0]); if (!r.ok && r.status >= 500) throw new Error(String(r.status)); }
catch (e) { console.log(`device-matrix: NOT_MEASURED — ${base} unreachable (${e.message})`); process.exit(3); }
const origin = new URL(base).origin;
// Installed Chrome first (real codec set), bundled Chromium as fallback. Always headless.
const browser = await chromium.launch({ channel: process.env.QA_CHANNEL || "chrome", headless: true })
  .catch(() => chromium.launch({ headless: true }));
const report = { base, at: new Date().toISOString(), results: [] }; let failures = 0;
const runOne = async (route, dev) => {
  const ctx = await browser.newContext(ALL[dev]); const p = await ctx.newPage(); const f = [];
  p.on("pageerror", (e) => f.push(`D2 page error: ${e.message.slice(0, 160)}`));
  p.on("console", (m) => { if (m.type() !== "error") return; const u = m.location()?.url || ""; if (!u || u.startsWith(origin)) f.push(`D2 console error: ${m.text().slice(0, 160)}`); });
  p.on("requestfailed", (r) => { const t = r.failure()?.errorText || ""; if (r.url().startsWith(origin) && !/ERR_ABORTED/.test(t)) f.push(`D3 failed request ${r.url().replace(origin, "")} ${t}`); });
  p.on("response", (r) => { if (r.url().startsWith(origin) && r.status() >= 400) f.push(`D3 HTTP ${r.status()} ${r.url().replace(origin, "")}`); });
  let status = 0;
  try { const res = await p.goto(base + route, { waitUntil: "load", timeout: 60000 }); status = res?.status() ?? 0; } catch (e) { f.push(`D1 navigation: ${e.message.slice(0, 120)}`); }
  if (status >= 400) f.push(`D1 HTTP ${status}`);
  await p.waitForTimeout(settle);
  const probe = await p.evaluate((reduced) => {
    const r = []; const vis = (e) => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0 && b.bottom > 0 && b.top < innerHeight && getComputedStyle(e).visibility !== "hidden"; };
    if (document.documentElement.scrollWidth > innerWidth + 1) r.push(`D4 horizontal overflow: ${document.documentElement.scrollWidth}px > ${innerWidth}px`);
    if (!reduced) for (const v of document.querySelectorAll("video")) {
      if (!vis(v) || (!v.currentSrc && !v.querySelector("source"))) continue;
      // Stuck = playback was requested (not paused, or autoplay) yet the media clock never moved: the signature of a
      // starved/stalled decoder. A deliberately paused lazy loop (preload=none, inactive step) is not a failure.
      if (v.paused && !v.autoplay) continue;
      if (!(v.currentTime > 0 || v.ended)) r.push(`D5 video stuck: ${v.currentSrc || "(no source chosen)"} readyState=${v.readyState} error=${v.error?.code ?? "-"}`);
    }
    for (const s of document.querySelectorAll('[role=status][aria-label*="oad" i], [aria-busy=true]')) if (vis(s) && +getComputedStyle(s).opacity > 0.1) r.push("D6 loading indicator still visible after settle budget");
    for (const e of document.querySelectorAll("a,button,[role=tab],label,h1,h2,h3")) {
      if (!vis(e) || e.closest('[aria-hidden="true"]') || !e.textContent.trim()) continue;
      const c = getComputedStyle(e); if (c.textOverflow === "ellipsis") continue;
      if (/(hidden|clip)/.test(c.overflowX) && e.scrollWidth > e.clientWidth + 2) r.push(`D7 clipped text: <${e.tagName.toLowerCase()}> "${e.textContent.trim().slice(0, 40)}"`);
    }
    return r;
  }, dev === "reduced-motion");
  f.push(...probe);
  // D11 H1 within the first viewport
  const h1 = await p.evaluate(() => { const h = document.querySelector("h1"); if (!h) return "none"; const b = h.getBoundingClientRect();
    return b.height > 0 && b.top < innerHeight && b.bottom > 0 ? "ok" : `off-screen top=${Math.round(b.top)}`; });
  if (h1 !== "ok" && h1 !== "none") f.push(`D11 H1 not in first viewport (${h1})`);
  // D10 phones: header menu control opens navigation
  if (/android|iphone/.test(dev)) {
    // first VISIBLE candidate (desktop dropdown triggers also carry aria-expanded but are hidden on phones)
    const cands = p.locator('header button[aria-label*="menu" i], header button[aria-expanded], header [aria-controls][aria-expanded]');
    let menu = null;
    for (let i = 0; i < await cands.count(); i++) if (await cands.nth(i).isVisible().catch(() => false)) { menu = cands.nth(i); break; }
    if (!menu) f.push("D10 no visible menu control in the header on a phone");
    else {
      const before = await p.evaluate(() => [...document.querySelectorAll("a[href^='/']")].filter((a) => { const b = a.getBoundingClientRect(); return b.width && b.height && b.top >= 0 && b.top < innerHeight && getComputedStyle(a).visibility !== "hidden"; }).length);
      await menu.click({ timeout: 3000 }).catch(() => {}); await p.waitForTimeout(700);
      const after = await p.evaluate(() => [...document.querySelectorAll("a[href^='/']")].filter((a) => { const b = a.getBoundingClientRect(); return b.width && b.height && b.top >= 0 && b.top < innerHeight && getComputedStyle(a).visibility !== "hidden"; }).length);
      if (after <= before) f.push(`D10 opening the menu exposed no navigation links (${before} -> ${after})`);
    }
    // reset: an open menu sheet would intercept every later click — start the remaining checks from a fresh load
    await p.goto(base + route, { waitUntil: "load", timeout: 60000 }).catch(() => {}); await p.waitForTimeout(Math.min(settle, 5000));
  }
  // D8 tablists (visible ones only)
  const lists = p.locator("[role=tablist]");
  for (let li = 0; li < await lists.count(); li++) {
    const tl = lists.nth(li); if (!(await tl.isVisible())) continue;
    const tabs = tl.locator("[role=tab]"); const n = await tabs.count();
    for (let k = 0; k < n; k++) {
      try { await tabs.nth(k).click({ timeout: 3000 }); await p.waitForTimeout(250);
        const sel = await tl.evaluate((el) => [...el.querySelectorAll("[role=tab]")].map((t) => t.getAttribute("aria-selected") === "true"));
        if (!sel[k] || sel.filter(Boolean).length !== 1) f.push(`D8 tablist #${li}: clicking tab ${k} selected [${sel.map((x, i) => x ? i : null).filter((x) => x !== null)}]`);
      } catch (e) { f.push(`D8 tablist #${li}: tab ${k} not clickable (${e.message.slice(0, 80)})`); }
    }
  }
  const film = await p.evaluate(() => [...document.querySelectorAll("video")].map((v) => v.currentSrc.split("/").pop()).filter(Boolean).join(","));
  const shot = path.join(out, `${route === "/" ? "home" : route.replace(/\//g, "_").replace(/^_/, "")}-${dev}.png`.replace(/@/g, "_"));
  await p.screenshot({ path: shot }).catch(() => {});
  // D9 route change from the bottom of the page must land at the top (client-side navigation)
  if (!/reduced/.test(dev)) {
    const target = await p.evaluate((route) => { const a = [...document.querySelectorAll("footer a[href^='/'], a[href^='/']")].find((x) => { const h = x.getAttribute("href"); return h && h !== route && !h.startsWith("/#") && !/\.(pdf|png|jpg|webp|mp4)$/.test(h); }); return a ? a.getAttribute("href") : null; }, route);
    if (target) {
      await p.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight)); await p.waitForTimeout(600);
      await p.evaluate((h) => { const a = [...document.querySelectorAll("a")].find((x) => x.getAttribute("href") === h); a?.click(); }, target);
      await p.waitForURL((u) => u.pathname === target.split("?")[0].split("#")[0], { timeout: 15000 }).catch(() => {});
      await p.waitForTimeout(1500);
      const y = await p.evaluate(() => Math.round(window.scrollY));
      if (y > 80) f.push(`D9 navigating ${route} -> ${target} landed at scrollY=${y} (should reset to top)`);
    }
  }
  const uniq = [...new Set(f)]; failures += uniq.length;
  report.results.push({ route, device: dev, pass: !uniq.length, media: film, failures: uniq, screenshot: shot });
  console.log(`${uniq.length ? "FAIL" : "PASS"} ${route} @ ${dev}${film ? ` [${film}]` : ""}${uniq.map((x) => "\n   - " + x).join("")}`);
  await ctx.close();
};
// devices of one route run concurrently (separate contexts); routes run in sequence
for (const route of routes) await Promise.all(pick.map((dev) => runOne(route, dev)));
await browser.close();
report.verdict = failures ? (override ? "FAIL_OVERRIDDEN" : "FAIL") : "PASS";
if (failures && override) report.override = { by: os.userInfo().username, reason: override };
fs.writeFileSync(path.join(out, "device-matrix.json"), JSON.stringify(report, null, 1));
console.log(`device-matrix: ${report.verdict} — ${report.results.filter((r) => r.pass).length}/${report.results.length} passed · report ${path.join(out, "device-matrix.json")}`);
if (failures && override) console.log(`OVERRIDDEN by ${report.override.by} — reason: ${override}`);
if (failures && !override) console.log(`Override only with explicit permission: --override "<reason>" / QA_OVERRIDE`);
process.exit(failures && !override ? 1 : 0);

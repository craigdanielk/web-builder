// Tests for the measurements the in-page PROBE used to compute and throw away
// (Task C2). Each test names the downstream check it unblocks.
//
// The probe only means anything against a real layout engine — jsdom returns a
// zero-sized getBoundingClientRect for everything and has no canvas, which is
// exactly what the probe's colour parser needs. So these run the real PROBE in
// real headless Chromium against hand-written fixtures, via page.setContent().
//
//   node --test scripts/quality/render-audit.facts.test.js
const { test, before, after } = require('node:test');
const assert = require('node:assert');
const { chromium } = require('playwright');
const { PROBE, toDefects, countedSections } = require('./render-audit');

// 1x1 red PNG. Natural size 1x1, rendered at 200x100 in the fixture — so
// rendered-vs-natural aspect distortion is measurable if rw/rh are recorded.
const PIXEL =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';

const PAGE = `
<main>
  <section id="hero" style="height:300px;background:#ffffff">
    <h1 style="color:#111111">Cape Crypto hero heading renders here</h1>
    <p style="color:#8a8a8a;background:#909090">Low contrast paragraph copy</p>
    <img src="${PIXEL}" alt="tile" style="width:200px;height:100px;object-fit:cover">
  </section>
  <section id="empty" style="height:120px;background:#ffffff"></section>
  <div id="tiny" style="height:10px;background:#ffffff">x</div>
  <section id="bgsec" style="height:150px;background-image:url(https://example.com/x.png)">
    <span style="color:#111111">Background section carries its own copy</span>
  </section>
</main>`;

// A section narrower than its content, clipped — el.scrollWidth > el.clientWidth.
// The page itself also overflows: the second section is wider than the viewport.
const OVERFLOW_PAGE = `
<main>
  <section id="clipped" style="width:400px;height:120px;overflow:hidden;background:#fff">
    <div style="width:1200px;height:60px;background:#eee">clipped wide child content</div>
  </section>
  <section id="wide" style="width:2000px;height:120px;background:#fff">wider than the viewport</section>
</main>`;

let browser, context;

before(async () => {
  browser = await chromium.launch({ headless: true });
  context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
});
after(async () => { if (browser) await browser.close(); });

async function probe(html) {
  const page = await context.newPage();
  await page.setContent(html, { waitUntil: 'load' });
  const facts = await page.evaluate(PROBE);
  await page.close();
  return facts;
}

const HEX = /^#[0-9a-f]{6}$/i;

// ── 1. Aspect distortion: rendered box + objectFit alongside natural size ──
test('images carry rendered box and objectFit alongside natural size', async () => {
  const f = await probe(PAGE);
  const img = f.images.find((i) => i.kind === 'img');
  assert.ok(img, 'no <img> recorded');
  assert.equal(typeof img.w, 'number', 'natural width missing');
  assert.equal(typeof img.h, 'number', 'natural height missing');
  assert.equal(img.rw, 200, 'rendered width not recorded');
  assert.equal(img.rh, 100, 'rendered height not recorded');
  // object-cover is cropped by intent — without this, every cover image reads
  // as aspect-distorted.
  assert.equal(img.objectFit, 'cover', 'objectFit not recorded');
});

// ── 2. Contrast remediation: fg/bg as hex + element identity ──
test('lowContrast entries carry fg/bg as hex and an element identity', async () => {
  const f = await probe(PAGE);
  assert.ok(f.lowContrast.length > 0, 'fixture produced no contrast failure');
  const lc = f.lowContrast[0];
  // hex, NOT the probe's native {rgb:[r,g,b],a} and not rgb(...) —
  // render-fix-contrast.js:26-30 parses only #rgb / #rrggbb.
  assert.match(lc.fg, HEX, `fg not hex: ${JSON.stringify(lc.fg)}`);
  assert.match(lc.bg, HEX, `bg not hex: ${JSON.stringify(lc.bg)}`);
  assert.ok(lc.selector, 'no selector — a failure cannot be traced to a source file');
  assert.equal(lc.tag, 'p');
  assert.equal(typeof lc.fontSize, 'number');
  assert.equal(typeof lc.fontWeight, 'number');
});

// ── 3. A failure count needs a denominator ──
test('contrast reports passes as well as failures', async () => {
  const f = await probe(PAGE);
  assert.ok(Array.isArray(f.contrast), 'facts.contrast missing');
  assert.ok(f.contrast.some((c) => c.pass === true), 'no passing measurement recorded');
  assert.ok(f.contrast.some((c) => c.pass === false), 'no failing measurement recorded');
  assert.ok(f.contrastSummary, 'facts.contrastSummary missing');
  assert.equal(f.contrastSummary.measured, f.contrast.length);
  assert.equal(f.contrastSummary.failed, f.lowContrast.length);
  assert.ok(f.contrastSummary.measured > f.contrastSummary.failed, 'no denominator');
  for (const c of f.contrast) assert.match(c.fg, HEX, 'contrast entry fg not hex');
});

// ── 4. Empty section + cross-route duplication ──
test('sections carry imgCount, hasBg and a text fingerprint', async () => {
  const f = await probe(PAGE);
  const byId = (id) => f.sections.find((s) => s.id === id);

  const hero = byId('hero');
  assert.ok(hero, 'hero section not recorded');
  assert.equal(hero.imgCount, 1, 'per-section image count missing');
  assert.equal(hero.hasBg, false);

  const empty = byId('empty');
  assert.equal(empty.imgCount, 0);
  assert.equal(empty.hasBg, false);
  assert.equal(empty.textLen, 0);

  const bgsec = byId('bgsec');
  assert.equal(bgsec.hasBg, true, 'CSS background-image not attributed to its section');

  // Fingerprint: two sections with identical text length must be
  // distinguishable, and identical text must fingerprint identically.
  assert.ok(hero.textFp, 'no text fingerprint');
  assert.notEqual(hero.textFp, bgsec.textFp);
  const again = await probe(PAGE);
  assert.equal(again.sections.find((s) => s.id === 'hero').textFp, hero.textFp, 'fingerprint not stable');
});

// ── 5. Horizontal overflow — not measurable at all before this ──
test('page and sections carry scrollWidth vs clientWidth', async () => {
  const f = await probe(OVERFLOW_PAGE);
  assert.ok(f.page, 'facts.page missing');
  assert.equal(typeof f.page.scrollWidth, 'number');
  assert.equal(typeof f.page.clientWidth, 'number');
  assert.equal(typeof f.page.innerWidth, 'number');
  assert.equal(f.page.overflowX, true, 'page horizontal overflow not detected');

  const clipped = f.sections.find((s) => s.id === 'clipped');
  assert.ok(clipped, 'clipped section not recorded');
  assert.equal(clipped.scrollWidth, 1200);
  assert.equal(clipped.clientWidth, 400);
  assert.equal(clipped.overflowX, true);

  const clean = await probe(PAGE);
  assert.equal(clean.page.overflowX, false, 'false overflow on a clean page');
  assert.equal(clean.sections.find((s) => s.id === 'hero').overflowX, false);
});

// ── 6. Zero-dimension sections: recorded, not dropped ──
test('sub-threshold blocks are recorded with belowThreshold instead of dropped', async () => {
  const f = await probe(PAGE);
  const tiny = f.sections.find((s) => s.id === 'tiny');
  assert.ok(tiny, 'a 10px block was dropped before it could be recorded');
  assert.equal(tiny.belowThreshold, true);
  assert.equal(tiny.h, 10);
  for (const s of f.sections.filter((x) => x.id !== 'tiny')) assert.equal(s.belowThreshold, false);
});

// Regression for the filter that :134 existed to provide: wrapper noise is now
// recorded, but it must still not reach the defect list or the summary counts.
test('recording wrapper noise does not leak it into defects or counts', async () => {
  const f = await probe(PAGE);
  const res = { route: '/', url: 'http://x/', httpStatus: 200, facts: f, consoleErrors: [], badRequests: [] };
  const defects = toDefects(res, ['/']);
  const evidence = defects.map((d) => `${d.finding} ${d.evidence}`).join(' ');
  assert.ok(!/tiny/.test(evidence), 'sub-threshold wrapper reached the defect list');
  assert.ok(!defects.some((d) => d.category === 'render_visibility' && /invisible/.test(d.finding)),
    'sub-threshold wrapper produced a visibility defect');
  // The counts orchestrate.py reads must be unchanged by the new records.
  assert.equal(countedSections(f).length, f.sections.length - 1, 'belowThreshold block counted as a section');
  assert.ok(countedSections(f).every((s) => !s.belowThreshold));
});

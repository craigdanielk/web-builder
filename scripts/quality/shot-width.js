// Full-page screenshot at an arbitrary viewport width.
//
// shot-live.js captures at a fixed 1440 viewport, which cannot answer "does the
// mobile breakpoint hold?". This is the same capture procedure — scroll the page
// to trigger lazy content, then neutralise scroll-reveal so nothing is captured
// mid-fade — with width and height as arguments.
//
// Usage: node shot-width.js <url> <out.png> [width=1440] [height=900]
// Exit 0 on a written file, 2 on any failure (the caller records NOT_MEASURED).
const { chromium } = require('playwright');
const { describe } = require('./lib/capability');

/** What this instrument is, in its own words. Compiled into the capability
 *  register by `scripts/capability_register.py`. */
const CAPABILITY = {
  id: 'aurelix.probe.shot-width',
  name: 'Full-page screenshot of a served URL at an arbitrary viewport width',
  kind: 'probe',
  invocation: 'node scripts/quality/shot-width.js <url> <out.png> [width=1440] [height=900]',
  preconditions: [
    'playwright chromium installed',
    'an http(s) URL that is already being served — a local build needs npm run start first',
    'the parent directory of <out.png> exists — it is not created',
  ],
  inputs: ['a served URL', 'an optional viewport width and height'],
  outputs: ['<out.png> — one full-page PNG at the requested width'],
  outcome: 'what a route looks like end-to-end at a chosen breakpoint, with mobile flags set below 600px so a UA-sniffing site serves its phone layout',
  exit_contract: {
    0: 'the PNG was written (see cannot_see — this includes a page that failed to load)',
    2: 'the browser launch, the in-page evaluate, the screenshot, or the close threw. The caller records NOT_MEASURED',
    64: 'usage error — <url> or <out.png> missing',
  },
  measures: [
    'the hydrated, scrolled-through, reveal-completed rendering of one route at ONE chosen width, full page height',
    'the mobile-vs-desktop layout fork, by setting isMobile and hasTouch below 600px width',
  ],
  cannot_see: [
    'ANY failure to load: the goto() rejection is swallowed by .catch(()=>{}), so a 404, a 500 or a refused connection is screenshotted and exits 0 — a written PNG is not evidence the route rendered',
    'more than the ONE width it was given per run — answering "does the responsive range hold" needs several invocations and something to compare them',
    'the difference between server-rendered and client-inserted content: it captures the hydrated DOM',
    'anything behind an interaction — a hamburger menu that only exists when opened is invisible to it, which is precisely the failure mode a narrow capture is usually run to find',
    'reveal machinery other than GSAP/ScrollTrigger and the `.rv` class',
    'anything about the image it wrote: it renders NO verdict. Horizontal overflow, a clipped table or a broken grid are visible in the PNG and asserted by nothing here',
  ],
  reachable_from: [],
  cost: 'one browser launch, a full scroll pass and ~5.3s of fixed waits — roughly 15-45s per width',
};

(async () => {
  if (describe(CAPABILITY)) return;
  const url = process.argv[2];
  const out = process.argv[3];
  const width = parseInt(process.argv[4] || '1440', 10);
  const height = parseInt(process.argv[5] || '900', 10);
  if (!url || !out) {
    console.error('usage: node shot-width.js <url> <out.png> [width] [height]');
    process.exit(64);
  }
  const b = await chromium.launch();
  const ctx = await b.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    // A 390-wide desktop UA renders desktop nav on sites that sniff the UA;
    // mobile flags make the narrow capture represent what a phone actually gets.
    isMobile: width < 600,
    hasTouch: width < 600,
  });
  const p = await ctx.newPage();
  await p.goto(url, { waitUntil: 'networkidle', timeout: 90000 }).catch(() => {});
  await p.waitForTimeout(2000);
  await p.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 600) {
      scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 160));
    }
    scrollTo(0, 0);
  });
  await p.waitForTimeout(2500);
  // Kill the reveal machinery, then force the reveal end-state. Without this a
  // full-page shot catches below-fold sections at opacity 0.
  await p.evaluate(() => {
    try {
      if (window.ScrollTrigger) window.ScrollTrigger.getAll().forEach((t) => t.kill());
      if (window.gsap) window.gsap.set('.rv', { opacity: 1, y: 0 });
    } catch (e) {}
    document.querySelectorAll('.rv').forEach((e) => {
      e.style.opacity = 1;
      e.style.transform = 'none';
    });
  });
  await p.waitForTimeout(800);
  await p.screenshot({ path: out, fullPage: true });
  console.log(`shot ok ${width}w -> ${out}`);
  await b.close();
})().catch((e) => {
  console.error(e.message);
  process.exit(2);
});

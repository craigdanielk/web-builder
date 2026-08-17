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
(async () => {
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

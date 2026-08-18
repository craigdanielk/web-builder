const { chromium } = require('playwright');
const { describe } = require('./lib/capability');

/** What this instrument is, in its own words. Compiled into the capability
 *  register by `scripts/capability_register.py`. */
const CAPABILITY = {
  id: 'aurelix.probe.shot-aa',
  name: 'Full-page screenshot of a local HTML FILE, reveal-state neutralised',
  kind: 'probe',
  invocation: 'node scripts/quality/shot-aa.js <path-to-local.html> <out.png>',
  preconditions: [
    'playwright chromium installed',
    'the FIRST argument is a filesystem path, not a URL — the script prefixes it with file:// itself, so passing an http(s) URL produces file://https://… and captures nothing useful',
    'a single self-contained HTML file: file:// gives it no dev server, so a Next.js route cannot be shot this way',
    'the parent directory of <out.png> exists — it is not created',
  ],
  inputs: ['a local HTML file path'],
  outputs: ['<out.png> — one full-page PNG at 1440x900, deviceScaleFactor 1'],
  outcome: 'a stitched full-page image of a local HTML file with GSAP/ScrollTrigger reveal state forced to its end position, so nothing is captured mid-fade',
  exit_contract: {
    0: 'the PNG was written (see cannot_see — this includes a page that failed to load)',
    2: 'the browser launch, the screenshot, or the close threw',
  },
  measures: [
    'the hydrated, reveal-completed rendering of one document at one viewport width (1440), full page height',
  ],
  cannot_see: [
    'ANY failure to load: the goto() rejection is swallowed by .catch(()=>{}), so a missing file, a broken path or a blank document is screenshotted and exits 0 — a written PNG is not evidence the page rendered',
    'more than one viewport — 1440x900 is hardcoded; it cannot answer whether the mobile breakpoint holds (that is shot-width.js)',
    'the difference between server-rendered and client-inserted content: it captures the hydrated DOM after 2.5s, so JS-injected markup is indistinguishable from HTML that shipped',
    'anything behind an interaction — no click, hover, focus or menu-open state is exercised',
    'lazy content that needs scrolling: unlike shot-live.js and shot-width.js it never scrolls, so an IntersectionObserver-loaded image below the fold is captured empty',
    'reveal machinery other than GSAP/ScrollTrigger and the `.rv` class — a Framer Motion or CSS-only reveal is not neutralised and can be caught mid-animation',
    'anything about the image it wrote: it renders NO verdict, compares nothing, and asserts no dimension, colour or overflow property',
  ],
  reachable_from: [],
  cost: 'one browser launch plus ~3s of fixed waits — roughly 5-15s',
};

(async () => {
  if (describe(CAPABILITY)) return;
  const file = 'file://' + process.argv[2], out = process.argv[3];
  const b = await chromium.launch();
  const p = await (await b.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1})).newPage();
  await p.goto(file, {waitUntil:'networkidle', timeout:60000}).catch(()=>{});
  await p.waitForTimeout(2500);
  // kill scroll-reveal state so the stitched full-page shot is true
  await p.evaluate(()=>{ try{ if(window.ScrollTrigger){ScrollTrigger.getAll().forEach(t=>t.kill());} if(window.gsap){gsap.set('.rv',{clearProps:'all',opacity:1,y:0});} }catch(e){} document.querySelectorAll('.rv').forEach(e=>{e.style.opacity=1;e.style.transform='none';}); });
  await p.waitForTimeout(500);
  await p.screenshot({path:out, fullPage:true});
  console.log('SHOT '+out); await b.close();
})().catch(e=>{console.error('FAIL',e.message);process.exit(2)});

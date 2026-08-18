const { chromium } = require('playwright');
const { describe } = require('./lib/capability');

/** What this instrument is, in its own words. Compiled into the capability
 *  register by `scripts/capability_register.py`. */
const CAPABILITY = {
  id: 'aurelix.probe.shot-live',
  name: 'Full-page screenshot of a served URL at 1440, scrolled and reveal-neutralised',
  kind: 'probe',
  invocation: 'node scripts/quality/shot-live.js <url> <out.png>',
  preconditions: [
    'playwright chromium installed',
    'the FIRST argument is an http(s) URL — unlike shot-aa/shot-hero it is passed to goto() verbatim, so a local build must already be served (e.g. npm run start in output/<project>/site)',
    'the parent directory of <out.png> exists — it is not created',
  ],
  inputs: ['a served URL'],
  outputs: ['<out.png> — one full-page PNG at 1440x900, deviceScaleFactor 1'],
  outcome: 'a stitched full-page image of a served page after the whole document has been scrolled through and reveal state forced to its end position',
  exit_contract: {
    0: 'the PNG was written (see cannot_see — this includes a page that failed to load)',
    2: 'the browser launch, the in-page evaluate, the screenshot, or the close threw',
  },
  measures: [
    'the hydrated, scrolled-through, reveal-completed rendering of one route at 1440 wide, full page height',
    'lazy content triggered by the 600px-step scroll pass',
  ],
  cannot_see: [
    'ANY failure to load: the goto() rejection is swallowed by .catch(()=>{}), so a 404, a 500, a connection refusal or a stale dev server is screenshotted and exits 0 — a written PNG is not evidence the route rendered',
    'more than one viewport — 1440x900 is hardcoded, which is exactly the gap shot-width.js exists to fill',
    'the difference between server-rendered and client-inserted content: it captures the hydrated DOM, so an empty SSR payload filled in by JS is indistinguishable from correct server rendering',
    'anything behind an interaction — no click, hover, focus, menu-open or form state is exercised',
    'reveal machinery other than GSAP/ScrollTrigger and the `.rv` class; a Framer Motion or CSS-only reveal can still be caught mid-animation',
    'one route: it shoots the URL it was given and follows no link',
    'anything about the image it wrote: it renders NO verdict, compares nothing against a benchmark, and asserts no dimension, colour or overflow property. A human or a separate gate must look at the PNG',
  ],
  reachable_from: [],
  cost: 'one browser launch, a full scroll pass and ~5.3s of fixed waits — roughly 15-45s depending on page length',
};

(async () => {
  if (describe(CAPABILITY)) return;
  const url = process.argv[2], out = process.argv[3];
  const b = await chromium.launch();
  const p = await (await b.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1})).newPage();
  await p.goto(url, {waitUntil:'networkidle', timeout:90000}).catch(()=>{});
  await p.waitForTimeout(2000);
  await p.evaluate(async()=>{for(let y=0;y<document.body.scrollHeight;y+=600){scrollTo(0,y);await new Promise(r=>setTimeout(r,160));}scrollTo(0,0);});
  await p.waitForTimeout(2500);
  await p.evaluate(()=>{try{if(window.ScrollTrigger)ScrollTrigger.getAll().forEach(t=>t.kill());if(window.gsap)gsap.set('.rv',{opacity:1,y:0});}catch(e){}document.querySelectorAll('.rv').forEach(e=>{e.style.opacity=1;e.style.transform='none';});});
  await p.waitForTimeout(800);
  await p.screenshot({path:out, fullPage:true});
  console.log('LIVE shot ok'); await b.close();
})().catch(e=>{console.error(e.message);process.exit(2)});

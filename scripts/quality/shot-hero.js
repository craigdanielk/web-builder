const { chromium } = require('playwright');
const { describe } = require('./lib/capability');

/** What this instrument is, in its own words. Compiled into the capability
 *  register by `scripts/capability_register.py`. */
const CAPABILITY = {
  id: 'aurelix.probe.shot-hero',
  name: 'Above-the-fold screenshot of a local HTML FILE',
  kind: 'probe',
  invocation: 'node scripts/quality/shot-hero.js <path-to-local.html> <out.png>',
  preconditions: [
    'playwright chromium installed',
    'the FIRST argument is a filesystem path, not a URL — the script prefixes it with file:// itself',
    'a single self-contained HTML file: file:// gives it no dev server',
    'the parent directory of <out.png> exists — it is not created',
  ],
  inputs: ['a local HTML file path'],
  outputs: ['<out.png> — one viewport-sized PNG, 1440x860, NOT full page'],
  outcome: 'what the first screenful of a local HTML file looks like 3 seconds after load',
  exit_contract: {
    0: 'the PNG was written (see cannot_see — this includes a page that failed to load)',
    2: 'the browser launch, the screenshot, or the close threw',
  },
  measures: ['the hydrated rendering of the top 860px of one document at 1440 wide'],
  cannot_see: [
    'ANY failure to load: the goto() rejection is swallowed by .catch(()=>{}), so a missing file or a blank document is screenshotted and exits 0',
    'ANYTHING BELOW 860px — this is the only one of the shot-* family that does not pass fullPage, by design; the rest of the page does not exist to it',
    'more than one viewport — 1440x860 is hardcoded',
    'the difference between server-rendered and client-inserted content: it captures the hydrated DOM after a flat 3s wait',
    'reveal state: unlike shot-aa/shot-live/shot-width it does NOT neutralise GSAP/ScrollTrigger or `.rv`, so an element still fading in is captured mid-animation and reads as a missing or faint element',
    'anything behind an interaction — no click, hover, focus or menu-open state',
    'anything about the image it wrote: it renders no verdict and asserts nothing',
  ],
  reachable_from: [],
  cost: 'one browser launch plus a flat 3s wait — roughly 5-12s',
};

(async () => {
  if (describe(CAPABILITY)) return;
  const b = await chromium.launch();
  const p = await (await b.newContext({viewport:{width:1440,height:860}})).newPage();
  await p.goto('file://'+process.argv[2], {waitUntil:'networkidle',timeout:60000}).catch(()=>{});
  await p.waitForTimeout(3000);
  await p.screenshot({path:process.argv[3]});
  console.log('HERO ok'); await b.close();
})().catch(e=>{console.error(e.message);process.exit(2)});

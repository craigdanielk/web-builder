#!/usr/bin/env node

/**
 * Animation Detection Test Script
 * Runs the full animation detection pipeline against test URLs
 * and validates the intensity scoring.
 *
 * Usage:
 *   node test-animation-detector.js [url1] [url2] [url3]
 *
 * Defaults to 3 representative sites if no URLs provided.
 */

'use strict';

const { chromium } = require('playwright');
const {
  getPreNavigationScript,
  setupNetworkInterception,
  getMutationObserverScript,
  extractAnimationData,
  analyzeAnimationEvidence,
} = require('./lib/animation-detector');

const { describe } = require('./lib/capability');

/** What this instrument is, in its own words. Compiled into the capability
 *  register by `scripts/capability_register.py`.
 *
 *  NOT A TEST, despite the filename. It asserts nothing and has no expected
 *  values: the "Expect: moderate" comments beside its default URLs are prose,
 *  never compared to `analysis.intensity.level`. It drives the detector against
 *  live sites and prints what it saw, which is a PROBE. Declaring it a test
 *  would put a green tick beside a run that cannot fail. */
const CAPABILITY = {
  id: 'aurelix.probe.animation-detection',
  name: 'Animation-detection probe over live URLs',
  kind: 'probe',
  invocation: 'node scripts/quality/test-animation-detector.js [url ...]',
  preconditions: [
    'playwright chromium installed (`npx playwright install chromium`) — nothing checks it, ' +
      'and its absence is printed per-URL and then exited 0',
    'outbound network access to every URL given; defaults to example.com, stripe.com, linear.app',
  ],
  inputs: ['URLs on argv, or three hardcoded default sites', 'scripts/quality/lib/animation-detector.js'],
  outputs: [],
  outcome:
    'what motion a live site actually ships: detected libraries and how they were detected, ' +
    '@keyframes count, animated/transition element counts, scroll triggers and IntersectionObservers, ' +
    'Lottie/Rive/3D asset requests, and the intensity level + score + confidence the scorer derives',
  exit_contract: {
    0: 'the run completed — INCLUDING when every URL errored. Per-URL failures are caught, ' +
       'printed as "ERROR:" and reported as success:false in a table; the process still exits 0',
    1: 'main() itself rejected (a fault outside the per-URL try, e.g. the summary formatter)',
  },
  measures: [
    'runtime animation evidence from a real browser: injected pre-navigation hooks, network ' +
      'interception, a MutationObserver, and a full-page scroll that triggers lazy reveals',
    'the intensity scorer end to end, on input no fixture can produce',
  ],
  cannot_see: [
    'whether the intensity it reports is RIGHT. There is no expected value and no assertion — ' +
      'stripe.com scoring "none" and scoring "expressive" produce the same exit code',
    'section-level attribution: it passes [] for sections and [] for the DOM to ' +
      'analyzeAnimationEvidence, so every per-section field is empty by construction, not by measurement',
    'motion that needs interaction — hover, click, focus, form state, carousels on a timer past ' +
      'the fixed 1.5s-per-viewport scroll settle. It scrolls and waits, nothing more',
    'anything about an Aurelix build: it reads live third-party sites and no output/ directory, ' +
      'so it can never tell you what the pipeline emitted',
    'that it ran at all in CI or the chain — reachable_from is [], measured repo-wide',
  ],
  reachable_from: [],
  cost:
    'a chromium launch and a full scroll per URL: ~30-60s each on the three defaults, ' +
    'plus network. No credentials, no spend',
};

const VIEWPORT = { width: 1440, height: 900 };
const SCROLL_SETTLE_MS = 1500;
const POST_LOAD_DELAY_MS = 3000;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function testUrl(url) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`  Testing: ${url}`);
  console.log(`${'='.repeat(70)}\n`);

  let browser = null;
  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
      viewport: VIEWPORT,
      deviceScaleFactor: 1,
      userAgent:
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ' +
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    });
    const page = await context.newPage();

    // Step 1: Pre-navigation hooks
    console.log('  [1/6] Injecting pre-navigation script...');
    await page.addInitScript(getPreNavigationScript());

    console.log('  [2/6] Setting up network interception...');
    const getNetworkResults = await setupNetworkInterception(page);

    // Step 2: Navigate
    console.log('  [3/6] Navigating to URL...');
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60_000 });
    await sleep(POST_LOAD_DELAY_MS);

    // Step 3: Mutation observer
    console.log('  [4/6] Injecting mutation observer...');
    await page.evaluate(getMutationObserverScript());

    // Step 4: Scroll the page to trigger lazy animations
    console.log('  [5/6] Scrolling page to trigger animations...');
    const pageHeight = await page.evaluate(() => document.body.scrollHeight);
    const totalSteps = Math.ceil(pageHeight / VIEWPORT.height);

    for (let step = 0; step < totalSteps; step++) {
      const scrollY = step * VIEWPORT.height;
      await page.evaluate((y) => window.scrollTo(0, y), scrollY);
      await sleep(SCROLL_SETTLE_MS);
    }

    // Scroll back to top
    await page.evaluate(() => window.scrollTo(0, 0));
    await sleep(500);

    // Step 5: Extract animation data
    console.log('  [6/6] Extracting animation data...');
    const evidence = await extractAnimationData(page);
    const networkResults = getNetworkResults();

    // Step 6: Analyze (with empty sections/DOM since this is a standalone test)
    const analysis = analyzeAnimationEvidence(evidence, networkResults, [], []);

    // Print results
    console.log('\n  --- RAW EVIDENCE ---');
    console.log(`  Libraries detected: ${evidence.libraries.length}`);
    for (const lib of evidence.libraries) {
      console.log(`    - ${lib.name} (via ${lib.detectedVia}, confidence: ${lib.confidence})`);
    }
    console.log(`  CSS keyframes: ${evidence.cssKeyframes.length}`);
    for (const kf of evidence.cssKeyframes.slice(0, 10)) {
      console.log(`    - @keyframes ${kf.name}`);
    }
    if (evidence.cssKeyframes.length > 10) {
      console.log(`    ... and ${evidence.cssKeyframes.length - 10} more`);
    }
    console.log(`  Animated elements: ${evidence.animatedElementCount}`);
    console.log(`  Transition elements: ${evidence.transitionElementCount}`);
    console.log(`  Scroll attributes: AOS=${evidence.scrollAttributes.aos}, ` +
      `data-scroll=${evidence.scrollAttributes.scroll}, parallax=${evidence.scrollAttributes.parallax}`);
    console.log(`  IntersectionObservers: ${evidence.intersectionObservers.length}`);
    console.log(`  Scroll mutations: ${evidence.scrollMutations.classChanges.length} class changes, ` +
      `${evidence.scrollMutations.styleChanges} style changes`);
    console.log(`  Script patterns: ${evidence.scriptPatterns.length}`);
    for (const sp of evidence.scriptPatterns) {
      console.log(`    - ${sp.library}: ${sp.src.slice(0, 80)}`);
    }

    console.log('\n  --- NETWORK RESULTS ---');
    console.log(`  Lottie files: ${networkResults.lottieFiles.length}`);
    console.log(`  Rive files: ${networkResults.riveFiles.length}`);
    console.log(`  3D files: ${networkResults.threeDFiles.length}`);
    console.log(`  CSS files: ${networkResults.cssFiles.length}`);

    console.log('\n  --- ANALYSIS ---');
    console.log(`  Intensity: ${analysis.intensity.level} (score: ${analysis.intensity.score}, confidence: ${analysis.intensity.confidence})`);
    console.log(`  Engine: ${analysis.engine}`);
    console.log(`  Libraries: ${analysis.libraries.map(l => l.name).join(', ') || 'none'}`);
    console.log(`  CSS animations: ${analysis.cssAnimations.keyframes.length} keyframes, ` +
      `${analysis.cssAnimations.animatedElements} animated, ${analysis.cssAnimations.transitionElements} transitions`);
    console.log(`  Scroll animations: ${analysis.scrollAnimations.triggerCount} triggers, ` +
      `${analysis.scrollAnimations.observerCount} observers`);
    console.log(`  Assets: ${analysis.assets.lottie.length} Lottie, ` +
      `${analysis.assets.rive.length} Rive, ${analysis.assets.threeD.length} 3D`);

    return {
      url,
      intensity: analysis.intensity,
      engine: analysis.engine,
      libraryCount: analysis.libraries.length,
      libraries: analysis.libraries.map(l => l.name),
      success: true,
    };
  } catch (err) {
    console.error(`  ERROR: ${err.message}`);
    return { url, error: err.message, success: false };
  } finally {
    if (browser) await browser.close();
  }
}

async function main() {
  if (describe(CAPABILITY)) return 0;
  const args = process.argv.slice(2);
  const urls = args.length > 0
    ? args
    : [
        'https://example.com',      // Expect: none/subtle
        'https://stripe.com',       // Expect: moderate
        'https://linear.app',       // Expect: moderate/expressive
      ];

  console.log('\n  ANIMATION DETECTION TEST');
  console.log(`  Testing ${urls.length} URL(s)\n`);

  const results = [];
  for (const url of urls) {
    const result = await testUrl(url);
    results.push(result);
  }

  // Summary table
  console.log(`\n${'='.repeat(70)}`);
  console.log('  SUMMARY');
  console.log(`${'='.repeat(70)}`);
  console.log('  ' + 'URL'.padEnd(35) + 'Intensity'.padEnd(15) + 'Score'.padEnd(8) + 'Conf.'.padEnd(8) + 'Engine'.padEnd(15) + 'Libraries');
  console.log('  ' + '-'.repeat(65));

  for (const r of results) {
    if (r.success) {
      console.log(
        '  ' +
        r.url.replace(/^https?:\/\//, '').slice(0, 33).padEnd(35) +
        r.intensity.level.padEnd(15) +
        String(r.intensity.score).padEnd(8) +
        String(r.intensity.confidence).padEnd(8) +
        r.engine.padEnd(15) +
        r.libraries.join(', ')
      );
    } else {
      console.log('  ' + r.url.replace(/^https?:\/\//, '').slice(0, 33).padEnd(35) + 'ERROR: ' + r.error);
    }
  }

  console.log('');
}

main().catch((err) => {
  console.error('FATAL: ' + err.message);
  console.error(err.stack);
  process.exit(1);
});

/**
 * extract-reference.js
 *
 * Extracts visual and structural data from a live reference website.
 * Used by the web-builder quality pipeline to validate or enrich presets
 * against real-world implementations.
 *
 * Workflow:
 *   1. Launch headless Chromium via Playwright
 *   2. Navigate to URL, wait for full load + settle
 *   3. Scroll-capture the page in viewport-sized steps (triggers lazy content)
 *   4. Extract rendered DOM with 20 computed CSS properties per element
 *   5. Identify visual sections and crop per-section screenshots
 *   6. Extract text content with styling metadata
 *   7. Extract assets (images, fonts, backgrounds)
 *   8. Return a structured extraction object
 *
 * @module extract-reference
 */

'use strict';

const { chromium } = require('playwright');
const sharp = require('sharp');
const path = require('path');
const fs = require('fs');
const {
  getPreNavigationScript,
  setupNetworkInterception,
  getMutationObserverScript,
  extractAnimationData,
} = require('./animation-detector');
const { extractGsapFromBundles, mergeGsapData } = require('./gsap-extractor');

// ── Constants ────────────────────────────────────────────────────────────────

/** Viewport dimensions used for consistent capture */
const VIEWPORT = { width: 1440, height: 900 };

/** Maximum number of DOM elements to extract (prevents runaway on heavy pages) */
const MAX_DOM_ELEMENTS = 500;

/** Milliseconds to wait after each scroll step for lazy content to settle */
const SCROLL_SETTLE_MS = 1500;

/** Milliseconds to wait after initial page load before starting extraction */
const POST_LOAD_DELAY_MS = 3000;

/**
 * The 20 CSS properties captured per visible element.
 * These cover color, typography, layout, decorative, and transform dimensions.
 */
const CSS_PROPERTIES = [
  'color',
  'backgroundColor',
  'fontSize',
  'fontFamily',
  'fontWeight',
  'lineHeight',
  'padding',
  'margin',
  'width',
  'height',
  'display',
  'position',
  'borderRadius',
  'opacity',
  'transform',
  'boxShadow',
  'letterSpacing',
  'textTransform',
  'gap',
  'maxWidth',
  'animationName',
  'animationDuration',
  'animationTimingFunction',
  'transition',
];

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Pause execution for a given number of milliseconds.
 * @param {number} ms
 * @returns {Promise<void>}
 */
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Ensure a directory exists, creating it recursively if needed.
 * @param {string} dir - Absolute path to the directory.
 */
function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

// ── Cookie modal dismissal ───────────────────────────────────────
async function dismissCookieModals(page) {
  const selectors = [
    'button[id*="cookie" i][id*="accept" i]',
    'button[class*="cookie" i][class*="accept" i]',
    'button:has-text("Accept All")',
    'button:has-text("Accept all")',
    'button:has-text("Accept Cookies")',
    'button:has-text("Got it")',
    'button:has-text("I agree")',
    'button:has-text("OK")',
    '[data-testid*="cookie" i] button',
    '.cookie-banner button:first-of-type',
    '#onetrust-accept-btn-handler',
    '.cc-accept',
    '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
    '[aria-label*="cookie" i][aria-label*="accept" i]',
    '[aria-label*="consent" i]',
  ];

  for (const sel of selectors) {
    try {
      const btn = await page.$(sel);
      if (btn) {
        const visible = await btn.isVisible().catch(() => false);
        if (visible) {
          await btn.click();
          await page.waitForTimeout(800);
          console.log(`[extract] Dismissed cookie modal via: ${sel}`);
          return;
        }
      }
    } catch (_) {
      // Selector not found or click failed, try next
    }
  }
  console.log('[extract] No cookie modal detected');
}

// ── Pre-extraction scroll to trigger lazy content ───────────────
async function triggerLazyContent(page) {
  const viewportHeight = 900;
  let previousHeight = 0;
  let currentHeight = await page.evaluate(() => document.body.scrollHeight);
  let iterations = 0;
  const MAX_ITERATIONS = 30; // safety cap: 30 * 900px = 27000px max

  while (currentHeight > previousHeight && iterations < MAX_ITERATIONS) {
    previousHeight = currentHeight;
    // Scroll incrementally (one viewport at a time) to trigger lazy-load
    const scrollTarget = (iterations + 1) * viewportHeight;
    await page.evaluate((y) => window.scrollTo(0, y), scrollTarget);
    await page.waitForTimeout(800);
    currentHeight = await page.evaluate(() => document.body.scrollHeight);
    iterations++;
  }

  // Scroll back to top for consistent extraction
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);

  console.log(
    `[extract] Lazy content triggered: ${iterations} scroll passes, final height: ${currentHeight}px`
  );
}

// ── Core Extraction ──────────────────────────────────────────────────────────

/**
 * Extract visual and structural data from a reference website URL.
 *
 * @param {string} url - The fully-qualified URL to extract from.
 * @param {string} [outputDir] - Optional directory to persist screenshots.
 *   If omitted, screenshots are returned as in-memory Buffers only.
 * @returns {Promise<ExtractionResult>} Structured extraction data.
 *
 * @typedef {Object} ExtractionResult
 * @property {string} url - The source URL.
 * @property {string} timestamp - ISO-8601 extraction timestamp.
 * @property {{ width: number, height: number }} viewport - Viewport used.
 * @property {number} pageHeight - Total scrollable page height in px.
 * @property {Section[]} sections - Identified visual sections.
 * @property {DOMElement[]} renderedDOM - Extracted DOM elements with styles.
 * @property {TextContent[]} textContent - Text nodes with styling metadata.
 * @property {Assets} assets - Images, fonts, and background-images found.
 * @property {Screenshots} screenshots - Captured screenshot buffers/paths.
 */
async function extractReference(url, outputDir) {
  let browser = null;

  try {
    // ── 1. Launch browser ──────────────────────────────────────────────
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
      viewport: VIEWPORT,
      deviceScaleFactor: 1,
      // Spoof a standard desktop user-agent to avoid bot-blocking
      userAgent:
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ' +
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    });
    const page = await context.newPage();

    // ── Animation: pre-navigation hooks ────────────────────────────────
    await page.addInitScript(getPreNavigationScript());
    const getNetworkResults = await setupNetworkInterception(page);

    // ── 2. Navigate and wait for load ──────────────────────────────────
    console.log(`[extract] Navigating to ${url}`);
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 60_000 });
    } catch (e) {
      if (e.message.includes('Timeout')) {
        console.log(`[extract] networkidle timed out, falling back to domcontentloaded`);
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30_000 });
        await sleep(5000); // extra settle time for JS-heavy sites
      } else {
        throw e;
      }
    }
    await sleep(POST_LOAD_DELAY_MS);
    console.log(`[extract] Page loaded, settling for ${POST_LOAD_DELAY_MS}ms`);

    // ── Cookie modal dismissal ──────────────────────────────────────
    await dismissCookieModals(page);

    // ── Trigger lazy-loaded content ─────────────────────────────────
    await triggerLazyContent(page);

    // ── Animation: mutation observer for scroll-triggered changes ─────
    await page.evaluate(getMutationObserverScript());

    // ── 3. Measure page height ─────────────────────────────────────────
    const pageHeight = await page.evaluate(() => document.body.scrollHeight);
    console.log(`[extract] Page height: ${pageHeight}px`);

    // ── 4. Scroll-capture in viewport steps ────────────────────────────
    // Scrolling in steps ensures lazy-loaded images and sections are triggered.
    const scrollCaptures = [];
    const totalSteps = Math.ceil(pageHeight / VIEWPORT.height);

    for (let step = 0; step < totalSteps; step++) {
      const scrollY = step * VIEWPORT.height;
      await page.evaluate((y) => window.scrollTo(0, y), scrollY);
      await sleep(SCROLL_SETTLE_MS);

      const buffer = await page.screenshot({ type: 'png' });
      scrollCaptures.push({ scrollY, buffer });
      console.log(
        `[extract] Captured scroll step ${step + 1}/${totalSteps} at y=${scrollY}`
      );
    }

    // Scroll back to top for full-page screenshot
    await page.evaluate(() => window.scrollTo(0, 0));
    await sleep(SCROLL_SETTLE_MS);

    // ── 5. Full-page reference screenshot ──────────────────────────────
    const fullPageBuffer = await page.screenshot({
      type: 'png',
      fullPage: true,
    });
    console.log(`[extract] Full-page screenshot captured`);

    // ── 6. Extract rendered DOM ────────────────────────────────────────
    // Uses a TreeWalker to visit only visible elements, collects computed
    // styles for each. Limited to MAX_DOM_ELEMENTS to prevent blowup.
    const renderedDOM = await page.evaluate(
      ({ props, maxElements }) => {
        const results = [];

        /**
         * Check whether an element is visible (non-zero dimensions,
         * not hidden via display/visibility/opacity).
         */
        function isVisible(el) {
          const rect = el.getBoundingClientRect();
          if (rect.width === 0 && rect.height === 0) return false;
          const style = window.getComputedStyle(el);
          if (style.display === 'none') return false;
          if (style.visibility === 'hidden') return false;
          if (parseFloat(style.opacity) === 0) return false;
          return true;
        }

        // TreeWalker filters to ELEMENT_NODE only
        const walker = document.createTreeWalker(
          document.body,
          NodeFilter.SHOW_ELEMENT,
          {
            acceptNode(node) {
              if (results.length >= maxElements) return NodeFilter.FILTER_REJECT;
              if (!isVisible(node)) return NodeFilter.FILTER_SKIP;
              return NodeFilter.FILTER_ACCEPT;
            },
          }
        );

        let node = walker.nextNode();
        while (node && results.length < maxElements) {
          const rect = node.getBoundingClientRect();
          const computed = window.getComputedStyle(node);

          const styles = {};
          for (const prop of props) {
            styles[prop] = computed.getPropertyValue(
              // Convert camelCase to kebab-case for getPropertyValue
              prop.replace(/([A-Z])/g, '-$1').toLowerCase()
            );
          }

          results.push({
            tag: node.tagName.toLowerCase(),
            className: node.className?.toString?.()?.slice(0, 200) || '',
            id: node.id || '',
            rect: {
              x: Math.round(rect.x),
              y: Math.round(rect.y + window.scrollY), // absolute Y
              width: Math.round(rect.width),
              height: Math.round(rect.height),
            },
            styles,
          });

          node = walker.nextNode();
        }

        return results;
      },
      { props: CSS_PROPERTIES, maxElements: MAX_DOM_ELEMENTS }
    );

    console.log(`[extract] Extracted ${renderedDOM.length} DOM elements`);

    // ── 6b. Extract animation data ──────────────────────────────────
    console.log('[extract] Detecting animation patterns...');
    const rawAnimationEvidence = await extractAnimationData(page);
    const networkAnimationResults = getNetworkResults();
    console.log(
      `[extract] Animation: ${rawAnimationEvidence.libraries.length} libraries, ` +
        `${rawAnimationEvidence.cssKeyframes.length} keyframes, ` +
        `${rawAnimationEvidence.animatedElementCount} animated elements`
    );

    // ── 6c. GSAP static bundle analysis + merge ──────────────────────
    const jsFileUrls = networkAnimationResults.jsFiles || [];
    let mergedGsapCalls = rawAnimationEvidence.gsapCalls || [];
    if (jsFileUrls.length > 0) {
      console.log(`[extract] Analyzing ${jsFileUrls.length} JS bundles for GSAP calls...`);
      try {
        const staticResult = await extractGsapFromBundles(jsFileUrls);
        console.log(
          `[extract] Static GSAP analysis: ${staticResult.totalCalls} calls from ${staticResult.bundlesAnalyzed} bundles`
        );
        mergedGsapCalls = mergeGsapData(staticResult.calls, mergedGsapCalls);
        console.log(`[extract] Merged GSAP calls: ${mergedGsapCalls.length} total`);
      } catch (err) {
        console.warn(`[extract] GSAP static analysis failed: ${err.message}`);
      }
    }
    // Attach merged calls back to evidence for downstream consumption
    rawAnimationEvidence.gsapCalls = mergedGsapCalls;

    // ── 7. Identify visual sections ────────────────────────────────────
    // v2.0.2: Recursive section detection — descends into wrapper divs,
    // extracts content per-section using DOM scoping (not rect overlap).
    const sections = await page.evaluate(() => {
      const container = document.querySelector('main') || document.body;
      const sectionData = [];

      // Recursive: if a child is a wrapper (>80% of container height and
      // contains multiple tall children), descend into it instead.
      function collectSections(parent, pageHeight) {
        const children = Array.from(parent.children);
        for (const child of children) {
          const rect = child.getBoundingClientRect();
          const absoluteTop = rect.top + window.scrollY;
          const height = rect.height;

          // Skip tiny/invisible elements
          if (height < 50) continue;
          const style = window.getComputedStyle(child);
          if (style.display === 'none' || style.visibility === 'hidden') continue;

          // Detect wrapper: covers >80% of page AND has multiple visible children >50px
          const isWrapper = height > pageHeight * 0.8;
          if (isWrapper) {
            const tallChildren = Array.from(child.children).filter(c => {
              const cr = c.getBoundingClientRect();
              return cr.height > 50;
            });
            if (tallChildren.length > 1) {
              // Recurse into wrapper instead of treating it as a section
              collectSections(child, pageHeight);
              continue;
            }
          }

          const tag = child.tagName.toLowerCase();
          const id = child.id || '';
          const classNames = child.className?.toString?.() || '';
          const role = child.getAttribute('role') || '';

          // Infer label from heading inside (ANY tag, not just section/article)
          let label = '';
          if (tag === 'nav' || role === 'navigation') label = 'navigation';
          else if (tag === 'header') label = 'header';
          else if (tag === 'footer' || role === 'contentinfo') label = 'footer';
          else {
            const heading = child.querySelector('h1, h2, h3');
            label = heading ? heading.textContent.trim().slice(0, 60) : '';
          }

          // Per-section DOM-scoped content extraction (v2.0.2)
          const HEADING_TAGS = new Set(['H1', 'H2', 'H3', 'H4', 'H5', 'H6']);
          const INTERACTIVE_TAGS = new Set(['A', 'BUTTON']);
          const headings = [];
          const bodyText = [];
          const ctas = [];

          const textEls = child.querySelectorAll(
            'h1, h2, h3, h4, h5, h6, p, li, blockquote, figcaption, a, button'
          );
          const seen = new Set(); // deduplicate nested text
          textEls.forEach(el => {
            const text = el.textContent?.trim();
            if (!text || text.length < 2 || seen.has(text)) return;
            seen.add(text);
            const elRect = el.getBoundingClientRect();
            if (elRect.width === 0 && elRect.height === 0) return;

            if (HEADING_TAGS.has(el.tagName)) {
              headings.push(text.slice(0, 200));
            } else if (INTERACTIVE_TAGS.has(el.tagName)) {
              ctas.push({ text: text.slice(0, 100), href: el.href || null });
            } else {
              bodyText.push(text.slice(0, 300));
            }
          });

          // Per-section images
          const images = [];
          child.querySelectorAll('img').forEach(img => {
            const src = img.src || img.dataset?.src || '';
            if (!src || src.startsWith('data:image/gif')) return;
            images.push({
              src,
              alt: img.alt || '',
              width: img.naturalWidth || img.width,
              height: img.naturalHeight || img.height,
            });
          });

          // Per-section background images
          const bgImages = [];
          const bgEls = child.querySelectorAll('[style*="background"]');
          bgEls.forEach(el => {
            const bg = window.getComputedStyle(el).backgroundImage;
            if (bg && bg !== 'none' && bg.includes('url(')) {
              bgImages.push(bg.slice(0, 500));
            }
          });

          sectionData.push({
            index: sectionData.length,
            tag,
            id,
            classNames: classNames.slice(0, 200),
            role,
            label,
            rect: {
              x: Math.round(rect.x),
              y: Math.round(absoluteTop),
              width: Math.round(rect.width),
              height: Math.round(height),
            },
            // v2.0.2: Embedded content (DOM-scoped, not rect-based)
            content: {
              headings,
              body_text: bodyText.slice(0, 20), // cap for sanity
              ctas: ctas.slice(0, 10),
              image_count: images.length,
            },
            images,
            backgroundImages: bgImages,
          });
        }
      }

      const pageHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
      collectSections(container, pageHeight);
      return sectionData;
    });

    // v2.0.2: Post-filter — remove wrapper sections that slipped through recursion.
    // A wrapper is any section covering >70% of page height with zero meaningful content.
    const preFilterCount = sections.length;
    const pageHeightForFilter = pageHeight || 1;
    const filteredSections = sections.filter(sec => {
      const c = sec.content;
      const coverageRatio = sec.rect.height / pageHeightForFilter;
      const hasContent = c.headings.length > 0 || c.body_text.length > 0 || c.image_count > 0;
      if (coverageRatio > 0.7 && !hasContent) {
        console.log(`[extract]   Filtered out wrapper: section ${sec.index} (${sec.tag}, ${sec.rect.height}px, ${(coverageRatio * 100).toFixed(0)}% of page, 0 content)`);
        return false;
      }
      return true;
    });

    // Re-index after filtering
    filteredSections.forEach((sec, i) => { sec.index = i; });
    // Replace sections array
    sections.length = 0;
    sections.push(...filteredSections);

    console.log(`[extract] Identified ${sections.length} visual sections (${preFilterCount - sections.length} wrapper(s) filtered)`);
    for (const sec of sections) {
      const c = sec.content;
      console.log(
        `[extract]   Section ${sec.index}: ${sec.tag} (${sec.rect.height}px) — ` +
        `${c.headings.length}h, ${c.body_text.length}p, ${c.ctas.length}cta, ${c.image_count}img` +
        (sec.label ? ` — "${sec.label}"` : '')
      );
    }

    // ── 8. Assign sectionIndex to DOM elements ─────────────────────────
    // v2.0.2: Sort sections by height ascending (smallest first) so inner
    // sections match before outer wrappers. Fixes the wrapper-swallows-all bug.
    const sectionsBySize = [...sections].sort((a, b) => a.rect.height - b.rect.height);
    for (const el of renderedDOM) {
      el.sectionIndex = -1;
      const elMidY = el.rect.y + el.rect.height / 2;

      for (const sec of sectionsBySize) {
        if (elMidY >= sec.rect.y && elMidY <= sec.rect.y + sec.rect.height) {
          el.sectionIndex = sec.index;
          break;
        }
      }
    }

    // ── 9. Crop section screenshots from scroll captures ───────────────
    // Each section screenshot is assembled by finding the scroll capture(s)
    // that cover its vertical range, then cropping with sharp.
    const sectionScreenshots = {};

    for (const sec of sections) {
      try {
        const { y: secY, height: secHeight, width: secWidth } = sec.rect;

        // Find the scroll capture whose scrollY range covers the section start
        const capture = scrollCaptures.find(
          (sc) =>
            secY >= sc.scrollY && secY < sc.scrollY + VIEWPORT.height
        );

        if (!capture) {
          console.warn(
            `[extract] No scroll capture covers section ${sec.index} at y=${secY}`
          );
          continue;
        }

        // Calculate crop region within the capture buffer
        const localY = secY - capture.scrollY;
        const cropHeight = Math.min(
          secHeight,
          VIEWPORT.height - localY // don't exceed the capture boundary
        );

        if (cropHeight <= 0 || secWidth <= 0) continue;

        const cropped = await sharp(capture.buffer)
          .extract({
            left: 0,
            top: Math.max(0, Math.round(localY)),
            width: Math.min(secWidth, VIEWPORT.width),
            height: Math.round(cropHeight),
          })
          .png()
          .toBuffer();

        sectionScreenshots[sec.index] = cropped;

        // Persist to disk if outputDir provided
        if (outputDir) {
          const screenshotDir = path.join(outputDir, 'sections');
          ensureDir(screenshotDir);
          const filename = `section-${String(sec.index).padStart(2, '0')}.png`;
          fs.writeFileSync(path.join(screenshotDir, filename), cropped);
        }
      } catch (err) {
        console.warn(
          `[extract] Failed to crop section ${sec.index}: ${err.message}`
        );
      }
    }

    // ── 10. Extract text content with positions ────────────────────────
    const textContent = await page.evaluate(() => {
      const items = [];
      const HEADING_TAGS = new Set(['H1', 'H2', 'H3', 'H4', 'H5', 'H6']);
      const INTERACTIVE_TAGS = new Set(['A', 'BUTTON']);

      // Walk text-bearing elements
      const selector =
        'h1, h2, h3, h4, h5, h6, p, li, a, button, span, blockquote, figcaption, label';
      const elements = document.querySelectorAll(selector);

      elements.forEach((el) => {
        const text = el.textContent?.trim();
        if (!text || text.length < 2) return;

        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return;

        const computed = window.getComputedStyle(el);
        const tag = el.tagName;

        items.push({
          text: text.slice(0, 300), // cap length for sanity
          tag: tag.toLowerCase(),
          isHeading: HEADING_TAGS.has(tag),
          isInteractive: INTERACTIVE_TAGS.has(tag),
          href: el.href || null,
          rect: {
            x: Math.round(rect.x),
            y: Math.round(rect.y + window.scrollY),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          },
          styles: {
            color: computed.color,
            fontSize: computed.fontSize,
            fontFamily: computed.fontFamily,
            fontWeight: computed.fontWeight,
            lineHeight: computed.lineHeight,
            letterSpacing: computed.letterSpacing,
            textTransform: computed.textTransform,
          },
        });
      });

      return items;
    });

    console.log(`[extract] Extracted ${textContent.length} text content items`);

    // ── Assign sectionIndex to text content ───────────────────────────
    // v2.0.2: Use smallest-first ordering to avoid wrapper sections swallowing everything
    for (const item of textContent) {
      item.sectionIndex = null;
      const midY = item.rect.y + item.rect.height / 2;
      for (const sec of sectionsBySize) {
        if (midY >= sec.rect.y && midY <= sec.rect.y + sec.rect.height) {
          item.sectionIndex = sec.index;
          break;
        }
      }
    }
    console.log(
      `[extract] Assigned sectionIndex to ${textContent.filter((t) => t.sectionIndex !== null).length}/${textContent.length} text items`
    );

    // ── 11. Extract assets ─────────────────────────────────────────────
    const assets = await page.evaluate(() => {
      // Images
      const images = Array.from(document.querySelectorAll('img')).map((img) => ({
        src: img.src || img.dataset?.src || '',
        alt: img.alt || '',
        width: img.naturalWidth || img.width,
        height: img.naturalHeight || img.height,
        loading: img.loading || 'auto',
      }));

      // Background images from computed styles (check first 200 elements)
      const bgImages = [];
      const allEls = document.querySelectorAll('*');
      const limit = Math.min(allEls.length, 200);
      for (let i = 0; i < limit; i++) {
        const bg = window.getComputedStyle(allEls[i]).backgroundImage;
        if (bg && bg !== 'none') {
          bgImages.push({
            element: allEls[i].tagName.toLowerCase(),
            backgroundImage: bg.slice(0, 500),
          });
        }
      }

      // Fonts: collect from all stylesheets
      const fonts = new Set();
      try {
        for (const sheet of document.styleSheets) {
          try {
            for (const rule of sheet.cssRules) {
              if (rule instanceof CSSFontFaceRule) {
                const family = rule.style.getPropertyValue('font-family');
                if (family) fonts.add(family.replace(/['"]/g, '').trim());
              }
            }
          } catch (_) {
            // Cross-origin stylesheets will throw; skip them
          }
        }
      } catch (_) {
        // Ignore stylesheet access errors
      }

      // Also grab fonts from <link> preload/prefetch tags
      const fontLinks = Array.from(
        document.querySelectorAll(
          'link[rel="preload"][as="font"], link[href*="fonts.googleapis.com"]'
        )
      ).map((link) => link.href);

      return {
        images,
        backgroundImages: bgImages,
        fonts: [...fonts],
        fontLinks,
      };
    });

    // ── 11b. Inline SVG extraction (v1.2.0) ─────────────────────────────
    const svgAssets = await page.evaluate(() => {
      const svgs = [];
      // Logo SVGs - from containers with logo/brand/partner in class or role
      const logoSelectors = [
        '[class*="logo"] svg', '[class*="brand"] svg', '[class*="partner"] svg',
        '[class*="client"] svg', '[class*="sponsor"] svg',
        '[role="img"] svg', 'header svg', 'nav svg',
      ];
      const logoSvgs = document.querySelectorAll(logoSelectors.join(', '));
      logoSvgs.forEach(svg => {
        const rect = svg.getBoundingClientRect();
        if (rect.width > 10 && rect.height > 10 && rect.width < 300) {
          svgs.push({
            category: 'logo',
            viewBox: svg.getAttribute('viewBox') || '',
            innerHTML: svg.innerHTML.substring(0, 2000),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            parentClasses: (svg.parentElement?.className || '').toString().substring(0, 200),
          });
        }
      });
      // Icon SVGs - smaller elements in feature/card areas
      const iconSelectors = [
        '[class*="icon"] svg', '[class*="feature"] svg', '[class*="card"] svg',
        '[class*="benefit"] svg', '[class*="stat"] svg',
      ];
      const iconSvgs = document.querySelectorAll(iconSelectors.join(', '));
      iconSvgs.forEach(svg => {
        const rect = svg.getBoundingClientRect();
        if (rect.width > 8 && rect.width < 80 && rect.height > 8 && rect.height < 80) {
          svgs.push({
            category: 'icon',
            viewBox: svg.getAttribute('viewBox') || '',
            innerHTML: svg.innerHTML.substring(0, 1000),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            parentClasses: (svg.parentElement?.className || '').toString().substring(0, 200),
          });
        }
      });
      return svgs;
    });

    // ── 11c. Icon library detection (v1.2.0) ───────────────────────────
    const iconLibrary = await page.evaluate(() => {
      const result = { library: null, icons: [], count: 0 };
      // Lucide
      const lucideEls = document.querySelectorAll('[class*="lucide-"], svg[class*="lucide"]');
      if (lucideEls.length > 0) {
        result.library = 'lucide';
        lucideEls.forEach(el => {
          const cls = [...(el.classList || [])].find(c => c.startsWith('lucide-'));
          if (cls) result.icons.push(cls.replace('lucide-', ''));
        });
      }
      // Font Awesome
      if (!result.library) {
        const faEls = document.querySelectorAll('[class*="fa-"]');
        if (faEls.length > 0) {
          result.library = 'font-awesome';
          faEls.forEach(el => {
            const cls = [...(el.classList || [])].find(c =>
              c.startsWith('fa-') && !['fa-solid', 'fa-regular', 'fa-light', 'fa-brands', 'fa-thin', 'fa-duotone'].includes(c)
            );
            if (cls) result.icons.push(cls.replace('fa-', ''));
          });
        }
      }
      // Heroicons
      if (!result.library) {
        const heroEls = document.querySelectorAll('svg[data-slot="icon"], [class*="heroicon"]');
        if (heroEls.length > 0) {
          result.library = 'heroicons';
        }
      }
      // Material Icons
      if (!result.library) {
        const matEls = document.querySelectorAll('.material-icons, .material-symbols-outlined');
        if (matEls.length > 0) {
          result.library = 'material-icons';
          matEls.forEach(el => { if (el.textContent) result.icons.push(el.textContent.trim()); });
        }
      }
      result.icons = [...new Set(result.icons)];
      result.count = result.icons.length;
      return result;
    });

    // ── 11d. Enhanced logo image extraction (v1.2.0) ─────────────────────
    const logoImages = await page.evaluate(() => {
      const logos = [];
      const selectors = [
        '[class*="logo"] img', '[class*="brand"] img', '[class*="partner"] img',
        '[class*="client"] img', '[class*="sponsor"] img', '[class*="trust"] img',
        '[class*="company"] img',
      ];
      document.querySelectorAll(selectors.join(', ')).forEach(img => {
        if (img.src && !img.src.startsWith('data:image/gif') && !img.src.includes('placeholder')) {
          const rect = img.getBoundingClientRect();
          logos.push({
            url: img.src,
            alt: img.alt || '',
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            type: 'raster',
          });
        }
      });
      return logos;
    });

    assets.svgs = svgAssets;
    assets.iconLibrary = iconLibrary;
    assets.logos = logoImages;

    // ── Assign sectionIndex to images ─────────────────────────────────
    for (const img of assets.images) {
      img.sectionIndex = null;
    }
    // v2.0.2: Pass sections sorted by height ascending for smallest-first matching
    const sectionRectsForImages = sectionsBySize.map((s) => ({ index: s.index, y: s.rect.y, height: s.rect.height }));
    const imagePositions = await page.evaluate((sectionRects) => {
      return Array.from(document.querySelectorAll('img')).map((img) => {
        const rect = img.getBoundingClientRect();
        const absY = rect.top + window.scrollY;
        const midY = absY + rect.height / 2;
        let sectionIndex = null;
        for (const sec of sectionRects) {
          if (midY >= sec.y && midY <= sec.y + sec.height) {
            sectionIndex = sec.index;
            break;
          }
        }
        return {
          src: img.src || img.dataset?.src || '',
          sectionIndex,
        };
      });
    }, sectionRectsForImages);

    for (const img of assets.images) {
      const match = imagePositions.find((p) => p.src === img.src);
      if (match) img.sectionIndex = match.sectionIndex;
    }
    console.log(
      `[extract] Assigned sectionIndex to ${assets.images.filter((i) => i.sectionIndex !== null).length}/${assets.images.length} images`
    );

    console.log(
      `[extract] Found ${assets.images.length} images, ` +
        `${assets.fonts.length} fonts, ` +
        `${assets.backgroundImages.length} background-images, ` +
        `${assets.svgs.length} inline SVGs, ` +
        `${assets.logos.length} logo images, ` +
        `icon library: ${assets.iconLibrary.library || 'none'} (${assets.iconLibrary.count} icons)`
    );

    // ── 12. Persist full-page screenshot if outputDir given ────────────
    if (outputDir) {
      ensureDir(outputDir);
      fs.writeFileSync(path.join(outputDir, 'full-page.png'), fullPageBuffer);
      console.log(`[extract] Screenshots saved to ${outputDir}`);
    }

    // ── 13. Build and return result ────────────────────────────────────
    const result = {
      url,
      timestamp: new Date().toISOString(),
      viewport: VIEWPORT,
      pageHeight,
      sections,
      renderedDOM,
      textContent,
      assets,
      screenshots: {
        fullPage: outputDir
          ? path.join(outputDir, 'full-page.png')
          : fullPageBuffer,
        sectionScreenshots: outputDir
          ? Object.fromEntries(
              Object.entries(sectionScreenshots).map(([idx]) => [
                idx,
                path.join(
                  outputDir,
                  'sections',
                  `section-${String(idx).padStart(2, '0')}.png`
                ),
              ])
            )
          : sectionScreenshots,
        scrollCaptures: scrollCaptures.length, // just the count (buffers are large)
      },
      animations: {
        evidence: rawAnimationEvidence,
        networkResults: networkAnimationResults,
      },
    };

    console.log(`[extract] Extraction complete for ${url}`);
    return result;
  } finally {
    // ── Cleanup: always close the browser ──────────────────────────────
    if (browser) {
      await browser.close();
      console.log(`[extract] Browser closed`);
    }
  }
}

// ── Exports ──────────────────────────────────────────────────────────────────

module.exports = { extractReference };

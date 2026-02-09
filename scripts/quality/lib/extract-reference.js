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
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60_000 });
    await sleep(POST_LOAD_DELAY_MS);
    console.log(`[extract] Page loaded, settling for ${POST_LOAD_DELAY_MS}ms`);

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

    // ── 7. Identify visual sections ────────────────────────────────────
    // Sections are defined as block-level children of <main> or <body>
    // that are taller than 50px. This gives us the major content blocks.
    const sections = await page.evaluate(() => {
      const container = document.querySelector('main') || document.body;
      const children = Array.from(container.children);
      const sectionData = [];

      children.forEach((child, index) => {
        const rect = child.getBoundingClientRect();
        const absoluteTop = rect.top + window.scrollY;
        const height = rect.height;

        // Filter out tiny or invisible elements
        if (height < 50) return;

        const tag = child.tagName.toLowerCase();
        const id = child.id || '';
        const classNames = child.className?.toString?.() || '';
        const role = child.getAttribute('role') || '';

        // Try to infer a semantic label for the section
        let label = '';
        if (tag === 'nav' || role === 'navigation') label = 'navigation';
        else if (tag === 'header') label = 'header';
        else if (tag === 'footer' || role === 'contentinfo') label = 'footer';
        else if (tag === 'section' || tag === 'article') {
          // Use the first heading inside as a label hint
          const heading = child.querySelector('h1, h2, h3');
          label = heading ? heading.textContent.trim().slice(0, 60) : '';
        }

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
        });
      });

      return sectionData;
    });

    console.log(`[extract] Identified ${sections.length} visual sections`);

    // ── 8. Assign sectionIndex to DOM elements ─────────────────────────
    // For each DOM element, determine which section it belongs to based on
    // vertical overlap of its rect.y with section boundaries.
    for (const el of renderedDOM) {
      el.sectionIndex = -1; // default: not in any section
      const elMidY = el.rect.y + el.rect.height / 2;

      for (const sec of sections) {
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

    console.log(
      `[extract] Found ${assets.images.length} images, ` +
        `${assets.fonts.length} fonts, ` +
        `${assets.backgroundImages.length} background-images`
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

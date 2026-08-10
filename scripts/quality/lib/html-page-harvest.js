/**
 * HTML Page Harvest — dependency-free static HTML → per-page section content.
 *
 * Consumes the raw HTML that the UI/UX audit engine already captured for every
 * route it crawled, and turns each capture into the per-page shape the
 * multipage manifest builder expects (`{page_id, page_type, source_url, nav,
 * sections}`).
 *
 * WHY static HTML and not a second Playwright crawl: the audit bundle already
 * holds the site's real information architecture *and* the raw HTML of every
 * route. Re-crawling would duplicate work and let the two views of the same
 * site drift apart. The trade-off is that static HTML carries no layout box —
 * see `estimateRect()` — and no computed styles, so global style tokens must
 * still come from the (single-URL) Playwright extraction.
 *
 * No third-party parser is used on purpose: web-builder's only npm dependency
 * is playwright, and adding cheerio/jsdom for this would be a heavier change
 * than the parsing actually needs.
 *
 * @module html-page-harvest
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// Tokenizer helpers
// ---------------------------------------------------------------------------

const VOID_ELEMENTS = new Set([
  'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
  'link', 'meta', 'param', 'source', 'track', 'wbr',
]);

/** Elements that delimit a page section in document order. */
const SECTION_TAGS = new Set(['header', 'nav', 'main', 'section', 'footer', 'article', 'aside']);

/** Wrappers that hold sections rather than being one. Descended into. */
const CONTAINER_TAGS = new Set(['main', 'article']);

const ENTITIES = {
  amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ',
  ndash: '–', mdash: '—', hellip: '…',
  lsquo: '‘', rsquo: '’', ldquo: '“', rdquo: '”',
  copy: '©', reg: '®', trade: '™', deg: '°',
};

function decodeEntities(str) {
  if (!str) return '';
  return str
    .replace(/&#x([0-9a-fA-F]+);/g, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(parseInt(d, 10)))
    .replace(/&([a-zA-Z]+);/g, (m, name) => (ENTITIES[name] != null ? ENTITIES[name] : m));
}

/** Remove content that must never contribute text or fake tag boundaries. */
function cleanHtml(html) {
  return String(html || '')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<noscript\b[^>]*>[\s\S]*?<\/noscript>/gi, ' ');
}

function stripTags(html) {
  return decodeEntities(
    String(html || '')
      .replace(/<svg\b[^>]*>[\s\S]*?<\/svg>/gi, ' ')
      .replace(/<[^>]+>/g, ' ')
  )
    .replace(/\s+/g, ' ')
    .trim();
}

function getAttr(attrs, name) {
  const re = new RegExp(`\\b${name}\\s*=\\s*("([^"]*)"|'([^']*)'|([^\\s>]+))`, 'i');
  const m = re.exec(attrs || '');
  if (!m) return '';
  return decodeEntities(m[2] != null ? m[2] : m[3] != null ? m[3] : m[4] || '');
}

/**
 * Return the top-level (non-nested relative to each other) elements whose tag
 * is in `tagNames`, in document order. Balanced by tag-name depth counting.
 */
function collectBlocks(html, tagNames) {
  const tagRe = /<(\/?)([a-zA-Z][a-zA-Z0-9-]*)\b([^>]*?)(\/?)>/g;
  const blocks = [];
  let current = null;
  let depth = 0;
  let m;

  while ((m = tagRe.exec(html)) !== null) {
    const closing = m[1] === '/';
    const name = m[2].toLowerCase();
    const selfClosing = m[4] === '/' || VOID_ELEMENTS.has(name);

    if (current) {
      if (name !== current.tag || selfClosing) continue;
      if (!closing) {
        depth++;
      } else {
        depth--;
        if (depth === 0) {
          current.inner = html.slice(current.contentStart, m.index);
          blocks.push(current);
          current = null;
        }
      }
    } else if (!closing && !selfClosing && tagNames.has(name)) {
      current = { tag: name, attrs: m[3] || '', contentStart: tagRe.lastIndex, inner: '' };
      depth = 1;
    }
  }

  // Unterminated final element (malformed markup): keep what we have.
  if (current) {
    current.inner = html.slice(current.contentStart);
    blocks.push(current);
  }
  return blocks;
}

// ---------------------------------------------------------------------------
// Per-section content extraction
// ---------------------------------------------------------------------------

function absolutize(url, baseUrl) {
  const raw = String(url || '').trim();
  if (!raw) return '';
  if (/^(https?:|data:|mailto:|tel:|#)/i.test(raw)) return raw;
  try {
    return new URL(raw, baseUrl).href;
  } catch (_) {
    return raw;
  }
}

function extractHeadings(inner) {
  const out = [];
  const re = /<h([1-6])\b[^>]*>([\s\S]*?)<\/h\1>/gi;
  let m;
  while ((m = re.exec(inner)) !== null) {
    const text = stripTags(m[2]);
    if (text) out.push(text);
  }
  return out;
}

function extractBodyText(inner) {
  const out = [];
  const re = /<(p|li|blockquote|dd|figcaption)\b[^>]*>([\s\S]*?)<\/\1>/gi;
  let m;
  while ((m = re.exec(inner)) !== null) {
    const text = stripTags(m[2]);
    // Two chars filters out bullet glyphs and stray separators.
    if (text.length > 2) out.push(text);
  }
  return out;
}

function extractCtas(inner, baseUrl) {
  const out = [];
  const seen = new Set();
  const anchorRe = /<a\b([^>]*)>([\s\S]*?)<\/a>/gi;
  let m;
  while ((m = anchorRe.exec(inner)) !== null) {
    const text = stripTags(m[2]);
    if (!text) continue;
    const href = absolutize(getAttr(m[1], 'href'), baseUrl);
    const key = `${text} ${href}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ text, href });
  }
  const buttonRe = /<button\b[^>]*>([\s\S]*?)<\/button>/gi;
  while ((m = buttonRe.exec(inner)) !== null) {
    const text = stripTags(m[1]);
    if (!text || seen.has(`${text} `)) continue;
    seen.add(`${text} `);
    out.push({ text, href: '' });
  }
  return out;
}

function extractImages(inner, baseUrl) {
  const out = [];
  const seen = new Set();
  const re = /<img\b([^>]*)>/gi;
  let m;
  while ((m = re.exec(inner)) !== null) {
    const attrs = m[1];
    const src = absolutize(getAttr(attrs, 'src') || getAttr(attrs, 'data-src'), baseUrl);
    if (!src || seen.has(src)) continue;
    seen.add(src);
    const width = parseInt(getAttr(attrs, 'width'), 10);
    const height = parseInt(getAttr(attrs, 'height'), 10);
    out.push({
      src,
      alt: getAttr(attrs, 'alt') || '',
      width: Number.isFinite(width) ? width : null,
      height: Number.isFinite(height) ? height : null,
    });
  }
  return out;
}

/**
 * Static HTML has no layout box. `archetype-mapper.js` reads `rect.height` for
 * variant selection (hero size, footer size) and `rect.y` in its legacy
 * text-matching fallback, so a synthetic, monotonically increasing rect is
 * supplied. Markup volume is the only proxy available; treat these numbers as
 * ordering hints, never as measurements.
 */
function estimateRect(inner, yOffset) {
  const height = Math.max(200, Math.min(2400, Math.round(inner.length / 4)));
  return { x: 0, y: yOffset, width: 1440, height };
}

function classFragments(attrs) {
  return `${getAttr(attrs, 'class')} ${getAttr(attrs, 'id')}`.trim();
}

/**
 * Split one page's HTML into ordered *blocks* carrying DOM-scoped content.
 *
 * These are deliberately NOT site-spec sections and must not be consumed as
 * such: they carry no `archetype`, `variant`, `section_uid` or `source_index`,
 * because those are resolved one layer up in `build-site-spec.js:buildPage()`
 * (archetype/variant need the archetype mapper; the uid is derived from them).
 * The field is named `blocks` so that a raw block can never be mistaken for a
 * contract-satisfying section — `buildPage()` enforces the contract itself.
 *
 * Containers (`main`, `article`) are descended into so their child sections
 * become the blocks, mirroring the recursive descent that
 * `extract-reference.js` performs on the live DOM.
 */
function harvestBlocks(html, baseUrl) {
  const cleaned = cleanHtml(html);
  const bodyMatch = /<body\b[^>]*>([\s\S]*)<\/body>/i.exec(cleaned);
  const body = bodyMatch ? bodyMatch[1] : cleaned;

  const flattened = [];
  for (const block of collectBlocks(body, SECTION_TAGS)) {
    if (CONTAINER_TAGS.has(block.tag)) {
      const children = collectBlocks(block.inner, SECTION_TAGS);
      if (children.length > 0) {
        flattened.push(...children);
        continue;
      }
    }
    flattened.push(block);
  }

  const blocks = [];
  let y = 0;
  for (const block of flattened) {
    const headings = extractHeadings(block.inner);
    const bodyText = extractBodyText(block.inner);
    const ctas = extractCtas(block.inner, baseUrl);
    const images = extractImages(block.inner, baseUrl);

    // Empty structural wrappers carry no signal for any downstream stage.
    if (headings.length === 0 && bodyText.length === 0 && ctas.length === 0 && images.length === 0) {
      continue;
    }

    const rect = estimateRect(block.inner, y);
    y += rect.height;

    // A <header> wrapping the primary <nav> is the site chrome, not a hero.
    // archetype-mapper maps the `header` tag to HERO at 0.9, which outranks —
    // and, via its adjacent-duplicate dedup, deletes — the real hero section
    // below it. Reporting it as what it functionally is keeps both.
    const isSiteHeader = block.tag === 'header' && /<nav\b/i.test(block.inner);

    blocks.push({
      index: blocks.length,
      tag: isSiteHeader ? 'nav' : block.tag,
      role: getAttr(block.attrs, 'role') || '',
      classNames: getAttr(block.attrs, 'class') || '',
      id: getAttr(block.attrs, 'id') || '',
      label: headings[0] || classFragments(block.attrs),
      rect,
      content: {
        headings,
        body_text: bodyText,
        ctas,
        image_count: images.length,
      },
      images,
      metrics: { nodes: [] },
    });
  }
  return blocks;
}

/** Primary navigation links, taken from the first `nav` (or `header`) block. */
function harvestNav(html, baseUrl) {
  const cleaned = cleanHtml(html);
  const navBlocks = collectBlocks(cleaned, new Set(['nav']));
  const source = navBlocks[0] || collectBlocks(cleaned, new Set(['header']))[0];
  if (!source) return { links: [] };
  const links = extractCtas(source.inner, baseUrl)
    .filter((l) => l.href && !l.href.startsWith('#'))
    .map((l) => ({ label: l.text, href: l.href }));
  return { links };
}

function extractTitle(html) {
  const m = /<title\b[^>]*>([\s\S]*?)<\/title>/i.exec(html || '');
  return m ? stripTags(m[1]) : '';
}

// ---------------------------------------------------------------------------
// Route identity
// ---------------------------------------------------------------------------

function pathnameOf(url) {
  try {
    return new URL(url).pathname || '/';
  } catch (_) {
    return String(url || '/');
  }
}

/** Deterministic, filesystem-safe page id derived from the route path. */
function pageIdFromUrl(url) {
  const pathname = pathnameOf(url).replace(/\/+$/, '');
  if (!pathname || pathname === '') return 'homepage';
  return pathname
    .replace(/^\/+/, '')
    .replace(/\//g, '-')
    .replace(/[^a-zA-Z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase() || 'homepage';
}

/**
 * Classify a route into a page_type the manifest builder understands.
 * Valid values (build_site_manifest.PAGE_TYPE_DEFINITIONS): homepage, about,
 * contact, collection, product, blog, content, not-found.
 */
function pageTypeFromUrl(url) {
  const pathname = pathnameOf(url).replace(/\/+$/, '').toLowerCase();
  if (!pathname) return 'homepage';
  const segments = pathname.replace(/^\/+/, '').split('/');
  const first = segments[0];
  if (first === 'about' || first === 'about-us') return 'about';
  if (first === 'contact' || first === 'contact-us') return 'contact';
  if (first === 'blog' || first === 'news' || first === 'articles') return 'blog';
  if (first === 'collections' || first === 'shop' || first === 'category') return 'collection';
  if (first === 'products' || first === 'product') return 'product';
  return 'content';
}

// ---------------------------------------------------------------------------
// Capture bundle loading
// ---------------------------------------------------------------------------

/**
 * Thrown when a capture bundle was produced without the audit engine's
 * opt-in `--store-html` flag. The bundle still reports a plausible
 * `html_length`, so a silent skip here would look like "the site has no
 * content" instead of "this bundle cannot answer the question".
 */
class MissingCaptureHtmlError extends Error {
  constructor(urls, source) {
    super(
      `[html-page-harvest] ${urls.length} capture record(s) in ${source} have no "html" key. ` +
      'The audit engine drops HTML at the disk-persist step unless it was run with --store-html, ' +
      'so html_length can be non-zero while the HTML itself is absent. This is NOT "no content" — ' +
      'it is an unusable bundle. Re-run the audit with --store-html.\n' +
      `Affected URLs: ${urls.slice(0, 5).join(', ')}${urls.length > 5 ? ` (+${urls.length - 5} more)` : ''}`
    );
    this.name = 'MissingCaptureHtmlError';
    this.urls = urls;
    this.source = source;
  }
}

/**
 * Load an audit capture bundle.
 *
 * `bundleDir` may be the audit run directory (containing `captures/` and/or
 * `captures_manifest.json`) or the `captures/` directory itself.
 *
 * Records are keyed and ordered by their `url` field, never by filename:
 * capture filenames embed Python's builtin `hash()`, which is salted per
 * process, so the same route lands in a differently-named file on every run.
 */
function loadCaptures(bundleDir) {
  const dir = path.resolve(bundleDir);
  const manifestPath = fs.existsSync(path.join(dir, 'captures_manifest.json'))
    ? path.join(dir, 'captures_manifest.json')
    : path.join(dir, '..', 'captures_manifest.json');

  let records = null;
  let source = manifestPath;

  if (fs.existsSync(manifestPath)) {
    const parsed = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    records = Array.isArray(parsed) ? parsed : parsed.captures;
  }

  if (!Array.isArray(records) || records.length === 0) {
    const capturesDir = fs.existsSync(path.join(dir, 'captures')) ? path.join(dir, 'captures') : dir;
    source = capturesDir;
    if (!fs.existsSync(capturesDir)) {
      throw new Error(`[html-page-harvest] No capture bundle found at ${dir}`);
    }
    records = fs
      .readdirSync(capturesDir)
      .filter((f) => f.endsWith('.json'))
      .sort() // numeric prefix carries crawl order; the hash suffix is ignored
      .map((f) => JSON.parse(fs.readFileSync(path.join(capturesDir, f), 'utf8')));
  }

  // Order by url, de-duplicated, preserving first occurrence (crawl order).
  const byUrl = new Map();
  for (const rec of records) {
    const url = rec && rec.url;
    if (!url || byUrl.has(url)) continue;
    byUrl.set(url, rec);
  }

  const missingHtml = [];
  for (const [url, rec] of byUrl) {
    if (!Object.prototype.hasOwnProperty.call(rec, 'html')) missingHtml.push(url);
  }
  if (missingHtml.length > 0) {
    throw new MissingCaptureHtmlError(missingHtml, source);
  }

  return [...byUrl.values()];
}

/** Keep only successful, HTML-bearing captures. */
function usableCaptures(captures) {
  return captures.filter(
    (c) => !c.fetch_error && (c.http_status == null || c.http_status < 400) && typeof c.html === 'string' && c.html.length > 0
  );
}

/**
 * Turn one capture record into a RAW harvested page: route identity, nav, and
 * ordered `blocks` carrying DOM-scoped content.
 *
 * This is an intermediate, NOT the delivered contract. `blocks` become
 * contract sections (with archetype, variant, section_uid, source_index) only
 * after `build-site-spec.js:buildPage()` runs. Read `site-spec.json` to see
 * what is actually delivered.
 */
function harvestPage(capture) {
  const url = capture.url;
  return {
    page_id: pageIdFromUrl(url),
    page_type: pageTypeFromUrl(url),
    route: (() => {
      const p = pathnameOf(url).replace(/\/+$/, '');
      return p === '' ? '/' : p;
    })(),
    source_url: url,
    title: extractTitle(capture.html),
    nav: harvestNav(capture.html, url),
    blocks: harvestBlocks(capture.html, url),
    harvest: {
      method: 'audit-capture',
      http_status: capture.http_status ?? null,
      html_length: capture.html_length ?? capture.html.length,
    },
  };
}

module.exports = {
  MissingCaptureHtmlError,
  loadCaptures,
  usableCaptures,
  harvestPage,
  harvestBlocks,
  harvestNav,
  pageIdFromUrl,
  pageTypeFromUrl,
  pathnameOf,
  stripTags,
  decodeEntities,
  collectBlocks,
  extractCtas,
  extractImages,
  extractHeadings,
  extractBodyText,
};

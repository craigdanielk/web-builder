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

/**
 * Direct child ELEMENTS of a fragment, in document order, whatever their tag.
 *
 * `collectBlocks()` above answers "which of these named tags are top-level",
 * counting depth by tag name only; that is enough for section discovery but
 * cannot answer "what are this node's children", which is the question item
 * grouping asks. A stack keeps mixed nesting honest, and a close tag with no
 * matching open on the stack is ignored rather than unwinding — real-world
 * markup (an unclosed `<p>`) must degrade, not derail.
 */
function parseChildren(html) {
  const tagRe = /<(\/?)([a-zA-Z][a-zA-Z0-9-]*)\b([^>]*?)(\/?)>/g;
  const out = [];
  const stack = [];
  let current = null;
  let m;

  while ((m = tagRe.exec(html)) !== null) {
    const closing = m[1] === '/';
    const name = m[2].toLowerCase();
    const selfClosing = m[4] === '/' || VOID_ELEMENTS.has(name);

    if (!closing) {
      if (selfClosing) {
        if (!current) out.push({ tag: name, attrs: m[3] || '', inner: '', selfClosing: true });
        continue;
      }
      if (!current) {
        current = { tag: name, attrs: m[3] || '', contentStart: tagRe.lastIndex, inner: '', selfClosing: false };
        stack.length = 0;
      }
      stack.push(name);
    } else {
      if (!current) continue;
      const idx = stack.lastIndexOf(name);
      if (idx === -1) continue;
      stack.length = idx;
      if (stack.length === 0) {
        current.inner = html.slice(current.contentStart, m.index);
        out.push(current);
        current = null;
      }
    }
  }

  if (current) {
    current.inner = html.slice(current.contentStart);
    out.push(current);
  }
  return out;
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

// ---------------------------------------------------------------------------
// Item grouping
//
// A repeater's items are not a property of its text — they are a property of
// its DOM. Flattening a section into parallel `headings[]` / `body_text[]`
// throws that structure away and forces the consumer to re-infer it by
// position, which is wrong the moment a section carries its own intro or a
// card is missing a field. Grouping recovers the structure before it is lost.
//
// Two shapes cover every repeater observed in real captures, and one rule
// covers both: a run of sibling elements whose signatures repeat with a fixed
// period. Period 1 is the card-grid shape (`<div class="step-card">` ×3);
// period >1 is the flat-run shape (`<h3><p><h3><p><h3><p>`), where the items
// are not wrapped at all and only the repetition marks their boundaries.
// ---------------------------------------------------------------------------

/** Longest an item's element cycle may be. Beyond this it is a layout, not an item. */
const MAX_ITEM_PERIOD = 4;

/** How far below a section root to look for a repeater before giving up. */
const MAX_GROUPING_DEPTH = 8;

/** Guard against pathological nodes (a nav with hundreds of links). */
const MAX_CHILDREN_SCANNED = 200;

/** Items emitted per section. Generous — a real repeater rarely exceeds this. */
const MAX_ITEMS = 24;

function normalizedClass(attrs) {
  return getAttr(attrs, 'class')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .sort()
    .join(' ');
}

/**
 * Shape key for sibling comparison: tag plus its class set.
 *
 * Class-based rather than structural on purpose — authors mark repeated items
 * with a repeated class far more reliably than with identical inner markup
 * (a card missing its image still carries `class="card"`).
 */
function elementSignature(el) {
  return `${el.tag}.${normalizedClass(el.attrs)}`;
}

/**
 * Find the strongest repeating run in a signature sequence.
 *
 * Ranked by cycle count first, then by the shorter period: for `[A,A,A]`,
 * period 1 gives 3 items and period 2 would give 2 items of two cards each —
 * more elements covered, but the wrong reading. More items of a simpler shape
 * is always the better answer.
 *
 * @returns {{start:number, period:number, count:number}|null}
 */
function findRepeatingRun(signatures) {
  const n = signatures.length;
  let best = null;

  for (let period = 1; period <= MAX_ITEM_PERIOD; period++) {
    for (let start = 0; start + period * 2 <= n; start++) {
      let count = 1;
      while (start + period * (count + 1) <= n) {
        let same = true;
        for (let k = 0; k < period; k++) {
          if (signatures[start + k] !== signatures[start + period * count + k]) { same = false; break; }
        }
        if (!same) break;
        count++;
      }
      if (count < 2) continue;
      if (!best || count > best.count || (count === best.count && period < best.period)) {
        best = { start, period, count };
      }
    }
  }
  return best;
}

function serializeElement(el) {
  if (el.selfClosing) return `<${el.tag}${el.attrs}>`;
  return `<${el.tag}${el.attrs}>${el.inner}</${el.tag}>`;
}

/** Bare `<span>` text, used only when an item carries no heading and no body. */
function extractSpanTexts(frag) {
  const out = [];
  const re = /<span\b[^>]*>([\s\S]*?)<\/span>/gi;
  let m;
  while ((m = re.exec(frag)) !== null) {
    const text = stripTags(m[1]);
    if (text) out.push(text);
  }
  return out;
}

/**
 * First link in a fragment regardless of whether it has visible text.
 * A logo-bar item is an `<a>` wrapping only an `<img>`; `extractCtas()`
 * (rightly) drops textless anchors, which would discard the item's only href.
 */
function firstHref(frag, baseUrl) {
  const m = /<a\b([^>]*)>/i.exec(frag);
  if (!m) return null;
  const href = absolutize(getAttr(m[1], 'href'), baseUrl);
  if (!href) return null;
  return { href, label: getAttr(m[1], 'aria-label') || getAttr(m[1], 'title') || '' };
}

/** Turn one cycle of sibling elements into an item record. */
function buildItem(elements, baseUrl, period) {
  const frag = elements.map(serializeElement).join('');
  const headings = extractHeadings(frag);
  const bodyText = extractBodyText(frag);
  const ctas = extractCtas(frag, baseUrl);
  const images = extractImages(frag, baseUrl);

  let heading = headings[0] || '';
  let body = bodyText[0] || '';

  // Stat-style items ("5+" / "Years operating") are spans, not headings and
  // paragraphs. Only consulted when the semantic tags yielded nothing, so a
  // span inside a heading is never double-counted.
  const spans = (!heading && !body) ? extractSpanTexts(frag) : [];
  if (spans.length > 0) heading = spans[0];
  if (spans.length > 1) body = spans[1];

  // An item has internal structure; prose does not. Three consecutive
  // `<p>` paragraphs of an About story repeat perfectly as siblings and are
  // NOT a repeater — reporting them as three items would invent a card grid
  // out of a paragraph. Requiring a heading, an image, a link, a span pair or
  // a multi-element cycle keeps every real repeater on this site (step cards,
  // stat blocks, feature runs, logo links, post lists) and rejects prose runs.
  const structured =
    period > 1 ||
    headings.length > 0 ||
    images.length > 0 ||
    ctas.length > 0 ||
    spans.length > 1 ||
    /<a\b[^>]*\bhref/i.test(frag);

  let cta = ctas[0] || null;
  const link = firstHref(frag, baseUrl);
  if (!cta && link) cta = { text: link.label, href: link.href };

  // Image-only item (logo bar): the alt/aria-label is the only name it has.
  if (!heading && !body && images.length > 0) heading = images[0].alt || (link ? link.label : '') || '';
  // Link-only item (nav, link column): the anchor text is the item's label.
  if (!heading && !body && cta && cta.text) heading = cta.text;

  return {
    structured,
    item: {
      heading,
      body,
      cta,
      image: images[0] || null,
      headings,
      body_text: bodyText,
      ctas,
      images,
    },
  };
}

function itemHasContent(item) {
  return Boolean(item.heading || item.body || item.image || (item.cta && (item.cta.text || item.cta.href)));
}

/**
 * Walk a section subtree collecting every repeating-run candidate, then keep
 * the shallowest one.
 *
 * Shallowest wins because depth means specificity: a footer's three columns sit
 * above the link lists inside them, and the columns are the items a consumer
 * means. Taking the run with the most cycles instead would return twelve links
 * and lose the columns entirely.
 */
function findItemGroup(inner, baseUrl) {
  const candidates = [];

  const visit = (html, depth) => {
    if (depth > MAX_GROUPING_DEPTH) return;
    const children = parseChildren(html).slice(0, MAX_CHILDREN_SCANNED);
    if (children.length >= 2) {
      const run = findRepeatingRun(children.map(elementSignature));
      if (run) {
        const items = [];
        let structuredCount = 0;
        for (let i = 0; i < run.count; i++) {
          const start = run.start + i * run.period;
          const built = buildItem(children.slice(start, start + run.period), baseUrl, run.period);
          if (built.structured) structuredCount++;
          items.push(built.item);
        }
        const populated = items.filter(itemHasContent);
        if (populated.length >= 2 && structuredCount >= 2) {
          candidates.push({
            depth,
            items,
            grouping: {
              method: run.period === 1 ? 'sibling-repeat' : 'cycle-repeat',
              signature: elementSignature(children[run.start]),
              period: run.period,
              depth,
            },
          });
        }
      }
    }
    for (const child of children) {
      if (child.inner) visit(child.inner, depth + 1);
    }
  };

  visit(inner, 0);
  if (candidates.length === 0) return null;

  candidates.sort((a, b) => {
    if (a.depth !== b.depth) return a.depth - b.depth;
    return b.items.length - a.items.length;
  });
  const best = candidates[0];
  best.items = best.items.slice(0, MAX_ITEMS).map((item, index) => ({ index, ...item }));
  return best;
}

/**
 * Multiset difference: strings the section owns that no item claimed.
 *
 * This is what separates a section's own intro from item copy without any
 * off-by-one arithmetic — a string belongs to the section exactly when no item
 * took it, which is a fact about the DOM, not a guess about counts.
 */
function subtractClaimed(all, claimed) {
  const remaining = new Map();
  for (const value of claimed) remaining.set(value, (remaining.get(value) || 0) + 1);
  const out = [];
  for (const value of all) {
    const n = remaining.get(value) || 0;
    if (n > 0) remaining.set(value, n - 1);
    else out.push(value);
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

    // Grouped items, derived from the DOM rather than inferred from the flat
    // lists. `headings` / `body_text` above keep their exact current meaning
    // (every string in the section, in document order) so existing consumers
    // are untouched; `section_headings` / `section_body_text` carry only the
    // copy no item claimed, which is what a fill needs for section-level slots.
    const group = findItemGroup(block.inner, baseUrl);
    const items = group ? group.items : [];
    const claimedHeadings = items.flatMap((it) => it.headings);
    const claimedBody = items.flatMap((it) => it.body_text);

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
        items,
        item_count: items.length,
        item_grouping: group ? group.grouping : null,
        section_headings: subtractClaimed(headings, claimedHeadings),
        section_body_text: subtractClaimed(bodyText, claimedBody),
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
  parseChildren,
  findRepeatingRun,
  findItemGroup,
  extractCtas,
  extractImages,
  extractHeadings,
  extractBodyText,
};

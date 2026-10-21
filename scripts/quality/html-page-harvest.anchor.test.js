// One-page sites navigate by fragment: <a href="#collection"> -> <section id="collection">.
// The nav harvest dropped every `#` link, so THURIS's nav shipped empty. A
// fragment link is kept only when it names a section the page actually has;
// skip-links and dangling fragments are still dropped. Section ids are carried
// to the site-spec as `anchor` — allowlisted, because they reach generated TSX.
//
//   node --test scripts/quality/html-page-harvest.anchor.test.js
const { test } = require('node:test');
const assert = require('node:assert');
const { harvestPage, safeAnchor } = require('./lib/html-page-harvest');

const HTML = `<!doctype html><html><head><title>T</title></head><body>
<header><nav>
  <a href="#collection">The Collection</a>
  <a href="#main-content">Skip to content</a>
  <a href="/about">About</a>
</nav></header>
<main>
<section id="collection" data-tone="dark"><h2>Three essences.</h2><p>Body copy here.</p></section>
<section id="bad id&quot;onload" data-tone="light"><h2>Second.</h2><p>More copy.</p></section>
</main></body></html>`;

const page = () => harvestPage({ url: 'https://example.com/', http_status: 200, html: HTML });

test('fragment links survive only when the page has that section id', () => {
  const hrefs = page().nav.links.map((l) => l.href);
  assert.ok(hrefs.includes('#collection'), `got ${hrefs}`);
  assert.ok(!hrefs.includes('#main-content'), 'dangling fragment must be dropped');
  assert.ok(hrefs.some((h) => h.endsWith('/about')));
});

test('safeAnchor allowlists ids that are safe to write into TSX', () => {
  assert.strictEqual(safeAnchor('collection'), 'collection');
  assert.strictEqual(safeAnchor('rose-geranium'), 'rose-geranium');
  assert.strictEqual(safeAnchor('bad id"onload'), null);
  assert.strictEqual(safeAnchor('1starts-with-digit'), null);
  assert.strictEqual(safeAnchor(''), null);
});

test('blocks carry an allowlisted anchor', () => {
  const anchors = page().blocks.map((b) => b.anchor);
  assert.ok(anchors.includes('collection'));
  assert.ok(!anchors.some((a) => a && a.includes('"')));
});

// A kicker (eyebrow) is the short line a section opens with BEFORE its first
// heading — a DOM-order fact the flat headings/body_text lists throw away. Lost,
// it became body_text[0] and filled the subtitle: THURIS's hero rendered its
// eyebrow under the headline. The flat lists are unchanged (other consumers read
// them); `kicker` is additive, and the fill subtracts it.
//
//   node --test scripts/quality/html-page-harvest.kicker.test.js
const { test } = require('node:test');
const assert = require('node:assert');
const { harvestPage } = require('./lib/html-page-harvest');

const HTML = `<!doctype html><html><head><title>T</title></head><body><main>
<section id="hero"><p>THURIS · BOTANICAL FRAGRANCE HOUSE</p><h1>The Founding Collection</h1>
  <h2>A trace of origin.</h2><p>Three rare botanical essences.</p></section>
<section id="faq"><h2>Before you reserve</h2><p>Answer copy here.</p></section>
<section id="two"><p>First pre-heading line</p><p>Second pre-heading line</p><h2>Heading</h2></section>
<section id="long"><p>${'A very long opening paragraph that is plainly body copy, not a kicker. '.repeat(2)}</p><h2>Heading</h2></section>
</main></body></html>`;

const byId = () => {
  const p = harvestPage({ url: 'https://example.com/', http_status: 200, html: HTML });
  return Object.fromEntries(p.blocks.map((b) => [b.id, b]));
};

test('the line before the first heading is the kicker', () => {
  const b = byId().hero;
  assert.strictEqual(b.content.kicker, 'THURIS · BOTANICAL FRAGRANCE HOUSE');
  // flat list unchanged
  assert.strictEqual(b.content.body_text[0], 'THURIS · BOTANICAL FRAGRANCE HOUSE');
});

test('no pre-heading text, several lines, or a long paragraph: no kicker', () => {
  const b = byId();
  assert.strictEqual(b.faq.content.kicker, null);
  assert.strictEqual(b.two.content.kicker, null);
  assert.strictEqual(b.long.content.kicker, null);
});

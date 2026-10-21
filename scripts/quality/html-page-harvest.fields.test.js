// Declared item fields: `<span data-field="price">AED 395</span>` inside a
// repeated item is recorded as item.fields.price. The item harvest reads
// headings, paragraphs, links and images; a price or a country in a <span> was
// simply lost, so THURIS's cards shipped without prices and its origin rows ran
// species and country together. A field is only what the source DECLARES —
// nothing is inferred from a value's shape — so crawled sites are unaffected.
//
//   node --test scripts/quality/html-page-harvest.fields.test.js
const { test } = require('node:test');
const assert = require('node:assert');
const { harvestPage } = require('./lib/html-page-harvest');

const HTML = `<!doctype html><html><head><title>T</title></head><body><main>
<section id="collection"><h2>Three essences.</h2><div class="grid">
  <article><h3>Frankincense</h3><p>Boswellia serrata · India · 10 ml</p><span data-field="price">AED 395</span><a href="#f">Reserve Frankincense</a></article>
  <article><h3>Neroli</h3><p>Citrus aurantium blossom · France · 10 ml</p><span data-field="price">AED 445</span><a href="#n">Reserve Neroli</a></article>
  <article><h3>Rose</h3><p>Pelargonium</p><span data-field="Bad Name">x</span><span>undeclared</span><a href="#r">Reserve Rose</a></article>
</div></section>
</main></body></html>`;

const items = () => harvestPage({ url: 'https://example.com/', http_status: 200, html: HTML })
  .blocks.find((b) => b.id === 'collection').content.items;

test('declared fields are recorded per item', () => {
  const it = items();
  assert.deepStrictEqual(it[0].fields, { price: 'AED 395' });
  assert.deepStrictEqual(it[1].fields, { price: 'AED 445' });
});

test('undeclared spans and non-allowlisted names are not fields', () => {
  assert.deepStrictEqual(items()[2].fields, {});
});

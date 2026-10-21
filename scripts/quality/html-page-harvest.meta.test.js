// The harvested page carries the source's <title> AND <meta name="description">,
// so layout.tsx metadata is sourced rather than "Built with web-builder pipeline".
//
//   node --test scripts/quality/html-page-harvest.meta.test.js
const { test } = require('node:test');
const assert = require('node:assert');
const { harvestPage } = require('./lib/html-page-harvest');

const page = (head) => ({
  url: 'https://example.com/',
  http_status: 200,
  html: `<!doctype html><html><head>${head}</head><body><main><section><h1>x</h1></section></main></body></html>`,
});

test('meta description is harvested verbatim, entities decoded', () => {
  const p = harvestPage(page('<title>T</title><meta name="description" content="Three essences &amp; one house.">'));
  assert.strictEqual(p.title, 'T');
  assert.strictEqual(p.description, 'Three essences & one house.');
});

test('attribute order and case do not matter', () => {
  const p = harvestPage(page('<META content="Reversed order" NAME="Description">'));
  assert.strictEqual(p.description, 'Reversed order');
});

test('absent description is empty, never a default', () => {
  const p = harvestPage(page('<title>T</title><meta name="viewport" content="width=device-width">'));
  assert.strictEqual(p.description, '');
});

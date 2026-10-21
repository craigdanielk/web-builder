// A source section may DECLARE its variant: <section class="hero" data-variant="product-hero">.
// selectVariant() chose HERO variants from an estimated height only, so an
// operator-authored page had no way to ask for the layout its art direction
// specifies (THURIS: image dominant, copy left). A declaration wins only when it
// names a variant the taxonomy lists for that archetype; anything else is
// ignored and the heuristic stands.
//
//   node --test scripts/quality/archetype-mapper.variant.test.js
const { test } = require('node:test');
const assert = require('node:assert');
const { harvestPage } = require('./lib/html-page-harvest');
const { mapSectionsToArchetypes } = require('./lib/archetype-mapper');

const page = (attrs) => harvestPage({
  url: 'https://example.com/', http_status: 200,
  html: `<!doctype html><html><head><title>T</title></head><body><main>
    <section class="hero" ${attrs}><h1>The Founding Collection</h1><p>Three rare botanical essences.</p><a href="#c">Reserve</a></section>
  </main></body></html>`,
});

const heroVariant = (attrs) => {
  const raw = page(attrs);
  const { mappedSections } = mapSectionsToArchetypes(raw.blocks, [], { dedupe: false });
  return mappedSections.find((s) => s.archetype === 'HERO').variant;
};

test('a declared taxonomy variant is honoured', () => {
  assert.strictEqual(heroVariant('data-variant="product-hero"'), 'product-hero');
});

test('an unknown or unsafe declaration falls back to the heuristic', () => {
  const fallback = heroVariant('');
  assert.strictEqual(heroVariant('data-variant="made-up-variant"'), fallback);
  assert.strictEqual(heroVariant('data-variant="x\\" onload=1"'), fallback);
});

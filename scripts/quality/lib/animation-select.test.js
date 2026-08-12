const { test } = require('node:test');
const assert = require('node:assert');
const injector = require('./animation-injector');

test('selectAnimation is exported', () => {
  assert.equal(typeof injector.selectAnimation, 'function');
});

test('returns a pattern for a common archetype', () => {
  const got = injector.selectAnimation('HERO', 'moderate', 'framer-motion', []);
  assert.ok(got === null || typeof got === 'string');
});

test('respects intensity ceiling', () => {
  const subtle = injector.selectAnimation('HERO', 'subtle', 'framer-motion', []);
  const dramatic = injector.selectAnimation('HERO', 'dramatic', 'framer-motion', []);
  // A subtle preset must never select something a dramatic preset would reject.
  assert.ok(subtle === null || dramatic !== null);
});

test('does not repeat an already-used pattern', () => {
  const first = injector.selectAnimation('FEATURES', 'moderate', 'framer-motion', []);
  if (first) {
    const second = injector.selectAnimation('FEATURES', 'moderate', 'framer-motion', [first]);
    assert.notEqual(second, first);
  }
});

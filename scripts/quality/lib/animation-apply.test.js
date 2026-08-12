const { test } = require('node:test');
const assert = require('node:assert');
const { applyAnimation } = require('./animation-apply');

const PLAIN = `'use client';

export default function Hero() {
  return (
    <section className="py-16">
      <h1>Buy Bitcoin South Africa</h1>
    </section>
  );
}
`;

test('adds the framer-motion import when absent', () => {
  const out = applyAnimation(PLAIN, 'fade-up', 'framer-motion');
  assert.ok(out.applied, out.reason);
  assert.ok(out.tsx.includes("from 'framer-motion'"));
});

test('wraps the root section in a motion element', () => {
  const out = applyAnimation(PLAIN, 'fade-up', 'framer-motion');
  assert.ok(out.tsx.includes('<motion.section'));
  assert.ok(out.tsx.includes('</motion.section>'));
});

test('preserves all original text content', () => {
  const out = applyAnimation(PLAIN, 'fade-up', 'framer-motion');
  assert.ok(out.tsx.includes('Buy Bitcoin South Africa'));
  assert.ok(out.tsx.includes('className="py-16"'));
});

test('is idempotent — a section already animated is left alone', () => {
  const once = applyAnimation(PLAIN, 'fade-up', 'framer-motion');
  const twice = applyAnimation(once.tsx, 'fade-up', 'framer-motion');
  assert.equal(twice.applied, false);
  assert.equal(twice.tsx, once.tsx);
});

test('returns the input unchanged when it cannot find a root element', () => {
  const weird = 'export const x = 1;';
  const out = applyAnimation(weird, 'fade-up', 'framer-motion');
  assert.equal(out.applied, false);
  assert.equal(out.tsx, weird);
});

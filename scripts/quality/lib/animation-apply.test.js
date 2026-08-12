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

// Genuine pipeline output (cape-crypto about/01-hero.tsx): plain <section>
// root, but children already carry framer-motion stagger animations
// (<motion.h1>, <motion.p>, <motion.div>). The root-level reveal must still
// be applied — inner motion elements are additive, not a signal to refuse.
const REAL_SECTION_WITH_INNER_MOTION = `// Template: HERO / centered
// Description: Classic centered hero with headline, subtitle, and dual CTAs
// Animation: framer-motion staggered text entrance
// Tokens: {headline}, {subheadline}, {primary_cta_text}, {primary_cta_url}, {secondary_cta_text}, {secondary_cta_url}

'use client';

import { motion } from 'framer-motion';

export default function HeroCentered() {
  return (
    <section className="py-24 md:py-36 bg-white">
      <div className="container mx-auto px-4 text-center">
        <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="text-4xl md:text-6xl font-bold text-gray-900 mb-6 max-w-4xl mx-auto leading-tight">
          Proudly South African crypto, since 2020
        </motion.h1>
        <motion.p initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.12 }} className="text-lg md:text-xl text-gray-600 mb-10 max-w-2xl mx-auto">
          Cape Crypto is a fully licensed South African exchange on a mission to bring crypto to everyday South Africans — with the lowest trading fees in the country.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.24 }} className="flex flex-col sm:flex-row items-center justify-center gap-4">
        </motion.div>
      </div>
    </section>
  );
}
`;

test('wraps a real section whose root is plain <section> even when children already use framer-motion', () => {
  const out = applyAnimation(REAL_SECTION_WITH_INNER_MOTION, 'fade-up', 'framer-motion');
  assert.ok(out.applied, out.reason);
  assert.ok(out.tsx.includes('<motion.section'));
  assert.ok(out.tsx.includes('</motion.section>'));
  // inner motion elements untouched
  assert.ok(out.tsx.includes('<motion.h1'));
  assert.ok(out.tsx.includes('Proudly South African crypto, since 2020'));
});

test('is idempotent on a real section — second pass refuses because the root is now motion.section', () => {
  const once = applyAnimation(REAL_SECTION_WITH_INNER_MOTION, 'fade-up', 'framer-motion');
  const twice = applyAnimation(once.tsx, 'fade-up', 'framer-motion');
  assert.equal(twice.applied, false);
  assert.equal(twice.tsx, once.tsx);
});

test('refuses a file whose root is already <motion.section>', () => {
  const alreadyRootAnimated = `'use client';

import { motion } from 'framer-motion';

export default function Hero() {
  return (
    <motion.section initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} className="py-16">
      <h1>Buy Bitcoin South Africa</h1>
    </motion.section>
  );
}
`;
  const out = applyAnimation(alreadyRootAnimated, 'fade-up', 'framer-motion');
  assert.equal(out.applied, false);
  assert.equal(out.reason, 'root already animated');
  assert.equal(out.tsx, alreadyRootAnimated);
});

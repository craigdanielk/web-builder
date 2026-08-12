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

// --- Fix round 2: correctness bug — sibling root sections must not be
// mispaired (first open tag + last close tag), which would silently corrupt
// valid JSX. Each of these must be refused with output UNMODIFIED.

test('refuses two sibling root <section> elements rather than mispairing tags', () => {
  const siblings = `'use client';

export default function TwoSections() {
  return (
    <>
      <section id="a">A</section>
      <section id="b">B</section>
    </>
  );
}
`;
  const out = applyAnimation(siblings, 'fade-up', 'framer-motion');
  assert.equal(out.applied, false);
  assert.equal(out.tsx, siblings);
});

test('refuses when the only <section> token is inside a string literal (no real root element)', () => {
  const stringLiteral = `'use client';

export default function NoRealSection() {
  const label = '<section class="x">not real markup</section>';
  return (
    <div className="py-16">
      <p>{label}</p>
    </div>
  );
}
`;
  const out = applyAnimation(stringLiteral, 'fade-up', 'framer-motion');
  assert.equal(out.applied, false);
  assert.equal(out.tsx, stringLiteral);
});

test('refuses a mispairing that a string-literal section token would otherwise cause', () => {
  // Here the string contains an UNBALANCED fake close tag that, if not
  // masked, would pair with the real open tag and corrupt the output.
  const trap = `'use client';

export default function Trap() {
  const snippet = 'oops</section>';
  return (
    <section className="py-16">
      <p>{snippet}</p>
    </section>
  );
}
`;
  const out = applyAnimation(trap, 'fade-up', 'framer-motion');
  // Masking neutralizes the fake close tag entirely, so this still resolves
  // to exactly one real root section and wraps cleanly — the string content
  // is untouched.
  assert.ok(out.applied, out.reason);
  assert.ok(out.tsx.includes("'oops</section>'"));
});

test('refuses when the only <section> token is inside a comment (no real root element)', () => {
  const commented = `'use client';

// old markup: <section class="legacy">retired</section>
export default function NoRealSection() {
  return (
    <div className="py-16">
      <h1>Still here</h1>
    </div>
  );
}
`;
  const out = applyAnimation(commented, 'fade-up', 'framer-motion');
  assert.equal(out.applied, false);
  assert.equal(out.tsx, commented);
});

test('wraps the real root even when a decoy <section> sits in a string literal', () => {
  const stringLiteral = `'use client';

export default function Weird() {
  const snippet = '<section class="x">nope</section>';
  return (
    <section className="py-16">
      <p>{snippet}</p>
    </section>
  );
}
`;
  const out = applyAnimation(stringLiteral, 'fade-up', 'framer-motion');
  assert.ok(out.applied, out.reason);
  assert.ok(out.tsx.includes("'<section class=\"x\">nope</section>'"));
  assert.ok(out.tsx.includes('<motion.section'));
});

test('wraps the real root even when a decoy <section> sits in a comment', () => {
  const commented = `'use client';

// old markup: <section class="legacy">retired</section>
export default function Commented() {
  return (
    <section className="py-16">
      <h1>Still here</h1>
    </section>
  );
}
`;
  const out = applyAnimation(commented, 'fade-up', 'framer-motion');
  assert.ok(out.applied, out.reason);
  assert.ok(out.tsx.includes('// old markup: <section class="legacy">retired</section>'));
  assert.ok(out.tsx.includes('<motion.section'));
});

test('refuses a self-closing <section /> root', () => {
  const selfClosing = `'use client';

export default function Empty() {
  return <section className="py-16" />;
}
`;
  const out = applyAnimation(selfClosing, 'fade-up', 'framer-motion');
  assert.equal(out.applied, false);
  assert.equal(out.tsx, selfClosing);
});

test('refuses a fragment root', () => {
  const fragment = `'use client';

export default function Fragment() {
  return (
    <>
      <h1>No section here</h1>
    </>
  );
}
`;
  const out = applyAnimation(fragment, 'fade-up', 'framer-motion');
  assert.equal(out.applied, false);
  assert.equal(out.tsx, fragment);
});

test('refuses a <div> root', () => {
  const divRoot = `'use client';

export default function DivRoot() {
  return (
    <div className="py-16">
      <h1>No section here</h1>
    </div>
  );
}
`;
  const out = applyAnimation(divRoot, 'fade-up', 'framer-motion');
  assert.equal(out.applied, false);
  assert.equal(out.tsx, divRoot);
});

// --- Fix round 2: usedFallback must be a first-class boolean field, not
// something Task 7 has to regex out of `reason`.

test('returns usedFallback:false for a known library pattern', () => {
  const out = applyAnimation(PLAIN, 'fade-up', 'framer-motion');
  assert.equal(out.applied, true);
  assert.equal(out.usedFallback, false);
});

test('returns usedFallback:true for an unknown/registry pattern name', () => {
  const out = applyAnimation(PLAIN, 'codehagen__hero_badge', 'framer-motion');
  assert.equal(out.applied, true);
  assert.equal(out.usedFallback, true);
  assert.ok(out.reason.includes('fallback'));
});

test('returns usedFallback:false on refusal paths too (no misleading true)', () => {
  const weird = 'export const x = 1;';
  const out = applyAnimation(weird, 'fade-up', 'framer-motion');
  assert.equal(out.applied, false);
  assert.equal(out.usedFallback, false);
});

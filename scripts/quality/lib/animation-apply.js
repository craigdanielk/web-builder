/**
 * Apply a registry animation pattern to an already-built section body.
 *
 * Deterministic string transform, no LLM. Template-resolved sections skip the
 * LLM entirely, so animation could never reach them while it lived in the
 * prompt. This runs after fill, on every section, regardless of origin.
 *
 * Refuses rather than guesses: if no safe insertion point exists, returns the
 * input unmodified with applied:false.
 */
'use strict';

const VARIANTS = {
  'fade-up': {
    initial: '{ opacity: 0, y: 24 }',
    whileInView: '{ opacity: 1, y: 0 }',
    transition: '{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }',
  },
  'fade-in': {
    initial: '{ opacity: 0 }',
    whileInView: '{ opacity: 1 }',
    transition: '{ duration: 0.6 }',
  },
  'slide-left': {
    initial: '{ opacity: 0, x: -32 }',
    whileInView: '{ opacity: 1, x: 0 }',
    transition: '{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }',
  },
};

const DEFAULT_PATTERN = 'fade-up';

function applyAnimation(tsx, pattern, engine) {
  if (engine !== 'framer-motion') {
    return { tsx, applied: false, reason: `engine ${engine} not supported by applyAnimation` };
  }
  if (tsx.includes('<motion.')) {
    return { tsx, applied: false, reason: 'already animated' };
  }

  const v = VARIANTS[pattern] || VARIANTS[DEFAULT_PATTERN];
  const usedFallback = !VARIANTS[pattern];

  // Find the outermost <section ...> ... </section> pair.
  const open = tsx.match(/<section(\s[^>]*)?>/);
  if (!open) {
    return { tsx, applied: false, reason: 'no root <section> element found' };
  }
  const closeIdx = tsx.lastIndexOf('</section>');
  if (closeIdx === -1) {
    return { tsx, applied: false, reason: 'no closing </section> found' };
  }

  let out = tsx;

  // Rewrite the closing tag first so the earlier index stays valid.
  out = out.slice(0, closeIdx) + '</motion.section>' + out.slice(closeIdx + '</section>'.length);

  const attrs = (open[1] || '').trim();
  const motionOpen =
    `<motion.section${attrs ? ' ' + attrs : ''}` +
    ` initial={${v.initial}}` +
    ` whileInView={${v.whileInView}}` +
    ` viewport={{ once: true, amount: 0.15 }}` +
    ` transition={${v.transition}}>`;
  out = out.replace(open[0], motionOpen);

  if (!/from ['"]framer-motion['"]/.test(out)) {
    if (/^'use client';/m.test(out)) {
      out = out.replace(/^'use client';\s*/m, "'use client';\n\nimport { motion } from 'framer-motion';\n");
    } else {
      out = "import { motion } from 'framer-motion';\n" + out;
    }
  }

  const variantUsed = usedFallback ? `${DEFAULT_PATTERN} (fallback for unknown pattern '${pattern}')` : pattern;
  return { tsx: out, applied: true, reason: `applied ${variantUsed}` };
}

module.exports = { applyAnimation, VARIANTS, DEFAULT_PATTERN };

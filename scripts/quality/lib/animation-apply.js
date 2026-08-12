/**
 * Apply a registry animation pattern to an already-built section body.
 *
 * Deterministic string transform, no LLM. Template-resolved sections skip the
 * LLM entirely, so animation could never reach them while it lived in the
 * prompt. This runs after fill, on every section, regardless of origin.
 *
 * Refuses rather than guesses: if no safe insertion point exists, returns the
 * input unmodified with applied:false. A transform that mangles a valid file
 * is far worse than one that declines — so every ambiguous shape (sibling
 * root sections, a `<section>` token inside a string/comment, unbalanced
 * tags, a self-closing root) is a refusal, not a best-effort guess.
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

/**
 * Replace the contents of string/template literals and comments with spaces
 * (same length, same positions) so a naive regex scan over the result can't
 * mistake a `<section>` inside a string or comment for real markup. Callers
 * use indices found in the masked text to slice the ORIGINAL text — masking
 * never changes length or shifts offsets, only literal string/comment bytes.
 */
function maskNonCode(src) {
  let out = '';
  let i = 0;
  const n = src.length;
  while (i < n) {
    const c = src[i];
    const c2 = i + 1 < n ? src[i + 1] : '';

    if (c === '/' && c2 === '/') {
      let j = i;
      while (j < n && src[j] !== '\n') {
        out += ' ';
        j++;
      }
      i = j;
      continue;
    }

    if (c === '/' && c2 === '*') {
      let j = i;
      out += '  ';
      j += 2;
      while (j < n && !(src[j] === '*' && src[j + 1] === '/')) {
        out += src[j] === '\n' ? '\n' : ' ';
        j++;
      }
      if (j < n) {
        out += '  ';
        j += 2;
      }
      i = j;
      continue;
    }

    if (c === "'" || c === '"' || c === '`') {
      const quote = c;
      let j = i + 1;
      out += ' ';
      while (j < n && src[j] !== quote) {
        if (src[j] === '\\' && j + 1 < n) {
          out += src[j] === '\n' ? '\n' : ' ';
          out += src[j + 1] === '\n' ? '\n' : ' ';
          j += 2;
          continue;
        }
        out += src[j] === '\n' ? '\n' : ' ';
        j++;
      }
      if (j < n) {
        out += ' ';
        j++;
      }
      i = j;
      continue;
    }

    out += c;
    i++;
  }
  return out;
}

/**
 * Depth-walk the masked text for `<section>` tokens and find every
 * top-level (depth-0) element. Returns null if the tags don't balance at
 * all (caller must refuse). Otherwise returns an array of root candidates —
 * exactly one means an unambiguous root; zero or more than one means refuse.
 */
function findRootSectionSpans(maskedText) {
  const re = /<section\b([^>]*?)(\/)?>|<\/section>/g;
  const spans = [];
  let depth = 0;
  let openStart = null;
  let openTagEnd = null;
  let openAttrs = null;
  let m;

  while ((m = re.exec(maskedText))) {
    const isClose = m[0] === '</section>';

    if (isClose) {
      depth--;
      if (depth < 0) {
        return null; // closing tag with no matching open — unbalanced
      }
      if (depth === 0 && openStart !== null) {
        spans.push({
          start: openStart,
          openTagEnd,
          closeTagStart: re.lastIndex - '</section>'.length,
          end: re.lastIndex,
          selfClosing: false,
          attrs: openAttrs,
        });
        openStart = null;
        openTagEnd = null;
        openAttrs = null;
      }
      continue;
    }

    const selfClosing = m[2] === '/';
    if (depth === 0) {
      if (selfClosing) {
        spans.push({ start: m.index, end: re.lastIndex, selfClosing: true, attrs: m[1] });
      } else {
        openStart = m.index;
        openTagEnd = re.lastIndex;
        openAttrs = m[1];
        depth++;
      }
    } else if (!selfClosing) {
      depth++;
    }
  }

  if (depth !== 0) {
    return null; // open tag(s) never closed — unbalanced
  }

  return spans;
}

function applyAnimation(tsx, pattern, engine) {
  if (engine !== 'framer-motion') {
    return { tsx, applied: false, reason: `engine ${engine} not supported by applyAnimation`, usedFallback: false };
  }

  const masked = maskNonCode(tsx);

  // Root-scoped check: only refuse if the ROOT element is already a
  // motion.section. Templates legitimately carry inner <motion.h1>,
  // <motion.div>, etc. stagger animations on children — those are additive
  // to a root-level reveal, not conflicting with it, so they must not block.
  if (/<motion\.section(\s[^>]*)?>/.test(masked)) {
    return { tsx, applied: false, reason: 'root already animated', usedFallback: false };
  }

  const spans = findRootSectionSpans(masked);
  if (spans === null) {
    return { tsx, applied: false, reason: 'unbalanced <section> tags — refusing rather than guessing', usedFallback: false };
  }
  if (spans.length === 0) {
    return { tsx, applied: false, reason: 'no root <section> element found', usedFallback: false };
  }
  if (spans.length > 1) {
    return { tsx, applied: false, reason: `${spans.length} sibling root <section> elements found — refusing rather than guessing which is the root`, usedFallback: false };
  }

  const root = spans[0];
  if (root.selfClosing) {
    return { tsx, applied: false, reason: 'root is a self-closing <section /> — no body to wrap', usedFallback: false };
  }

  const v = VARIANTS[pattern] || VARIANTS[DEFAULT_PATTERN];
  const usedFallback = !VARIANTS[pattern];

  // Re-derive attrs from the ORIGINAL open tag text, not the masked match —
  // masking blanks out string contents (e.g. className="py-16" -> spaces),
  // and root.attrs came from the masked text used only for tag-position
  // detection.
  const originalOpenTag = tsx.slice(root.start, root.openTagEnd);
  const originalOpenMatch = originalOpenTag.match(/^<section\s?([^]*?)\/?>$/);
  const attrs = (originalOpenMatch ? originalOpenMatch[1] : '').trim();
  const motionOpen =
    `<motion.section${attrs ? ' ' + attrs : ''}` +
    ` initial={${v.initial}}` +
    ` whileInView={${v.whileInView}}` +
    ` viewport={{ once: true, amount: 0.15 }}` +
    ` transition={${v.transition}}>`;

  // All offsets came from the masked text but map 1:1 onto the original
  // (masking never changes length or shifts positions), so a single
  // reconstruction from precise stored offsets is safe — no re-searching.
  let out =
    tsx.slice(0, root.start) +
    motionOpen +
    tsx.slice(root.openTagEnd, root.closeTagStart) +
    '</motion.section>' +
    tsx.slice(root.closeTagStart + '</section>'.length);

  if (!/from ['"]framer-motion['"]/.test(out)) {
    if (/^'use client';/m.test(out)) {
      out = out.replace(/^'use client';\s*/m, "'use client';\n\nimport { motion } from 'framer-motion';\n");
    } else {
      out = "import { motion } from 'framer-motion';\n" + out;
    }
  }

  const variantUsed = usedFallback ? `${DEFAULT_PATTERN} (fallback for unknown pattern '${pattern}')` : pattern;
  return { tsx: out, applied: true, reason: `applied ${variantUsed}`, usedFallback };
}

module.exports = { applyAnimation, VARIANTS, DEFAULT_PATTERN };

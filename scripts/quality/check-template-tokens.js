#!/usr/bin/env node
/**
 * check-template-tokens — the section-template conversion diagnostic, committed.
 *
 * WHY THIS FILE EXISTS
 *
 * The diagnostic that has circulated for two sessions is a one-line grep:
 *
 *   grep -oE "bg-white|text-gray-[0-9]+|bg-gray-[0-9]+|py-[0-9]+" <template>
 *
 * It is wrong twice over, and both wrongs read as "the conversion is
 * incomplete" when it is not:
 *
 *   1. `py-[0-9]+` flags `px-8 py-4` on a button and `py-6` on an accordion
 *      row. Component-internal padding is CORRECT — it is the outer <section>,
 *      and only the outer <section>, that must take its rhythm from the design
 *      system. A card's inner padding is the card's business.
 *
 *   2. It matches prose inside the header comment. Every converted template
 *      documents which literals it replaced ("shipped `bg-white text-gray-900
 *      py-24`"), so the more thoroughly a file is converted, the more hits the
 *      grep returns.
 *
 * It also gets retyped slightly differently every session, so no two
 * measurements are comparable. Hence: a script, with tests.
 *
 * THE TWO REAL TESTS
 *   (a) palette-literal — zero OPAQUE palette literals outside comments.
 *   (b) section-rhythm  — the outer <section> takes its vertical rhythm from
 *                         var(--section-py).
 *
 * TRANSLUCENT OVERLAYS ARE NOT VIOLATIONS (they are warnings).
 * `bg-white/5` is a scrim: its job is to lighten whatever sits beneath it, not
 * to declare a colour role. It is a different defect class from `bg-white`,
 * which asserts an absolute ground the text was never measured against. But it
 * is not innocent either — a scrim still assumes which way the ground runs. So
 * it is reported on its own channel (`translucent-overlay`, warning) where it
 * is visible without hard-failing a gate on a decision that has not been made.
 * Task E2 owns that decision.
 *
 * CONTRACT
 *   node scripts/quality/check-template-tokens.js [dir]
 *     → prints `<file>:<line> <rule> <snippet>` per violation
 *     → exit 0 clean, exit 1 violations found
 *   Exported: check(source) · checkFile(path) · checkDir(dir)
 */

const fs = require('fs');
const path = require('path');

const { describe } = require('./lib/capability');

/** What this instrument is, in its own words. Compiled into the capability
 *  register by `scripts/capability_register.py`; see that file for why it lives
 *  here rather than in a separate document. */
const CAPABILITY = {
  id: 'aurelix.gate.template-tokens',
  name: 'Section-template token conversion check',
  kind: 'gate',
  invocation: 'node scripts/quality/check-template-tokens.js [dir]   (default: section-templates/)',
  preconditions: [
    'a directory of .tsx section templates on disk; defaults to web-builder/section-templates',
  ],
  inputs: ['every .tsx under the target directory, recursively, skipping node_modules and dot-directories'],
  outputs: [],
  outcome: 'which templates still hardcode an opaque palette literal, and which outer <section> does not take its vertical rhythm from var(--section-py)',
  exit_contract: {
    0: 'PASS — no violations in any template scanned',
    1: 'FAIL — at least one violation. NOTE: a missing target directory ALSO returns 1, so "the directory is not there" and "the templates are wrong" are the same exit code',
  },
  measures: [
    'opaque Tailwind palette literals (bg|text|border|ring|fill|stroke|divide|from|via|to)-(white|black|gray/grey/slate/zinc/neutral/stone-NNN) outside comments and outside strings',
    'whether the outer <section> returned by the default export carries --section-py in its opening tag',
    'translucent overlays (bg-white/5 and kin) on a separate WARNING channel that never affects the exit code',
  ],
  cannot_see: [
    'the database tier — it walks a filesystem directory, and the unconverted templates are the ' +
      '74 rows of section_archetypes.code_template, which never touch disk and are therefore never scanned',
    'a palette literal written as a hex or an arbitrary value: the regex names Tailwind colour FAMILIES, ' +
      'so #ffffff, bg-[#0b0b0b] and style={{color:"white"}} all pass',
    'rendered colour — it is a text scan, so a template reading var(--surface) passes even when that ' +
      'token compiles to the wrong value, which is exactly what the conformance gate looks at instead',
    'rhythm on any root element other than <section>: a <header> or <footer> root is deliberately exempt, ' +
      'so a footer with hardcoded py-24 is invisible here',
    'whether the template renders at all — it never parses, compiles or executes the file',
  ],
  reachable_from: ['scripts/quality/check-template-tokens.test.js (imported as a module by the tests)', 'standalone CLI'],
  cost: 'under a second over the 15 local templates; no network, no build, no database',
};

// ---------------------------------------------------------------------------
// Rule (a): opaque palette literals.
//
// Deliberately narrow. Every entry here names an ABSOLUTE colour — a value that
// cannot follow a benchmark. Anything with a `/opacity` suffix is excluded by
// the negative lookahead and handled as a warning instead. Tailwind variant
// prefixes (`hover:`, `md:`, `dark:`) are covered because the boundary before
// each pattern is a `:` or whitespace, both non-word characters.
// ---------------------------------------------------------------------------
const PALETTE_LITERAL = new RegExp(
  [
    '\\b(?:bg|text|border|ring|fill|stroke|divide|from|via|to)-',
    '(?:white|black|(?:gray|grey|slate|zinc|neutral|stone)-\\d{2,3})',
    '\\b(?!/)',
  ].join(''),
  'g',
);

// The same families WITH an opacity suffix — a scrim, not a ground.
const TRANSLUCENT_OVERLAY = new RegExp(
  [
    '\\b(?:bg|text|border|ring|fill|stroke|divide|from|via|to)-',
    '(?:white|black|(?:gray|grey|slate|zinc|neutral|stone)-\\d{2,3})',
    '/\\d{1,3}\\b',
  ].join(''),
  'g',
);

const SECTION_RHYTHM_TOKEN = '--section-py';

/**
 * Blank out comments, preserving every byte offset and line break so that
 * line numbers and snippets still refer to the original source.
 *
 * Handles `//` line comments and block comments, and refuses to treat the `//`
 * in `"https://…"` as a comment by tracking string state. Not a full JS lexer —
 * regex literals are not tracked — but the only way that misfires is a regex
 * containing an unbalanced quote, which no template has.
 */
function stripComments(source) {
  const out = source.split('');
  let i = 0;
  const n = source.length;
  const blank = (from, to) => {
    for (let k = from; k < to && k < n; k++) {
      if (out[k] !== '\n') out[k] = ' ';
    }
  };

  while (i < n) {
    const c = source[i];
    const next = source[i + 1];

    if (c === '"' || c === "'" || c === '`') {
      const quote = c;
      i++;
      while (i < n) {
        if (source[i] === '\\') { i += 2; continue; }
        if (source[i] === quote) { i++; break; }
        i++;
      }
      continue;
    }

    if (c === '/' && next === '/') {
      let end = source.indexOf('\n', i);
      if (end === -1) end = n;
      blank(i, end);
      i = end;
      continue;
    }

    if (c === '/' && next === '*') {
      let end = source.indexOf('*/', i + 2);
      end = end === -1 ? n : end + 2;
      blank(i, end);
      i = end;
      continue;
    }

    i++;
  }

  return out.join('');
}

/**
 * Locate the opening tag of the outer JSX element returned by the default
 * export: the first `return` inside that export whose next meaningful character
 * begins a JSX element. `return null;` guards (a template returns null rather
 * than render a heading over nothing) are skipped, as they must be.
 *
 * Returns { tagName, open, close, line } or null when the file has no default
 * export or returns no JSX.
 */
function findOuterElement(stripped) {
  const exportMatch = /export\s+default\s/.exec(stripped);
  if (!exportMatch) return null;

  const returnRe = /\breturn\b/g;
  returnRe.lastIndex = exportMatch.index;

  let m;
  while ((m = returnRe.exec(stripped)) !== null) {
    let j = m.index + m[0].length;
    // Skip whitespace and the wrapping parens of `return (\n  <section …`.
    while (j < stripped.length && (/\s/.test(stripped[j]) || stripped[j] === '(')) j++;
    if (stripped[j] !== '<') continue;

    const tagMatch = /^<([A-Za-z][\w.:-]*)/.exec(stripped.slice(j));
    if (!tagMatch) continue;

    const close = findTagClose(stripped, j);
    if (close === -1) continue;

    return {
      tagName: tagMatch[1],
      open: j,
      close,
      line: lineOf(stripped, j),
    };
  }
  return null;
}

/**
 * End of the opening tag that starts at `start` — the `>` at brace/paren depth
 * zero. JSX attribute values are expressions (`style={{ … }}`), so a naive
 * search for the next `>` lands inside `=>` or a comparison. Strings are
 * skipped wholesale.
 */
function findTagClose(source, start) {
  let depth = 0;
  for (let i = start + 1; i < source.length; i++) {
    const c = source[i];
    if (c === '"' || c === "'" || c === '`') {
      const quote = c;
      i++;
      while (i < source.length) {
        if (source[i] === '\\') { i += 2; continue; }
        if (source[i] === quote) break;
        i++;
      }
      continue;
    }
    if (c === '{') { depth++; continue; }
    if (c === '}') { depth--; continue; }
    if (c === '>' && depth === 0) return i;
  }
  return -1;
}

function lineOf(source, index) {
  let line = 1;
  for (let i = 0; i < index && i < source.length; i++) {
    if (source[i] === '\n') line++;
  }
  return line;
}

function snippetOf(source, line) {
  const text = (source.split('\n')[line - 1] || '').trim();
  return text.length > 120 ? `${text.slice(0, 117)}...` : text;
}

/**
 * check(source, file?) → { violations, warnings }
 *
 * violations/warnings entries: { file, line, rule, snippet }
 * At most one entry per (line, rule) — a className carrying two literals is one
 * defect on one line, not two.
 */
function check(source, file = '<source>') {
  const stripped = stripComments(source);
  const violations = [];
  const warnings = [];
  const seen = new Set();

  const record = (bucket, line, rule) => {
    const key = `${line}:${rule}`;
    if (seen.has(key)) return;
    seen.add(key);
    bucket.push({ file, line, rule, snippet: snippetOf(source, line) });
  };

  // (a) opaque palette literals, outside comments.
  let m;
  PALETTE_LITERAL.lastIndex = 0;
  while ((m = PALETTE_LITERAL.exec(stripped)) !== null) {
    record(violations, lineOf(stripped, m.index), 'palette-literal');
  }

  TRANSLUCENT_OVERLAY.lastIndex = 0;
  while ((m = TRANSLUCENT_OVERLAY.exec(stripped)) !== null) {
    record(warnings, lineOf(stripped, m.index), 'translucent-overlay');
  }

  // (b) the outer <section> takes its rhythm from var(--section-py).
  // Only <section>. A <header> nav has no section rhythm (it has --nav-py) and
  // a <footer> is checked by whatever owns footer rhythm — widening this rule
  // to every root tag is how the old grep started flagging button padding.
  const outer = findOuterElement(stripped);
  if (outer && outer.tagName === 'section') {
    const openingTag = stripped.slice(outer.open, outer.close + 1);
    if (!openingTag.includes(SECTION_RHYTHM_TOKEN)) {
      record(violations, outer.line, 'section-rhythm');
    }
  }

  violations.sort((a, b) => a.line - b.line);
  warnings.sort((a, b) => a.line - b.line);
  return { violations, warnings };
}

function checkFile(filePath) {
  const source = fs.readFileSync(filePath, 'utf8');
  return check(source, filePath);
}

/** Recursively check every .tsx under `dir`. */
function checkDir(dir) {
  const files = [];
  const walk = (d) => {
    for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
      const full = path.join(d, entry.name);
      if (entry.isDirectory()) {
        if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue;
        walk(full);
      } else if (entry.name.endsWith('.tsx')) {
        files.push(full);
      }
    }
  };
  walk(dir);
  files.sort();

  const violations = [];
  const warnings = [];
  for (const file of files) {
    const result = checkFile(file);
    violations.push(...result.violations);
    warnings.push(...result.warnings);
  }
  return { files, violations, warnings };
}

function main(argv) {
  if (describe(CAPABILITY, argv.slice(2))) return 0;
  const target = argv[2] || path.resolve(__dirname, '../../section-templates');
  if (!fs.existsSync(target)) {
    process.stderr.write(`check-template-tokens: no such directory: ${target}\n`);
    return 1;
  }

  const { files, violations, warnings } = checkDir(target);

  for (const v of violations) {
    process.stdout.write(`${v.file}:${v.line} ${v.rule} ${v.snippet}\n`);
  }
  for (const w of warnings) {
    process.stdout.write(`${w.file}:${w.line} ${w.rule} (warning) ${w.snippet}\n`);
  }

  const suffix = warnings.length ? `, ${warnings.length} warning(s)` : '';
  process.stdout.write(
    `check-template-tokens: ${files.length} template(s), ${violations.length} violation(s)${suffix}\n`,
  );
  return violations.length ? 1 : 0;
}

if (require.main === module) {
  process.exit(main(process.argv));
}

module.exports = { check, checkFile, checkDir, stripComments, findOuterElement };

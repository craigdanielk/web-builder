const { test } = require('node:test');
const assert = require('node:assert');
const path = require('path');
const { check, checkDir } = require('./check-template-tokens');

const TEMPLATES_DIR = path.resolve(__dirname, '../../section-templates');

// ============================================================================
// THE TWO REAL TESTS
//
// The diagnostic that has circulated for two sessions is:
//
//   grep -oE "bg-white|text-gray-[0-9]+|bg-gray-[0-9]+|py-[0-9]+" <template>
//
// It is wrong twice over. It flags `px-8 py-4` on a button and `py-6` on an
// accordion row — component-internal padding, which is CORRECT and has nothing
// to do with the design system — and it matches prose inside the header comment
// that explains which literals were removed. Both false positives have been
// read as "the conversion is incomplete" by at least two sessions.
//
// The two things that actually matter:
//   (a) zero OPAQUE palette literals outside comments;
//   (b) the outer <section> takes its rhythm from var(--section-py).
// ============================================================================

test('button padding is not a violation', () => {
  // px-8 py-4 on a button is component-internal padding, not section rhythm.
  assert.deepEqual(check('<button className="px-8 py-4">').violations, []);
});

test('a palette literal in a comment is not a violation', () => {
  const source = '// was bg-white before conversion\n<div className="bg-[var(--surface)]">';
  assert.deepEqual(check(source).violations, []);
});

test('a palette literal in a block comment is not a violation', () => {
  const source = '/**\n * shipped `bg-white text-gray-900 py-24`\n */\n<div className="bg-[var(--surface)]">';
  assert.deepEqual(check(source).violations, []);
});

test('an opaque palette literal in markup is a violation', () => {
  const result = check('<div className="bg-white text-gray-900">');
  assert.equal(result.violations.length, 1);
  assert.equal(result.violations[0].rule, 'palette-literal');
});

test('outer section without var(--section-py) is a violation', () => {
  const result = check('export default function S(){return <section className="py-24">;}');
  assert.equal(result.violations[0].rule, 'section-rhythm');
});

test('outer section with var(--section-py) is not a violation', () => {
  const source =
    'export default function S(){return <section style={{ paddingTop: "var(--section-py, 96px)" }} />;}';
  assert.deepEqual(check(source).violations, []);
});

test('an early `return null` does not hide the outer section', () => {
  const source =
    'export default function S({items}){\n' +
    '  if (!items.length) return null;\n' +
    '  return <section className="py-24">{items}</section>;\n' +
    '}';
  assert.equal(check(source).violations[0].rule, 'section-rhythm');
});

test('a nested <section> is not the outer element and is not rhythm-checked', () => {
  const source =
    'export default function S(){\n' +
    '  return <div style={{ padding: "var(--section-py, 96px)" }}><section className="py-6" /></div>;\n' +
    '}';
  assert.deepEqual(check(source).violations, []);
});

test('violations carry the line number of the offending markup', () => {
  const source = '// bg-white\n\n<div className="bg-white">';
  const result = check(source);
  assert.equal(result.violations.length, 1);
  assert.equal(result.violations[0].line, 3);
});

test('all committed local templates pass', async () => {
  const result = await checkDir(TEMPLATES_DIR);
  assert.ok(result.files.length >= 14, `expected >= 14 templates, found ${result.files.length}`);
  assert.deepEqual(
    result.violations.map((v) => `${v.file}:${v.line} ${v.rule} ${v.snippet}`),
    [],
  );
});

// Smoke test: the audit must complete on a page with slow third-party images
// and must report per-section facts, not just counts.
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

const REPORT = process.env.RA_REPORT;

test('report exists', () => {
  assert.ok(REPORT && fs.existsSync(REPORT), `no report at ${REPORT}`);
});

test('every route carries raw facts', () => {
  const r = JSON.parse(fs.readFileSync(REPORT, 'utf8'));
  assert.ok(Array.isArray(r.routes) && r.routes.length > 0, 'no routes in report');
  for (const route of r.routes) {
    assert.ok(route.facts, `route ${route.route} has no facts`);
    assert.ok(Array.isArray(route.facts.sections), `route ${route.route} facts.sections missing`);
  }
});

test('per-section dimensions and text length are present', () => {
  const r = JSON.parse(fs.readFileSync(REPORT, 'utf8'));
  const home = r.routes.find((x) => x.route === '/');
  assert.ok(home, 'no / route');
  for (const s of home.facts.sections) {
    assert.equal(typeof s.h, 'number', 'section height missing');
    assert.equal(typeof s.textLen, 'number', 'section textLen missing');
  }
});

test('viewport-triggered sections are not reported as empty', () => {
  const r = JSON.parse(fs.readFileSync(REPORT, 'utf8'));
  const home = r.routes.find((x) => x.route === '/');
  const withText = home.facts.sections.filter((s) => s.textLen > 50);
  assert.ok(withText.length >= 4, `only ${withText.length} sections had text — scroll likely did not fire`);
});

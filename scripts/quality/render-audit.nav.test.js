// A one-page site navigates by in-page fragments. render_nav reported THURIS's
// nav (#collection, #ritual, #origin, #preorder) as "no links to real in-site
// routes" although every fragment names a section on the page. A fragment link
// now counts as reachable when the probe found its target id on the page; a
// dangling fragment still does not.
//
//   node --test scripts/quality/render-audit.nav.test.js
const { test } = require('node:test');
const assert = require('node:assert');
const { toDefects } = require('./render-audit');

const res = (navLinks) => ({
  route: '/', status: 200,
  facts: { sections: [], images: [], navLinks, lowContrast: [] },
  consoleErrors: [],
});

const navDefects = (navLinks) => toDefects(res(navLinks), ['/']).filter((d) => d.category === 'render_nav' || d.type === 'render_nav' || /render_nav/.test(JSON.stringify(d)));

test('fragment links whose targets exist are reachable navigation', () => {
  const d = navDefects([
    { text: 'The Collection', href: '#collection', targetExists: true },
    { text: 'Ritual', href: '#ritual', targetExists: true },
  ]);
  assert.strictEqual(d.length, 0, JSON.stringify(d));
});

test('dangling fragments are still unreachable', () => {
  const d = navDefects([
    { text: 'Gone', href: '#nowhere', targetExists: false },
    { text: 'Also gone', href: '#missing' },
  ]);
  assert.ok(d.some((x) => /no links to real in-site routes/.test(JSON.stringify(x))), JSON.stringify(d));
});

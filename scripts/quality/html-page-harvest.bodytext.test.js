// A list item that WRAPS block content (<li><h3/><p/><span/></li>) is a card,
// not a sentence. extractBodyText matched the whole <li> and flattened heading,
// paragraph and span into one string ("Frankincense Boswellia serrata India"),
// so THURIS's origin cards ran species and country together. A container with
// block children is descended into; a plain <li>text</li> is still one string.
//
//   node --test scripts/quality/html-page-harvest.bodytext.test.js
const { test } = require('node:test');
const assert = require('node:assert');
const { extractBodyText } = require('./lib/html-page-harvest');

test('li wrapping block children yields the children, not a flattened string', () => {
  const out = extractBodyText('<ul><li class="row"><h3>Frankincense</h3><p>Boswellia serrata</p><span>India</span></li></ul>');
  assert.deepStrictEqual(out, ['Boswellia serrata']);
});

test('plain list items are still one string each', () => {
  assert.deepStrictEqual(
    extractBodyText('<ul><li>First plain item</li><li>Second <b>bold</b> item</li></ul>'),
    ['First plain item', 'Second bold item'],
  );
});

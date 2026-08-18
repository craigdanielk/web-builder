#!/usr/bin/env node
// One-off: run the deterministic Playwright reference extractor for AA competitor analysis.
'use strict';
const fs = require('fs');
const path = require('path');
const { extractReference } = require('./lib/extract-reference');
const { describe } = require('./lib/capability');

/** What this instrument is, in its own words. Compiled into the capability
 *  register by `scripts/capability_register.py`. */
const CAPABILITY = {
  id: 'aurelix.extractor.run-extract-aa',
  name: 'Reference extractor CLI (raw extractReference to a directory)',
  kind: 'extractor',
  invocation: 'node scripts/quality/run-extract-aa.js <url> <outDir>',
  preconditions: [
    'playwright chromium installed — extractReference() launches a real browser',
    'the URL reachable over the network from this machine',
    '<outDir> writable; it is created recursively',
  ],
  inputs: ['a live URL'],
  outputs: [
    '<outDir>/extract.json — the whole extractReference() return value, unfiltered and unscored',
    'whatever extractReference() itself persists into <outDir> (screenshots, section crops)',
  ],
  outcome: 'the raw extraction object for one page on disk, plus its top-level key list on stdout — the thinnest possible operator handle on extractReference()',
  exit_contract: {
    0: 'extract.json written',
    1: 'usage error — <url> or <outDir> missing',
    2: 'EXTRACT_FAIL — extractReference() or the write threw',
  },
  measures: [
    'exactly what extractReference() returns for one URL: rendered DOM with computed styles, sections, text content, assets, raw animation evidence',
  ],
  cannot_see: [
    'one page and one 1440x900 desktop viewport — extractReference\'s fixed capture; no interior page is followed and no narrow breakpoint is exercised',
    'meaning: it SCORES nothing. It does not call analyzeAnimationEvidence, so animations.evidence stays raw and animations.profile is absent — capture-benchmark-pages.js exists because this wire has to be made by the caller',
    'whether the extraction is empty in the way that matters: it writes and exits 0 on a result with zero sections and zero text, which is indistinguishable here from a genuinely sparse page',
    'whether the page it got is the page it asked for — a redirect, geo-block or bot wall is captured as a successful extraction',
    'anything behind auth, interaction, or a consent overlay',
  ],
  reachable_from: [],
  cost: 'one browser launch and full scroll-capture — roughly 30-120s; writes a multi-MB extract.json',
};

(async () => {
  if (describe(CAPABILITY)) return;
  const url = process.argv[2];
  const outDir = process.argv[3];
  if (!url || !outDir) { console.error('usage: run-extract-aa.js <url> <outDir>'); process.exit(1); }
  fs.mkdirSync(outDir, { recursive: true });
  const data = await extractReference(url, outDir);
  const jsonPath = path.join(outDir, 'extract.json');
  fs.writeFileSync(jsonPath, JSON.stringify(data, null, 2));
  console.log('WROTE ' + jsonPath);
  // brief top-level summary to stdout
  const keys = data && typeof data === 'object' ? Object.keys(data) : [];
  console.log('TOP_KEYS ' + JSON.stringify(keys));
})().catch(e => { console.error('EXTRACT_FAIL', e && e.message); process.exit(2); });

#!/usr/bin/env node
// One-off: run the deterministic Playwright reference extractor for AA competitor analysis.
'use strict';
const fs = require('fs');
const path = require('path');
const { extractReference } = require('./lib/extract-reference');

(async () => {
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

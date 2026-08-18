#!/usr/bin/env node
// Classify the sections of a PERSISTED capture corpus, and report the measured
// reference sequence per page.
//
// WHY THIS EXISTS
// `extract-reference.js` now annotates sections with an archetype at capture
// time, but the corpora already on disk were captured before that field
// existed. Re-capturing to obtain a label the classifier can derive from what
// is already persisted would be a second measurement of the same site on a
// different day — the corpus exists precisely so that does not have to happen.
//
// WHAT IT IS NOT
// It is not a second classifier. It calls `annotateSectionArchetypes` from
// `lib/archetype-mapper.js`, the same function `extract-reference.js` calls,
// with the same threshold. A section the mapper cannot place above the
// threshold is reported NOT_MEASURED, never a default archetype.
//
// USAGE
//   node scripts/quality/annotate-corpus-archetypes.js <corpus-dir> [--json]
//   node scripts/quality/annotate-corpus-archetypes.js <corpus-dir> --write [--out <dir>]
//
// `--write` rewrites `<slug>/extraction.json` with the annotation. Without
// `--out` that is in place; with `--out` the whole corpus is copied there
// first, so a corpus owned by another lane is never touched.
//
// EXIT CODES
//   0   every page classified (some sections may be NOT_MEASURED — that is a
//       measurement, not a failure)
//   3   NOT_MEASURED — no page in the corpus carried sections
//   64  usage error

'use strict';

const fs = require('fs');
const path = require('path');
const { annotateSectionArchetypes } = require('./lib/archetype-mapper');

const EXIT_OK = 0;
const EXIT_NOT_MEASURED = 3;
const EXIT_USAGE = 64;

function usage(msg) {
  process.stderr.write(`annotate-corpus-archetypes.js: ${msg}\n`);
  process.stderr.write(
    'usage: <corpus-dir> [--json] [--write] [--out <dir>]\n'
  );
  process.exit(EXIT_USAGE);
}

function parseArgs(argv) {
  const out = { corpus: null, json: false, write: false, outDir: null };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--json') out.json = true;
    else if (a === '--write') out.write = true;
    else if (a === '--out') {
      if (i + 1 >= argv.length) usage('--out needs a value');
      i += 1;
      out.outDir = argv[i];
    } else if (a.startsWith('--')) usage(`unknown flag ${a}`);
    else if (out.corpus === null) out.corpus = a;
    else usage(`unexpected argument ${a}`);
  }
  if (!out.corpus) usage('a corpus directory is required');
  return out;
}

/** Read `index.json` and return its page slugs, in corpus order. */
function corpusSlugs(corpusDir) {
  const indexPath = path.join(corpusDir, 'index.json');
  if (!fs.existsSync(indexPath)) {
    usage(`no corpus index at ${indexPath}`);
  }
  const index = JSON.parse(fs.readFileSync(indexPath, 'utf-8'));
  return index.map((e) => e.slug);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const corpusDir = path.resolve(args.corpus);
  const slugs = corpusSlugs(corpusDir);

  let targetDir = corpusDir;
  if (args.write && args.outDir) {
    targetDir = path.resolve(args.outDir);
    fs.cpSync(corpusDir, targetDir, { recursive: true });
  }

  const pages = [];
  let totalSections = 0;

  for (const slug of slugs) {
    const src = path.join(corpusDir, slug, 'extraction.json');
    if (!fs.existsSync(src)) {
      pages.push({ slug, status: 'NOT_MEASURED', reason: 'no extraction.json' });
      continue;
    }
    const data = JSON.parse(fs.readFileSync(src, 'utf-8'));
    const result = annotateSectionArchetypes(data.sections || [], data.textContent);
    totalSections += result.sections.length;

    pages.push({
      slug,
      url: data.url,
      status: 'MEASURED',
      section_count: result.sections.length,
      measured: result.measured,
      not_measured: result.notMeasured,
      min_confidence: result.minConfidence,
      sequence: result.sections.map((s) => ({
        index: s.index,
        archetype: s.archetype,
        variant: s.archetype_variant,
        confidence: s.archetype_confidence,
        method: s.archetype_method,
        status: s.archetype_status,
        label: s.label || '',
      })),
    });

    if (args.write) {
      data.sections = result.sections;
      const dest = path.join(targetDir, slug, 'extraction.json');
      fs.writeFileSync(dest, `${JSON.stringify(data, null, 2)}\n`);
    }
  }

  if (args.json) {
    process.stdout.write(`${JSON.stringify({ corpus: corpusDir, pages }, null, 2)}\n`);
  } else {
    for (const p of pages) {
      if (p.status !== 'MEASURED') {
        process.stdout.write(`\n${p.slug}: NOT_MEASURED — ${p.reason}\n`);
        continue;
      }
      process.stdout.write(
        `\n${p.slug}  (${p.section_count} sections: ${p.measured} measured, ` +
          `${p.not_measured} NOT_MEASURED)\n`
      );
      for (const s of p.sequence) {
        const name =
          s.status === 'MEASURED'
            ? `${s.archetype}/${s.variant}`
            : 'NOT_MEASURED';
        process.stdout.write(
          `  ${String(s.index).padStart(2)}  ${name.padEnd(34)} ` +
            `${s.confidence.toFixed(2)}  ${s.method}\n`
        );
      }
    }
    if (args.write) {
      process.stdout.write(`\nwrote annotated corpus to ${targetDir}\n`);
    }
  }

  // No sections anywhere is not an empty pass: the corpus measured nothing.
  return totalSections > 0 ? EXIT_OK : EXIT_NOT_MEASURED;
}

process.exit(main());

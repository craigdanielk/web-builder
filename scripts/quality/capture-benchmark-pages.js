#!/usr/bin/env node
// Capture reference pages as benchmark source material, and PERSIST the corpus.
//
// PATTERNS ONLY — the downstream compile lifts no markup, copy, asset or SVG.
// See scripts/commission_benchmark.py, which reads what this writes.
//
// PROVENANCE OF THIS FILE
// Recovered from git (`git show 9805e275^:scripts/quality/capture-benchmark-pages.js`,
// 41 lines) and generalised. The original hardcoded an absolute `require`, six
// Robinhood URLs, and — the defect this rewrite exists to fix — an absolute OUT
// path inside a prior session's scratchpad. Both prior capture corpora were
// written there and are gone, which is the direct reason the benchmark census
// had to reconstruct production from git rather than re-run it
// (docs/census/2026-08-17-benchmark-production.md §6.3). The corpus is the
// evidence for every number in a benchmark, so it is now written under
// `benchmarks/corpora/<market-slug>/` by default.
//
// THE `why` FIELD IS REQUIRED INPUT, NOT DECORATION
// It is the only thing that makes `_meta.captured_from` provenanced, and both
// existing benchmarks carry it (census §6.2). A page list entry missing `why`
// is a usage error, not a warning.
//
// THE ANIMATION WIRE
// `extract-reference.js:1071` returns `animations.evidence = rawAnimationEvidence`
// — the RAW output of `extractAnimationData()`, NOT the scored profile. (The
// census expected to find `analyzeAnimationEvidence()` already called there;
// `grep -n analyzeAnimationEvidence scripts/quality/lib/extract-reference.js`
// returns 0 hits.) So this step calls it and writes the result to
// `animations.profile`, which is where the compiler reads `intensity.{level,
// score, confidence}` from. The compiler does NOT re-derive intensity from a
// CSS-duration histogram — that is a second, disagreeing measurement of the
// same property.
//
// USAGE
//   node scripts/quality/capture-benchmark-pages.js --market <slug> \
//        --pages <pages.json> [--out <dir>]
//
//   node scripts/quality/capture-benchmark-pages.js --market <slug> \
//        --page 'home|https://example.com/|HERO, NAV, FOOTER' \
//        --page 'about|https://example.com/about|ABOUT, TEAM'
//
// `<pages.json>` is either an array of `[slug, url, why]` triples or an array
// of `{slug, url, why}` objects.
//
// EXIT CODES
//   0   every page captured
//   3   NOT_MEASURED — no page captured; the corpus index is still written so
//       the failure is inspectable
//   64  usage error

const path = require('path');
const fs = require('fs');
const { extractReference } = require('./lib/extract-reference.js');
const { analyzeAnimationEvidence } = require('./lib/animation-detector.js');

const WEB_BUILDER = path.resolve(__dirname, '..', '..');
const EXIT_OK = 0;
const EXIT_NOT_MEASURED = 3;
const EXIT_USAGE = 64;

function usage(msg) {
  process.stderr.write(`capture-benchmark-pages.js: ${msg}\n`);
  process.stderr.write(
    'usage: --market <slug> (--pages <file.json> | --page "slug|url|why" ...) ' +
      '[--out <dir>]\n'
  );
  process.exit(EXIT_USAGE);
}

function parseArgs(argv) {
  const out = { market: null, pages: null, pageSpecs: [], outDir: null };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    const next = () => {
      if (i + 1 >= argv.length) usage(`${a} needs a value`);
      i += 1;
      return argv[i];
    };
    if (a === '--market') out.market = next();
    else if (a === '--pages') out.pages = next();
    else if (a === '--page') out.pageSpecs.push(next());
    else if (a === '--out') out.outDir = next();
    else usage(`unknown argument ${a}`);
  }
  return out;
}

// A page is [slug, url, why]. `why` names the archetypes the page is captured
// for; it is required so the benchmark's captured_from is provenanced.
function normalisePages(args) {
  const raw = [];
  if (args.pages) {
    const parsed = JSON.parse(fs.readFileSync(args.pages, 'utf8'));
    if (!Array.isArray(parsed)) usage(`${args.pages} must hold a JSON array`);
    for (const entry of parsed) {
      if (Array.isArray(entry)) raw.push({ slug: entry[0], url: entry[1], why: entry[2] });
      else raw.push({ slug: entry.slug, url: entry.url, why: entry.why });
    }
  }
  for (const spec of args.pageSpecs) {
    const parts = spec.split('|');
    raw.push({ slug: parts[0], url: parts[1], why: parts.slice(2).join('|') });
  }
  if (raw.length === 0) usage('no pages given; pass --pages or --page');

  const seen = new Set();
  return raw.map((p, idx) => {
    const slug = String(p.slug || '').trim();
    const url = String(p.url || '').trim();
    const why = String(p.why || '').trim();
    if (!slug) usage(`page ${idx}: slug is required`);
    if (!/^[a-z0-9][a-z0-9-]*$/.test(slug)) {
      usage(`page ${idx}: slug ${JSON.stringify(slug)} must be [a-z0-9-]`);
    }
    if (!/^https?:\/\//.test(url)) {
      usage(`page ${slug}: url must be http(s), got ${JSON.stringify(url)}`);
    }
    if (!why) {
      usage(
        `page ${slug}: "why" is required — it is the page-selection rationale ` +
          'that provenances _meta.captured_from. An unexplained capture is an ' +
          'unexplained benchmark.'
      );
    }
    if (seen.has(slug)) usage(`duplicate slug ${slug}`);
    seen.add(slug);
    return { slug, url, why };
  });
}

(async () => {
  const args = parseArgs(process.argv.slice(2));
  if (!args.market) usage('--market <slug> is required');
  if (!/^[a-z0-9][a-z0-9-]*$/.test(args.market)) {
    usage(`--market ${JSON.stringify(args.market)} must be [a-z0-9-]`);
  }
  const pages = normalisePages(args);

  // Named, in-repo, per-market. Not a scratch path — see the header.
  const OUT = args.outDir
    ? path.resolve(args.outDir)
    : path.join(WEB_BUILDER, 'benchmarks', 'corpora', args.market);

  fs.mkdirSync(OUT, { recursive: true });
  const index = [];
  let ok = 0;

  for (const { slug, url, why } of pages) {
    const dir = path.join(OUT, slug);
    fs.mkdirSync(dir, { recursive: true });
    process.stderr.write(`\n=== ${slug} ${url}\n    why: ${why}\n`);
    try {
      const res = await extractReference(url, dir);

      // The animation wire (see header). Failure here must not lose a capture
      // that otherwise succeeded — the compiler treats a missing profile as
      // motion NOT_MEASURED, which is the honest outcome.
      let profileError = null;
      try {
        res.animations = res.animations || {};
        res.animations.profile = analyzeAnimationEvidence(
          res.animations.evidence || {},
          res.animations.networkResults || {},
          res.sections || [],
          res.renderedDOM || []
        );
      } catch (e) {
        profileError = String((e && e.message) || e);
        process.stderr.write(`    animation profile FAILED ${profileError}\n`);
      }

      fs.writeFileSync(
        path.join(dir, 'extraction.json'),
        JSON.stringify(res, null, 2)
      );
      const domLen = (res.renderedDOM || []).length;
      const textLen = (res.textContent || []).length;
      const level =
        ((res.animations.profile || {}).intensity || {}).level || null;
      index.push({
        slug,
        url,
        why,
        ok: true,
        dom_elements: domLen,
        text_nodes: textLen,
        motion_level: level,
        animation_profile_error: profileError,
      });
      ok += 1;
      process.stderr.write(
        `    ok  dom=${domLen} text=${textLen} motion=${level}\n`
      );
    } catch (e) {
      index.push({ slug, url, why, ok: false, error: String((e && e.message) || e) });
      process.stderr.write(`    FAIL ${(e && e.message) || e}\n`);
    }
  }

  // The index is written even on total failure: an inspectable record of what
  // was attempted beats a silent empty directory.
  fs.writeFileSync(
    path.join(OUT, 'index.json'),
    JSON.stringify(index, null, 2) + '\n'
  );
  process.stderr.write(`\ncorpus: ${OUT}   ${ok}/${pages.length} captured\n`);

  if (ok === 0) {
    process.stderr.write(
      'NOT_MEASURED: no page captured. Nothing downstream can compile from ' +
        'this corpus.\n'
    );
    process.exit(EXIT_NOT_MEASURED);
  }
  process.exit(EXIT_OK);
})().catch((e) => {
  process.stderr.write(`capture-benchmark-pages.js: ${(e && e.stack) || e}\n`);
  process.exit(1);
});

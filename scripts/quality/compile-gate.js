#!/usr/bin/env node
/**
 * compile-gate.js — the first real compile check in the pipeline.
 *
 * `stage_validate` matches strings and counts braces. It has never compiled
 * anything, which is why `key=` (a token substitution that ate its value)
 * shipped: the braces balance, `export default` is present, and the file is
 * syntactically dead. Every `tsc` check to date has been a human running an
 * ad hoc harness.
 *
 *   node scripts/quality/compile-gate.js <site-dir> [--out <dir>]
 *
 * Exit codes:
 *   0  pass          — no structural errors
 *   1  fail          — TS1xxx structural errors present
 *   3  not_measured  — no TypeScript compiler could be resolved, or tsc could
 *                      not be made to produce diagnostics. NOT_MEASURED is not
 *                      a pass, and this gate never degrades into one.
 *
 * Writes <out>/compile-gate.json (default: the parent of <site-dir>).
 *
 * Diagnostic partition — deliberate, and the reason the gate is trustworthy on
 * a site whose node_modules is absent:
 *   TS1xxx                    structural (parse/syntax) → FAIL
 *   TS2307 & friends          module-not-found noise    → reported, not fatal
 *   everything else           reported, not fatal
 * A missing install produces a blizzard of TS2307/TS7026; none of it can hide
 * a syntax error, and none of it can be mistaken for one.
 */

const fs = require('fs');
const path = require('path');
const { execFileSync, spawnSync } = require('child_process');

const { describe } = require('./lib/capability');

/** What this gate is, in its own words. Compiled into the capability register by
 *  `scripts/capability_register.py`; see that file for why it lives here. */
const CAPABILITY = {
  id: 'aurelix.gate.compile',
  name: 'TypeScript compile gate',
  kind: 'gate',
  invocation: 'node scripts/quality/compile-gate.js <site-dir> [--out <dir>]',
  preconditions: [
    'a generated site directory containing .ts/.tsx sources',
    'a resolvable TypeScript compiler — local tsc, or one reachable from the site',
  ],
  inputs: ['the generated site directory'],
  outputs: ['<out>/compile-gate.json (default: the parent of <site-dir>)'],
  outcome: 'whether the generated TypeScript actually parses, partitioned so a missing install cannot mask a syntax error',
  exit_contract: {
    0: 'PASS — no structural errors',
    1: 'FAIL — TS1xxx structural (parse/syntax) errors present',
    3: 'NOT_MEASURED — no TypeScript compiler could be resolved, or tsc produced no diagnostics',
  },
  measures: [
    'TS1xxx structural errors — the class that `key=` (a token substitution that ate its value) belongs to',
    'module-not-found (TS2307 and friends) and everything else, reported but never fatal',
  ],
  cannot_see: [
    'type CORRECTNESS — the partition deliberately treats non-structural diagnostics as noise, ' +
      'so a site that parses but is deeply mistyped passes here',
    'runtime behaviour: a file that compiles can still render nothing',
    'anything at all when it globs sources itself without a tsconfig.json and finds none — ' +
      'it returns "no .ts/.tsx sources found" and exits 3. Read compile-gate.json, not the summary line',
    'whether the site was built; it type-checks source, and a stale .next is invisible to it',
  ],
  reachable_from: ['orchestrate.py:9370', 'run_pipeline.py:951', 'npm run compile-gate', 'standalone CLI'],
  cost: '~10-60s depending on site size; tsc timeout is 300s',
};

const TSC_TIMEOUT_MS = 300_000;

/** Codes that mean "the module graph is incomplete", not "the code is broken". */
const MODULE_CODES = new Set(['TS2307', 'TS2792', 'TS2875', 'TS7016']);

/** Codes that mean the compiler never got as far as looking at the code. */
const CONFIG_CODES = new Set(['TS18003', 'TS6053', 'TS5083']);

const STRUCTURAL = /^TS1\d{3}$/;

// ── tsc resolution ──────────────────────────────────────────────────────────

function tscCandidates(siteDir) {
  const out = [];
  // 1. The generated site's own devDependency — the compiler the site's own
  //    `next build` would use. Always preferred.
  out.push(path.join(siteDir, 'node_modules', 'typescript', 'bin', 'tsc'));
  out.push(path.join(siteDir, 'node_modules', 'typescript', 'lib', 'tsc.js'));
  // 2. A typescript installed alongside these quality tools.
  try {
    out.push(require.resolve('typescript/bin/tsc', { paths: [__dirname] }));
  } catch {
    /* not installed here */
  }
  // 3. The nested install that ships inside the global vercel CLI. Present on
  //    every machine that can deploy, which makes it a real fallback rather
  //    than a hopeful one.
  try {
    const globalRoot = execFileSync('npm', ['root', '-g'], {
      encoding: 'utf8',
      timeout: 20_000,
    }).trim();
    if (globalRoot) {
      out.push(path.join(globalRoot, 'vercel', 'node_modules', 'typescript', 'bin', 'tsc'));
      out.push(path.join(globalRoot, 'typescript', 'bin', 'tsc'));
    }
  } catch {
    /* npm unavailable */
  }
  return out;
}

function resolveTsc(siteDir) {
  for (const candidate of tscCandidates(path.resolve(siteDir))) {
    if (candidate && fs.existsSync(candidate)) return path.resolve(candidate);
  }
  return null;
}

// ── diagnostics ─────────────────────────────────────────────────────────────

const DIAG_WITH_FILE = /^(.+?)\((\d+),(\d+)\):\s+error\s+(TS\d+):\s+(.*)$/;
const DIAG_BARE = /^error\s+(TS\d+):\s+(.*)$/;

function parseDiagnostics(stdout, stderr) {
  const diagnostics = [];
  for (const line of `${stdout}\n${stderr}`.split('\n')) {
    const trimmed = line.trimEnd();
    let m = DIAG_WITH_FILE.exec(trimmed);
    if (m) {
      diagnostics.push({
        file: m[1],
        line: Number(m[2]),
        column: Number(m[3]),
        code: m[4],
        message: m[5],
      });
      continue;
    }
    m = DIAG_BARE.exec(trimmed.trimStart());
    if (m) {
      diagnostics.push({ file: null, line: null, column: null, code: m[1], message: m[2] });
    }
  }
  return diagnostics;
}

// ── source enumeration (only when the site has no tsconfig) ─────────────────

function collectSources(dir, root = dir, acc = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name === '.next' || entry.name.startsWith('.git')) {
      continue;
    }
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) collectSources(full, root, acc);
    else if (/\.tsx?$/.test(entry.name) && !entry.name.endsWith('.d.ts')) {
      acc.push(path.relative(root, full));
    }
  }
  return acc;
}

// ── the gate ────────────────────────────────────────────────────────────────

/**
 * @param {string} siteDir  the generated Next.js site (contains tsconfig.json)
 * @param {object} [opts]
 * @param {string|null} [opts.tscPath]  explicit compiler; `null` forces the
 *        unresolvable path (used to prove the gate reports NOT_MEASURED rather
 *        than passing when no compiler exists)
 * @param {string} [opts.outputDir]  where compile-gate.json is written
 * @param {boolean} [opts.write=true]
 */
async function compileGate(siteDirArg, opts = {}) {
  // Absolute throughout: tsc runs with cwd=siteDir, so a relative compiler
  // path would be re-resolved against the site and vanish.
  const siteDir = path.resolve(siteDirArg);
  const outputDir = opts.outputDir || path.dirname(siteDir);
  const write = opts.write !== false;

  const emit = (result) => {
    const report = {
      status: result.status,
      site_dir: path.resolve(siteDir),
      errors: result.errors || [],
      module_errors: result.module_errors || [],
      other_errors: result.other_errors || [],
      tsc_path: result.tsc_path || null,
      not_measured_reason: result.not_measured_reason || null,
      checked_at: new Date().toISOString(),
    };
    if (write) {
      fs.mkdirSync(outputDir, { recursive: true });
      fs.writeFileSync(
        path.join(outputDir, 'compile-gate.json'),
        JSON.stringify(report, null, 2) + '\n',
        'utf8'
      );
    }
    return { ...report, exitCode: result.exitCode };
  };

  if (!fs.existsSync(siteDir)) {
    return emit({
      status: 'not_measured',
      exitCode: 3,
      not_measured_reason: `site directory does not exist: ${siteDir}`,
    });
  }

  const tscPath = 'tscPath' in opts ? opts.tscPath : resolveTsc(siteDir);
  if (!tscPath) {
    return emit({
      status: 'not_measured',
      exitCode: 3,
      not_measured_reason:
        'no TypeScript compiler could be resolved (site devDependency, quality tools, ' +
        'and the nested vercel CLI install were all absent). NOT_MEASURED is not a pass.',
    });
  }

  const hasTsconfig = fs.existsSync(path.join(siteDir, 'tsconfig.json'));
  let args;
  if (hasTsconfig) {
    args = [tscPath, '-p', 'tsconfig.json', '--noEmit', '--skipLibCheck', '--pretty', 'false'];
  } else {
    const sources = collectSources(siteDir);
    if (sources.length === 0) {
      return emit({
        status: 'not_measured',
        exitCode: 3,
        tsc_path: tscPath,
        not_measured_reason: `no .ts/.tsx sources found under ${siteDir}`,
      });
    }
    args = [
      tscPath,
      '--noEmit',
      '--jsx',
      'react-jsx',
      '--skipLibCheck',
      '--target',
      'ES2020',
      '--module',
      'esnext',
      '--moduleResolution',
      'bundler',
      ...sources,
    ];
  }

  const run = spawnSync(process.execPath, args, {
    cwd: siteDir,
    encoding: 'utf8',
    timeout: TSC_TIMEOUT_MS,
    maxBuffer: 64 * 1024 * 1024,
  });

  if (run.error) {
    return emit({
      status: 'not_measured',
      exitCode: 3,
      tsc_path: tscPath,
      not_measured_reason: `tsc could not be executed: ${run.error.message}`,
    });
  }

  const diagnostics = parseDiagnostics(run.stdout || '', run.stderr || '');

  const configFailure = diagnostics.find((d) => CONFIG_CODES.has(d.code));
  if (configFailure) {
    return emit({
      status: 'not_measured',
      exitCode: 3,
      tsc_path: tscPath,
      not_measured_reason: `tsc never compiled anything: ${configFailure.code} ${configFailure.message}`,
    });
  }

  if (run.status !== 0 && diagnostics.length === 0) {
    const detail = (run.stderr || run.stdout || '').trim().slice(0, 500);
    return emit({
      status: 'not_measured',
      exitCode: 3,
      tsc_path: tscPath,
      not_measured_reason: `tsc exited ${run.status} with no parseable diagnostics: ${detail}`,
    });
  }

  const errors = diagnostics.filter((d) => STRUCTURAL.test(d.code));
  const module_errors = diagnostics.filter((d) => MODULE_CODES.has(d.code));
  const other_errors = diagnostics.filter(
    (d) => !STRUCTURAL.test(d.code) && !MODULE_CODES.has(d.code)
  );

  return emit({
    status: errors.length > 0 ? 'fail' : 'pass',
    exitCode: errors.length > 0 ? 1 : 0,
    errors,
    module_errors,
    other_errors,
    tsc_path: tscPath,
  });
}

// ── CLI ─────────────────────────────────────────────────────────────────────

async function main(argv) {
  if (describe(CAPABILITY, argv.slice(2))) return 0;
  const args = argv.slice(2);
  const positional = [];
  let outputDir;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--out') outputDir = args[++i];
    else positional.push(args[i]);
  }
  const siteDir = positional[0];
  if (!siteDir) {
    console.error('usage: compile-gate.js <site-dir> [--out <dir>]');
    return 3;
  }

  const r = await compileGate(siteDir, outputDir ? { outputDir } : {});

  if (r.status === 'not_measured') {
    console.error(`COMPILE GATE: NOT_MEASURED — ${r.not_measured_reason}`);
    console.error('  (NOT_MEASURED is not a pass.)');
    return r.exitCode;
  }

  const noise = r.module_errors.length + r.other_errors.length;
  if (r.status === 'fail') {
    console.error(`COMPILE GATE: FAIL — ${r.errors.length} structural error(s)`);
    for (const e of r.errors.slice(0, 50)) {
      console.error(`  ${e.file}:${e.line}:${e.column}  ${e.code}  ${e.message}`);
    }
    if (r.errors.length > 50) console.error(`  ... and ${r.errors.length - 50} more`);
  } else {
    console.log('COMPILE GATE: PASS — 0 structural errors');
  }
  if (noise) {
    console.log(
      `  (non-fatal: ${r.module_errors.length} module-not-found, ${r.other_errors.length} other diagnostics)`
    );
  }
  console.log(`  tsc: ${r.tsc_path}`);
  return r.exitCode;
}

if (require.main === module) {
  main(process.argv).then(
    (code) => process.exit(code),
    (err) => {
      console.error(`COMPILE GATE: NOT_MEASURED — gate crashed: ${err.stack || err}`);
      process.exit(3);
    }
  );
}

module.exports = { compileGate, resolveTsc, parseDiagnostics };

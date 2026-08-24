#!/usr/bin/env node
/**
 * Pre-deploy design-conformance gate.  Task C3.
 *
 * WHY THIS EXISTS
 * ---------------
 * `aurelix-uiux-audit/lib/design_conformance.py` can already say "the rendered
 * ground is #0b0b0b but the benchmark declares #ffffff".  It has only ever run
 * POST-deploy, against a live URL.  Nothing checked conformance before a build
 * was published, so the only thing standing between a compiled design and a
 * site that ignores it was a human looking at the page.
 *
 * This gate closes that loop: it serves the ALREADY-BUILT site on a free local
 * port, runs the existing analyser against `http://127.0.0.1:<port>`, and turns
 * the rule results into an exit code.  It does not build, does not deploy, and
 * does not fork the analyser — `conformance_runner.py` is a thin driver over
 * the same three public functions the audit calls.
 *
 * CONTRACT
 *   exit 0  PASS          every measured rule conforms
 *   exit 1  FAIL          at least one rule failed WITH a measured value
 *   exit 3  NOT_MEASURED  nothing could be measured, or the only failures had
 *                         no measurement behind them.  NOT_MEASURED != PASS.
 *
 *   writes <output>/conformance.json — violations carry
 *   {layer, rule, measured, expected, route, section, attribution}.
 *
 * ON `route`
 * ----------
 * `evaluate()` now attributes each per-element rule to the routes it was
 * actually measured on (design_conformance.py, `_attribute`), and says in
 * `evidence[0].metadata.attribution` whether it could.  This gate reports what
 * it is told and invents nothing:
 *
 *   attribution=per_route      `route` = the worst offending route when the
 *                              rule offends on exactly one; null when several,
 *                              with all of them in `affected_routes` and their
 *                              counts in `route_counts`.
 *   attribution=site_aggregate `route` stays null and `attribution_reason`
 *                              carries WHY — the measurement is a union over
 *                              routes (palette size, undeclared font count), so
 *                              no single route owns it.
 *   attribution=per_page_absent  no per-page measurements were supplied.
 *
 * `section` is still null everywhere: nothing measures sections yet.
 *
 * ON `waived`
 * -----------
 * A violation matching a declared deviation
 * (`<benchmark-stem>.deviations.json`) arrives carrying
 * `evidence[0].metadata.waiver`.  It is moved to the `waived` array, counted in
 * `counts.waived`, printed separately, and does NOT fail the build.  It is
 * never dropped.  A waiver whose declared build_value no longer matches the
 * measurement arrives with `waiver_rejected` instead and fails normally.
 *
 * USAGE
 *   node scripts/quality/conformance-gate.js \
 *        --build-dir output/cape-crypto/site \
 *        --benchmark benchmarks/enterprise-payments-bvnk.json \
 *        --output output/cape-crypto
 *
 *   --results-json <file>   skip serving; interpret an existing runner result.
 *                           The verdict seam, used by the tests.
 */

'use strict';

const fs = require('fs');
const net = require('net');
const path = require('path');
const { spawn, spawnSync } = require('child_process');

const { describe } = require('./lib/capability');

const SCRIPTS = path.resolve(__dirname, '..');
const WEB_BUILDER = path.resolve(SCRIPTS, '..');
const RUNNER = path.join(__dirname, 'conformance_runner.py');
const DEFAULT_BENCHMARK = path.join(WEB_BUILDER, 'benchmarks', 'enterprise-payments-bvnk.json');

/** What this gate is, in its own words. Compiled into the capability register by
 *  `scripts/capability_register.py`; see that file for why it lives here. */
const CAPABILITY = {
  id: 'aurelix.gate.conformance',
  name: 'Design conformance gate',
  kind: 'gate',
  invocation: 'node scripts/quality/conformance-gate.js --build-dir <site-dir> --benchmark <file> --output <dir>',
  preconditions: [
    'a production build exists (.next/ with a prerender-manifest) — this gate does not build',
    'a ratified benchmark file; defaults to benchmarks/enterprise-payments-bvnk.json',
    'python3 with the aurelix-uiux-audit analyser importable (conformance_runner.py drives it)',
  ],
  inputs: ['the built site directory', 'a benchmark json'],
  outputs: ['<output>/conformance.json — violations carry {layer, rule, measured, expected, route, '
    + 'section, attribution, affected_routes, route_counts}; waived findings are in a separate '
    + '`waived` array with the deviation that waived them'],
  outcome: 'per-rule PASS/FAIL with measured vs expected, over every prerendered route of the built site',
  exit_contract: {
    0: 'PASS — every measured rule conforms',
    1: 'FAIL — at least one rule failed WITH a measured value behind it',
    3: 'NOT_MEASURED — nothing could be measured, or the only failures had no measurement. NOT_MEASURED is not a pass',
  },
  measures: [
    'computed style of the rendered page: type scale, shadow layers, palette size, spacing rhythm',
    'the whole prerendered route set, not a sampled page',
  ],
  cannot_see: [
    'source-level token drift — it reads computed style, so a template that hardcodes a literal ' +
      'matching the benchmark passes here while still being unmaintainable',
    'anything not rendered on a prerendered route: client-only states, hover, modals, authed pages',
    'WHICH SECTION an offence is in. Routes are attributed (see the header); sections are not ' +
      'measured at all, so `section` is null on every finding',
    'a route it could not attribute. dna_palette_size and the undeclared-set branch of ' +
      'dna_font_families measure a union over routes — every route can conform while the union ' +
      'breaches — so those keep route null and say so in attribution_reason rather than invent one',
    'whether a declared deviation is still a good decision. It checks that the waiver names a ' +
      'reason, a person and a date, and that the build still measures what was waived; it cannot ' +
      'check that the reason is true',
    'whether the benchmark itself is right — a wrong ratified benchmark produces confident conformance',
  ],
  reachable_from: ['orchestrate.py:9867', 'run_pipeline.py:992', 'standalone CLI'],
  cost: '~30s on a 65-route site, plus the production build it requires',
};

const EXIT = { pass: 0, fail: 1, not_measured: 3 };

const USAGE = `conformance-gate — pre-deploy design-conformance gate

  --build-dir <dir>      built Next.js site (must contain .next/). Served locally.
  --benchmark <file>     ratified benchmark JSON [default: enterprise-payments-bvnk.json]
  --output <dir>         where conformance.json is written [default: --build-dir/..]
  --routes <a,b,...>     override the route list (default: read from prerender-manifest)
  --results-json <file>  interpret an existing runner result instead of serving
  --ready-timeout-ms <n> how long to wait for the local server [default: 90000]
  --help

exit 0 PASS · 1 FAIL · 3 NOT_MEASURED  (NOT_MEASURED is never PASS)
`;

// ── args ──────────────────────────────────────────────────────────────────

function parseArgs(argv) {
  const out = { readyTimeoutMs: 90000 };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    const next = () => argv[(i += 1)];
    if (a === '--help' || a === '-h') out.help = true;
    else if (a === '--build-dir') out.buildDir = next();
    else if (a === '--benchmark') out.benchmark = next();
    else if (a === '--output') out.output = next();
    else if (a === '--routes') out.routes = next();
    else if (a === '--results-json') out.resultsJson = next();
    else if (a === '--ready-timeout-ms') out.readyTimeoutMs = Number(next());
    else if (a === '--python') out.python = next();
    else return { error: `unknown argument: ${a}` };
  }
  return out;
}

// ── report ────────────────────────────────────────────────────────────────

function writeReport(outputDir, report) {
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(path.join(outputDir, 'conformance.json'),
    `${JSON.stringify(report, null, 2)}\n`, 'utf8');
}

function baseReport(extra) {
  return Object.assign({
    tool: 'conformance-gate',
    generated_at: new Date().toISOString(),
    status: 'not_measured',
    exit_code: EXIT.not_measured,
    reason: null,
    build_dir: null,
    benchmark: null,
    base_url: null,
    routes_measured: [],
    counts: { pass: 0, fail: 0, not_measured: 0, waived: 0 },
    violations: [],
    waived: [],
    not_measured: [],
  }, extra || {});
}

function notMeasured(outputDir, reason, extra) {
  // `not_measured_reason` mirrors the field name `_run_compile_gate`
  // (orchestrate.py:8452) already reads off its sibling gate, so a chain call
  // site can interpret both gates with the same three lines.
  const report = baseReport(Object.assign(
    { reason, not_measured_reason: reason }, extra || {}));
  writeReport(outputDir, report);
  return EXIT.not_measured;
}

/**
 * The verdict. The ONE place PASS/FAIL/NOT_MEASURED is defined.
 *
 * A FAIL whose evidence carries no `observed` or no `expected` is an opinion,
 * not a finding — it is recorded as NOT_MEASURED and never fails a build.
 */
/** Absolute measured URL -> route path. `http://127.0.0.1:41234/fees` -> `/fees`. */
function toRoute(url, baseUrl) {
  if (typeof url !== 'string' || !url) return null;
  if (baseUrl && url.startsWith(baseUrl)) return url.slice(baseUrl.length) || '/';
  try { return new URL(url).pathname || '/'; } catch (_) { return url; }
}

function decide(results, ctx) {
  const violations = [];
  const waived = [];
  const unmeasured = [];
  let passCount = 0;
  const base = ctx.baseUrl || '';

  for (const r of results || []) {
    const state = String(r.state || '').toUpperCase();
    const ev = (r.evidence && r.evidence[0]) || {};
    const meta = ev.metadata || {};
    const measured = ev.observed === undefined ? null : ev.observed;
    const expected = ev.expected === undefined ? null : ev.expected;

    if (state === 'PASS') { passCount += 1; continue; }
    if (state === 'NOT_APPLICABLE') continue;

    if (state === 'FAIL' && measured !== null && expected !== null) {
      // Attribution comes from the analyser, which measured it. This gate does
      // not derive a route from anything else — see the header.
      const offending = (meta.offending_routes || []).map((u) => toRoute(u, base));
      const routeCounts = {};
      for (const [u, n] of Object.entries(meta.route_counts || {})) {
        routeCounts[toRoute(u, base)] = n;
      }
      const finding = {
        layer: r.layer || null,
        rule: r.rule_id || null,
        measured,
        expected,
        // One offending route is a route. Several is a list, and claiming one of
        // them would be inventing a fact; the list is in affected_routes.
        route: offending.length === 1 ? offending[0] : null,
        section: null,                       // nothing measures sections yet
        attribution: meta.attribution || null,
        attribution_reason: meta.attribution_reason || null,
        severity: r.severity || null,
        prevalence: typeof r.prevalence === 'number' ? r.prevalence : null,
        issue: r.issue || null,
        route_counts: routeCounts,
        affected_routes: offending.length ? offending : (ctx.routes || []),
      };
      if (meta.waiver) {
        // Counted and printed separately, never dropped, and never a PASS.
        waived.push(Object.assign({ waiver: meta.waiver }, finding));
        continue;
      }
      if (meta.waiver_rejected) finding.waiver_rejected = meta.waiver_rejected;
      violations.push(finding);
      continue;
    }
    unmeasured.push({
      rule: r.rule_id || null,
      layer: r.layer || null,
      reason: state === 'FAIL'
        ? 'reported FAIL with no measured/expected value — recorded as unmeasured, '
          + 'a violation without a measurement is an opinion'
        : (r.issue || 'NOT_MEASURED'),
    });
  }

  const status = violations.length ? 'fail'
    : unmeasured.length ? 'not_measured'
      : 'pass';

  return {
    status,
    exit_code: EXIT[status],
    counts: {
      pass: passCount,
      fail: violations.length,
      not_measured: unmeasured.length,
      waived: waived.length,
    },
    violations,
    waived,
    not_measured: unmeasured,
  };
}

/** Where a finding is, in one line. Never "null" where a route is known. */
function whereClause(v) {
  if (v.route) return ` at ${v.route}`;
  const n = (v.affected_routes || []).length;
  if (v.attribution === 'per_route' && n) {
    const named = (v.affected_routes || []).slice(0, 4)
      .map((r) => `${r}(${v.route_counts && v.route_counts[r] !== undefined ? v.route_counts[r] : '?'})`)
      .join(' ');
    return ` on ${n} route(s): ${named}${n > 4 ? ` +${n - 4}` : ''}`;
  }
  // Not attributable. Say which kind of not-attributable, never a bare null.
  return ` [route not attributed: ${v.attribution || 'unknown'}]`;
}

/** Violations and waived findings, printed separately. Waived is never silent. */
function printFindings(report) {
  for (const v of report.violations) {
    process.stdout.write(`  ${v.rule} [${v.layer}]${whereClause(v)} measured=`
      + `${JSON.stringify(v.measured).slice(0, 160)} expected=`
      + `${JSON.stringify(v.expected).slice(0, 160)}\n`);
  }
  for (const v of report.waived || []) {
    process.stdout.write(`  WAIVED ${v.rule} [${v.layer}]${whereClause(v)} — `
      + `${v.waiver.decided_by} on ${v.waiver.decided_on}: ${v.waiver.reason}\n`);
  }
}

// ── serving ───────────────────────────────────────────────────────────────

/** Ask the OS for an ephemeral port, then hand it to `next start`. Never hardcoded. */
async function freePortAsync() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.once('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitForServer(baseUrl, timeoutMs, isDead) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (isDead()) return false;
    try {
      const res = await fetch(`${baseUrl}/`, { redirect: 'manual' });
      if (res.status < 500) return true;
    } catch (_) { /* not up yet */ }
    await sleep(300);
  }
  return false;
}

/** Routes to measure: the statically-known ones, minus Next's internals. */
function discoverRoutes(buildDir) {
  const found = new Set(['/']);
  const manifest = path.join(buildDir, '.next', 'prerender-manifest.json');
  if (fs.existsSync(manifest)) {
    try {
      const m = JSON.parse(fs.readFileSync(manifest, 'utf8'));
      for (const r of Object.keys(m.routes || {})) {
        if (r.startsWith('/_')) continue;      // _not-found, _global-error
        if (r.includes('[')) continue;         // dynamic, no known param
        found.add(r);
      }
    } catch (_) { /* fall through to the app scan */ }
  }
  const appDir = path.join(buildDir, 'src', 'app');
  if (fs.existsSync(appDir)) {
    const walk = (dir, prefix) => {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        if (!e.isDirectory()) continue;
        if (e.name.startsWith('_') || e.name.startsWith('[') || e.name.startsWith('(')) continue;
        const sub = path.join(dir, e.name);
        if (fs.existsSync(path.join(sub, 'page.tsx')) || fs.existsSync(path.join(sub, 'page.jsx'))) {
          found.add(`${prefix}/${e.name}`);
        }
        walk(sub, `${prefix}/${e.name}`);
      }
    };
    walk(appDir, '');
  }
  return Array.from(found).sort();
}

// ── main ──────────────────────────────────────────────────────────────────

async function main() {
  if (describe(CAPABILITY)) return 0;
  const args = parseArgs(process.argv.slice(2));
  if (args.help || process.argv.length === 2) { process.stdout.write(USAGE); return 0; }
  if (args.error) { process.stderr.write(`${args.error}\n\n${USAGE}`); return EXIT.not_measured; }

  // --- verdict seam: interpret an existing runner result ---
  if (args.resultsJson) {
    const outputDir = path.resolve(args.output || path.dirname(args.resultsJson));
    let payload;
    try {
      payload = JSON.parse(fs.readFileSync(args.resultsJson, 'utf8'));
    } catch (e) {
      return notMeasured(outputDir, `results file unreadable: ${e.message}`);
    }
    if (payload.error) return notMeasured(outputDir, payload.error);
    const verdict = decide(payload.results, { routes: payload.urls_reached || [] });
    const report = baseReport(Object.assign({
      benchmark: args.benchmark || null,
      routes_measured: payload.urls_reached || [],
    }, verdict));
    writeReport(outputDir, report);
    process.stdout.write(`CONFORMANCE GATE: ${report.status.toUpperCase()} — `
      + `${report.counts.fail} violation(s), ${report.counts.pass} rule(s) conform, `
      + `${report.counts.not_measured} not measured, ${report.counts.waived} waived\n`);
    printFindings(report);
    return report.exit_code;
  }

  if (!args.buildDir) {
    process.stderr.write(`--build-dir is required\n\n${USAGE}`);
    return EXIT.not_measured;
  }
  const buildDir = path.resolve(WEB_BUILDER, args.buildDir);
  const outputDir = path.resolve(args.output ? path.resolve(WEB_BUILDER, args.output)
    : path.dirname(buildDir));
  const benchmark = path.resolve(WEB_BUILDER, args.benchmark || DEFAULT_BENCHMARK);
  const ctxPaths = { build_dir: buildDir, benchmark };

  if (!fs.existsSync(benchmark)) {
    return notMeasured(outputDir, `benchmark not found: ${benchmark}`, ctxPaths);
  }
  if (!fs.existsSync(path.join(buildDir, '.next'))) {
    return notMeasured(outputDir,
      `no build to serve: ${path.join(buildDir, '.next')} does not exist. `
      + 'The gate does not build — run the build first.', ctxPaths);
  }
  const nextBin = path.join(buildDir, 'node_modules', '.bin', 'next');
  if (!fs.existsSync(nextBin)) {
    return notMeasured(outputDir,
      `cannot serve the build: ${nextBin} is missing (dependencies not installed)`, ctxPaths);
  }

  const routes = args.routes
    ? args.routes.split(',').map((r) => r.trim()).filter(Boolean)
    : discoverRoutes(buildDir);
  if (!routes.length) {
    return notMeasured(outputDir, 'no routes to measure', ctxPaths);
  }

  const port = await freePortAsync();
  const baseUrl = `http://127.0.0.1:${port}`;
  let exited = null;
  const server = spawn(nextBin, ['start', '-p', String(port), '-H', '127.0.0.1'], {
    cwd: buildDir,
    env: Object.assign({}, process.env, { NODE_ENV: 'production', PORT: String(port) }),
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let serverLog = '';
  server.stdout.on('data', (d) => { serverLog += d.toString(); });
  server.stderr.on('data', (d) => { serverLog += d.toString(); });
  server.on('exit', (code) => { exited = code; });

  const stop = () => { try { server.kill('SIGTERM'); } catch (_) { /* gone */ } };

  try {
    const up = await waitForServer(baseUrl, args.readyTimeoutMs, () => exited !== null);
    if (!up) {
      stop();
      return notMeasured(outputDir,
        `local server never became reachable on ${baseUrl} within `
        + `${args.readyTimeoutMs}ms — nothing was measured. Server output: `
        + serverLog.slice(-600).trim(), Object.assign({ base_url: baseUrl }, ctxPaths));
    }

    const resultsPath = path.join(outputDir, 'conformance-raw.json');
    fs.mkdirSync(outputDir, { recursive: true });
    const urls = routes.map((r) => `${baseUrl}${r === '/' ? '/' : r}`);
    const py = args.python || process.env.PYTHON || 'python3';
    const run = spawnSync(py, [RUNNER, '--benchmark', benchmark, '--out', resultsPath,
      ...urls.flatMap((u) => ['--url', u])], {
      cwd: WEB_BUILDER, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024,
    });
    stop();

    if (run.error) {
      return notMeasured(outputDir, `could not run ${py}: ${run.error.message}`,
        Object.assign({ base_url: baseUrl }, ctxPaths));
    }
    let payload;
    try {
      payload = JSON.parse(fs.readFileSync(resultsPath, 'utf8'));
    } catch (e) {
      return notMeasured(outputDir,
        `analyser produced no readable result (${e.message}); stderr: `
        + `${(run.stderr || '').slice(-600).trim()}`,
        Object.assign({ base_url: baseUrl }, ctxPaths));
    }
    if (payload.error) {
      return notMeasured(outputDir, payload.error,
        Object.assign({ base_url: baseUrl }, ctxPaths));
    }

    const reached = payload.urls_reached || [];
    if (!reached.length) {
      return notMeasured(outputDir, 'no route was successfully loaded by the browser',
        Object.assign({ base_url: baseUrl }, ctxPaths));
    }
    const reachedRoutes = reached.map((u) => u.slice(baseUrl.length) || '/');
    const verdict = decide(payload.results, { routes: reachedRoutes, baseUrl });
    const report = baseReport(Object.assign({
      build_dir: buildDir,
      benchmark,
      base_url: baseUrl,
      routes_measured: reachedRoutes,
      routes_requested: routes,
      routes_skipped: payload.notes || [],
    }, verdict));
    writeReport(outputDir, report);

    process.stdout.write(`CONFORMANCE GATE: ${report.status.toUpperCase()} — `
      + `${report.counts.fail} violation(s), ${report.counts.pass} rule(s) conform, `
      + `${report.counts.not_measured} not measured, ${report.counts.waived} waived, over `
      + `${reachedRoutes.length} route(s)\n`);
    printFindings(report);
    return report.exit_code;
  } finally {
    stop();
  }
}

main().then((code) => { process.exitCode = code; })
  .catch((err) => {
    process.stderr.write(`conformance gate crashed: ${err && err.stack}\n`);
    process.exitCode = EXIT.not_measured;
  });

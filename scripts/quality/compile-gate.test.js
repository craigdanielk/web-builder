const { test, before } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { compileGate } = require('./compile-gate');

const QUALITY_DIR = __dirname;
const WEB_BUILDER = path.resolve(QUALITY_DIR, '..', '..');
const FIXTURE_SRC = path.join(QUALITY_DIR, 'fixtures', 'compile-gate');

/**
 * A real `node_modules` carrying typescript + react/next/framer-motion types.
 *
 * The gate exists to prove that missing-module noise cannot mask structural
 * errors, so the "with modules" fixtures must link against a genuine install
 * rather than hand-written stubs. Any generated site under output/ will do.
 * If none is present the tests FAIL loudly — they must never skip, because a
 * skipped compile test reads as a passing one.
 */
function realNodeModules() {
  const outputDir = path.join(WEB_BUILDER, 'output');
  if (!fs.existsSync(outputDir)) return null;
  for (const project of fs.readdirSync(outputDir).sort()) {
    const nm = path.join(outputDir, project, 'site', 'node_modules');
    if (
      fs.existsSync(path.join(nm, 'typescript', 'package.json')) &&
      fs.existsSync(path.join(nm, '@types', 'react', 'package.json'))
    ) {
      return nm;
    }
  }
  return null;
}

let NODE_MODULES = null;

before(() => {
  NODE_MODULES = realNodeModules();
  assert.ok(
    NODE_MODULES,
    'No output/*/site/node_modules with typescript + @types/react was found. ' +
      'The compile-gate tests need a real install to link against; run a build first.'
  );
});

const FIXTURES = {
  'site-clean': { src: 'clean', nodeModules: true },
  'site-with-broken-jsx': { src: 'broken', nodeModules: true },
  'site-with-broken-jsx-no-node-modules': { src: 'broken', nodeModules: false },
};

function fixture(name) {
  const spec = FIXTURES[name];
  if (!spec) throw new Error(`unknown fixture: ${name}`);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), `compile-gate-${name}-`));
  fs.cpSync(path.join(FIXTURE_SRC, spec.src), dir, { recursive: true });
  fs.copyFileSync(path.join(FIXTURE_SRC, 'tsconfig.json'), path.join(dir, 'tsconfig.json'));
  if (spec.nodeModules) {
    fs.symlinkSync(NODE_MODULES, path.join(dir, 'node_modules'), 'dir');
  }
  return dir;
}

function readReport(dir) {
  const p = path.join(path.dirname(dir), 'compile-gate.json');
  assert.ok(fs.existsSync(p), `compile-gate.json was not written to ${p}`);
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

test('a corrupted section fails the gate', async () => {
  const dir = fixture('site-with-broken-jsx'); // `Expected '</', got 'ident'`
  const r = await compileGate(dir);
  assert.equal(r.status, 'fail');
  assert.equal(r.exitCode, 1);
  assert.ok(
    r.errors.some((e) => /^TS1\d{3}$/.test(e.code)),
    `expected a TS1xxx structural error, got ${JSON.stringify(r.errors)}`
  );
  const onDisk = readReport(dir);
  assert.equal(onDisk.status, 'fail');
  assert.ok(onDisk.errors.length > 0);
});

test('a clean build passes', async () => {
  const dir = fixture('site-clean');
  const r = await compileGate(dir);
  assert.equal(r.status, 'pass', JSON.stringify(r.errors));
  assert.equal(r.exitCode, 0);
  assert.equal(readReport(dir).status, 'pass');
});

test('a hidden tsc reports NOT_MEASURED and exits non-zero', async () => {
  const dir = fixture('site-clean');
  const r = await compileGate(dir, { tscPath: null });
  assert.equal(r.status, 'not_measured');
  assert.equal(r.exitCode, 3);
  assert.match(r.not_measured_reason, /typescript/i);
  const onDisk = readReport(dir);
  assert.equal(onDisk.status, 'not_measured');
  assert.match(onDisk.not_measured_reason, /typescript/i);
});

test('missing-module noise does not mask structural errors', async () => {
  const dir = fixture('site-with-broken-jsx-no-node-modules');
  const r = await compileGate(dir);
  assert.equal(r.status, 'fail'); // not 'not_measured', not 'pass'
  assert.ok(r.errors.every((e) => /^TS1\d{3}$/.test(e.code)));
  assert.ok(
    r.tsc_path && fs.existsSync(r.tsc_path),
    'the gate must fall back to a tsc outside the site when the site has none'
  );
});

test('a relative site-dir still resolves the compiler', async () => {
  // tsc runs with cwd=siteDir. A relative compiler path gets re-resolved
  // against the site and disappears — which the first real run against
  // output/cape-crypto/site reported as NOT_MEASURED.
  const dir = fixture('site-clean');
  const relative = path.relative(process.cwd(), dir);
  const r = await compileGate(relative);
  assert.equal(r.status, 'pass', r.not_measured_reason || JSON.stringify(r.errors));
});

test('module-not-found alone does not fail the gate', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'compile-gate-nomodules-'));
  fs.cpSync(path.join(FIXTURE_SRC, 'clean'), dir, { recursive: true });
  fs.copyFileSync(path.join(FIXTURE_SRC, 'tsconfig.json'), path.join(dir, 'tsconfig.json'));
  const r = await compileGate(dir);
  assert.equal(r.status, 'pass');
  assert.ok(
    r.module_errors.some((e) => e.code === 'TS2307'),
    'the TS2307 noise should be reported, just not fatal'
  );
});

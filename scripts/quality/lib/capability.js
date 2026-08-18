'use strict';
/**
 * The capability declaration — an instrument describing itself, in its own file.
 *
 * WHY THIS EXISTS
 * ---------------
 * On 2026-08-18 five checkers were hand-written that duplicated instruments
 * already sitting in this directory, and the real conformance gate — run once,
 * at the end of the day — found three defects the hand-written one is
 * structurally incapable of seeing.  The instruments were not missing and were
 * not unreachable: 22 of the 31 files here already parse argv.  They were
 * undiscoverable and undescribed.
 *
 * A separate document describing them would go stale the first time a flag
 * changed, and nothing would fail when it did.  `registry/capability-matrix.yaml`
 * is the proof: every row carries `last_measured: '2026-05-09'` and is still
 * shipping.  So the declaration lives HERE, beside the code it describes, and
 * the register is compiled from it.  A flag change and its description change in
 * one edit, or `capability_register.py compile --check` fails the test suite.
 *
 * WHY `--describe` AND NOT A COMMENT BLOCK
 * ----------------------------------------
 * Executing the declaration proves the file LOADS.  `shopify_bulk_importer` is
 * the cautionary case: `--help` works and 53 tests pass, while every subcommand
 * raises ImportError, because argparse builds its parser before the lazy import
 * and no test exercises the CLI path.  A parsed comment would have described
 * that tool as healthy.  A `--describe` that runs after the requires cannot.
 *
 * WHY VALIDATION IS UNCONDITIONAL
 * -------------------------------
 * `validate()` runs on every invocation, not only under `--describe`.  A
 * malformed declaration is a defect in the instrument, and a defect that only
 * appears when someone happens to compile the register is a defect that ships.
 *
 * USAGE
 *   const { describe } = require('./lib/capability');   // from scripts/quality/
 *   const CAPABILITY = { id: 'aurelix.gate.conformance', ... };
 *   async function main() {
 *     if (describe(CAPABILITY)) return 0;               // FIRST thing in main
 *     ...
 *   }
 */

/** What an instrument IS.  The compiler rejects anything else. */
const KINDS = new Set([
  'gate',       // three-state verdict on a build: PASS / FAIL / NOT_MEASURED
  'probe',      // measures and reports; renders no verdict
  'extractor',  // pulls facts out of a source (a site, a bundle, a store)
  'compiler',   // turns declared inputs into a derived artifact
  'adapter',    // targets one platform behind a shared interface
  'generator',  // creates content or assets
  'builder',    // assembles a registry, spec or manifest
  'fixer',      // mutates source to remediate a finding
  'migration',  // moves state from one shape to another
  'harness',    // runs other instruments
]);

/**
 * Every field is required.  There is no optional half of this contract: a
 * declaration that omits a field is how the register goes back to being prose.
 */
const REQUIRED = [
  'id',              // stable dotted identity; the register's primary key
  'name',            // one human line
  'kind',            // from KINDS
  'invocation',      // the EXACT command line.  Evidence is matched against it
  'preconditions',   // what must already be true, in words an operator can act on
  'inputs',          // what it reads
  'outputs',         // what it writes
  'outcome',         // what you learn by running it
  'exit_contract',   // {code: meaning} — every code it can return
  'measures',        // what it can see
  'cannot_see',      // what it CANNOT see.  Never empty.  See below
  'reachable_from',  // call sites today; [] means nothing invokes it
  'cost',            // wall-clock and prerequisites, honestly
];

/** Fields the compiler owns.  A declaration that sets one is refused: an
 *  instrument does not get to grade itself. */
const COMPILER_OWNED = new Set(['status', 'evidence', 'source_file', 'language']);

const NON_EMPTY_LISTS = ['preconditions', 'inputs', 'outputs', 'measures', 'cannot_see'];

/**
 * WHY `cannot_see` IS MANDATORY AND MAY NOT BE EMPTY
 * -------------------------------------------------
 * It is the only field no static analysis can derive, and the only one that
 * stops the next person deleting a "redundant" gate.  The conformance gate
 * cannot see source-level token drift; the source-grep checker cannot see
 * computed style.  Neither is redundant — each is blind exactly where the other
 * looks — and nothing in this repo recorded that until now.
 *
 * An instrument that genuinely believes it sees everything is wrong, so there
 * is no escape value.  Write the honest limit.
 */
function validate(spec, where = 'capability declaration') {
  const problems = [];
  if (!spec || typeof spec !== 'object' || Array.isArray(spec)) {
    throw new Error(`${where}: expected an object, got ${Array.isArray(spec) ? 'array' : typeof spec}`);
  }
  for (const field of REQUIRED) {
    if (!(field in spec)) problems.push(`missing required field \`${field}\``);
  }
  for (const field of COMPILER_OWNED) {
    if (field in spec) {
      problems.push(`\`${field}\` is owned by the compiler and may not be declared — ` +
                    `an instrument does not grade itself`);
    }
  }
  if (spec.kind !== undefined && !KINDS.has(spec.kind)) {
    problems.push(`kind ${JSON.stringify(spec.kind)} is not one of: ${[...KINDS].sort().join(', ')}`);
  }
  if (typeof spec.id === 'string' && !/^[a-z0-9]+(\.[a-z0-9][a-z0-9-]*)+$/.test(spec.id)) {
    problems.push(`id ${JSON.stringify(spec.id)} must be dotted lowercase, e.g. aurelix.gate.conformance`);
  }
  for (const field of NON_EMPTY_LISTS) {
    if (!(field in spec)) continue;
    const v = spec[field];
    if (!Array.isArray(v)) { problems.push(`\`${field}\` must be a list of strings`); continue; }
    const bad = v.filter((s) => typeof s !== 'string' || !s.trim());
    if (bad.length) problems.push(`\`${field}\` contains an empty or non-string entry`);
    if (v.length === 0 && field === 'cannot_see') {
      problems.push('`cannot_see` may not be empty — every instrument is blind somewhere, ' +
                    'and that blindness is why its neighbour is not redundant');
    }
    if (v.length === 0 && field !== 'cannot_see' && field !== 'inputs' && field !== 'outputs') {
      problems.push(`\`${field}\` may not be empty`);
    }
  }
  if ('cannot_see' in spec && Array.isArray(spec.cannot_see) && spec.cannot_see.length === 0) {
    // already reported above; keep the single message
  }
  if ('exit_contract' in spec) {
    const ec = spec.exit_contract;
    if (!ec || typeof ec !== 'object' || Array.isArray(ec)) {
      problems.push('`exit_contract` must be an object mapping exit code to meaning');
    } else if (Object.keys(ec).length === 0) {
      problems.push('`exit_contract` may not be empty — every instrument returns something');
    } else {
      for (const [code, meaning] of Object.entries(ec)) {
        if (!/^\d+$/.test(String(code))) problems.push(`exit_contract key ${JSON.stringify(code)} is not an exit code`);
        if (typeof meaning !== 'string' || !meaning.trim()) {
          problems.push(`exit_contract[${code}] has no meaning`);
        }
      }
    }
  }
  if ('reachable_from' in spec && !Array.isArray(spec.reachable_from)) {
    problems.push('`reachable_from` must be a list (use [] for "nothing invokes this")');
  }
  for (const field of ['name', 'invocation', 'outcome', 'cost']) {
    if (field in spec && (typeof spec[field] !== 'string' || !spec[field].trim())) {
      problems.push(`\`${field}\` must be a non-empty string`);
    }
  }
  if (problems.length) {
    throw new Error(`${where} is invalid:\n  - ${problems.join('\n  - ')}`);
  }
  return spec;
}

/**
 * Validate always; print and signal "stop here" only under `--describe`.
 * Returns true when the caller should return immediately.
 */
function describe(spec, argv = process.argv.slice(2)) {
  validate(spec, `${spec && spec.id ? spec.id : 'capability declaration'}`);
  if (!argv.includes('--describe')) return false;
  process.stdout.write(JSON.stringify(spec, null, 2) + '\n');
  return true;
}

module.exports = { describe, validate, KINDS, REQUIRED, COMPILER_OWNED };

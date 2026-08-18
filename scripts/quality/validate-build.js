#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { validateBuild } = require('./lib/visual-validator');

const { describe } = require('./lib/capability');

/** What this instrument is, in its own words. Compiled into the capability
 *  register by `scripts/capability_register.py`; see that file for why it lives
 *  here rather than in a separate document. */
const CAPABILITY = {
  id: 'aurelix.gate.validate-build',
  name: 'Visual validation gate (screenshot diff, and a deployed-URL smoke check)',
  kind: 'gate',
  invocation: 'node scripts/quality/validate-build.js <project-dir> [--reference-dir <dir>] [--port <n>] [--threshold <0-1>]   |   node scripts/quality/validate-build.js <preview-url>',
  preconditions: [
    'project-dir mode: reference screenshots exist, either at --reference-dir or under ' +
      '<project-dir>/.quality/references, <project-dir>/references, or output/<name>/references',
    'project-dir mode: the project can start a dev server on --port (default 4567), and ' +
      'pixelmatch/pngjs/playwright are installed in scripts/quality/node_modules',
    'url mode: the URL is already deployed and reachable — this instrument neither builds nor deploys',
  ],
  inputs: [
    'project-dir mode: the project directory plus a directory of reference screenshots (.png/.jpg, ordered by filename)',
    'url mode: a single http(s) URL, read once with fetch()',
  ],
  outputs: ['project-dir mode: <project-dir>/.quality-report.json — per-section diffPercentage, overallSimilarity, iterations'],
  outcome: 'project-dir mode: which sections drifted from their reference screenshot, and by how much. url mode: whether a deployed page returns 200 with real text and no crash/hydration marker in the SSR HTML',
  exit_contract: {
    0: 'PASS — every section under the diff threshold; or url mode found no issues; or --help/no-args printed usage',
    1: 'FAIL — sections need regeneration, url-mode issues found, OR a precondition was missing (no references, absent project dir, validator threw). This gate has no NOT_MEASURED code, so "could not measure" is reported as FAIL',
  },
  measures: [
    'per-section pixel difference against a reference screenshot, as a diff percentage, with a diff image written per failing section',
    'url mode only: HTTP status, HTML length, the count of visible text elements, and the literal strings "Application error" / "Internal Server Error" / "Hydration failed" in the SSR HTML',
  ],
  cannot_see: [
    'whether the REFERENCE is right — it measures agreement with a prior screenshot, so a site that was wrong ' +
      'when the references were captured passes at 100% similarity',
    'anything at all with no reference screenshots: it exits 1 rather than 3, so "never measured" and ' +
      '"visually regressed" reach the caller as the same exit code',
    'url mode sees only the SSR HTML fetched once with no browser — no client render, no hydration in practice, ' +
      'no CSS, no images, no console errors. Its text-element count is a regex over raw HTML',
    'WHY a section drifted: a pixel diff cannot separate an intended redesign from a broken layout, ' +
      'so every deliberate change reads as a failure until the references are recaptured',
    'any route other than the ones the validator screenshots — there is no route list argument',
  ],
  reachable_from: ['scripts/quality/package.json → npm run validate', 'standalone CLI'],
  cost: 'project-dir mode: minutes — it starts a dev server and screenshots up to 2 iterations. url mode: one HTTP fetch, under a second',
};

// ---------------------------------------------------------------------------
// Post-deploy visual verification (Phase 5C)
// ---------------------------------------------------------------------------

/**
 * Validates a deployed preview URL: HTTP 200, content length, error indicators,
 * visible text elements, and hydration errors.
 * @param {string} previewUrl - Full URL of the deployed page (e.g. Vercel preview)
 * @returns {Promise<{ passed: boolean, issues: string[] }>}
 */
async function validateDeployment(previewUrl) {
  console.log(`\n  Validating deployment: ${previewUrl}\n`);
  const issues = [];

  try {
    // 1. Check HTTP 200 response
    const response = await fetch(previewUrl, {
      headers: { 'User-Agent': 'web-builder-validator/1.0' },
      redirect: 'follow',
    });

    if (response.status !== 200) {
      issues.push(`HTTP ${response.status} — expected 200`);
    } else {
      console.log(`  ✅ HTTP ${response.status} OK`);
    }

    // 2. Check response has content
    const html = await response.text();
    if (html.length < 500) {
      issues.push(`Page HTML too short (${html.length} chars) — may be an error page`);
    } else {
      console.log(`  ✅ Page has content (${html.length} chars)`);
    }

    // 3. Check for React/Next.js error indicators
    if (html.includes('Application error') || html.includes('Internal Server Error')) {
      issues.push('Page contains error message — application may have crashed');
    }

    // 4. Check for visible text content (basic check against blank page)
    const textMatch = html.match(/<(?:h[1-6]|p|span|a|li|td|th|label|button)[^>]*>[^<]+/gi);
    const textNodeCount = textMatch ? textMatch.length : 0;
    if (textNodeCount < 5) {
      issues.push(`Only ${textNodeCount} visible text elements — page may be blank/broken`);
    } else {
      console.log(`  ✅ Found ${textNodeCount} text elements`);
    }

    // 5. Check for console error indicators in SSR HTML
    if (html.includes('Hydration failed') || html.includes('hydration mismatch')) {
      issues.push('Hydration error detected in page HTML');
    }
  } catch (err) {
    issues.push(`Fetch failed: ${err.message}`);
  }

  // Report
  if (issues.length > 0) {
    console.log('\n  ⚠ Deployment issues found:');
    issues.forEach((i) => console.log(`    ❌ ${i}`));
  } else {
    console.log('\n  ✅ Deployment validation passed');
  }

  return { passed: issues.length === 0, issues };
}

// ---------------------------------------------------------------------------
// CLI argument parsing
// ---------------------------------------------------------------------------

function printUsage() {
  console.log(
    `Usage: node validate-build.js <project-dir> [options]
   Or:  node validate-build.js <preview-url>   (post-deploy validation)

Options (project-dir mode):
  --reference-dir <dir>   Directory containing reference screenshots (ordered by name)
  --port <number>         Dev server port (default: 4567)
  --threshold <0-1>       Per-section diff threshold (default: 0.25)
  -h, --help              Show this help message`
  );
}

function parseArgs(argv) {
  const args = argv.slice(2);

  if (args.length === 0 || args.includes('-h') || args.includes('--help')) {
    printUsage();
    process.exit(0);
  }

  const parsed = {
    projectDir: null,
    referenceDir: null,
    port: 4567,
    threshold: 0.25,
  };

  let i = 0;

  // First positional argument is the project directory
  if (!args[0].startsWith('--')) {
    parsed.projectDir = args[0];
    i = 1;
  }

  for (; i < args.length; i++) {
    switch (args[i]) {
      case '--reference-dir':
        parsed.referenceDir = args[++i];
        break;
      case '--port':
        parsed.port = parseInt(args[++i], 10);
        if (Number.isNaN(parsed.port)) {
          console.error('Error: --port must be a number');
          process.exit(1);
        }
        break;
      case '--threshold':
        parsed.threshold = parseFloat(args[++i]);
        if (Number.isNaN(parsed.threshold) || parsed.threshold < 0 || parsed.threshold > 1) {
          console.error('Error: --threshold must be a number between 0 and 1');
          process.exit(1);
        }
        break;
      default:
        if (!parsed.projectDir && !args[i].startsWith('--')) {
          parsed.projectDir = args[i];
        } else {
          console.error(`Unknown option: ${args[i]}`);
          printUsage();
          process.exit(1);
        }
    }
  }

  if (!parsed.projectDir) {
    console.error('Error: <project-dir> is required');
    printUsage();
    process.exit(1);
  }

  return parsed;
}

// ---------------------------------------------------------------------------
// Reference screenshot discovery
// ---------------------------------------------------------------------------

/**
 * Collect reference screenshots from a directory, sorted alphabetically.
 * Accepts .png and .jpg files.
 */
function discoverScreenshots(dir) {
  if (!fs.existsSync(dir)) {
    return [];
  }

  return fs
    .readdirSync(dir)
    .filter((f) => /\.(png|jpe?g)$/i.test(f))
    .sort()
    .map((f) => path.join(dir, f));
}

/**
 * Auto-detect reference screenshots.
 * Looks in common locations relative to the project directory:
 *   1. <project-dir>/.quality/references/
 *   2. <project-dir>/references/
 *   3. output/<project-name>/references/  (relative to cwd)
 */
function autoDetectReferences(projectDir) {
  const candidates = [
    path.join(projectDir, '.quality', 'references'),
    path.join(projectDir, 'references'),
    path.join(
      process.cwd(),
      'output',
      path.basename(projectDir),
      'references'
    ),
  ];

  for (const candidate of candidates) {
    const shots = discoverScreenshots(candidate);
    if (shots.length > 0) {
      console.log(`  Auto-detected references in: ${candidate}`);
      return shots;
    }
  }

  return [];
}

// ---------------------------------------------------------------------------
// Report formatting
// ---------------------------------------------------------------------------

function formatReport(report) {
  const PASS = '\x1b[32m✓ PASS\x1b[0m';
  const FAIL = '\x1b[31m✗ FAIL\x1b[0m';
  const BOLD = '\x1b[1m';
  const RESET = '\x1b[0m';
  const DIM = '\x1b[2m';

  const lines = [];

  lines.push('');
  lines.push(`${BOLD}━━━ Visual Validation Report ━━━${RESET}`);
  lines.push('');

  // Per-section results
  for (const section of report.sections) {
    const similarity = ((1 - section.diffPercentage) * 100).toFixed(1);
    const status = section.needsRegeneration ? FAIL : PASS;
    const bar = buildProgressBar(1 - section.diffPercentage, 20);

    lines.push(`  ${status}  ${section.name}  ${bar}  ${similarity}%`);

    if (section.needsRegeneration) {
      lines.push(
        `        ${DIM}diff: ${section.diffScreenshot}${RESET}`
      );
    }
  }

  lines.push('');

  // Summary
  const overallPct = (report.overallSimilarity * 100).toFixed(1);
  lines.push(
    `  ${BOLD}Overall similarity:${RESET}  ${overallPct}%  ${buildProgressBar(report.overallSimilarity, 30)}`
  );
  lines.push(
    `  ${BOLD}Sections needing fixes:${RESET}  ${report.sectionsNeedingFixes} / ${report.sections.length}`
  );
  lines.push(`  ${BOLD}Iterations used:${RESET}  ${report.iterations}`);

  lines.push('');

  // Verdict
  if (report.passed) {
    lines.push(`  ${BOLD}\x1b[32m▶ PASSED${RESET}`);
  } else {
    lines.push(`  ${BOLD}\x1b[31m▶ FAILED${RESET}`);
    lines.push('');
    lines.push('  Sections that need regeneration:');
    for (const section of report.sections) {
      if (section.needsRegeneration) {
        const sim = ((1 - section.diffPercentage) * 100).toFixed(1);
        lines.push(`    - ${section.name} (${sim}% similar)`);
      }
    }
  }

  lines.push('');

  return lines.join('\n');
}

function buildProgressBar(ratio, length) {
  const filled = Math.round(ratio * length);
  const empty = length - filled;
  const green = '\x1b[42m \x1b[0m';
  const gray = '\x1b[100m \x1b[0m';
  return green.repeat(filled) + gray.repeat(empty);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const argv = process.argv.slice(2);
  if (describe(CAPABILITY, argv)) return 0;
  const firstArg = argv[0];

  // Standalone deployment validation: node validate-build.js <preview-url>
  if (firstArg && (firstArg.startsWith('http://') || firstArg.startsWith('https://'))) {
    const result = await validateDeployment(firstArg);
    process.exit(result.passed ? 0 : 1);
  }

  if (!firstArg || firstArg === '-h' || firstArg === '--help') {
    printUsage();
    process.exit(0);
  }

  const opts = parseArgs(process.argv);

  const projectDir = path.resolve(opts.projectDir);

  if (!fs.existsSync(projectDir)) {
    console.error(`Error: Project directory does not exist: ${projectDir}`);
    process.exit(1);
  }

  console.log(`\nValidating build: ${projectDir}`);

  // Discover reference screenshots
  let referenceScreenshots;

  if (opts.referenceDir) {
    const refDir = path.resolve(opts.referenceDir);
    referenceScreenshots = discoverScreenshots(refDir);
    if (referenceScreenshots.length === 0) {
      console.error(`Error: No screenshots found in ${refDir}`);
      process.exit(1);
    }
    console.log(
      `  Using ${referenceScreenshots.length} reference(s) from: ${refDir}`
    );
  } else {
    referenceScreenshots = autoDetectReferences(projectDir);
    if (referenceScreenshots.length === 0) {
      console.error(
        'Error: No reference screenshots found.\n' +
          'Use --reference-dir to specify the directory, or place them in:\n' +
          `  ${path.join(projectDir, '.quality', 'references')}/\n` +
          `  ${path.join(projectDir, 'references')}/`
      );
      process.exit(1);
    }
  }

  console.log(`  Port: ${opts.port}`);
  console.log(`  Threshold: ${opts.threshold}`);
  console.log('');

  // Run validation
  let report;
  try {
    report = await validateBuild(projectDir, referenceScreenshots, {
      port: opts.port,
      diffThreshold: opts.threshold,
      maxIterations: 2,
    });
  } catch (err) {
    console.error(`\nValidation error: ${err.message}`);
    if (err.stack) {
      console.error(err.stack);
    }
    process.exit(1);
  }

  // Print formatted report
  console.log(formatReport(report));

  // Save JSON report
  const reportPath = path.join(projectDir, '.quality-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`Report saved to: ${reportPath}\n`);

  // Exit code reflects pass/fail
  process.exit(report.passed ? 0 : 1);
}

module.exports = { validateDeployment };

main().catch((err) => {
  console.error('Unexpected error:', err);
  process.exit(1);
});

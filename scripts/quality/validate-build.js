#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { validateBuild } = require('./lib/visual-validator');

// ---------------------------------------------------------------------------
// CLI argument parsing
// ---------------------------------------------------------------------------

function printUsage() {
  console.log(
    `Usage: node validate-build.js <project-dir> [options]

Options:
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

main().catch((err) => {
  console.error('Unexpected error:', err);
  process.exit(1);
});

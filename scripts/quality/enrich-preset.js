#!/usr/bin/env node

/**
 * Preset Enrichment CLI
 * Analyzes reference sites listed in a web-builder preset, extracts their
 * real design tokens, and compares against the preset's claimed values.
 *
 * Usage: node enrich-preset.js <preset-name> [--output-dir <dir>] [--max-sites <n>]
 */

const path = require('path');
const fs = require('fs');
const { extractReference } = require('./lib/extract-reference');
const { collectTokens, compareToPreset, parsePreset } = require('./lib/design-tokens');
const { describe } = require('./lib/capability');

const PRESETS_DIR = path.resolve(__dirname, '../../skills/presets');
const DEFAULT_OUTPUT_DIR = path.resolve(__dirname, '../../output/enrichment');

/** What this instrument is, in its own words. Compiled into the capability
 *  register by `scripts/capability_register.py`; see that file for why it lives
 *  here. */
const CAPABILITY = {
  id: 'aurelix.probe.preset-enrichment',
  name: 'Preset claim vs live reference-site probe',
  kind: 'probe',
  invocation: 'node scripts/quality/enrich-preset.js <preset-name> [--output-dir <dir>] [--max-sites <n>]',
  preconditions: [
    'skills/presets/<preset-name>.md exists and lists reference sites',
    'playwright with chromium installed — extract-reference.js launches a headless browser and nothing checks it first',
    'outbound network access to the reference sites',
  ],
  inputs: ['skills/presets/<preset-name>.md', 'the live reference sites the preset names'],
  outputs: [
    '<output-dir>/enrichment-report-<preset>.md — accuracy, confirmed claims, discrepancies, top fonts, discoveries',
    '<output-dir>/<preset>/<host>/ — the raw per-site extraction from extract-reference.js',
  ],
  outcome: 'how much of what a preset claims about its reference sites is true of those sites today, per claim, with the measured value beside the claimed one',
  exit_contract: {
    0: 'the report was written. It exits 0 at ANY accuracy — 0% confirmed and 100% confirmed return the same code, because this reports and does not judge',
    1: 'no preset name given, the preset file does not exist, the preset lists no usable reference sites, every site failed to extract, or a fatal throw',
  },
  measures: [
    'rendered fonts, text colours, background colours and border radii per reference site, from computed style in a real browser',
    'frequency across sites — a token on 5 of 5 sites is reported differently from one on 1 of 5',
    'match / mismatch / discovery against the preset\'s own claims, with a severity per mismatch',
  ],
  cannot_see: [
    'a site it failed to reach. Per-site failures are caught, pushed to failedSites and printed, and the accuracy figure is then computed over the survivors alone — a report saying "5 sites analyzed" where 4 failed reads as a weaker claim, not as an unmeasured one, and still exits 0',
    'whether the reference site is the one the preset meant. nameToUrl() GUESSES a URL from a prose name — it strips punctuation and appends .com — so a wrong-but-live domain is measured with full confidence and never flagged',
    'whether the preset is wrong or the site changed. A discrepancy is reported as a discrepancy; which side moved is outside what it reads',
    'anything a headless chromium at 1440x900 does not render: consent walls, geo-variant designs, A/B arms, authed and hover states',
    'whether anyone acts on it. It never edits the preset it grades, no caller invokes it beyond the npm alias, and no gate reads the report',
  ],
  reachable_from: ['scripts/quality/package.json — `npm run enrich`', 'standalone CLI'],
  cost: 'browser-bound: roughly 10-40s per reference site, default 5 sites. Requires network and an installed chromium',
};

function parseArgs() {
  const args = process.argv.slice(2);
  const config = { presetName: null, outputDir: DEFAULT_OUTPUT_DIR, maxSites: 5 };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--output-dir' || args[i] === '-o') config.outputDir = path.resolve(args[++i]);
    else if (args[i] === '--max-sites' || args[i] === '-n') config.maxSites = parseInt(args[++i], 10);
    else if (args[i] === '--help' || args[i] === '-h') { printUsage(); process.exit(0); }
    else if (!args[i].startsWith('-')) config.presetName = args[i];
  }
  return config;
}

function printUsage() {
  console.log('\nUsage: node enrich-preset.js <preset-name> [options]\n');
  console.log('Options:');
  console.log('  --output-dir, -o <dir>   Output directory (default: output/enrichment/)');
  console.log('  --max-sites, -n <num>    Max sites to analyze (default: 5)');
  console.log('  --help, -h               Show help\n');
  console.log('Available presets:');
  const presets = fs.readdirSync(PRESETS_DIR)
    .filter((f) => f.endsWith('.md') && f !== '_template.md')
    .map((f) => '  - ' + f.replace('.md', ''));
  console.log(presets.join('\n'));
}

function nameToUrl(name) {
  let cleaned = name.trim().toLowerCase();
  if (cleaned.startsWith('look for') || cleaned.length > 50) return null;
  cleaned = cleaned.replace(/\s*\(.*\)\s*$/, '').trim();
  if (!cleaned) return null;
  if (cleaned.includes('.com') || cleaned.includes('.')) {
    return cleaned.startsWith('http') ? cleaned : 'https://www.' + cleaned;
  }
  const domain = cleaned.replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '').trim();
  return domain ? 'https://www.' + domain + '.com' : null;
}

function aggregateTokens(allTokens) {
  const fontFreq = {}, colorFreq = {}, bgColorFreq = {}, radiusFreq = {};
  for (const tokens of allTokens) {
    for (const f of tokens.fonts) fontFreq[f] = (fontFreq[f] || 0) + 1;
    for (const c of tokens.colors.slice(0, 20)) colorFreq[c] = (colorFreq[c] || 0) + 1;
    for (const bg of tokens.backgroundColors.slice(0, 10)) bgColorFreq[bg] = (bgColorFreq[bg] || 0) + 1;
    for (const r of tokens.borderRadii) radiusFreq[r] = (radiusFreq[r] || 0) + 1;
  }
  const sortByFreq = (obj) =>
    Object.entries(obj).sort((a, b) => b[1] - a[1])
      .map(([value, count]) => ({ value, count, percentage: count / allTokens.length }));
  return {
    siteCount: allTokens.length,
    fonts: sortByFreq(fontFreq),
    textColors: sortByFreq(colorFreq).slice(0, 15),
    backgroundColors: sortByFreq(bgColorFreq).slice(0, 10),
    borderRadii: sortByFreq(radiusFreq).slice(0, 10),
  };
}

function generateReport(presetName, aggregated, comparison, analyzed, failed) {
  const ts = new Date().toISOString().split('T')[0];
  const acc = (comparison.accuracy * 100).toFixed(1);
  let r = '# Preset Enrichment Report: ' + presetName + '\n\n';
  r += '**Generated:** ' + ts + '\n';
  r += '**Sites Analyzed:** ' + analyzed.length + '\n';
  r += '**Preset Accuracy:** ' + acc + '%\n\n---\n\n';
  r += '## Sites Analyzed\n\n';
  r += analyzed.map((s) => '- ' + s).join('\n') + '\n';
  if (failed.length > 0) r += '\n' + failed.map((s) => '- FAILED: ' + s).join('\n') + '\n';
  r += '\n---\n\n## Confirmed (' + comparison.matches.length + ')\n\n';
  r += comparison.matches.map((m) => '- ' + m.type + ': ' + m.claim + (m.detail ? ' — ' + m.detail : '')).join('\n') + '\n';
  r += '\n## Discrepancies (' + comparison.mismatches.length + ')\n\n';
  r += comparison.mismatches.map((m) => '- [' + m.severity + '] ' + m.type + ': ' + m.claim + ' → ' + m.actual).join('\n') + '\n';
  r += '\n---\n\n## Top Fonts\n\n';
  r += aggregated.fonts.slice(0, 8).map((f) => '- ' + f.value + ' (' + f.count + '/' + aggregated.siteCount + ' sites)').join('\n') + '\n';
  r += '\n## Discoveries\n\n';
  r += comparison.discoveries.map((d) => '- ' + d.type + ': ' + d.value).join('\n') + '\n';
  return r;
}

async function main() {
  if (describe(CAPABILITY)) return;
  const config = parseArgs();
  if (!config.presetName) { console.error('Error: No preset name.'); printUsage(); process.exit(1); }

  const presetPath = path.join(PRESETS_DIR, config.presetName + '.md');
  if (!fs.existsSync(presetPath)) { console.error('Error: Preset not found: ' + presetPath); printUsage(); process.exit(1); }

  const preset = parsePreset(presetPath);
  const siteNames = preset.referenceSites.map(nameToUrl).filter(Boolean).slice(0, config.maxSites);
  if (siteNames.length === 0) { console.error('Error: No reference sites found in preset.'); process.exit(1); }

  console.log('\n  PRESET ENRICHMENT: ' + config.presetName);
  console.log('  Sites to analyze: ' + siteNames.length + '\n');

  const extractionDir = path.join(config.outputDir, config.presetName);
  fs.mkdirSync(extractionDir, { recursive: true });

  const allTokens = [], analyzedSites = [], failedSites = [];

  for (let i = 0; i < siteNames.length; i++) {
    const url = siteNames[i];
    console.log('  [' + (i + 1) + '/' + siteNames.length + '] ' + url);
    try {
      const siteDir = path.join(extractionDir, url.replace(/https?:\/\//, '').replace(/[/\\:]/g, '-'));
      const data = await extractReference(url, siteDir);
      const tokens = collectTokens(data);
      allTokens.push(tokens);
      analyzedSites.push(url);
      console.log('    Fonts: ' + tokens.fonts.slice(0, 4).join(', '));
    } catch (err) {
      console.error('    Failed: ' + err.message);
      failedSites.push(url);
    }
  }

  if (allTokens.length === 0) { console.error('No sites analyzed.'); process.exit(1); }

  const aggregated = aggregateTokens(allTokens);
  const merged = {
    fonts: [...new Set(allTokens.flatMap((t) => t.fonts))],
    allFonts: [...new Set(allTokens.flatMap((t) => t.allFonts))],
    colors: [...new Set(allTokens.flatMap((t) => t.colors))],
    backgroundColors: [...new Set(allTokens.flatMap((t) => t.backgroundColors))],
    fontSizes: [...new Set(allTokens.flatMap((t) => t.fontSizes))],
    fontWeights: [...new Set(allTokens.flatMap((t) => t.fontWeights))],
    borderRadii: [...new Set(allTokens.flatMap((t) => t.borderRadii))],
    spacing: [], notable: [],
  };

  const comparison = compareToPreset(merged, presetPath);
  comparison.sitesAnalyzed = analyzedSites.length;

  const report = generateReport(config.presetName, aggregated, comparison, analyzedSites, failedSites);
  const reportPath = path.join(config.outputDir, 'enrichment-report-' + config.presetName + '.md');
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, report, 'utf-8');

  console.log('\n  ENRICHMENT COMPLETE');
  console.log('  Accuracy:      ' + (comparison.accuracy * 100).toFixed(1) + '%');
  console.log('  Confirmed:     ' + comparison.matches.length);
  console.log('  Discrepancies: ' + comparison.mismatches.length);
  console.log('  Report: ' + reportPath + '\n');
}

main().catch((err) => { console.error('FATAL: ' + err.message); process.exit(1); });

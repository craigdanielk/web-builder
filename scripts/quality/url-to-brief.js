#!/usr/bin/env node

/**
 * URL → Brief Generator
 * Extracts text content from a reference URL and generates a complete
 * web-builder brief .md file using Claude.
 *
 * Usage:
 *   node url-to-brief.js <url> <project-name> [--extraction-dir <dir>]
 *
 * If --extraction-dir is provided, skips extraction and reads existing data.
 * Otherwise, runs extractReference() first.
 */

'use strict';

const path = require('path');
const fs = require('fs');
require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

const { callClaudeCli } = require('./lib/claude-cli');
const { extractReference } = require('./lib/extract-reference');
const { describe } = require('./lib/capability');

const BRIEFS_DIR = path.resolve(__dirname, '../../briefs');
const BRIEF_TEMPLATE_PATH = path.join(BRIEFS_DIR, '_template.md');

/** What this instrument is, in its own words. Compiled into the capability
 *  register by `scripts/capability_register.py`; see that file for why it
 *  lives here. */
const CAPABILITY = {
  id: 'aurelix.generator.url-to-brief',
  name: 'URL → brief generator (LLM)',
  kind: 'generator',
  invocation: 'node scripts/quality/url-to-brief.js <url> <project-name> [--extraction-dir <dir>]',
  preconditions: [
    'briefs/_template.md exists — it is read unconditionally and a missing file throws',
    'the `claude` CLI is installed and subscription-authenticated (callClaudeCli; no ANTHROPIC_API_KEY is used)',
    'without --extraction-dir: playwright chromium installed and the URL reachable, because extractReference() crawls it live',
    'with --extraction-dir: that directory already holds extraction-data.json (written by url-to-preset.js)',
  ],
  inputs: [
    'a live URL, or a prior extraction directory\'s extraction-data.json',
    'briefs/_template.md',
  ],
  outputs: [
    'briefs/<project-name>.md — OVERWRITTEN unconditionally, no backup, no confirmation',
    'without --extraction-dir also: output/extractions/<project-name>/ (whatever extractReference persists)',
  ],
  outcome: 'a written client brief inferred by an LLM from one page of extracted headings, paragraphs, CTAs, links, section labels and image alt text',
  exit_contract: {
    0: 'the brief was written — or --help was passed',
    1: 'usage error (url or project-name missing), --extraction-dir has no extraction-data.json, or any exception (extraction failure, missing template, claude CLI failure) via the FATAL handler',
  },
  measures: [
    'up to 20 headings, 15 paragraphs >30 chars, 10 interactive elements, 15 links, all section labels and 10 image alts from the extraction',
    'a single page — the URL it was given, nothing followed from it',
  ],
  cannot_see: [
    'whether anything it wrote is TRUE — the brief is an LLM inference about business, audience and brand personality from one page of markup, and nothing downstream distinguishes it from an operator-authored brief',
    'more than one page: extractReference() crawls exactly the URL given, so a site whose purpose lives on /about or /pricing is described from its home page alone',
    'design tokens, colour, type or layout — it reads text and hrefs only; that half is url-to-preset.js',
    'that a --extraction-dir bundle is stale: it reads extraction-data.json with no freshness or source-URL check, so a brief can be generated for one URL from another URL\'s crawl',
    'whether briefs/<project-name>.md already held hand-authored work — it overwrites, and only git recovers it',
    'its own output quality: the CLI response is written to disk unparsed and unvalidated, so an error message or a refusal becomes the brief',
  ],
  reachable_from: ['scripts/orchestrate.py:889 (the --from-url path, step 0b)'],
  cost: 'one live crawl (~30-90s) unless --extraction-dir is given, plus one `claude` sonnet call; 120s timeout when invoked from orchestrate.py',
};

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function parseArgs() {
  const args = process.argv.slice(2);
  const config = { url: null, projectName: null, extractionDir: null };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--extraction-dir' || args[i] === '-e') {
      config.extractionDir = path.resolve(args[++i]);
    } else if (args[i] === '--help' || args[i] === '-h') {
      console.log('\nUsage: node url-to-brief.js <url> <project-name> [--extraction-dir <dir>]\n');
      process.exit(0);
    } else if (!args[i].startsWith('-')) {
      if (!config.url) config.url = args[i];
      else if (!config.projectName) config.projectName = args[i];
    }
  }

  if (!config.url || !config.projectName) {
    console.error('Error: Both <url> and <project-name> are required.');
    process.exit(1);
  }

  return config;
}

// ---------------------------------------------------------------------------
// Brief generation via Claude
// ---------------------------------------------------------------------------

async function generateBrief(url, extractionData, projectName) {
  const briefTemplate = fs.readFileSync(BRIEF_TEMPLATE_PATH, 'utf-8');

  // Extract meaningful text content
  const headings = (extractionData.textContent || [])
    .filter((t) => t.isHeading)
    .slice(0, 20)
    .map((t) => `<${t.tag}>: "${t.text.slice(0, 200)}"`);

  const paragraphs = (extractionData.textContent || [])
    .filter((t) => t.tag === 'p' && t.text.length > 30)
    .slice(0, 15)
    .map((t) => t.text.slice(0, 300));

  const ctas = (extractionData.textContent || [])
    .filter((t) => t.isInteractive)
    .slice(0, 10)
    .map((t) => `"${t.text.slice(0, 80)}"${t.href ? ' → ' + t.href.slice(0, 60) : ''}`);

  const links = (extractionData.textContent || [])
    .filter((t) => t.tag === 'a' && t.href)
    .slice(0, 15)
    .map((t) => `"${t.text.slice(0, 60)}" → ${t.href.slice(0, 80)}`);

  // Section labels
  const sectionLabels = (extractionData.sections || [])
    .filter((s) => s.label)
    .map((s) => s.label);

  // Image alt texts
  const imageAlts = (extractionData.assets?.images || [])
    .filter((img) => img.alt && img.alt.length > 3)
    .slice(0, 10)
    .map((img) => img.alt);

  const prompt = `You are a senior web strategist analyzing a website to create a client brief for rebuilding it.

## Source URL
${url}

## Extracted Content

### Page Headings (in order)
${headings.join('\n') || '(none extracted)'}

### Body Text Samples
${paragraphs.join('\n---\n') || '(none extracted)'}

### Call-to-Action Buttons
${ctas.join('\n') || '(none found)'}

### Navigation Links
${links.join('\n') || '(none found)'}

### Section Labels
${sectionLabels.join(', ') || '(none detected)'}

### Image Descriptions
${imageAlts.join(', ') || '(none available)'}

## Brief Template
${briefTemplate}

## Instructions

Generate a COMPLETE brief following the template format EXACTLY. Analyze the extracted content to determine:

1. **Business**: What does this business do? Infer from headings, body text, and CTAs.
2. **What They Need**: Based on the site structure, what is the website's purpose?
3. **Key Requirements**: What features/sections does the current site have that the rebuild should include?
4. **Target Audience**: Infer from the tone, imagery, and product/service type.
5. **Brand Personality**: Analyze the heading tone, CTA language, and writing style.
6. **Specific Requests**: Note any distinctive design elements, layouts, or content approaches that should be preserved.
7. **Technical Notes**: Standard Next.js build unless something specific was detected.

The project name is: ${projectName}

Write the brief as if a human project manager analyzed the site and wrote requirements.
Be specific and concrete — no generic filler.

Output ONLY the brief markdown. No explanation, no code fences around the entire output.`;

  // Subscription-auth via the claude CLI (no ANTHROPIC_API_KEY needed).
  return callClaudeCli(prompt, 'sonnet');
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  if (describe(CAPABILITY)) return 0;
  const config = parseArgs();

  console.log('\n  URL → BRIEF GENERATOR');
  console.log('  URL:     ' + config.url);
  console.log('  Project: ' + config.projectName);
  console.log('');

  let extractionData;

  if (config.extractionDir) {
    // Load existing extraction data
    const dataPath = path.join(config.extractionDir, 'extraction-data.json');
    if (!fs.existsSync(dataPath)) {
      console.error('Error: No extraction data at ' + dataPath);
      process.exit(1);
    }
    console.log('  [1/2] Loading existing extraction data...');
    extractionData = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
  } else {
    // Run extraction
    console.log('  [1/2] Extracting content from URL...');
    const extractionDir = path.resolve(__dirname, '../../output/extractions', config.projectName);
    extractionData = await extractReference(config.url, extractionDir);
  }

  console.log('    Headings: ' + (extractionData.textContent || []).filter((t) => t.isHeading).length);
  console.log('    Paragraphs: ' + (extractionData.textContent || []).filter((t) => t.tag === 'p').length);
  console.log('    CTAs: ' + (extractionData.textContent || []).filter((t) => t.isInteractive).length);

  // Generate brief via Claude
  console.log('  [2/2] Generating brief via Claude...');
  const briefContent = await generateBrief(config.url, extractionData, config.projectName);

  // Save
  const outputPath = path.join(BRIEFS_DIR, config.projectName + '.md');
  fs.writeFileSync(outputPath, briefContent, 'utf-8');

  console.log('\n  BRIEF GENERATED');
  console.log('  Saved to: ' + outputPath);
  console.log('');
}

main().catch((err) => { console.error('FATAL: ' + err.message); console.error(err.stack); process.exit(1); });

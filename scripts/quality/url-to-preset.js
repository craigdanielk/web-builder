#!/usr/bin/env node

/**
 * URL → Preset Generator
 * Extracts visual identity from a reference URL and generates a complete
 * web-builder preset .md file using Claude.
 *
 * Usage:
 *   node url-to-preset.js <url> <preset-name> [--output-dir <dir>]
 *
 * Example:
 *   node url-to-preset.js https://www.tradecoffee.com artisan-clone
 */

'use strict';

const path = require('path');
const fs = require('fs');
require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

const Anthropic = require('@anthropic-ai/sdk');
const { extractReference } = require('./lib/extract-reference');
const { collectTokens, rgbToHex } = require('./lib/design-tokens');
const { mapSectionsToArchetypes } = require('./lib/archetype-mapper');

const PRESETS_DIR = path.resolve(__dirname, '../../skills/presets');
const TEMPLATE_PATH = path.join(PRESETS_DIR, '_template.md');

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function parseArgs() {
  const args = process.argv.slice(2);
  const config = { url: null, presetName: null, outputDir: PRESETS_DIR };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--output-dir' || args[i] === '-o') {
      config.outputDir = path.resolve(args[++i]);
    } else if (args[i] === '--help' || args[i] === '-h') {
      console.log('\nUsage: node url-to-preset.js <url> <preset-name> [--output-dir <dir>]\n');
      process.exit(0);
    } else if (!args[i].startsWith('-')) {
      if (!config.url) config.url = args[i];
      else if (!config.presetName) config.presetName = args[i];
    }
  }

  if (!config.url || !config.presetName) {
    console.error('Error: Both <url> and <preset-name> are required.');
    console.log('Usage: node url-to-preset.js <url> <preset-name> [--output-dir <dir>]');
    process.exit(1);
  }

  return config;
}

// ---------------------------------------------------------------------------
// Tailwind color approximation
// ---------------------------------------------------------------------------

function hexToTailwindApprox(hex) {
  if (!hex || !hex.startsWith('#')) return hex;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const brightness = (r * 299 + g * 587 + b * 114) / 1000;

  // Very rough mapping to Tailwind palette names
  if (brightness > 240) return 'white';
  if (brightness > 220) return 'gray-50';
  if (brightness > 200) return 'gray-100';
  if (brightness > 170) return 'gray-200';
  if (brightness > 140) return 'gray-300';
  if (brightness > 100) return 'gray-500';
  if (brightness > 60) return 'gray-700';
  if (brightness > 30) return 'gray-900';
  return 'black';
}

// ---------------------------------------------------------------------------
// Preset generation via Claude
// ---------------------------------------------------------------------------

async function generatePreset(url, tokens, mappedSections, extractionData) {
  const client = new Anthropic();
  const template = fs.readFileSync(TEMPLATE_PATH, 'utf-8');

  // Build section sequence from mapped archetypes
  const sectionSequence = mappedSections
    .map((s, i) => `${i + 1}. ${s.archetype.padEnd(20)} | ${s.variant}`)
    .join('\n');

  // Build token summary
  const fontList = tokens.fonts.slice(0, 6).join(', ') || 'system fonts only';
  const colorList = tokens.backgroundColors.slice(0, 8).map((c) => `${c} (${hexToTailwindApprox(c)})`).join(', ');
  const textColorList = tokens.colors.slice(0, 6).map((c) => `${c} (${hexToTailwindApprox(c)})`).join(', ');
  const radiiList = tokens.borderRadii.slice(0, 5).join(', ') || 'none detected';

  // Extract headings for tone analysis
  const headings = (extractionData.textContent || [])
    .filter((t) => t.isHeading)
    .slice(0, 10)
    .map((t) => t.text.slice(0, 100));

  const ctas = (extractionData.textContent || [])
    .filter((t) => t.isInteractive && t.tag === 'button')
    .slice(0, 8)
    .map((t) => t.text.slice(0, 60));

  const prompt = `You are a senior web designer creating a web-builder preset file from extracted design data.

## Source URL
${url}

## Extracted Design Tokens

### Fonts Found
${fontList}

### Background Colors (hex → approximate Tailwind)
${colorList || 'none detected'}

### Text Colors
${textColorList || 'none detected'}

### Border Radii Found
${radiiList}

### Section Structure Detected
${sectionSequence}

### Headings Found
${headings.map((h) => '- "' + h + '"').join('\n') || '(none extracted)'}

### CTA Button Text Found
${ctas.map((c) => '- "' + c + '"').join('\n') || '(none extracted)'}

## Preset Template
${template}

## Instructions

Generate a COMPLETE preset file following the template format EXACTLY. Fill in every field based on the extracted design tokens.

Rules:
1. Use the REAL fonts detected. If two fonts found, map to heading_font and body_font. If one font, use it for both.
2. Map extracted colors to Tailwind utility names (stone-50, amber-700, etc.) — choose the closest Tailwind color.
3. Determine color_temperature from the palette: warm-earth, cool-blue, neutral, dark-neutral, etc.
4. Set border_radius based on extracted radii: sharp (0-4px), medium (6-16px), full (16-32px), pill (32px+).
5. Set animation_intensity to moderate unless the site clearly has heavy or minimal animation.
6. Use the detected section sequence for Default Section Sequence.
7. Write realistic Content Direction based on the heading tone and CTA language found.
8. Set the preset name to match the site's industry/type.
9. Include the source URL in Reference Sites.

Output ONLY the complete preset markdown. No explanation, no code fences around the entire output.`;

  const message = await client.messages.create({
    model: 'claude-sonnet-4-5-20250929',
    max_tokens: 4096,
    messages: [{ role: 'user', content: prompt }],
  });

  const text = message.content
    .filter((b) => b.type === 'text')
    .map((b) => b.text)
    .join('\n');

  return text;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const config = parseArgs();

  console.log('\n  URL → PRESET GENERATOR');
  console.log('  URL:    ' + config.url);
  console.log('  Preset: ' + config.presetName);
  console.log('');

  // Step 1: Extract
  console.log('  [1/4] Extracting visual data from URL...');
  const extractionDir = path.resolve(__dirname, '../../output/extractions', config.presetName);
  const extractionData = await extractReference(config.url, extractionDir);

  // Step 2: Collect tokens
  console.log('  [2/4] Collecting design tokens...');
  const tokens = collectTokens(extractionData);
  console.log('    Fonts: ' + tokens.fonts.slice(0, 4).join(', '));
  console.log('    Colors: ' + tokens.backgroundColors.length + ' bg, ' + tokens.colors.length + ' text');
  console.log('    Radii: ' + tokens.borderRadii.join(', '));

  // Step 3: Map archetypes
  console.log('  [3/4] Mapping sections to archetypes...');
  const mapped = mapSectionsToArchetypes(extractionData.sections, extractionData.textContent);
  for (const m of mapped) {
    console.log('    ' + m.archetype + ' | ' + m.variant + ' (' + m.method + ', ' + (m.confidence * 100).toFixed(0) + '%)');
  }

  // Step 4: Generate preset via Claude
  console.log('  [4/4] Generating preset via Claude...');
  const presetContent = await generatePreset(config.url, tokens, mapped, extractionData);

  // Save
  const outputPath = path.join(config.outputDir, config.presetName + '.md');
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, presetContent, 'utf-8');

  // Also save extraction data as JSON for the orchestrator
  const dataPath = path.join(extractionDir, 'extraction-data.json');
  const serializableData = {
    ...extractionData,
    screenshots: { scrollCaptures: extractionData.screenshots?.scrollCaptures || 0 },
  };
  fs.writeFileSync(dataPath, JSON.stringify(serializableData, null, 2), 'utf-8');

  // Save mapped sections
  const mappedPath = path.join(extractionDir, 'mapped-sections.json');
  fs.writeFileSync(mappedPath, JSON.stringify(mapped, null, 2), 'utf-8');

  console.log('\n  PRESET GENERATED');
  console.log('  Saved to: ' + outputPath);
  console.log('  Extraction: ' + extractionDir);
  console.log('');
}

main().catch((err) => { console.error('FATAL: ' + err.message); console.error(err.stack); process.exit(1); });

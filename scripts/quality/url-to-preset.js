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
const {
  collectTokens, collectAnimationTokens, rgbToHex,
  hexToTailwindHue, collectGradientColors, identifyColorSystem, profileSectionColors,
} = require('./lib/design-tokens');
const { mapSectionsToArchetypes } = require('./lib/archetype-mapper');
const { analyzeAnimationEvidence } = require('./lib/animation-detector');

const PRESETS_DIR = path.resolve(__dirname, '../../skills/presets');
const TEMPLATE_PATH = path.join(PRESETS_DIR, '_template.md');

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function parseArgs() {
  const args = process.argv.slice(2);
  const config = { url: null, presetName: null, outputDir: PRESETS_DIR, extractionDir: null };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--output-dir' || args[i] === '-o') {
      config.outputDir = path.resolve(args[++i]);
    } else if (args[i] === '--extraction-dir') {
      config.extractionDir = path.resolve(args[++i]);
    } else if (args[i] === '--help' || args[i] === '-h') {
      console.log('\nUsage: node url-to-preset.js <url> <preset-name> [--output-dir <dir>] [--extraction-dir <dir>]\n');
      process.exit(0);
    } else if (!args[i].startsWith('-')) {
      if (!config.url) config.url = args[i];
      else if (!config.presetName) config.presetName = args[i];
    }
  }

  if (!config.url || !config.presetName) {
    console.error('Error: Both <url> and <preset-name> are required.');
    console.log('Usage: node url-to-preset.js <url> <preset-name> [--output-dir <dir>] [--extraction-dir <dir>]');
    process.exit(1);
  }

  return config;
}

// ---------------------------------------------------------------------------
// Tailwind color approximation (v0.9.0: now hue-aware via design-tokens.js)
// ---------------------------------------------------------------------------

// Legacy alias — kept for backward compatibility
function hexToTailwindApprox(hex) {
  return hexToTailwindHue(hex);
}

// ---------------------------------------------------------------------------
// Preset generation via Claude
// ---------------------------------------------------------------------------

async function generatePreset(url, tokens, mappedSections, extractionData, animationAnalysis, animationTokens, colorSystemData, gsapPlugins = []) {
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
  const pageBackgroundFirstElement = extractionData.renderedDOM?.[0]?.styles?.backgroundColor ?? 'not detected';

  // Extract headings for tone analysis
  const headings = (extractionData.textContent || [])
    .filter((t) => t.isHeading)
    .slice(0, 10)
    .map((t) => t.text.slice(0, 100));

  const ctas = (extractionData.textContent || [])
    .filter((t) => t.isInteractive && t.tag === 'button')
    .slice(0, 8)
    .map((t) => t.text.slice(0, 60));

  // Build color system intelligence block (v0.9.0)
  const csData = colorSystemData || {};
  const colorSystemBlock = csData.system
    ? `### Color System Analysis
- Type: ${csData.system} (${(csData.accents || []).length} distinct accent families)
${(csData.accents || []).map((a) => `- Accent: ${a.tailwind} (${a.hex}, source: ${a.source})`).join('\n') || '- No accents detected'}
${csData.sectionColors ? Object.entries(csData.sectionColors).filter(([, v]) => v.accent).map(([i, v]) => `- Section ${i} accent: ${v.accent}${v.gradient ? ' (from gradient)' : ''}`).join('\n') : ''}`
    : '';

  const prompt = `You are a senior web designer creating a web-builder preset file from extracted design data.

## Source URL
${url}

## Extracted Design Tokens

### Fonts Found
${fontList}

### Background Colors (hex → approximate Tailwind)
${colorList || 'none detected'}
Page background (first DOM element): ${pageBackgroundFirstElement}

### Text Colors
${textColorList || 'none detected'}

${colorSystemBlock}

### Border Radii Found
${radiiList}

### Section Structure Detected
${sectionSequence}

### Headings Found
${headings.map((h) => '- "' + h + '"').join('\n') || '(none extracted)'}

### CTA Button Text Found
${ctas.map((c) => '- "' + c + '"').join('\n') || '(none extracted)'}

### Animation Evidence
- Detected intensity: ${animationAnalysis.intensity.level} (score: ${animationAnalysis.intensity.score}, confidence: ${(animationAnalysis.intensity.confidence * 100).toFixed(0)}%)
- Inferred engine: ${animationAnalysis.engine}
- Libraries found: ${animationAnalysis.libraries.map(l => l.name).join(', ') || 'none'}
- CSS keyframes: ${animationAnalysis.cssAnimations.keyframes.join(', ') || 'none'}
- Animated elements: ${animationAnalysis.cssAnimations.animatedElements}
- Transition elements: ${animationAnalysis.cssAnimations.transitionElements}
- Scroll triggers: ${animationAnalysis.scrollAnimations.triggerCount} (patterns: ${animationAnalysis.scrollAnimations.patterns.join(', ') || 'none'})
- Rich assets: ${animationAnalysis.assets.lottie.length} Lottie, ${animationAnalysis.assets.rive.length} Rive, ${animationAnalysis.assets.threeD.length} 3D
- Animation tokens: ${animationTokens.animationNames.slice(0, 10).join(', ') || 'none'}
- Transition properties: ${animationTokens.transitionProperties.slice(0, 10).join(', ') || 'none'}
- Easing functions: ${animationTokens.easingFunctions.slice(0, 5).join(', ') || 'default'}
${gsapPlugins.length > 0 ? `
### Detected GSAP Plugins
The reference site uses these GSAP plugins: ${gsapPlugins.join(', ')}

Include a "gsap_plugins" field in the preset YAML listing these plugins:
\`\`\`yaml
gsap_plugins:
${gsapPlugins.map(p => `  - ${p}`).join('\n')}
\`\`\`

Also add section_overrides that recommend specific plugin usage for sections:
- SplitText → HERO (character-reveal), CTA (word-reveal)
- Flip → PRODUCT-SHOWCASE (filter-grid), GALLERY (layout-transition)
- DrawSVG → HERO (logo-reveal), HOW-IT-WORKS (path-progress)
- MorphSVG → FEATURES (icon-morph)
- MotionPath → HERO (orbit), FEATURES (flow-along-path)
- Draggable → TESTIMONIALS (carousel), PRODUCT-SHOWCASE (slider)
- Observer → HERO (swipe-nav), GALLERY (swipe)
- CustomEase → Define brand-specific easing curves
` : ''}

## Preset Template
${template}

## Instructions

Generate a COMPLETE preset file following the template format EXACTLY. Fill in every field based on the extracted design tokens.

Rules:
1. Use the REAL fonts detected. If two fonts found, map to heading_font and body_font. If one font, use it for both.
2. Map extracted colors to Tailwind utility names (stone-50, amber-700, etc.) — choose the closest COLORED Tailwind name (e.g. green-500 not gray-200 for a green color).
3. Determine color_temperature from the palette: warm-earth, cool-blue, neutral, dark-neutral, etc.

### Color Temperature Classification Rule
Determine the site's background color from the FIRST rendered DOM element's backgroundColor (this is typically the body/page wrapper), NOT from overlays, modals, tooltips, or navigation dropdowns.

Cross-check: If more than 60% of text colors in the extraction are dark shades (black, gray-900, gray-800, gray-700), the site is almost certainly light-themed — classify as light even if some dark overlay elements are present.

Common misclassification triggers to IGNORE when determining bg_primary:
- Dark navigation bars or sticky headers
- Modal/dialog overlays
- Tooltip backgrounds
- Cookie consent banners
- Mobile menu panels

4. Set border_radius based on extracted radii: sharp (0-4px), medium (6-16px), full (16-32px), pill (32px+).
5. Set animation_intensity to "${animationAnalysis.intensity.level}" and animation_engine to "${animationAnalysis.engine}" based on the Animation Evidence above. If confidence is below 50%, default to moderate with css engine.
6. Use the detected section sequence for Default Section Sequence.
7. Write realistic Content Direction based on the heading tone and CTA language found.
8. Set the preset name to match the site's industry/type.
9. Include the source URL in Reference Sites.
10. If Color System Analysis shows "multi-accent" or "dual-accent", populate accent_secondary (and accent_tertiary if 3+ accents) using the detected accent Tailwind names.
11. If per-section accent colors are detected, add a section_accents block mapping section class/name to its accent Tailwind color.
12. Include secondary/tertiary accents in the Compact Style Header using the format: Accents: name:color name:color

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
  console.log('  [1/5] Extracting visual data from URL...');
  // Use provided extraction dir or default (with preset name for backwards compatibility)
  const extractionDir = config.extractionDir || path.resolve(__dirname, '../../output/extractions', config.presetName);
  const extractionData = await extractReference(config.url, extractionDir);

  // Step 2: Collect tokens
  console.log('  [2/5] Collecting design tokens...');
  const tokens = collectTokens(extractionData);
  console.log('    Fonts: ' + tokens.fonts.slice(0, 4).join(', '));
  console.log('    Colors: ' + tokens.backgroundColors.length + ' bg, ' + tokens.colors.length + ' text');
  console.log('    Radii: ' + tokens.borderRadii.join(', '));

  // Step 3: Map archetypes
  console.log('  [3/5] Mapping sections to archetypes...');
  const { mappedSections: mapped, gaps: archetypeGaps } = mapSectionsToArchetypes(extractionData.sections, extractionData.textContent);
  for (const m of mapped) {
    console.log('    ' + m.archetype + ' | ' + m.variant + ' (' + m.method + ', ' + (m.confidence * 100).toFixed(0) + '%)');
  }
  if (archetypeGaps.length > 0) {
    console.log('    \u26A0 ' + archetypeGaps.length + ' low-confidence mapping(s) flagged');
  }

  // Step 2b: Identify color system (v0.9.0)
  console.log('  [2b/5] Identifying color system...');
  const gradientData = collectGradientColors(extractionData);
  const colorSystem = identifyColorSystem(tokens, gradientData);
  const sectionColorProfile = profileSectionColors(extractionData, gradientData);
  console.log('    System: ' + colorSystem.system + ' (' + colorSystem.accents.length + ' accent families)');
  for (const acc of colorSystem.accents.slice(0, 5)) {
    console.log('      ' + acc.tailwind + ' (' + acc.hex + ', ' + acc.source + ')');
  }

  // Step 3b: Analyze animations
  console.log('  [3b/5] Analyzing animation patterns...');
  const animationAnalysis = analyzeAnimationEvidence(
    extractionData.animations?.evidence || {},
    extractionData.animations?.networkResults || {},
    extractionData.sections,
    extractionData.renderedDOM
  );
  const animationTokens = collectAnimationTokens(extractionData);
  console.log('    Intensity: ' + animationAnalysis.intensity.level +
    ' (score: ' + animationAnalysis.intensity.score +
    ', confidence: ' + (animationAnalysis.intensity.confidence * 100).toFixed(0) + '%)');
  console.log('    Engine: ' + animationAnalysis.engine);
  console.log('    Libraries: ' + (animationAnalysis.libraries.map(l => l.name).join(', ') || 'none'));

  // Step 4: Generate preset via Claude
  console.log('  [4/5] Generating preset via Claude...');
  const colorSystemData = {
    ...colorSystem,
    sectionColors: sectionColorProfile.sectionColors,
  };
  const gsapPlugins = animationAnalysis?.gsapPlugins || [];
  const presetContent = await generatePreset(config.url, tokens, mapped, extractionData, animationAnalysis, animationTokens, colorSystemData, gsapPlugins);

  // Save preset with atomic write (temp file + rename to prevent race conditions)
  const outputPath = path.join(config.outputDir, config.presetName + '.md');
  const tmpPresetPath = outputPath + '.tmp-' + Date.now();
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(tmpPresetPath, presetContent, 'utf-8');
  fs.renameSync(tmpPresetPath, outputPath);

  // Also save extraction data as JSON for the orchestrator (atomic write)
  const dataPath = path.join(extractionDir, 'extraction-data.json');
  const tmpDataPath = dataPath + '.tmp-' + Date.now();
  const serializableData = {
    ...extractionData,
    screenshots: { scrollCaptures: extractionData.screenshots?.scrollCaptures || 0 },
  };
  fs.writeFileSync(tmpDataPath, JSON.stringify(serializableData, null, 2), 'utf-8');
  fs.renameSync(tmpDataPath, dataPath);

  // Save mapped sections (atomic write)
  const mappedPath = path.join(extractionDir, 'mapped-sections.json');
  const tmpMappedPath = mappedPath + '.tmp-' + Date.now();
  fs.writeFileSync(tmpMappedPath, JSON.stringify(mapped, null, 2), 'utf-8');
  fs.renameSync(tmpMappedPath, mappedPath);

  // Save archetype gaps if any (atomic write)
  if (archetypeGaps.length > 0) {
    const gapsPath = path.join(extractionDir, 'archetype-gaps.json');
    const tmpGapsPath = gapsPath + '.tmp-' + Date.now();
    fs.writeFileSync(tmpGapsPath, JSON.stringify(archetypeGaps, null, 2), 'utf-8');
    fs.renameSync(tmpGapsPath, gapsPath);
  }

  // Save animation analysis (atomic write)
  const animPath = path.join(extractionDir, 'animation-analysis.json');
  const tmpAnimPath = animPath + '.tmp-' + Date.now();
  fs.writeFileSync(tmpAnimPath, JSON.stringify(animationAnalysis, null, 2), 'utf-8');
  fs.renameSync(tmpAnimPath, animPath);

  console.log('\n  PRESET GENERATED');
  console.log('  Saved to: ' + outputPath);
  console.log('  Extraction: ' + extractionDir);
  console.log('');
}

main().catch((err) => { console.error('FATAL: ' + err.message); console.error(err.stack); process.exit(1); });

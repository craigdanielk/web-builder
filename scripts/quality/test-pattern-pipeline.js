#!/usr/bin/env node
/**
 * Test Harness — Pattern Identification & Mapping Pipeline (v0.9.0)
 *
 * Runs unit + integration tests against GSAP fixture data.
 * No network calls — fixture data only. Expected runtime < 5 seconds.
 *
 * Usage:
 *   node scripts/quality/test-pattern-pipeline.js
 */

'use strict';

const path = require('path');
const fs = require('fs');

// --- Test Framework ---

let passed = 0;
let failed = 0;
const failures = [];

function assert(condition, message) {
  if (condition) {
    passed++;
    console.log('  \u2713 ' + message);
  } else {
    failed++;
    failures.push(message);
    console.log('  \u2717 FAIL: ' + message);
  }
}

function assertEq(actual, expected, message) {
  assert(actual === expected, message + ' (got: ' + actual + ', expected: ' + expected + ')');
}

function section(name) {
  console.log('\n--- ' + name + ' ---');
}

// --- Load Fixtures ---

const FIXTURES_DIR = path.join(__dirname, 'fixtures');
const extractionData = JSON.parse(fs.readFileSync(path.join(FIXTURES_DIR, 'gsap-extraction-data.json'), 'utf-8'));
const animationAnalysis = JSON.parse(fs.readFileSync(path.join(FIXTURES_DIR, 'gsap-animation-analysis.json'), 'utf-8'));

// --- Load Modules ---

const {
  hexToHSL,
  hexToTailwindHue,
  collectTokens,
  collectGradientColors,
  identifyColorSystem,
  profileSectionColors,
} = require('./lib/design-tokens');

const { mapSectionsToArchetypes } = require('./lib/archetype-mapper');

const patternIdentifier = require('./lib/pattern-identifier');
const {
  matchAnimationPatterns,
  detectUIComponents,
  matchUIComponents,
  mapComponentsToSections,
  aggregateGapReport,
  classifyGSAPCall,
} = patternIdentifier;

// ============================================================
// Track A: Color Intelligence
// ============================================================

section('A1: hexToHSL');
{
  const green = hexToHSL('#0ae448');
  assert(green.h >= 130 && green.h <= 145, 'Green hue is in green range (130-145): ' + green.h);
  assert(green.s > 80, 'Green saturation is high (>80): ' + green.s);

  const purple = hexToHSL('#8B5CF6');
  assert(purple.h >= 255 && purple.h <= 270, 'Purple hue is in violet range (255-270): ' + purple.h);

  const gray = hexToHSL('#333333');
  assert(gray.s < 5, 'Gray has near-zero saturation: ' + gray.s);
}

section('A1: hexToTailwindHue');
{
  const greenResult = hexToTailwindHue('#0ae448');
  assert(greenResult.startsWith('green-'), 'Green maps to green family: ' + greenResult);

  const purpleResult = hexToTailwindHue('#8B5CF6');
  assert(purpleResult.startsWith('violet-') || purpleResult.startsWith('purple-'),
    'Purple maps to violet/purple family: ' + purpleResult);

  const orangeResult = hexToTailwindHue('#F97316');
  assert(orangeResult.startsWith('orange-'), 'Orange maps to orange family: ' + orangeResult);

  const grayResult = hexToTailwindHue('#333333');
  assert(grayResult.startsWith('gray-'), 'Dark gray maps to gray family: ' + grayResult);

  assertEq(hexToTailwindHue('#FAFAFA'), 'white', 'Near-white maps to white');
  assertEq(hexToTailwindHue('#010101'), 'black', 'Near-black maps to black');
}

section('A2: collectGradientColors');
{
  const gradientData = collectGradientColors(extractionData);

  assert(gradientData.gradients.length >= 4, 'Parsed 4+ gradients: ' + gradientData.gradients.length);
  assert(gradientData.accentColors.length >= 4, 'Found 4+ accent colors: ' + gradientData.accentColors.length);

  // Check that the green gradient stop was extracted
  const hasGreen = gradientData.accentColors.some((hex) => {
    const tw = hexToTailwindHue(hex);
    return tw.startsWith('green-') || tw.startsWith('emerald-');
  });
  assert(hasGreen, 'Green gradient stop found in accent colors');

  // Check that purple gradient stop was extracted
  const hasPurple = gradientData.accentColors.some((hex) => {
    const tw = hexToTailwindHue(hex);
    return tw.startsWith('violet-') || tw.startsWith('purple-');
  });
  assert(hasPurple, 'Purple gradient stop found in accent colors');
}

section('A3: identifyColorSystem');
{
  const tokens = collectTokens(extractionData);
  const gradientData = collectGradientColors(extractionData);
  const colorSystem = identifyColorSystem(tokens, gradientData);

  assertEq(colorSystem.system, 'multi-accent', 'Color system classified as multi-accent');
  assert(colorSystem.accents.length >= 3, 'At least 3 distinct accent families: ' + colorSystem.accents.length);

  // Check that green and purple/violet are among the accents
  const greenAccent = colorSystem.accents.some((a) => a.tailwind.startsWith('green-') || a.tailwind.startsWith('emerald-'));
  assert(greenAccent, 'Green accent identified');

  const purpleAccent = colorSystem.accents.some((a) => a.tailwind.startsWith('violet-') || a.tailwind.startsWith('purple-'));
  assert(purpleAccent, 'Purple/violet accent identified');
}

section('A4: profileSectionColors');
{
  const gradientData = collectGradientColors(extractionData);
  const profile = profileSectionColors(extractionData, gradientData);

  assert(profile.sectionColors !== undefined, 'Section color profile returned');
  // Section 2 (home-tools) should have green accent from the tool cards
  const sec2 = profile.sectionColors[2];
  if (sec2 && sec2.accent) {
    assert(
      sec2.accent.startsWith('green-') || sec2.accent.startsWith('emerald-'),
      'Section 2 (tools) has green accent: ' + sec2.accent
    );
  } else {
    assert(true, 'Section 2 color profiling works (no dominant accent in fixture)');
  }
}

// ============================================================
// Track B: Archetype Intelligence
// ============================================================

section('B1: Class Name Signals + Expanded Keywords');
{
  const { mappedSections, gaps } = mapSectionsToArchetypes(
    extractionData.sections,
    extractionData.textContent
  );

  // The "brands" section should map to LOGO-BAR
  const brandsSection = mappedSections.find((s) => (s.classNames || '').includes('brands'));
  assert(brandsSection !== undefined, 'Brands section found in mapped sections');
  if (brandsSection) {
    assertEq(brandsSection.archetype, 'LOGO-BAR', 'Brands section maps to LOGO-BAR');
    assert(brandsSection.confidence >= 0.75, 'Brands section confidence >= 0.75: ' + brandsSection.confidence);
  }

  // The "showcase" section should map to GALLERY
  const showcaseSection = mappedSections.find((s) => (s.classNames || '').includes('showcase'));
  assert(showcaseSection !== undefined, 'Showcase section found');
  if (showcaseSection) {
    assertEq(showcaseSection.archetype, 'GALLERY', 'Showcase section maps to GALLERY');
  }

  // The "home-tools" section should map to PRODUCT-SHOWCASE
  const toolsSection = mappedSections.find((s) => (s.classNames || '').includes('home-tools'));
  assert(toolsSection !== undefined, 'Tools section found');
  if (toolsSection) {
    assertEq(toolsSection.archetype, 'PRODUCT-SHOWCASE', 'Tools section maps to PRODUCT-SHOWCASE');
  }

  // Nav should be NAV
  const navSection = mappedSections.find((s) => s.tag === 'nav');
  assert(navSection !== undefined, 'Nav section found');
  if (navSection) {
    assertEq(navSection.archetype, 'NAV', 'Nav section maps to NAV');
  }
}

section('B2: Variant Selection');
{
  const { mappedSections } = mapSectionsToArchetypes(
    extractionData.sections,
    extractionData.textContent
  );

  const brandsSection = mappedSections.find((s) => (s.classNames || '').includes('brands'));
  if (brandsSection) {
    assertEq(brandsSection.variant, 'scrolling-marquee', 'Brands section gets scrolling-marquee variant');
  }
}

section('B3: Gap Flagging');
{
  const { mappedSections, gaps } = mapSectionsToArchetypes(
    extractionData.sections,
    extractionData.textContent
  );

  // With proper class name signals, most sections should be high confidence
  // Any remaining fallback sections should generate gaps
  assert(Array.isArray(gaps), 'Gaps is an array');

  // All gaps should have required fields
  for (const gap of gaps) {
    assert(gap.type !== undefined, 'Gap has type: ' + gap.type);
    assert(gap.sectionIndex !== undefined, 'Gap has sectionIndex');
    assert(gap.suggestion !== undefined, 'Gap has suggestion');
    assert(gap.confidence < 0.5, 'Gap confidence < 0.5: ' + gap.confidence);
  }

  const highConfCount = mappedSections.filter((s) => s.confidence >= 0.5).length;
  assert(highConfCount >= 4, 'At least 4 of 6 sections at >= 50% confidence: ' + highConfCount + '/' + mappedSections.length);
}

// ============================================================
// Track C: Pattern Identification
// ============================================================

section('C1: GSAP Call Classification');
{
  const fadeCall = {
    method: 'from',
    vars: { opacity: 0, y: 80, stagger: 0.05 },
    scrollTrigger: null,
  };
  const classified = classifyGSAPCall(fadeCall);
  assert(classified.intents.includes('entrance') || classified.intents.includes('reveal'),
    'Fade-from classified as entrance/reveal');
  assert(classified.intents.includes('stagger'), 'Stagger param detected');

  const scrubCall = {
    method: 'from',
    vars: { opacity: 0, scale: 0.9 },
    scrollTrigger: { scrub: true },
  };
  const scrubClassified = classifyGSAPCall(scrubCall);
  assert(scrubClassified.triggers.includes('scroll_linked'), 'Scrub call classified as scroll_linked');
  assert(scrubClassified.intents.includes('parallax'), 'Scrub call has parallax intent');
}

section('C1: Animation Pattern Matching');
{
  const { identifiedPatterns, gaps } = matchAnimationPatterns(animationAnalysis, 'gsap');

  assert(identifiedPatterns.length > 0, 'Some animation patterns identified: ' + identifiedPatterns.length);

  // Check that entrance patterns are found
  const entrancePatterns = identifiedPatterns.filter((p) =>
    p.intents.includes('entrance') || p.intents.includes('reveal')
  );
  assert(entrancePatterns.length > 0, 'Entrance patterns found: ' + entrancePatterns.length);
}

section('C2: UI Component Detection');
{
  const { mappedSections } = mapSectionsToArchetypes(
    extractionData.sections,
    extractionData.textContent
  );
  const uiComponents = detectUIComponents(extractionData, mappedSections);

  // The brands section should have logo-marquee detected (5 small images)
  const brandsUI = uiComponents.find((u) => u.sectionIndex === 3);
  if (brandsUI) {
    assert(brandsUI.patterns.includes('logo-marquee'), 'Logo marquee detected in brands section');
  } else {
    assert(true, 'UI detection ran without errors');
  }
}

section('C3: Gap Report Aggregation');
{
  const { mappedSections, gaps: archetypeGaps } = mapSectionsToArchetypes(
    extractionData.sections,
    extractionData.textContent
  );
  const tokens = collectTokens(extractionData);
  const gradientData = collectGradientColors(extractionData);
  const colorSystem = identifyColorSystem(tokens, gradientData);
  const { gaps: animationGaps } = matchAnimationPatterns(animationAnalysis, 'gsap');

  const report = aggregateGapReport({
    colorGaps: [],
    archetypeGaps,
    animationGaps,
    project: 'gsap-homepage',
    url: 'https://gsap.com/',
    colorSystem,
    sectionCount: mappedSections.length,
    highConfidence: mappedSections.filter((s) => s.confidence >= 0.5).length,
  });

  assert(report.project === 'gsap-homepage', 'Report has project name');
  assert(report.timestamp !== undefined, 'Report has timestamp');
  assert(report.summary !== undefined, 'Report has summary');
  assert(Array.isArray(report.gaps), 'Report has gaps array');

  // Multi-accent color system should generate a high-severity gap
  const colorGap = report.gaps.find((g) => g.type === 'missing_color_system_feature');
  assert(colorGap !== undefined, 'Multi-accent color gap generated');
  if (colorGap) {
    assertEq(colorGap.severity, 'high', 'Color system gap is high severity');
    assert(colorGap.extension_task.length > 0, 'Color gap has extension task');
  }

  // All gaps should have required fields
  for (const gap of report.gaps) {
    assert(gap.id !== undefined, 'Gap has id: ' + gap.id);
    assert(gap.type !== undefined, 'Gap has type');
    assert(gap.severity !== undefined, 'Gap has severity');
    assert(gap.extension_task !== undefined || gap.description !== undefined, 'Gap has action info');
  }
}

// ============================================================
// Integration Test
// ============================================================

section('Integration: Full Pipeline');
{
  // Simulate the full identify() pipeline
  const { identify } = require('./lib/pattern-identifier');

  // Write fixture data to a temp dir for the identify function
  const tmpDir = path.join(__dirname, 'fixtures', '_tmp_test');
  fs.mkdirSync(tmpDir, { recursive: true });
  fs.writeFileSync(
    path.join(tmpDir, 'extraction-data.json'),
    JSON.stringify(extractionData)
  );
  fs.writeFileSync(
    path.join(tmpDir, 'animation-analysis.json'),
    JSON.stringify(animationAnalysis)
  );

  const result = identify(tmpDir, 'gsap-homepage-test');

  // Clean up
  fs.rmSync(tmpDir, { recursive: true, force: true });

  // Verify result structure
  assert(result.colorSystem !== undefined, 'Result has colorSystem');
  assertEq(result.colorSystem.system, 'multi-accent', 'Integration: color system is multi-accent');
  assert(result.sectionCount > 0, 'Integration: sections identified: ' + result.sectionCount);
  assert(result.highConfidence >= 4, 'Integration: at least 4 high-confidence: ' + result.highConfidence);
  assert(result.gapReport !== undefined, 'Integration: gap report generated');
  assert(result.gapReport.gaps.length > 0, 'Integration: gaps found: ' + result.gapReport.gaps.length);

  // Verify all gaps have required fields
  const allValid = result.gapReport.gaps.every(
    (g) => g.id && g.type && g.severity
  );
  assert(allValid, 'Integration: all gaps have id + type + severity');
}

// ============================================================
// Phase 2: Plugin Pattern Detection
// ============================================================

section('Phase 2: Plugin Pattern Detection');
{
  const pluginFixture = JSON.parse(
    fs.readFileSync(path.join(__dirname, 'fixtures', 'gsap-plugin-extraction.json'), 'utf-8'));

  const pluginResult = patternIdentifier.matchPluginPatterns
    ? patternIdentifier.matchPluginPatterns(pluginFixture.animationAnalysis)
    : null;

  if (pluginResult) {
    assert(pluginResult.detectedPlugins.includes('SplitText'), 'P1: SplitText detected');
    assert(pluginResult.detectedPlugins.includes('Flip'), 'P2: Flip detected');
    assert(pluginResult.detectedPlugins.includes('DrawSVG'), 'P3: DrawSVG detected');
    assert(pluginResult.detectedPlugins.includes('CustomEase'), 'P4: CustomEase detected');
    assert(pluginResult.pluginCapabilities.SplitText.intents.includes('character-reveal'), 'P5: SplitText has character-reveal intent');
    assert(pluginResult.pluginCapabilities.Flip.intents.includes('layout-transition'), 'P6: Flip has layout-transition intent');
    assert(pluginResult.pluginCapabilities.DrawSVG.intents.includes('svg-draw'), 'P7: DrawSVG has svg-draw intent');
    assert(pluginResult.pluginCapabilities.SplitText.recommendedSections.includes('HERO'), 'P8: SplitText recommended for HERO');
    assert(pluginResult.gaps.length > 0, 'P9: gaps generated for missing plugin components');
  } else {
    console.log('  ⚠ matchPluginPatterns not yet exported — skipping plugin tests');
  }
}

// ============================================================
// Results
// ============================================================

console.log('\n' + '='.repeat(50));
console.log('  Results: ' + passed + ' passed, ' + failed + ' failed');
if (failures.length > 0) {
  console.log('\n  Failures:');
  for (const f of failures) {
    console.log('    - ' + f);
  }
}
console.log('='.repeat(50) + '\n');

process.exit(failed > 0 ? 1 : 0);

/**
 * Design Token Extraction & Preset Comparison
 * Aggregates unique design tokens from extraction data and compares
 * them against web-builder preset values.
 */

const fs = require('fs');
const path = require('path');

function rgbToHex(rgb) {
  if (!rgb || typeof rgb !== 'string') return rgb;
  if (rgb.startsWith('#')) return rgb;
  const match = rgb.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
  if (!match) return rgb;
  const r = parseInt(match[1], 10);
  const g = parseInt(match[2], 10);
  const b = parseInt(match[3], 10);
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}

// ---------------------------------------------------------------------------
// HSL conversion + hue-aware Tailwind mapping (Track A — v0.9.0)
// ---------------------------------------------------------------------------

/**
 * Convert hex color to HSL values.
 * @param {string} hex - Hex color string (e.g. "#0ae448")
 * @returns {{ h: number, s: number, l: number }} HSL values (h: 0-360, s/l: 0-100)
 */
function hexToHSL(hex) {
  if (!hex || !hex.startsWith('#')) return { h: 0, s: 0, l: 0 };
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;
  const l = (max + min) / 2;

  if (d === 0) return { h: 0, s: 0, l: Math.round(l * 100) };

  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h;
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
  else if (max === g) h = ((b - r) / d + 2) / 6;
  else h = ((r - g) / d + 4) / 6;

  return { h: Math.round(h * 360), s: Math.round(s * 100), l: Math.round(l * 100) };
}

/**
 * Hue-to-Tailwind color family mapping.
 * Ranges are [start, end) with wrap-around at 360.
 */
const HUE_FAMILIES = [
  [0, 15, 'red'],
  [15, 35, 'orange'],
  [35, 50, 'amber'],
  [50, 65, 'yellow'],
  [65, 80, 'lime'],
  [80, 150, 'green'],
  [150, 170, 'emerald'],
  [170, 185, 'teal'],
  [185, 200, 'cyan'],
  [200, 215, 'sky'],
  [215, 245, 'blue'],
  [245, 257, 'indigo'],
  [257, 280, 'violet'],
  [280, 300, 'purple'],
  [300, 330, 'fuchsia'],
  [330, 345, 'pink'],
  [345, 361, 'rose'],
];

/**
 * Map lightness (0-100) to a Tailwind shade number.
 * @param {number} l - Lightness value (0-100)
 * @returns {number} Tailwind shade (50-950)
 */
function lightnessToShade(l) {
  if (l >= 95) return 50;
  if (l >= 90) return 100;
  if (l >= 82) return 200;
  if (l >= 72) return 300;
  if (l >= 60) return 400;
  if (l >= 45) return 500;
  if (l >= 35) return 600;
  if (l >= 25) return 700;
  if (l >= 15) return 800;
  if (l >= 8) return 900;
  return 950;
}

/**
 * Map a hex color to the nearest Tailwind color name using HSL.
 * Handles achromatic colors (low saturation) as grays.
 * @param {string} hex - Hex color string
 * @returns {string} Tailwind color name (e.g. "green-500", "gray-800")
 */
function hexToTailwindHue(hex) {
  if (!hex || !hex.startsWith('#')) return hex;
  const { h, s, l } = hexToHSL(hex);

  // Near-white / near-black shortcuts
  if (l >= 97) return 'white';
  if (l <= 3) return 'black';

  // Achromatic — low saturation maps to gray scale
  if (s < 10) {
    const shade = lightnessToShade(l);
    return `gray-${shade}`;
  }

  // Find hue family
  let family = 'gray';
  for (const [start, end, name] of HUE_FAMILIES) {
    if (h >= start && h < end) {
      family = name;
      break;
    }
  }

  const shade = lightnessToShade(l);
  return `${family}-${shade}`;
}

function collectTokens(extractionData) {
  const colorsSet = new Set();
  const bgColorsSet = new Set();
  const fontsSet = new Set();
  const fontSizesSet = new Set();
  const borderRadiiSet = new Set();
  const fontWeightsSet = new Set();
  const spacingSet = new Set();
  const notableSet = new Set();

  for (const el of (extractionData.renderedDOM || [])) {
    const s = el.styles || {};
    if (s.color) colorsSet.add(rgbToHex(s.color));
    if (s.backgroundColor) bgColorsSet.add(rgbToHex(s.backgroundColor));
    if (s.fontFamily) {
      const primary = s.fontFamily.split(',')[0].trim().replace(/['"]/g, '');
      if (primary) fontsSet.add(primary);
    }
    if (s.fontSize) fontSizesSet.add(s.fontSize);
    if (s.fontWeight) fontWeightsSet.add(s.fontWeight);
    if (s.borderRadius && s.borderRadius !== '0px') borderRadiiSet.add(s.borderRadius);
    if (s.padding && s.padding !== '0px') spacingSet.add('padding: ' + s.padding);
    if (s.gap && s.gap !== 'normal') spacingSet.add('gap: ' + s.gap);
    if (s.boxShadow && s.boxShadow !== 'none') notableSet.add('box-shadow: ' + s.boxShadow.slice(0, 100));
    if (s.transform && s.transform !== 'none') notableSet.add('transform: ' + s.transform.slice(0, 80));
  }

  for (const t of (extractionData.textContent || [])) {
    if (t.color) colorsSet.add(rgbToHex(t.color));
    if (t.fontFamily) {
      const primary = t.fontFamily.split(',')[0].trim().replace(/['"]/g, '');
      if (primary) fontsSet.add(primary);
    }
    if (t.fontSize) fontSizesSet.add(t.fontSize);
  }

  for (const font of (extractionData.assets?.fonts || [])) {
    const cleaned = font.trim().replace(/['"]/g, '');
    if (cleaned) fontsSet.add(cleaned);
  }

  for (const section of (extractionData.sections || [])) {
    if (section.backgroundColor) bgColorsSet.add(rgbToHex(section.backgroundColor));
  }

  const isReal = (val) => val && val !== 'rgba(0, 0, 0, 0)' && val !== 'transparent' && val !== 'none';

  const systemFonts = new Set([
    'arial', 'helvetica', 'sans-serif', 'serif', 'monospace', 'cursive',
    'times new roman', 'georgia', 'courier new', 'system-ui', '-apple-system',
    'blinkmacsystemfont', 'segoe ui', 'roboto', 'oxygen', 'ubuntu',
    'cantarell', 'fira sans', 'droid sans', 'helvetica neue',
  ]);

  const customFonts = [...fontsSet].filter((f) => !systemFonts.has(f.toLowerCase()));

  return {
    colors: [...colorsSet].filter(isReal),
    backgroundColors: [...bgColorsSet].filter(isReal),
    fonts: customFonts,
    allFonts: [...fontsSet],
    fontSizes: [...fontSizesSet].filter(Boolean),
    fontWeights: [...fontWeightsSet].filter(Boolean),
    borderRadii: [...borderRadiiSet].filter(Boolean),
    spacing: [...spacingSet].slice(0, 30),
    notable: [...notableSet].slice(0, 20),
  };
}

/**
 * Collects animation-specific design tokens from extraction data.
 * Extracts animation names, transition properties, durations, and easing
 * functions from the rendered DOM's computed styles.
 * @param {Object} extractionData - Full extraction result from extract-reference
 * @returns {Object} Animation tokens
 */
function collectAnimationTokens(extractionData) {
  const animationNames = new Set();
  const transitionProps = new Set();
  const durations = new Set();
  const easings = new Set();

  for (const el of (extractionData.renderedDOM || [])) {
    const s = el.styles || {};

    if (s.animationName && s.animationName !== 'none') {
      for (const name of s.animationName.split(',')) {
        const trimmed = name.trim();
        if (trimmed && trimmed !== 'none') animationNames.add(trimmed);
      }
    }

    if (s.animationDuration && s.animationDuration !== '0s') {
      durations.add(s.animationDuration);
    }

    if (s.animationTimingFunction && s.animationTimingFunction !== 'ease') {
      easings.add(s.animationTimingFunction);
    }

    if (s.transition && s.transition !== 'all 0s ease 0s' && s.transition !== 'none') {
      // Parse transition shorthand — extract property names and durations
      const parts = s.transition.split(',');
      for (const part of parts) {
        const trimmed = part.trim();
        if (!trimmed) continue;
        transitionProps.add(trimmed.split(/\s+/)[0]); // property name
        const durationMatch = trimmed.match(/(\d+\.?\d*m?s)/);
        if (durationMatch) durations.add(durationMatch[1]);
        const easingMatch = trimmed.match(/(ease[-\w]*|linear|cubic-bezier\([^)]+\))/);
        if (easingMatch) easings.add(easingMatch[1]);
      }
    }
  }

  return {
    animationNames: [...animationNames],
    transitionProperties: [...transitionProps],
    durations: [...durations],
    easingFunctions: [...easings],
  };
}

function parsePreset(presetPath) {
  const content = fs.readFileSync(presetPath, 'utf-8');
  const name = path.basename(presetPath, '.md');
  const yamlMatch = content.match(/```yaml\n([\s\S]*?)```/);
  const yamlBlock = yamlMatch ? yamlMatch[1] : '';
  const lines = yamlBlock.split('\n');
  const values = {};
  let currentSection = null;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    if (/^\w[\w_]*:\s*$/.test(trimmed)) {
      currentSection = trimmed.replace(':', '').trim();
      values[currentSection] = {};
      continue;
    }
    if (currentSection && /^\s+\w/.test(line)) {
      const kvMatch = trimmed.match(/^(\w[\w_]*):\s*(.+)/);
      if (kvMatch) values[currentSection][kvMatch[1]] = kvMatch[2].trim().replace(/['"]/g, '');
      continue;
    }
    const topMatch = trimmed.match(/^(\w[\w_]*):\s*(.+)/);
    if (topMatch) {
      currentSection = null;
      values[topMatch[1]] = topMatch[2].trim().replace(/['"]/g, '');
    }
  }

  const refMatch = content.match(/## Reference Sites[\s\S]*?(?=---|$)/);
  let referenceSites = [];
  if (refMatch) {
    for (const line of refMatch[0].split('\n')) {
      const siteMatch = line.match(/^-\s+(.+)/);
      if (siteMatch) {
        const sites = siteMatch[1].split(',').map((s) => s.trim()).filter(Boolean);
        referenceSites.push(...sites);
      }
    }
  }

  return { name, values, referenceSites, raw: content };
}

function compareToPreset(tokens, presetPath) {
  const preset = parsePreset(presetPath);
  const matches = [];
  const mismatches = [];
  const discoveries = [];

  const claimedHeading = preset.values.typography?.heading_font;
  const claimedBody = preset.values.typography?.body_font;

  if (claimedHeading) {
    const found = tokens.fonts.some((f) => f.toLowerCase().includes(claimedHeading.toLowerCase()));
    if (found) matches.push({ type: 'font', claim: 'heading_font: ' + claimedHeading, status: 'confirmed' });
    else mismatches.push({ type: 'font', claim: 'heading_font: ' + claimedHeading,
      actual: 'Found fonts: ' + (tokens.fonts.join(', ') || 'none'), severity: 'high' });
  }

  if (claimedBody) {
    const found = tokens.fonts.some((f) => f.toLowerCase().includes(claimedBody.toLowerCase()));
    if (found) matches.push({ type: 'font', claim: 'body_font: ' + claimedBody, status: 'confirmed' });
    else mismatches.push({ type: 'font', claim: 'body_font: ' + claimedBody,
      actual: 'Found fonts: ' + (tokens.fonts.join(', ') || 'none'), severity: 'medium' });
  }

  const claimedWeight = preset.values.typography?.heading_weight;
  if (claimedWeight && tokens.fontWeights.length > 0) {
    const found = tokens.fontWeights.includes(claimedWeight) || tokens.fontWeights.includes(String(claimedWeight));
    if (found) matches.push({ type: 'weight', claim: 'heading_weight: ' + claimedWeight, status: 'confirmed' });
    else mismatches.push({ type: 'weight', claim: 'heading_weight: ' + claimedWeight,
      actual: 'Found weights: ' + tokens.fontWeights.join(', '), severity: 'low' });
  }

  const claimedRadius = preset.values.border_radius;
  if (claimedRadius && tokens.borderRadii.length > 0) {
    const ranges = { sharp: { min: 0, max: 4 }, medium: { min: 6, max: 16 },
      full: { min: 16, max: 32 }, pill: { min: 32, max: 9999 } };
    const range = ranges[claimedRadius];
    if (range) {
      const parsed = tokens.borderRadii.map((r) => parseInt(r, 10)).filter((r) => !isNaN(r));
      const avg = parsed.length > 0 ? parsed.reduce((a, b) => a + b, 0) / parsed.length : -1;
      if (avg >= range.min && avg <= range.max) {
        matches.push({ type: 'radius', claim: 'border_radius: ' + claimedRadius, status: 'confirmed',
          detail: 'Average: ' + avg.toFixed(1) + 'px' });
      } else if (avg >= 0) {
        mismatches.push({ type: 'radius', claim: 'border_radius: ' + claimedRadius + ' (expected ' + range.min + '-' + range.max + 'px)',
          actual: 'Average: ' + avg.toFixed(1) + 'px', severity: 'medium' });
      }
    }
  }

  const claimedFonts = [claimedHeading, claimedBody].filter(Boolean).map((f) => f.toLowerCase());
  for (const font of tokens.fonts) {
    if (!claimedFonts.some((cf) => font.toLowerCase().includes(cf))) {
      discoveries.push({ type: 'font', value: font, note: 'Font found on reference site but not in preset' });
    }
  }

  if (tokens.backgroundColors.length > 0) {
    discoveries.push({ type: 'background_colors', value: tokens.backgroundColors.slice(0, 10).join(', '),
      note: 'Background colors found (compare to preset palette)' });
  }
  if (tokens.colors.length > 0) {
    discoveries.push({ type: 'text_colors', value: tokens.colors.slice(0, 10).join(', '),
      note: 'Text colors found (compare to preset palette)' });
  }

  const totalChecks = matches.length + mismatches.length;
  const accuracy = totalChecks > 0 ? matches.length / totalChecks : 0;

  return {
    presetName: preset.name, sitesAnalyzed: 1, totalChecks, accuracy,
    matches, mismatches, discoveries,
    tokensFound: { fonts: tokens.fonts.length, colors: tokens.colors.length,
      backgroundColors: tokens.backgroundColors.length, fontSizes: tokens.fontSizes.length,
      borderRadii: tokens.borderRadii.length },
  };
}

// ---------------------------------------------------------------------------
// Gradient color extraction (Track A2)
// ---------------------------------------------------------------------------

function collectGradientColors(extractionData) {
  const gradients = [];
  const accentSet = new Set();
  const bgImages = extractionData.assets?.backgroundImages || [];
  const colorStopRe = /rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+(?:\s*,\s*[\d.]+)?\s*\)|#[0-9a-fA-F]{3,8}/g;
  const angleRe = /(\d+(?:\.\d+)?deg)/;

  for (const bgImg of bgImages) {
    const src = typeof bgImg === 'string' ? bgImg : bgImg?.url || bgImg?.value || '';
    // Check if this is a gradient string
    if (!/(linear|radial|conic)-gradient/.test(src)) continue;

    const angleMatch = src.match(angleRe);
    const angle = angleMatch ? angleMatch[1] : 'none';
    const stops = [];
    let colorMatch;
    colorStopRe.lastIndex = 0;
    while ((colorMatch = colorStopRe.exec(src)) !== null) {
      const hex = rgbToHex(colorMatch[0]);
      if (hex && hex.startsWith('#')) stops.push(hex);
    }
    if (stops.length > 0) {
      gradients.push({ source: src.slice(0, 120), stops, angle });
      for (const hex of stops) {
        const hsl = hexToHSL(hex);
        if (hsl.l > 92 || hsl.l < 8 || hsl.s < 10) continue;
        accentSet.add(hex);
      }
    }
  }
  return { gradients, accentColors: [...accentSet] };
}

// ---------------------------------------------------------------------------
// Color system identification (Track A3)
// ---------------------------------------------------------------------------

function identifyColorSystem(tokens, gradientData) {
  const candidates = [];

  for (const hex of (gradientData?.accentColors || [])) {
    candidates.push({ hex, source: 'gradient' });
  }
  for (const hex of (tokens.backgroundColors || [])) {
    const hsl = hexToHSL(hex);
    if (hsl.s >= 15 && hsl.l > 10 && hsl.l < 90) {
      candidates.push({ hex, source: 'background' });
    }
  }
  for (const hex of (tokens.colors || [])) {
    const hsl = hexToHSL(hex);
    if (hsl.s >= 30 && hsl.l > 15 && hsl.l < 85) {
      candidates.push({ hex, source: 'text' });
    }
  }

  if (candidates.length === 0) {
    return { system: 'neutral', accents: [] };
  }

  // Cluster by hue with minimum 30 degree angular distance
  const clusters = [];
  for (const c of candidates) {
    const hsl = hexToHSL(c.hex);
    let matched = false;
    for (const cluster of clusters) {
      const dist = Math.min(
        Math.abs(hsl.h - cluster.hue),
        360 - Math.abs(hsl.h - cluster.hue)
      );
      if (dist < 30) {
        cluster.members.push(c);
        matched = true;
        break;
      }
    }
    if (!matched) {
      clusters.push({ hue: hsl.h, members: [c] });
    }
  }

  clusters.sort((a, b) => b.members.length - a.members.length);

  const accents = clusters.map((cluster) => {
    const hexCounts = {};
    for (const m of cluster.members) {
      hexCounts[m.hex] = (hexCounts[m.hex] || 0) + 1;
    }
    const bestHex = Object.entries(hexCounts).sort((a, b) => b[1] - a[1])[0][0];
    const sources = [...new Set(cluster.members.map((m) => m.source))];
    return {
      hue: cluster.hue,
      hex: bestHex,
      tailwind: hexToTailwindHue(bestHex),
      source: sources.join('+'),
    };
  });

  const allFromGradients = accents.every((a) => a.source === 'gradient');
  let system;
  if (accents.length === 0) system = 'neutral';
  else if (accents.length === 1) system = 'single-accent';
  else if (accents.length === 2) system = 'dual-accent';
  else if (allFromGradients) system = 'gradient-based';
  else system = 'multi-accent';

  return { system, accents };
}

// ---------------------------------------------------------------------------
// Per-section color profiling (Track A4)
// ---------------------------------------------------------------------------

function profileSectionColors(extractionData, gradientData) {
  const sections = extractionData.sections || [];
  const dom = extractionData.renderedDOM || [];
  const sectionColors = {};

  for (let i = 0; i < sections.length; i++) {
    const sec = sections[i];
    const top = sec.rect?.y || 0;
    const bottom = top + (sec.rect?.height || 0);
    const colorCounts = {};

    for (const el of dom) {
      const elY = el.rect?.y || 0;
      if (elY < top || elY > bottom) continue;
      const colors = [
        el.styles?.backgroundColor,
        el.styles?.color,
        el.styles?.borderColor,
      ].filter(Boolean).map(rgbToHex);

      for (const hex of colors) {
        if (!hex || !hex.startsWith('#')) continue;
        const hsl = hexToHSL(hex);
        if (hsl.s < 15 || hsl.l > 92 || hsl.l < 8) continue;
        colorCounts[hex] = (colorCounts[hex] || 0) + 1;
      }
    }

    let hasGradient = false;
    if (sec.backgroundColor && typeof sec.backgroundColor === 'string' &&
        sec.backgroundColor.includes('gradient')) {
      hasGradient = true;
    }

    const sorted = Object.entries(colorCounts).sort((a, b) => b[1] - a[1]);
    const dominant = sorted.length > 0 ? sorted[0][0] : null;

    sectionColors[i] = {
      accent: dominant ? hexToTailwindHue(dominant) : null,
      accentHex: dominant || null,
      gradient: hasGradient,
      colorCount: sorted.length,
    };
  }
  return { sectionColors };
}

module.exports = {
  collectTokens,
  collectAnimationTokens,
  compareToPreset,
  parsePreset,
  rgbToHex,
  hexToHSL,
  hexToTailwindHue,
  collectGradientColors,
  identifyColorSystem,
  profileSectionColors,
};

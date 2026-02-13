/**
 * Build Site Spec — Deterministic site-spec.json builder
 *
 * Reads extraction artifacts (extraction-data, mapped-sections, animation-analysis,
 * component-registry) and produces a single structured site-spec.json. No Claude calls.
 *
 * Usage: node scripts/quality/build-site-spec.js <extraction-dir> <project-name>
 * Example: node scripts/quality/build-site-spec.js output/extractions/sofi-health-be91e37d sofi-health
 *
 * @module build-site-spec
 */

'use strict';

const fs = require('fs');
const path = require('path');

const designTokens = (function () {
  try {
    return require('./lib/design-tokens.js');
  } catch (_) {
    return null;
  }
})();

const {
  applyConfidenceGates,
  getConfidenceGuidance,
  getTier,
  buildReanalysisPrompt,
} = require('./lib/confidence-gate');

// ---------------------------------------------------------------------------
// Color / font helpers (inline fallbacks when design-tokens not available)
// ---------------------------------------------------------------------------

function rgbToHex(rgb) {
  if (!rgb || typeof rgb !== 'string') return '#000000';
  if (rgb.startsWith('#')) return rgb;
  const match = rgb.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
  if (!match) return '#000000';
  const [, r, g, b] = match;
  return '#' + [r, g, b].map((x) => parseInt(x, 10).toString(16).padStart(2, '0')).join('');
}

function hexToRgb(hex) {
  if (!hex || !hex.startsWith('#')) return { r: 0, g: 0, b: 0 };
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return { r, g, b };
}

function hexLuminance(hex) {
  const rgb = hexToRgb(hex);
  return (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
}

const FONT_TO_GOOGLE = {
  HelveticaNowDisplayMedium: 'Inter',
  HelveticaNeue: 'Inter',
  Helvetica: 'Inter',
  Arial: 'Inter',
  Aeonik: 'DM Sans',
  Futura: 'Montserrat',
  Avenir: 'Nunito Sans',
  'Proxima Nova': 'Montserrat',
  Roboto: 'Roboto',
  'system-ui': 'Inter',
  'SF Pro Display': 'Inter',
  'SF Pro Text': 'Inter',
  'Segoe UI': 'Inter',
};

function mapToGoogleFont(fontName) {
  if (!fontName || typeof fontName !== 'string') return 'Inter';
  const name = fontName.trim();
  for (const [key, value] of Object.entries(FONT_TO_GOOGLE)) {
    if (name.toLowerCase().includes(key.toLowerCase())) return value;
  }
  return 'Inter';
}

function determineColorTemp(bgHex, textHex) {
  const bgLuminance = hexLuminance(bgHex || '#ffffff');
  if (bgLuminance < 0.3) return 'dark-neutral';
  if (bgLuminance > 0.7) return 'light-neutral';
  return 'balanced';
}

// ---------------------------------------------------------------------------
// Dominant radius from DOM
// ---------------------------------------------------------------------------

function findDominantRadius(domElements) {
  const radii = {};
  for (const el of domElements || []) {
    const r = el.styles?.borderRadius;
    if (r && r !== '0px' && r !== '0') {
      radii[r] = (radii[r] || 0) + 1;
    }
  }
  const sorted = Object.entries(radii).sort((a, b) => b[1] - a[1]);
  const dominant = sorted[0]?.[0];
  if (!dominant) return { button: 'rounded-lg', card: 'rounded-xl' };
  // Normalize common values to preset-friendly names
  if (/^\d+px$/.test(dominant)) {
    const n = parseInt(dominant, 10);
    if (n >= 24) return { button: 'rounded-full', card: 'rounded-3xl' };
    if (n >= 12) return { button: 'rounded-xl', card: 'rounded-2xl' };
  }
  return { button: 'rounded-lg', card: 'rounded-xl' };
}

// ---------------------------------------------------------------------------
// Density heuristic from spacing/padding
// ---------------------------------------------------------------------------

function determineDensity(domElements) {
  const gaps = [];
  const paddings = [];
  for (const el of domElements || []) {
    const s = el.styles || {};
    if (s.gap && s.gap !== 'normal') gaps.push(s.gap);
    if (s.padding && s.padding !== '0px') paddings.push(s.padding);
  }
  const all = [...gaps, ...paddings];
  if (all.length === 0) return 'balanced';
  const hasLarge = all.some((v) => /^\d*\.?\d*(rem|em)$/.test(v) && parseFloat(v) >= 2);
  const hasTight = all.some((v) => /^\d+px$/.test(v) && parseInt(v, 10) <= 16);
  if (hasLarge && !hasTight) return 'airy';
  if (hasTight && !hasLarge) return 'dense';
  return 'balanced';
}

// ---------------------------------------------------------------------------
// Animation tokens from extraction + optional animation-analysis
// ---------------------------------------------------------------------------

function buildAnimationTokens(extractionData, animationAnalysis) {
  const names = new Set();
  const durations = new Set();
  const easings = new Set();
  const dom = extractionData?.renderedDOM || [];
  for (const el of dom) {
    const s = el.styles || {};
    if (s.animationName && s.animationName !== 'none') names.add(s.animationName);
    if (s.animationDuration && s.animationDuration !== '0s') durations.add(s.animationDuration);
    if (s.transition && s.transition !== 'none') {
      const dur = s.transition.match(/(\d+\.?\d*m?s)/);
      if (dur) durations.add(dur[1]);
    }
  }
  if (animationAnalysis?.libraries?.length) {
    return {
      engine: animationAnalysis.engine || 'unknown',
      intensity: animationAnalysis.intensity?.level || 'moderate',
      libraries: animationAnalysis.libraries.map((l) => l.name),
      keyframes: [...names],
      durations: [...durations].slice(0, 10),
      easings: [...easings].slice(0, 5),
    };
  }
  return {
    engine: 'unknown',
    intensity: 'moderate',
    libraries: [],
    keyframes: [...names],
    durations: [...durations].slice(0, 10),
    easings: [...easings].slice(0, 5),
  };
}

// ---------------------------------------------------------------------------
// Style tokens from extraction data
// ---------------------------------------------------------------------------

function buildStyleTokens(extractionData) {
  const domElements = extractionData.renderedDOM || [];
  const useDesignTokens = designTokens && designTokens.rgbToHex;

  // Background colors
  const bgColors = {};
  for (const el of domElements) {
    const bg = el.styles?.backgroundColor;
    if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
      const hex = useDesignTokens ? designTokens.rgbToHex(bg) : rgbToHex(bg);
      if (hex && hex.startsWith('#')) bgColors[hex] = (bgColors[hex] || 0) + 1;
    }
  }
  const sortedBgs = Object.entries(bgColors).sort((a, b) => b[1] - a[1]);
  const bgPrimary = sortedBgs[0]?.[0] || '#ffffff';
  const bgSecondary = sortedBgs[1]?.[0] || bgPrimary;

  // Text colors
  const textColors = {};
  for (const el of domElements) {
    const c = el.styles?.color;
    if (c) {
      const hex = useDesignTokens ? designTokens.rgbToHex(c) : rgbToHex(c);
      if (hex) textColors[hex] = (textColors[hex] || 0) + 1;
    }
  }
  for (const t of extractionData.textContent || []) {
    if (t.color) {
      const hex = t.color.startsWith('#') ? t.color : (useDesignTokens ? designTokens.rgbToHex(t.color) : rgbToHex(t.color));
      if (hex) textColors[hex] = (textColors[hex] || 0) + 1;
    }
  }
  const sortedTexts = Object.entries(textColors).sort((a, b) => b[1] - a[1]);
  const textPrimary = sortedTexts[0]?.[0] || '#000000';
  const textMuted = sortedTexts[1]?.[0] || textPrimary;
  const accentCandidate = sortedTexts[2]?.[0] || textPrimary;

  // Fonts
  const fonts = extractionData.assets?.fonts || [];
  const fontFamilies = {};
  for (const el of domElements) {
    const ff = el.styles?.fontFamily;
    if (ff) {
      const name = ff.split(',')[0].trim().replace(/['"]/g, '');
      if (name) fontFamilies[name] = (fontFamilies[name] || 0) + 1;
    }
  }
  for (const t of extractionData.textContent || []) {
    if (t.fontFamily) {
      const name = t.fontFamily.split(',')[0].trim().replace(/['"]/g, '');
      if (name) fontFamilies[name] = (fontFamilies[name] || 0) + 1;
    }
  }
  const sortedFonts = Object.entries(fontFamilies).sort((a, b) => b[1] - a[1]);
  const primaryFont = sortedFonts[0]?.[0] || (fonts[0] && fonts[0].trim().replace(/['"]/g, '')) || 'system-ui';

  return {
    palette: {
      bg_primary: bgPrimary,
      bg_secondary: bgSecondary,
      text_primary: textPrimary,
      text_muted: textMuted,
      accent: accentCandidate,
      border: sortedBgs[2]?.[0] || bgSecondary,
    },
    fonts: {
      heading: { extracted: primaryFont, google_fallback: mapToGoogleFont(primaryFont), weight: 600 },
      body: { extracted: primaryFont, google_fallback: mapToGoogleFont(primaryFont), weight: 400 },
    },
    spacing: { section_padding: '6rem', internal_gap: '3rem', scale: 'generous' },
    border_radius: findDominantRadius(domElements),
    animation: buildAnimationTokens(extractionData, extractionData.animations),
    density: determineDensity(domElements),
    color_temperature: determineColorTemp(bgPrimary, textPrimary),
  };
}

// Fix animation tokens to receive full extractionData for DOM; animation analysis is separate.
function buildStyleTokensAnimationPart(extractionData, animationAnalysis) {
  return buildAnimationTokens(extractionData, animationAnalysis);
}

// ---------------------------------------------------------------------------
// Image role guess by URL/alt and archetype
// ---------------------------------------------------------------------------

const IMAGE_ROLE_SIGNALS = {
  hero: ['hero', 'banner', 'splash', 'main', 'header'],
  product: ['product', 'item', 'shop', 'catalog'],
  about: ['about', 'story', 'team', 'process'],
  team: ['team', 'staff', 'portrait', 'founder'],
  logo: ['logo', 'brand', 'partner'],
  location: ['location', 'store', 'map', 'cafe'],
  testimonial: ['testimonial', 'review', 'customer', 'avatar'],
};

function guessImageRole(img, archetype) {
  const alt = (img.alt || '').toLowerCase();
  const src = (img.src || '').toLowerCase();
  for (const [role, keywords] of Object.entries(IMAGE_ROLE_SIGNALS)) {
    if (keywords.some((kw) => alt.includes(kw) || src.includes(kw))) return role;
  }
  if (archetype === 'NAV' || archetype === 'FOOTER') return 'logo';
  if (archetype === 'HERO') return 'hero';
  if (archetype === 'PRODUCT-SHOWCASE' || archetype === 'GALLERY') return 'product';
  return 'general';
}

// ---------------------------------------------------------------------------
// Match components for archetype from registry (archetypes array + affinity)
// ---------------------------------------------------------------------------

function findComponentsForArchetype(archetype, componentRegistry) {
  const comps = componentRegistry.components || {};
  const byArchetype = [];
  const byAffinity = [];
  const fallback = [];

  for (const [id, c] of Object.entries(comps)) {
    if (!c.import_statement || !c.source_file) continue;
    const archList = Array.isArray(c.archetypes) ? c.archetypes : [];
    const aff = c.affinity && typeof c.affinity === 'object' ? c.affinity : {};
    if (archList.includes(archetype)) byArchetype.push({ id, ...c });
    else if (aff[archetype] != null) byAffinity.push({ id, ...c, score: aff[archetype] });
    else if (c.category === 'entrance' && (archetype !== 'NAV' && archetype !== 'FOOTER')) fallback.push({ id, ...c });
  }

  byAffinity.sort((a, b) => (b.score || 0) - (a.score || 0));
  const matched = [...byArchetype];
  const affinityLimit = 2;
  for (let i = 0; i < Math.min(affinityLimit, byAffinity.length); i++) matched.push(byAffinity[i]);
  if (matched.length === 0 && fallback.length > 0) {
    matched.push(fallback[0]);
    if (fallback.length > 1) matched.push(fallback[1]);
  }
  return matched.map((c) => ({
    id: c.id,
    import_statement: c.import_statement,
    source_file: c.source_file,
    engine: c.engine,
    category: c.category,
  }));
}

// ---------------------------------------------------------------------------
// Section specs from mapped-sections + extraction
// ---------------------------------------------------------------------------

function buildSections(extractionData, mappedSections, componentRegistry, animationAnalysis) {
  const sections = [];
  const images = extractionData.assets?.images || [];
  const textContent = extractionData.textContent || [];

  for (const mapped of mappedSections) {
    // v2.0.2: Prefer embedded per-section content from DOM-scoped extraction.
    // This is the primary content source — it was extracted via DOM containment
    // (querySelectorAll inside the section element), not rect overlap.
    const embeddedSection = (extractionData.sections || []).find(s => s.index === mapped.index);
    const embeddedContent = embeddedSection?.content;
    const embeddedImages = embeddedSection?.images || [];

    // Images: prefer embedded (DOM-scoped), supplement with sectionIndex-matched
    let sectionImages;
    if (embeddedImages.length > 0) {
      sectionImages = embeddedImages.map((img) => ({
        src: img.src,
        alt: img.alt || '',
        width: img.width,
        height: img.height,
        role: guessImageRole(img, mapped.archetype),
      }));
    } else {
      // Fallback: sectionIndex-based matching (for legacy extraction data)
      sectionImages = images
        .filter((img) => img.sectionIndex === mapped.index)
        .map((img) => ({
          src: img.src,
          alt: img.alt || '',
          width: img.width,
          height: img.height,
          role: guessImageRole(img, mapped.archetype),
        }));
    }

    // Text content: prefer embedded, fallback to sectionIndex
    let headings, bodyText, ctas;
    if (embeddedContent && (embeddedContent.headings?.length > 0 || embeddedContent.body_text?.length > 0)) {
      headings = embeddedContent.headings || [];
      bodyText = embeddedContent.body_text || [];
      ctas = (embeddedContent.ctas || []).map(c => typeof c === 'string' ? c : c.text);
    } else {
      // Fallback: sectionIndex-based text filtering
      const sectionText = textContent.filter((t) => {
        if (t.sectionIndex != null) return t.sectionIndex === mapped.index;
        const y = t.rect?.y ?? 0;
        const sec = extractionData.sections?.[mapped.index];
        if (!sec?.rect) return false;
        const top = sec.rect.y ?? 0;
        const bottom = top + (sec.rect.height ?? 0);
        return y >= top && y <= bottom;
      });
      headings = sectionText.filter((t) => t.isHeading).map((t) => t.text);
      bodyText = sectionText.filter((t) => !t.isHeading && !t.isInteractive).map((t) => t.text);
      ctas = sectionText.filter((t) => t.isInteractive).map((t) => t.text);
    }

    const matchedComponents = findComponentsForArchetype(mapped.archetype, componentRegistry);

    const detectedAnimations = [];
    if (animationAnalysis?.gsapCalls) {
      for (const call of animationAnalysis.gsapCalls) {
        if (call.section === mapped.index) detectedAnimations.push({ type: call.method, target: call.target });
      }
    }

    let recommended = 'entrance-fade';
    if (mapped.archetype === 'NAV') recommended = 'css-only';
    else if (mapped.archetype === 'HERO' && animationAnalysis?.engine === 'gsap') recommended = 'entrance-fade-up-stagger';
    else if (detectedAnimations.length > 0) recommended = 'entrance-fade';

    sections.push({
      index: mapped.index,
      archetype: mapped.archetype,
      variant: mapped.variant,
      confidence: mapped.confidence,
      confidence_tier: mapped.confidence_tier,
      confidence_note: mapped.confidence_note,
      method: mapped.method,
      source_rect: mapped.rect,
      content: {
        headings: headings.slice(0, 5),
        body_text: bodyText.slice(0, 10),
        ctas: ctas.slice(0, 5),
      },
      images: sectionImages,
      icons: { library: extractionData.assets?.iconLibrary?.library || null },
      animations: {
        detected: detectedAnimations,
        recommended,
      },
      components: {
        matched: matchedComponents.map((c) => ({
          id: c.id,
          import_statement: c.import_statement,
          source_file: c.source_file,
        })),
        fallbacks: [],
      },
    });
  }
  return sections;
}

// ---------------------------------------------------------------------------
// Component map: all components referenced in sections + registry defaults
// ---------------------------------------------------------------------------

function buildComponentMap(componentRegistry, sections) {
  const comps = componentRegistry.components || {};
  const seen = new Set();
  for (const sec of sections || []) {
    for (const m of sec.components?.matched || []) {
      if (m.id) seen.add(m.id);
    }
  }
  const map = {};
  for (const id of seen) {
    const c = comps[id];
    if (c && c.import_statement) {
      map[id] = {
        id,
        import_statement: c.import_statement,
        source_file: c.source_file,
        engine: c.engine,
        category: c.category,
      };
    }
  }
  return map;
}

// ---------------------------------------------------------------------------
// Global metadata
// ---------------------------------------------------------------------------

function inferPhotographyDirection(extractionData) {
  const images = extractionData.assets?.images || [];
  const alts = images.map((i) => (i.alt || '').toLowerCase()).join(' ');
  if (/product|item|shop|catalog/.test(alts)) return 'product-focused';
  if (/team|portrait|people|staff/.test(alts)) return 'people-focused';
  if (/location|store|place|interior/.test(alts)) return 'place-focused';
  if (images.length > 5) return 'rich-imagery';
  return 'neutral';
}

// ---------------------------------------------------------------------------
// Wire style.animation from animation-analysis when present
// ---------------------------------------------------------------------------

function applyAnimationAnalysisToStyle(styleTokens, animationAnalysis) {
  if (!animationAnalysis) return styleTokens;
  const anim = {
    ...styleTokens.animation,
    engine: animationAnalysis.engine || styleTokens.animation.engine,
    intensity: animationAnalysis.intensity?.level || styleTokens.animation.intensity,
    libraries: (animationAnalysis.libraries || []).map((l) => (typeof l === 'string' ? l : l.name)),
  };
  return { ...styleTokens, animation: anim };
}

// ---------------------------------------------------------------------------
// Main builder (programmatic)
// ---------------------------------------------------------------------------

function buildSiteSpec(options) {
  const {
    extractionData,
    mappedSections,
    animationAnalysis = null,
    componentRegistry = { components: {} },
    projectName,
  } = options;

  const { sections: gatedSections, stats, needsReanalysis } = applyConfidenceGates(mappedSections, {
    minConfidence: 0.5,
    verbose: true,
  });

  let style = buildStyleTokens(extractionData);
  style = applyAnimationAnalysisToStyle(style, animationAnalysis);

  const sections = buildSections(extractionData, gatedSections, componentRegistry, animationAnalysis);

  for (const section of sections) {
    const tier = section.confidence_tier || getTier(section.confidence);
    section.generation_guidance = getConfidenceGuidance(tier, section);
  }

  const component_map = buildComponentMap(componentRegistry, sections);

  const siteSpec = {
    version: '2.0.0',
    project: projectName,
    source_url: extractionData.url || '',
    extracted_at: extractionData.timestamp || new Date().toISOString(),
    style,
    sections,
    component_map,
    confidence_stats: stats,
    reanalysis: {
      needed: needsReanalysis.length > 0,
      sections: needsReanalysis,
      prompt: needsReanalysis.length > 0 ? buildReanalysisPrompt(needsReanalysis) : null,
    },
    global: {
      industry: 'auto-detected',
      tone: 'professional',
      photography_direction: inferPhotographyDirection(extractionData),
      icon_strategy: extractionData.assets?.iconLibrary?.library || 'lucide-react',
      detected_plugins: (animationAnalysis && animationAnalysis.libraries) ? animationAnalysis.libraries.map((l) => (typeof l === 'string' ? l : l.name)) : [],
      detected_ui_patterns: [],
    },
  };
  return siteSpec;
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function loadJson(filePath, defaultValue) {
  try {
    if (fs.existsSync(filePath)) {
      return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    }
  } catch (_) {}
  return defaultValue;
}

function runCLI() {
  const extractionDir = process.argv[2];
  const projectName = process.argv[3];

  if (!extractionDir || !projectName) {
    console.error('Usage: node build-site-spec.js <extraction-dir> <project-name>');
    console.error('Example: node build-site-spec.js output/extractions/sofi-health-be91e37d sofi-health');
    process.exit(1);
  }

  const extractionPath = path.join(extractionDir, 'extraction-data.json');
  const extractionData = loadJson(extractionPath, null);
  if (!extractionData) {
    console.error(`[build-site-spec] Missing or invalid extraction-data.json in ${extractionDir}`);
    process.exit(1);
  }

  const mappedPath = path.join(extractionDir, 'mapped-sections.json');
  const mappedSections = loadJson(mappedPath, null);
  if (!mappedSections || !Array.isArray(mappedSections)) {
    console.error(`[build-site-spec] Missing or invalid mapped-sections.json in ${extractionDir}`);
    process.exit(1);
  }

  const animationPath = path.join(extractionDir, 'animation-analysis.json');
  const animationAnalysis = loadJson(animationPath, null);

  const registryPath = path.resolve(__dirname, '..', '..', 'skills', 'animation-components', 'component-registry.json');
  const componentRegistry = loadJson(registryPath, { components: {} });

  const siteSpec = buildSiteSpec({
    extractionData,
    mappedSections,
    animationAnalysis,
    componentRegistry,
    projectName,
  });

  const outputDir = path.join('output', projectName);
  fs.mkdirSync(outputDir, { recursive: true });
  const outputPath = path.join(outputDir, 'site-spec.json');
  fs.writeFileSync(outputPath, JSON.stringify(siteSpec, null, 2), 'utf8');
  console.log(`[build-site-spec] Written to ${outputPath} (${siteSpec.sections.length} sections)`);
}

if (require.main === module) {
  runCLI();
} else {
  module.exports = {
    buildSiteSpec,
    buildStyleTokens,
    buildSections,
    buildComponentMap,
    findComponentsForArchetype,
    rgbToHex,
    mapToGoogleFont,
    determineColorTemp,
    inferPhotographyDirection,
  };
}

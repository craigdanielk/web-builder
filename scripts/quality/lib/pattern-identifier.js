/**
 * Pattern Identifier — v0.9.0 Track C
 *
 * Lean module that:
 *   C1: Matches site animation data to the v0.8.0 animation registry (1022 components)
 *   C2: Detects UI component patterns from DOM structure
 *   C3: Aggregates gaps from all sources into a single structured report
 *
 * Does NOT own color or archetype logic — those live in design-tokens.js and
 * archetype-mapper.js respectively. This module only handles animation/UI
 * pattern matching and gap aggregation.
 *
 * Usage:
 *   node pattern-identifier.js <extraction-dir> <project-name>
 *   Outputs JSON to stdout (for subprocess consumption by orchestrate.py)
 */

'use strict';

const fs = require('fs');
const path = require('path');

const {
  collectTokens,
  collectGradientColors,
  identifyColorSystem,
  profileSectionColors,
  hexToTailwindHue,
} = require('./design-tokens');

const { mapSectionsToArchetypes } = require('./archetype-mapper');
const { detectPinnedHorizontalScroll } = require('./animation-detector');

// ---------------------------------------------------------------------------
// Registry loading (cached)
// ---------------------------------------------------------------------------

const REGISTRY_DIR = path.resolve(__dirname, '../../../skills/animation-components/registry');
const COMPONENT_REGISTRY_PATH = path.resolve(__dirname, '../../../skills/animation-components/component-registry.json');
let _componentRegistryCache = null;

function loadComponentRegistry() {
  if (_componentRegistryCache) return _componentRegistryCache;
  try {
    const raw = fs.readFileSync(COMPONENT_REGISTRY_PATH, 'utf8');
    _componentRegistryCache = JSON.parse(raw);
    return _componentRegistryCache;
  } catch (err) {
    _componentRegistryCache = { components: {} };
    return _componentRegistryCache;
  }
}

function getRegistryComponentByFile(relativePath) {
  if (!relativePath) return null;
  const stem = path.basename(relativePath, '.tsx');
  const reg = loadComponentRegistry();
  return reg.components[stem] || null;
}

// ---------------------------------------------------------------------------
// UI Component Library Matching (v1.2.0)
// Maps detected UI component patterns to search queries and animation library
// categories. Used to find pre-built components in the registry instead of
// relying on Claude to generate them from scratch.
// ---------------------------------------------------------------------------

const UI_COMPONENT_LIBRARY_MAP = {
  'logo-marquee':     { search: 'marquee infinite scroll logo',  category: 'continuous',    suggestedFile: 'continuous/marquee.tsx' },
  'card-grid':        { search: 'card grid staggered entrance',  category: 'entrance',      suggestedFile: 'entrance/staggered-grid.tsx' },
  'accordion':        { search: 'accordion expand collapse',     category: 'interactive',   suggestedFile: null },
  'tabs':             { search: 'tab switch transition',         category: 'interactive',   suggestedFile: null },
  'video-embed':      { search: 'video player modal overlay',    category: null,            suggestedFile: null },
  'image-lightbox':   { search: 'image lightbox modal zoom',     category: 'interactive',   suggestedFile: null },
  'pricing-toggle':   { search: 'toggle switch pricing annual',  category: 'interactive',   suggestedFile: null },
  'carousel':         { search: 'carousel slider drag',          category: 'interactive',   suggestedFile: 'interactive/draggable-carousel.tsx' },
  'testimonial-slider': { search: 'testimonial slider rotate',   category: 'continuous',    suggestedFile: null },
  'counter':          { search: 'count up number animate',       category: 'text',          suggestedFile: 'text/count-up.tsx' },
  'typewriter':       { search: 'typewriter text typing',        category: 'text',          suggestedFile: 'text/word-reveal.tsx' },
  'parallax':         { search: 'parallax scroll layers depth',  category: 'scroll',        suggestedFile: 'scroll/parallax-layers.tsx' },
  'magnetic-button':  { search: 'magnetic button hover follow',  category: 'interactive',   suggestedFile: 'interactive/magnetic-button.tsx' },
  'cursor-effect':    { search: 'cursor trail follow mouse',     category: 'interactive',   suggestedFile: 'interactive/cursor-trail.tsx' },
  'progress-bar':     { search: 'progress bar scroll indicator', category: 'scroll',        suggestedFile: 'scroll/scroll-progress.tsx' },
  'text-reveal':      { search: 'text reveal character word',    category: 'text',          suggestedFile: 'text/word-reveal.tsx' },
  'hover-card':       { search: 'hover card tilt 3d',            category: 'interactive',   suggestedFile: 'interactive/hover-lift.tsx' },
  'infinite-scroll':  { search: 'infinite scroll load more',     category: null,            suggestedFile: null },
  'modal':            { search: 'modal dialog overlay',          category: null,            suggestedFile: null },
  'tooltip':          { search: 'tooltip hover popup',           category: null,            suggestedFile: null },
  'mega-menu':        { search: 'mega menu dropdown nav',         category: null,            suggestedFile: null },
  'sticky-nav':       { search: 'sticky navigation scroll hide', category: null,            suggestedFile: null },
  'back-to-top':      { search: 'back to top scroll button',     category: null,            suggestedFile: null },
  'breadcrumb':       { search: 'breadcrumb navigation trail',   category: null,            suggestedFile: null },
  'notification':     { search: 'notification toast alert',      category: null,            suggestedFile: null },
  'skeleton-loader':  { search: 'skeleton loading placeholder',  category: null,            suggestedFile: null },
};

let _searchIndex = null;
function loadSearchIndex() {
  if (_searchIndex) return _searchIndex;
  const indexPath = path.join(REGISTRY_DIR, 'animation_search_index.json');
  if (!fs.existsSync(indexPath)) return null;
  _searchIndex = JSON.parse(fs.readFileSync(indexPath, 'utf-8'));
  return _searchIndex;
}

let _taxonomy = null;
function loadTaxonomy() {
  if (_taxonomy) return _taxonomy;
  const taxPath = path.join(REGISTRY_DIR, 'animation_taxonomy.json');
  if (!fs.existsSync(taxPath)) return null;
  _taxonomy = JSON.parse(fs.readFileSync(taxPath, 'utf-8'));
  return _taxonomy;
}

// ---------------------------------------------------------------------------
// C1: Animation Pattern Matching
// ---------------------------------------------------------------------------

/**
 * GSAP call method → animation intent mapping
 */
const GSAP_METHOD_INTENTS = {
  'from': ['entrance', 'reveal'],
  'to': ['attention'],
  'fromTo': ['entrance', 'reveal'],
  'set': [],
  'timeline': ['entrance'],
};

/**
 * Classify a GSAP call into animation intents based on its parameters.
 */
function classifyGSAPCall(call) {
  const intents = new Set();
  const triggers = new Set();

  // Method-based classification
  const method = call.method || '';
  if (method.includes('from') || method.includes('fromTo')) {
    if (call.params?.opacity === 0 || call.vars?.opacity === 0) {
      intents.add('reveal');
      intents.add('entrance');
    }
    if (call.params?.y || call.vars?.y) intents.add('entrance');
    if (call.params?.scale || call.vars?.scale) intents.add('entrance');
  }

  // Stagger detection
  if (call.params?.stagger || call.vars?.stagger || call.stagger) {
    intents.add('stagger');
  }

  // ScrollTrigger detection
  if (call.scrollTrigger || call.params?.scrollTrigger || call.vars?.scrollTrigger) {
    const st = call.scrollTrigger || call.params?.scrollTrigger || call.vars?.scrollTrigger;
    if (st?.scrub === true || st?.scrub > 0) {
      triggers.add('scroll_linked');
      intents.add('parallax');
    } else {
      triggers.add('viewport');
    }
  }

  // Text split detection
  if (call.target?.includes?.('SplitText') || call.vars?.SplitText || method.includes('split')) {
    intents.add('typewrite');
    intents.add('reveal');
  }

  // Continuous animation detection
  if (call.params?.repeat === -1 || call.vars?.repeat === -1) {
    intents.add('attention');
    triggers.add('mount');
  }

  // Hover detection
  if (call.trigger === 'hover' || call.event === 'mouseenter') {
    triggers.add('hover');
  }

  if (intents.size === 0) intents.add('entrance');
  if (triggers.size === 0) triggers.add('viewport');

  return { intents: [...intents], triggers: [...triggers] };
}

/**
 * CSS keyframe name → intent mapping
 */
const KEYFRAME_INTENTS = {
  'marquee': ['reveal'],
  'scroll': ['parallax'],
  'fade': ['entrance', 'reveal'],
  'slide': ['entrance'],
  'bounce': ['attention'],
  'pulse': ['attention'],
  'spin': ['attention'],
  'rotate': ['attention'],
  'float': ['attention'],
  'glow': ['attention'],
  'shimmer': ['attention'],
  'blink': ['attention'],
  'wave': ['attention'],
  'typing': ['typewrite'],
  'typewriter': ['typewrite'],
};

/**
 * Match identified animation patterns against the registry search index.
 * @param {Object} animationAnalysis - From animation-analysis.json
 * @param {string} engine - Detected engine (gsap or framer-motion)
 * @returns {{ identifiedPatterns: Object[], gaps: Object[] }}
 */
function matchAnimationPatterns(animationAnalysis, engine) {
  const searchIndex = loadSearchIndex();
  if (!searchIndex) {
    return { identifiedPatterns: [], gaps: [] };
  }

  const identifiedPatterns = [];
  const gaps = [];

  // Process GSAP calls from gsap-extractor output
  const gsapCalls = animationAnalysis?.gsapCalls || animationAnalysis?.extractedCalls || [];
  const sectionOverrides = animationAnalysis?.sectionOverrides || {};

  for (const call of gsapCalls) {
    const { intents, triggers } = classifyGSAPCall(call);

    // Look up in search index
    const candidates = new Set();
    for (const intent of intents) {
      const byIntent = searchIndex.by_intent?.[intent] || [];
      for (const id of byIntent) candidates.add(id);
    }

    // Filter by framework
    const frameworkIds = new Set(searchIndex.by_framework?.[engine] || []);
    const frameworkFiltered = [...candidates].filter((id) => frameworkIds.has(id));

    const patternName = intents.join('-') || 'unknown';
    const sectionIndex = call.section ?? call.sectionIndex ?? null;

    if (frameworkFiltered.length > 0) {
      identifiedPatterns.push({
        pattern: patternName,
        intents,
        triggers,
        source: 'gsap-call',
        sectionIndex,
        registryMatches: frameworkFiltered.slice(0, 5),
        bestMatch: frameworkFiltered[0],
        status: 'available',
      });
    } else if (candidates.size > 0) {
      // Have matches but not in the right framework
      identifiedPatterns.push({
        pattern: patternName,
        intents,
        triggers,
        source: 'gsap-call',
        sectionIndex,
        registryMatches: [...candidates].slice(0, 5),
        bestMatch: [...candidates][0],
        status: 'available-other-framework',
      });
    } else {
      gaps.push({
        type: 'missing_animation_pattern',
        severity: 'low',
        description: `Animation pattern "${patternName}" (intents: ${intents.join(', ')}) found in site but no registry match.`,
        evidence: { call: { method: call.method, target: call.target }, intents, triggers },
        extension_task: `Add pattern "${patternName}" to skills/animation-patterns.md and create a component in skills/animation-components/.`,
      });
    }
  }

  // Process CSS keyframe animations
  const keyframes = animationAnalysis?.cssAnimations?.keyframes || [];
  for (const kf of keyframes) {
    const kfLower = (typeof kf === 'string' ? kf : kf.name || '').toLowerCase();
    let matchedIntents = [];
    for (const [pattern, intents] of Object.entries(KEYFRAME_INTENTS)) {
      if (kfLower.includes(pattern)) {
        matchedIntents = intents;
        break;
      }
    }

    if (matchedIntents.length > 0) {
      const candidates = new Set();
      for (const intent of matchedIntents) {
        const byIntent = searchIndex.by_intent?.[intent] || [];
        for (const id of byIntent) candidates.add(id);
      }

      identifiedPatterns.push({
        pattern: kfLower,
        intents: matchedIntents,
        triggers: ['mount'],
        source: 'css-keyframe',
        sectionIndex: null,
        registryMatches: [...candidates].slice(0, 3),
        bestMatch: candidates.size > 0 ? [...candidates][0] : null,
        status: candidates.size > 0 ? 'available' : 'gap',
      });
    }
  }

  return { identifiedPatterns, gaps };
}

// ---------------------------------------------------------------------------
// C1b: Plugin Pattern Matching
// ---------------------------------------------------------------------------

/**
 * Map detected GSAP plugins (from pluginUsage in animation analysis) to semantic
 * intents and recommended section archetypes. Generates gaps when an intent
 * has no matching component in the animation registry.
 * @param {Object} animationAnalysis - From animation-analysis.json (with pluginUsage)
 * @returns {{ detectedPlugins: string[], pluginCapabilities: Object, gaps: Object[] }}
 */
function matchPluginPatterns(animationAnalysis) {
  const pluginUsage = animationAnalysis?.pluginUsage || {};
  let detectedPlugins = Object.keys(pluginUsage);
  const pluginCapabilities = {};
  const gaps = [];

  // ── Bridge: promote library-detected plugins when static extraction is empty ──
  // gsap-extractor.js often fails on minified/Webflow bundles, leaving pluginUsage
  // empty. But animation-detector.js correctly identifies plugins via window globals
  // and script pattern matching (stored in animationAnalysis.libraries). Bridge them.
  const KNOWN_PLUGINS = [
    'SplitText', 'ScrambleText', 'Flip', 'DrawSVG', 'MorphSVG',
    'MotionPath', 'Draggable', 'Observer', 'ScrollSmoother', 'CustomEase', 'matchMedia',
  ];

  if (detectedPlugins.length === 0) {
    const libraryNames = (animationAnalysis?.libraries || []).map(function (l) {
      return l.name || '';
    });
    const gsapPluginNames = animationAnalysis?.gsapPlugins || [];
    const allCandidates = [...new Set([...libraryNames, ...gsapPluginNames])];

    const bridgedPlugins = allCandidates.filter(function (name) {
      return KNOWN_PLUGINS.includes(name);
    });

    if (bridgedPlugins.length > 0) {
      detectedPlugins = bridgedPlugins;
      // Note: usage data is unavailable from library detection, set to empty array
      for (const p of bridgedPlugins) {
        pluginUsage[p] = [];
      }
    }
  }

  const PLUGIN_INTENT_MAP = {
    SplitText: ['character-reveal', 'word-reveal', 'line-reveal'],
    ScrambleText: ['text-scramble', 'text-decode'],
    Flip: ['layout-transition', 'state-change', 'filter-grid'],
    DrawSVG: ['svg-draw', 'stroke-reveal', 'path-progress'],
    MorphSVG: ['shape-morph', 'icon-morph'],
    MotionPath: ['path-follow', 'orbit', 'flow-along-path'],
    Draggable: ['drag-interaction', 'swipe-carousel'],
    Observer: ['swipe-gesture', 'scroll-velocity'],
    ScrollSmoother: ['smooth-scroll'],
    CustomEase: ['custom-easing'],
    matchMedia: ['responsive-animation'],
  };

  const PLUGIN_SECTION_MAP = {
    SplitText: ['HERO', 'TESTIMONIALS', 'CTA', 'ABOUT'],
    Flip: ['PRODUCT-SHOWCASE', 'GALLERY', 'PORTFOLIO'],
    DrawSVG: ['HERO', 'HOW-IT-WORKS', 'FEATURES'],
    MorphSVG: ['HERO', 'FEATURES'],
    MotionPath: ['HERO', 'FEATURES', 'HOW-IT-WORKS'],
    Draggable: ['TESTIMONIALS', 'GALLERY', 'PRODUCT-SHOWCASE'],
    Observer: ['HERO', 'GALLERY'],
    CustomEase: [],
    matchMedia: [],
  };

  const searchIndex = loadSearchIndex();
  const byIntent = searchIndex?.by_intent || {};

  for (const plugin of detectedPlugins) {
    const intents = PLUGIN_INTENT_MAP[plugin] || [];
    const sections = PLUGIN_SECTION_MAP[plugin] || [];

    pluginCapabilities[plugin] = {
      intents,
      recommendedSections: sections,
      usage: pluginUsage[plugin],
    };

    for (const intent of intents) {
      if (!byIntent[intent] || byIntent[intent].length === 0) {
        gaps.push({
          type: 'missing_plugin_component',
          plugin,
          intent,
          severity: 'medium',
          suggestion: `Create animation component for ${plugin} ${intent} pattern`,
          extension_task: `Create skills/animation-components/*/gsap-${plugin.toLowerCase()}-${intent.replace(/-/g, '_')}.tsx`,
        });
      }
    }
  }

  return { detectedPlugins, pluginCapabilities, gaps };
}

// ---------------------------------------------------------------------------
// C2: UI Component Detection
// ---------------------------------------------------------------------------

/**
 * Detect UI component patterns from DOM structure.
 * @param {Object} extractionData - Full extraction result
 * @param {Object[]} mappedSections - From archetype mapper
 * @returns {Object[]} Detected UI patterns per section
 */
function detectUIComponents(extractionData, mappedSections) {
  const dom = extractionData.renderedDOM || [];
  const sections = extractionData.sections || [];
  const detected = [];

  for (let i = 0; i < sections.length; i++) {
    const sec = sections[i];
    const top = sec.rect?.y || 0;
    const bottom = top + (sec.rect?.height || 0);

    // Get DOM elements within this section
    const sectionElements = dom.filter((el) => {
      const elY = el.rect?.y || 0;
      return elY >= top && elY <= bottom;
    });

    const classStr = ((sec.classNames || '') + ' ' + (sec.id || '')).toLowerCase();
    const patterns = [];

    // Logo marquee: multiple small images in a row
    const images = sectionElements.filter((el) =>
      el.tag === 'img' && el.rect?.width < 200 && el.rect?.height < 100
    );
    if (images.length >= 4) {
      patterns.push('logo-marquee');
    }

    // Video embed
    const hasVideo = sectionElements.some((el) =>
      el.tag === 'video' || el.tag === 'iframe' ||
      /video|player|embed/.test((el.classNames || '').toLowerCase())
    );
    if (hasVideo) patterns.push('video-embed');

    // Card grid: 3+ repeated siblings with similar structure
    const divGroups = {};
    for (const el of sectionElements) {
      if (el.parentId) {
        divGroups[el.parentId] = (divGroups[el.parentId] || 0) + 1;
      }
    }
    const hasCardGrid = Object.values(divGroups).some((count) => count >= 3);
    if (hasCardGrid) patterns.push('card-grid');

    // Code block
    const hasCode = sectionElements.some((el) =>
      el.tag === 'pre' || el.tag === 'code' ||
      /hljs|prism|highlight|syntax/.test((el.classNames || '').toLowerCase())
    );
    if (hasCode) patterns.push('code-block');

    // Accordion / FAQ
    const hasAccordion = sectionElements.some((el) =>
      el.tag === 'details' || el.tag === 'summary' ||
      /accordion|collapse|expand|disclosure/.test((el.classNames || '').toLowerCase())
    );
    if (hasAccordion) patterns.push('accordion');

    // Tab interface
    const hasTabs = sectionElements.some((el) =>
      el.role === 'tablist' || el.role === 'tab' ||
      /tab-|tabs|tablist/.test((el.classNames || '').toLowerCase())
    );
    if (hasTabs) patterns.push('tab-interface');

    // Form
    const hasForm = sectionElements.some((el) => el.tag === 'form');
    if (hasForm) patterns.push('form');

    // Carousel / slider
    const hasCarousel = sectionElements.some((el) =>
      /swiper|carousel|slider|slick|glide/.test((el.classNames || '').toLowerCase())
    );
    if (hasCarousel) patterns.push('carousel');

    if (patterns.length > 0) {
      detected.push({
        sectionIndex: i,
        label: sec.label || '',
        patterns,
      });
    }
  }

  return detected;
}

/**
 * Match detected UI component patterns against the animation library.
 * For each detected UI pattern, finds the best matching library component
 * if one exists.
 *
 * @param {string[]} detectedPatterns - Array of UI pattern names detected from the source site
 * @param {object} [searchIndex] - Optional animation_search_index.json data for richer matching
 * @returns {Array<{ pattern: string, matched: boolean, component: object|null, searchQuery: string }>}
 */
function matchUIComponents(detectedPatterns, searchIndex) {
  if (!detectedPatterns || detectedPatterns.length === 0) return [];

  const results = [];

  detectedPatterns.forEach(function (pattern) {
    const normalized = pattern.toLowerCase().replace(/[^a-z0-9]/g, '-');
    let mapping = UI_COMPONENT_LIBRARY_MAP[normalized];

    if (!mapping) {
      // Try partial match
      const keys = Object.keys(UI_COMPONENT_LIBRARY_MAP);
      for (let k = 0; k < keys.length; k++) {
        if (normalized.includes(keys[k]) || keys[k].includes(normalized)) {
          mapping = UI_COMPONENT_LIBRARY_MAP[keys[k]];
          break;
        }
      }
    }

    if (mapping && mapping.suggestedFile) {
      results.push({
        pattern,
        matched: true,
        component: {
          file: mapping.suggestedFile,
          category: mapping.category,
          searchQuery: mapping.search,
        },
        searchQuery: mapping.search,
      });
    } else if (mapping && searchIndex) {
      // Try to find a match in the search index
      const match = searchIndexLookup(searchIndex, mapping.search, mapping.category);
      results.push({
        pattern,
        matched: !!match,
        component: match,
        searchQuery: mapping.search,
      });
    } else {
      results.push({
        pattern,
        matched: false,
        component: null,
        searchQuery: mapping ? mapping.search : pattern,
      });
    }
  });

  return results;
}

/**
 * Simple search index lookup - finds the best matching component from the search index.
 * @param {object} searchIndex - The animation_search_index.json data
 * @param {string} query - Search query string
 * @param {string|null} category - Optional category to filter by
 * @returns {object|null} - Matched component info or null
 */
function searchIndexLookup(searchIndex, query, category) {
  if (!searchIndex) return null;

  const words = query.toLowerCase().split(/\s+/);
  let bestMatch = null;
  let bestScore = 0;

  // Search by section role if available
  if (searchIndex.by_section_role) {
    const roles = Object.keys(searchIndex.by_section_role);
    roles.forEach(function (role) {
      const entries = searchIndex.by_section_role[role] || [];
      entries.forEach(function (entry) {
        let score = 0;
        const entryText = ((entry.name || '') + ' ' + (entry.description || '') + ' ' + (entry.tags || []).join(' ')).toLowerCase();
        words.forEach(function (w) {
          if (entryText.includes(w)) score++;
        });
        if (category && entry.category === category) score += 2;
        if (score > bestScore) {
          bestScore = score;
          bestMatch = { file: entry.file || (entry.category + '/' + entry.name + '.tsx'), category: entry.category };
        }
      });
    });
  }

  // Also search by motion intent if available
  if (searchIndex.by_motion_intent) {
    const intents = Object.keys(searchIndex.by_motion_intent);
    intents.forEach(function (intent) {
      if (!words.some(function (w) {
        return intent.toLowerCase().includes(w);
      })) return;
      const entries = searchIndex.by_motion_intent[intent] || [];
      entries.forEach(function (entry) {
        let score = 2; // bonus for intent match
        if (category && entry.category === category) score += 2;
        if (score > bestScore) {
          bestScore = score;
          bestMatch = { file: entry.file || (entry.category + '/' + entry.name + '.tsx'), category: entry.category };
        }
      });
    });
  }

  return bestScore >= 2 ? bestMatch : null;
}

/**
 * Build a prompt context block for matched UI components.
 *
 * @param {Array} matchedComponents - Output from matchUIComponents()
 * @returns {{ block: string, componentFiles: string[] }}
 */
function buildUIComponentBlock(matchedComponents) {
  if (!matchedComponents || matchedComponents.length === 0) {
    return { block: '', componentFiles: [] };
  }

  const matched = matchedComponents.filter(function (m) {
    return m.matched;
  });
  if (matched.length === 0) return { block: '', componentFiles: [] };

  const lines = [];
  const componentFiles = [];

  lines.push('═══ UI COMPONENT INJECTION ═══');
  lines.push('The following UI patterns were detected on the source site and matched to library components.');
  lines.push('Use the library component instead of building from scratch.');
  lines.push('');

  matched.forEach(function (m) {
    var comp = m.component;
    var regComp = getRegistryComponentByFile(comp.file);
    var filePath = regComp ? regComp.source_file : comp.file;
    var importLine = regComp ? regComp.import_statement : ('Import from: @/components/animations/' + comp.file.split('/').pop().replace('.tsx', ''));
    lines.push('Pattern: ' + m.pattern);
    lines.push('  Component file: ' + filePath);
    lines.push('  ' + importLine);
    lines.push('');
    componentFiles.push(filePath);
  });

  lines.push('═════════════════════════════');

  return { block: lines.join('\n'), componentFiles };
}

/**
 * Map detected components to sections for prompt injection.
 * @param {Object[]} animationPatterns - From matchAnimationPatterns()
 * @param {Object[]} uiComponents - From detectUIComponents()
 * @returns {Object} Map of sectionIndex → { animations, uiComponents }
 */
function mapComponentsToSections(animationPatterns, uiComponents) {
  const mapping = {};

  // Group animation patterns by section
  for (const p of animationPatterns) {
    if (p.sectionIndex == null) continue;
    if (!mapping[p.sectionIndex]) mapping[p.sectionIndex] = { animations: [], uiComponents: [] };
    mapping[p.sectionIndex].animations.push({
      pattern: p.pattern,
      bestMatch: p.bestMatch,
      status: p.status,
    });
  }

  // Group UI components by section
  for (const u of uiComponents) {
    if (!mapping[u.sectionIndex]) mapping[u.sectionIndex] = { animations: [], uiComponents: [] };
    mapping[u.sectionIndex].uiComponents = u.patterns;
  }

  return mapping;
}

// ---------------------------------------------------------------------------
// C3: Gap Report Aggregation
// ---------------------------------------------------------------------------

/**
 * Aggregate all gaps into a single structured report.
 * @param {Object} params
 * @param {Object[]} params.colorGaps - From identifyColorSystem gaps
 * @param {Object[]} params.archetypeGaps - From archetype mapper
 * @param {Object[]} params.animationGaps - From matchAnimationPatterns
 * @param {Object[]} params.pluginGaps - From matchPluginPatterns
 * @param {Object[]} params.uiGaps - From UI component detection
 * @param {string} params.project - Project name
 * @param {string} params.url - Source URL
 * @param {Object} params.colorSystem - Color system identification
 * @param {number} params.sectionCount - Total sections
 * @param {number} params.highConfidence - Sections mapped at >= 50% confidence
 * @returns {Object} Structured gap report
 */
function aggregateGapReport({
  colorGaps = [],
  archetypeGaps = [],
  animationGaps = [],
  pluginGaps = [],
  uiGaps = [],
  project = '',
  url = '',
  colorSystem = {},
  sectionCount = 0,
  highConfidence = 0,
}) {
  const allGaps = [];
  let idCounter = 1;

  // Color system gaps
  if (colorSystem.system === 'multi-accent' || colorSystem.system === 'gradient-based') {
    allGaps.push({
      id: `gap-${String(idCounter++).padStart(3, '0')}`,
      type: 'missing_color_system_feature',
      severity: 'high',
      description: `Site uses ${colorSystem.system} color system with ${colorSystem.accents?.length || 0} distinct accents. Preset format only supports single accent.`,
      evidence: {
        system: colorSystem.system,
        accents: (colorSystem.accents || []).map((a) => ({ tailwind: a.tailwind, hex: a.hex })),
      },
      extension_task: 'Add section_accents map to style-schema.md and preset _template.md. Update url-to-preset.js prompt to output per-section accents.',
    });
  }

  // Archetype gaps
  for (const gap of archetypeGaps) {
    allGaps.push({
      id: `gap-${String(idCounter++).padStart(3, '0')}`,
      type: gap.type || 'low_confidence_mapping',
      severity: gap.confidence <= 0.3 ? 'high' : 'medium',
      description: gap.suggestion || `Low confidence mapping for section ${gap.sectionIndex}`,
      evidence: gap.rawSignals || {},
      extension_task: `Review section "${gap.label || '(unnamed)'}" (class: ${gap.classNames || 'none'}) — currently mapped to ${gap.assignedArchetype} at ${(gap.confidence * 100).toFixed(0)}%. Add keywords or class signals to archetype-mapper.js.`,
    });
  }

  // Animation gaps
  for (const gap of animationGaps) {
    allGaps.push({
      id: `gap-${String(idCounter++).padStart(3, '0')}`,
      ...gap,
    });
  }

  // Plugin gaps (missing plugin component patterns)
  for (const gap of pluginGaps) {
    allGaps.push({
      id: `gap-${String(idCounter++).padStart(3, '0')}`,
      ...gap,
    });
  }

  // UI component gaps (none for now — UI patterns map to existing archetypes)

  // Custom color gaps
  for (const gap of colorGaps) {
    allGaps.push({
      id: `gap-${String(idCounter++).padStart(3, '0')}`,
      ...gap,
    });
  }

  // Count by type
  const gapTypes = {};
  for (const gap of allGaps) {
    gapTypes[gap.type] = (gapTypes[gap.type] || 0) + 1;
  }

  return {
    project,
    url,
    timestamp: new Date().toISOString(),
    summary: {
      total_sections: sectionCount,
      high_confidence_mappings: highConfidence,
      low_confidence_mappings: sectionCount - highConfidence,
      total_gaps: allGaps.length,
    },
    gaps: allGaps,
    gap_types: gapTypes,
  };
}

// ---------------------------------------------------------------------------
// Main entry point (CLI or module)
// ---------------------------------------------------------------------------

/**
 * Run the full identification pipeline on extraction data.
 * @param {string} extractionDir - Path to extraction directory
 * @param {string} projectName - Project name
 * @returns {Object} Full identification result
 */
function identify(extractionDir, projectName) {
  // Load extraction data
  const dataPath = path.join(extractionDir, 'extraction-data.json');
  const animPath = path.join(extractionDir, 'animation-analysis.json');

  if (!fs.existsSync(dataPath)) {
    return {
      error: 'extraction-data.json not found at ' + dataPath,
      colorSystem: { system: 'unknown', accents: [] },
      sectionCount: 0,
      highConfidence: 0,
      animationPatterns: [],
      uiComponents: [],
      sectionMapping: {},
      gapReport: aggregateGapReport({ project: projectName }),
    };
  }

  const extractionData = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
  const animationAnalysis = fs.existsSync(animPath)
    ? JSON.parse(fs.readFileSync(animPath, 'utf-8'))
    : {};

  // Track A: Color intelligence
  const tokens = require('./design-tokens').collectTokens(extractionData);
  const gradientData = collectGradientColors(extractionData);
  const colorSystem = identifyColorSystem(tokens, gradientData);
  const sectionColorProfile = profileSectionColors(extractionData, gradientData);

  // Track B: Archetype intelligence
  const { mappedSections, gaps: archetypeGaps } = mapSectionsToArchetypes(
    extractionData.sections || [],
    extractionData.textContent || []
  );

  const sectionCount = mappedSections.length;
  const highConfidence = mappedSections.filter((s) => s.confidence >= 0.5).length;

  // Track C: Animation + UI pattern matching
  const engine = animationAnalysis.engine || 'framer-motion';
  const { identifiedPatterns, gaps: animationGaps } = matchAnimationPatterns(animationAnalysis, engine);
  const pluginResult = matchPluginPatterns(animationAnalysis);
  const uiComponents = detectUIComponents(extractionData, mappedSections);
  const sectionMapping = mapComponentsToSections(identifiedPatterns, uiComponents);

  // Pinned horizontal scroll detection (from runtime GSAP calls + static bundle analysis)
  const gsapCalls = animationAnalysis?.gsapCalls || animationAnalysis?.extractedCalls || [];
  const pinnedScrollResult = detectPinnedHorizontalScroll(gsapCalls);

  // Also check static bundle evidence from gsap-extractor
  const staticPinnedEvidence = animationAnalysis?.pluginUsage?._pinnedHorizontalScroll;
  const pinnedScrollDetected = pinnedScrollResult.detected || !!staticPinnedEvidence;

  // Aggregate gap report (include plugin gaps)
  const gapReport = aggregateGapReport({
    colorGaps: [],
    archetypeGaps,
    animationGaps,
    pluginGaps: pluginResult.gaps,
    uiGaps: [],
    project: projectName,
    url: extractionData.url || '',
    colorSystem,
    sectionCount,
    highConfidence,
  });

  return {
    colorSystem,
    sectionColorProfile,
    sectionCount,
    highConfidence,
    mappedSections,
    animationPatterns: identifiedPatterns,
    detectedPlugins: pluginResult.detectedPlugins,
    pluginCapabilities: pluginResult.pluginCapabilities,
    pinnedScrollDetected,
    pinnedScrollEvidence: pinnedScrollResult.evidence,
    uiComponents,
    sectionMapping,
    gapReport,
  };
}

// CLI entry point
if (require.main === module) {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error('Usage: node pattern-identifier.js <extraction-dir> <project-name>');
    process.exit(1);
  }
  const result = identify(args[0], args[1]);
  console.log(JSON.stringify(result));
}

module.exports = {
  identify,
  matchAnimationPatterns,
  matchPluginPatterns,
  detectUIComponents,
  matchUIComponents,
  buildUIComponentBlock,
  searchIndexLookup,
  UI_COMPONENT_LIBRARY_MAP,
  mapComponentsToSections,
  aggregateGapReport,
  classifyGSAPCall,
};

'use strict';

/**
 * Animation Injector Module
 * Transforms animation analysis data + preset config into per-section prompt
 * blocks that get injected into section generation prompts.
 *
 * Three-tier injection strategy (in priority order):
 * 1. Component Library: If a matching component exists in skills/animation-components/,
 *    inject the full source code with customized props from extracted data.
 * 2. Extracted Signature: If perSection data has captured animations,
 *    inject summarized extracted signature (from animation-summarizer).
 * 3. Pattern Snippet: Fall back to reference code snippets (original behavior).
 *
 * Consumes: animation-analysis.json, component-registry.json, component .tsx files
 * Produces: animation context strings with token budgets, dependency lists,
 *           and component file paths for stage_deploy() to copy.
 */

const fs = require('fs');
const path = require('path');
const { summarizeSection } = require('./animation-summarizer');

// ---------------------------------------------------------------------------
// Registry management
// ---------------------------------------------------------------------------

const REGISTRY_PATH = path.resolve(__dirname, '../../../skills/animation-components/component-registry.json');
const COMPONENTS_DIR = path.resolve(__dirname, '../../../skills/animation-components');

let _registryCache = null;

/**
 * Load and cache the animation component registry.
 * @returns {Object} The registry object with component definitions
 */
function loadRegistry() {
  if (_registryCache) return _registryCache;

  try {
    const raw = fs.readFileSync(REGISTRY_PATH, 'utf8');
    _registryCache = JSON.parse(raw);
    return _registryCache;
  } catch (err) {
    console.warn(`[animation-injector] Could not load registry: ${err.message}`);
    _registryCache = { component_count: 0, components: {} };
    return _registryCache;
  }
}

/**
 * Look up a component in the registry by pattern name.
 * Returns null if not found or if it's a placeholder.
 * @param {string} patternName
 * @returns {Object|null} Component definition from registry
 */
function lookupComponent(patternName) {
  const registry = loadRegistry();
  const comp = registry.components[patternName];
  if (!comp) return null;
  if (comp.status === 'placeholder') return null;
  return comp;
}

/**
 * Read a component's source file from the library.
 * @param {string} relativePath - Relative path within skills/animation-components/ (e.g. source_file from registry)
 * @returns {string|null} Component source code, or null if file not found
 */
function readComponentSource(relativePath) {
  const fullPath = path.join(COMPONENTS_DIR, relativePath);
  try {
    return fs.readFileSync(fullPath, 'utf8');
  } catch (err) {
    console.warn(`[animation-injector] Component file not found: ${relativePath}`);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Extracted data → pattern mapping
// ---------------------------------------------------------------------------

/**
 * Map extracted GSAP animation data to a library pattern name.
 * Uses heuristics based on animation properties to determine the best match.
 * @param {Object} sectionData - Per-section extracted animation data
 * @returns {string|null} Pattern name or null if no confident match
 */
function mapExtractedToPattern(sectionData) {
  if (!sectionData || !sectionData.animations || sectionData.animations.length === 0) {
    return null;
  }

  const anims = sectionData.animations;

  // Check for counter pattern (onUpdate with textContent)
  const hasCounter = anims.some(function (a) {
    const vars = a.vars || {};
    return vars.onUpdate && (
      String(vars.onUpdate).includes('textContent') ||
      String(vars.onUpdate).includes('innerText') ||
      String(vars.onUpdate).includes('toFixed')
    );
  });
  if (hasCounter) return 'count-up';

  // Check for timeline with text targets → character-reveal
  const hasTimeline = anims.some(function (a) { return a.type === 'timeline'; });
  const hasTextTarget = anims.some(function (a) {
    const target = String(a.target || '');
    return target.includes('char') || target.includes('letter') ||
           target.includes('span') || target.includes('.char');
  });
  if (hasTimeline && hasTextTarget) return 'character-reveal';

  // Check for word-level targets
  const hasWordTarget = anims.some(function (a) {
    const target = String(a.target || '');
    return target.includes('word') || target.includes('[data-word]');
  });
  if (hasWordTarget) return 'word-reveal';

  // Check for ScrollTrigger with pin → pin-and-reveal
  const hasPinnedScroll = anims.some(function (a) {
    const st = a.scrollTrigger || (a.vars && a.vars.scrollTrigger) || {};
    return st.pin === true || st.pin;
  });
  if (hasPinnedScroll) return 'pin-and-reveal';

  // Check for ScrollTrigger with scrub → parallax-section
  const hasScrub = anims.some(function (a) {
    const st = a.scrollTrigger || (a.vars && a.vars.scrollTrigger) || {};
    return st.scrub === true || typeof st.scrub === 'number';
  });
  if (hasScrub) return 'parallax-section';

  // Check for stagger → fade-up-stagger
  const hasStagger = anims.some(function (a) {
    const vars = a.vars || {};
    return vars.stagger !== undefined && vars.stagger !== 0;
  });
  const hasYMovement = anims.some(function (a) {
    const vars = a.vars || {};
    return vars.y !== undefined;
  });

  // Timeline without text targets → staggered-timeline
  if (hasTimeline && !hasTextTarget && !hasStagger) return 'staggered-timeline';

  // Stagger with Y movement → fade-up-stagger
  if (hasStagger && hasYMovement) return 'fade-up-stagger';
  if (hasStagger) return 'fade-up-stagger';

  // Simple Y movement → fade-up-single
  if (hasYMovement) return 'fade-up-single';

  // X movement → slide-in
  const hasXMovement = anims.some(function (a) {
    const vars = a.vars || {};
    return vars.x !== undefined;
  });
  if (hasXMovement) {
    const xVal = anims.find(function (a) { return (a.vars || {}).x !== undefined; }).vars.x;
    return xVal < 0 ? 'slide-in-left' : 'slide-in-right';
  }

  // Scale → scale-up
  const hasScale = anims.some(function (a) {
    const vars = a.vars || {};
    return vars.scale !== undefined;
  });
  if (hasScale) return 'scale-up';

  return null;
}

/**
 * Extract prop overrides from extracted animation data to customize a component.
 * @param {Object} sectionData - Per-section extracted animation data
 * @param {Object} componentDef - Component definition from registry
 * @returns {Object} Props to override on the component
 */
function extractPropOverrides(sectionData, componentDef) {
  const overrides = {};
  if (!sectionData || !sectionData.animations || sectionData.animations.length === 0) {
    return overrides;
  }

  const defaults = componentDef.defaultProps || {};
  const allowedProps = componentDef.props || [];

  // Find the primary animation (first one with vars)
  const primary = sectionData.animations.find(function (a) {
    return a.vars && Object.keys(a.vars).length > 0;
  });
  if (!primary) return overrides;

  const vars = primary.vars;

  // Map extracted values to component props
  if (allowedProps.includes('duration') && vars.duration !== undefined && vars.duration !== defaults.duration) {
    overrides.duration = vars.duration;
  }
  if (allowedProps.includes('ease') && vars.ease && vars.ease !== defaults.ease) {
    overrides.ease = vars.ease;
  }
  if (allowedProps.includes('stagger') && vars.stagger !== undefined && vars.stagger !== defaults.stagger) {
    overrides.stagger = typeof vars.stagger === 'object' ? vars.stagger.each || vars.stagger.amount : vars.stagger;
  }
  if (allowedProps.includes('y') && vars.y !== undefined && vars.y !== defaults.y) {
    overrides.y = vars.y;
  }
  if (allowedProps.includes('x') && vars.x !== undefined && vars.x !== defaults.x) {
    overrides.x = vars.x;
  }
  if (allowedProps.includes('scale') && vars.scale !== undefined && vars.scale !== defaults.scale) {
    overrides.scale = vars.scale;
  }

  // ScrollTrigger start
  const st = vars.scrollTrigger || primary.scrollTrigger || {};
  if (allowedProps.includes('triggerStart') && st.start && st.start !== defaults.triggerStart) {
    overrides.triggerStart = st.start;
  }

  return overrides;
}

// ---------------------------------------------------------------------------
// Pattern-to-Archetype Map (from animation-patterns.md)
// ---------------------------------------------------------------------------

const ARCHETYPE_PATTERN_MAP = {
  HERO: ['character-reveal', 'staggered-timeline'],
  NAV: null,               // static — no animation
  FEATURES: ['fade-up-stagger'],
  'PRODUCT-SHOWCASE': ['fade-up-stagger'],
  STATS: ['count-up'],
  ABOUT: ['word-reveal'],
  'HOW-IT-WORKS': ['fade-up-stagger'],
  TESTIMONIALS: ['fade-up-stagger'],
  CTA: ['staggered-timeline'],
  GALLERY: ['fade-up-stagger'],
  TEAM: ['fade-up-stagger'],
  CONTACT: ['fade-up-single'],
  FOOTER: null,            // static — no animation
  'LOGO-BAR': ['marquee'],
  PRICING: ['fade-up-stagger'],
  FAQ: ['fade-up-single'],
  NEWSLETTER: ['fade-up-single'],
  'TRUST-BADGES': null,    // static — no animation
};

// ---------------------------------------------------------------------------
// Affinity-based animation selection (Tier 3 enhancement)
// ---------------------------------------------------------------------------

/**
 * Select the best animation pattern for an archetype using affinity scores
 * from the component registry, filtered by engine compatibility, intensity,
 * and deduplication across sections.
 *
 * @param {string} archetype - Section archetype (e.g. 'HERO', 'FEATURES')
 * @param {string} presetIntensity - From parsePresetIntensity()
 * @param {string} engine - 'gsap' | 'framer-motion'
 * @param {string[]} usedPatterns - Patterns already selected in earlier sections
 * @returns {string|null} Best pattern name, or null if no candidates
 */
function selectAnimation(archetype, presetIntensity, engine, usedPatterns) {
  var registry = loadRegistry();
  var intensityRank = { subtle: 1, moderate: 2, expressive: 3, dramatic: 4 };
  var presetRank = intensityRank[presetIntensity] || 2;

  var candidates = [];

  var entries = Object.entries(registry.components);
  for (var i = 0; i < entries.length; i++) {
    var name = entries[i][0];
    var comp = entries[i][1];

    // Filter: engine match (or css/css+react/css+framer which work with both)
    var compEngine = comp.engine || 'framer-motion';
    if (compEngine !== 'css' && compEngine !== 'css+react' && compEngine !== 'css+framer' && compEngine !== engine) continue;

    // Filter: intensity <= preset intensity (don't use expressive on subtle preset)
    var compRank = intensityRank[comp.intensity] || 2;
    if (compRank > presetRank) continue;

    // Filter: must have affinity data for this archetype
    var affinity = comp.affinity || {};
    var score = affinity[archetype] || 0;
    if (score === 0) continue;

    // Filter: not already used in recent sections (deduplication)
    if (usedPatterns.indexOf(name) !== -1) continue;

    // Filter: must be "ready" status
    if (comp.status !== 'ready') continue;

    candidates.push({ name: name, score: score, intensity: comp.intensity });
  }

  if (candidates.length === 0) return null;

  // Sort: highest affinity first, break ties by preferring higher intensity
  candidates.sort(function (a, b) {
    if (b.score !== a.score) return b.score - a.score;
    return (intensityRank[b.intensity] || 0) - (intensityRank[a.intensity] || 0);
  });

  return candidates[0].name;
}

// ---------------------------------------------------------------------------
// Reference code snippets keyed by pattern name (fallback when no component)
// ---------------------------------------------------------------------------

const PATTERN_SNIPPETS = {
  'fade-up-stagger': `gsap.from(".card", {
  y: 40,
  opacity: 0,
  duration: 0.8,
  stagger: 0.12,
  ease: "power3.out",
  scrollTrigger: {
    trigger: sectionRef.current,
    start: "top 80%",
    once: true,
  },
});`,

  'fade-up-single': `gsap.from(elementRef.current, {
  y: 30,
  opacity: 0,
  duration: 0.7,
  ease: "power2.out",
  scrollTrigger: {
    trigger: elementRef.current,
    start: "top 85%",
    once: true,
  },
});`,

  'character-reveal': `const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
tl.from(charsRef.current.filter(Boolean), {
  opacity: 0,
  y: 40,
  rotateX: -90,
  stagger: 0.03,
  duration: 0.8,
});`,

  'word-reveal': `gsap.from("[data-word]", {
  y: "100%",
  opacity: 0,
  duration: 0.7,
  stagger: 0.06,
  ease: "power3.out",
  scrollTrigger: {
    trigger: headingRef.current,
    start: "top 85%",
    once: true,
  },
});`,

  'count-up': `const proxy = { val: 0 };
gsap.to(proxy, {
  val: metric.countTo,
  duration: 1.6,
  ease: "power2.out",
  scrollTrigger: {
    trigger: el,
    start: "top 85%",
    once: true,
  },
  onUpdate() {
    el.textContent = metric.decimals
      ? proxy.val.toFixed(metric.decimals)
      : String(Math.round(proxy.val));
  },
});`,

  'staggered-timeline': `const tl = gsap.timeline({
  defaults: { ease: "power3.out" },
  scrollTrigger: {
    trigger: sectionRef.current,
    start: "top 75%",
    once: true,
  },
});
tl.from(".headline", { y: 40, opacity: 0, duration: 0.8 })
  .from(".subtitle", { y: 30, opacity: 0, duration: 0.6 }, "-=0.4")
  .from(".body-text", { y: 20, opacity: 0, duration: 0.5 }, "-=0.3")
  .from(".cta-button", { y: 20, opacity: 0, duration: 0.4 }, "-=0.2");`,
};

// Framer Motion fallback snippet
const FRAMER_FADE_UP_SNIPPET = `<motion.div
  initial={{ opacity: 0, y: 20 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true }}
  transition={{ duration: 0.6, ease: "easeOut" }}
>
  {/* section content */}
</motion.div>`;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Parse the animation_intensity setting from a preset file.
 * @param {string} presetContent - Full text of the preset file
 * @returns {string} 'subtle' | 'moderate' | 'expressive' | 'dramatic'
 */
function parsePresetIntensity(presetContent) {
  var match = presetContent.match(/animation_intensity:\s*(subtle|moderate|expressive|dramatic)/i);
  return match ? match[1].toLowerCase() : 'moderate';
}

/**
 * Detect animation engine from a preset's Motion line.
 * @param {string} presetContent - Full text of the preset file
 * @returns {string} 'gsap' | 'framer-motion'
 */
function detectEngine(presetContent) {
  if (!presetContent) return 'framer-motion';
  const match = presetContent.match(/Motion:.*?\/(gsap|framer-motion)/);
  return match ? match[1] : 'framer-motion';
}

/**
 * Parse section_overrides from preset content.
 * Format example: "section_overrides: hero:lottie-hero features:scroll-reveal"
 * @param {string} presetContent
 * @returns {Object<string, string>}
 */
function parseSectionOverrides(presetContent) {
  const overrides = {};
  if (!presetContent) return overrides;

  const match = presetContent.match(/section_overrides:\s*(.+)/i);
  if (!match) return overrides;

  const pairs = match[1].trim().split(/\s+/);
  for (const pair of pairs) {
    const [archetype, pattern] = pair.split(':');
    if (archetype && pattern) {
      overrides[archetype.toUpperCase()] = pattern;
    }
  }
  return overrides;
}

/**
 * Determine the animation pattern(s) for a section archetype.
 * @param {string} archetype
 * @param {Object<string, string>} overrides
 * @returns {string[]|null}
 */
function resolvePatterns(archetype, overrides) {
  const normalized = (archetype || '').toUpperCase();

  if (overrides[normalized]) {
    return [overrides[normalized]];
  }

  if (Object.prototype.hasOwnProperty.call(ARCHETYPE_PATTERN_MAP, normalized)) {
    return ARCHETYPE_PATTERN_MAP[normalized];
  }

  // Unknown archetype — default to fade-up-stagger
  return ['fade-up-stagger'];
}

/**
 * Determine intensity label from the animation analysis.
 * @param {Object|null} animationAnalysis
 * @returns {string}
 */
function getIntensity(animationAnalysis) {
  if (!animationAnalysis) return 'moderate';
  return (animationAnalysis.intensity && animationAnalysis.intensity.level) || 'moderate';
}

/**
 * Check whether a section has a Lottie file associated with it.
 * @param {Object|null} animationAnalysis
 * @param {string} archetype
 * @param {string|null} overridePattern
 * @returns {{ isLottie: boolean, filename: string|null }}
 */
function checkLottie(animationAnalysis, archetype, overridePattern, sectionIndex, sectionLabel) {
  if (overridePattern && overridePattern.startsWith('lottie')) {
    return { isLottie: true, filename: null };
  }

  const lottieAssets = (animationAnalysis && animationAnalysis.assets && animationAnalysis.assets.lottie)
    ? animationAnalysis.assets.lottie
    : (animationAnalysis && animationAnalysis.lottieFiles)
      ? animationAnalysis.lottieFiles
      : [];

  if (lottieAssets.length === 0) {
    return { isLottie: false, filename: null };
  }

  // Strategy 1: Fuzzy match by archetype name
  const normalized = (archetype || '').toLowerCase();
  var match = lottieAssets.find(function (l) {
    const name = (l.name || l.url || '').toLowerCase();
    return name.includes(normalized);
  });

  // Strategy 2: Fuzzy match by section label words (3+ char words only)
  if (!match && sectionLabel) {
    const words = sectionLabel.toLowerCase().split(/\s+/).filter(function (w) {
      return w.length >= 3 && !['the', 'and', 'for', 'with', 'that', 'this'].includes(w);
    });
    match = lottieAssets.find(function (l) {
      const name = (l.name || l.url || '').toLowerCase();
      return words.some(function (w) { return name.includes(w); });
    });
  }

  // Strategy 3: Position-based assignment (distribute Lottie assets sequentially)
  if (!match && typeof sectionIndex === 'number') {
    // Skip NAV (index 0) and FOOTER (last) for Lottie assignment
    const contentIndex = Math.max(0, sectionIndex - 1); // offset for NAV
    if (contentIndex < lottieAssets.length) {
      match = lottieAssets[contentIndex];
    }
  }

  if (match) {
    const url = match.url || '';
    const filename = url.split('/').pop().replace('.json', '');
    return { isLottie: true, filename: filename || null, url: url };
  }

  return { isLottie: false, filename: null };
}

/**
 * Determine token budget for a section.
 * @param {string[]|null} patterns
 * @param {string} engine
 * @param {boolean} isLottie
 * @param {boolean} hasComponentSource - Whether a library component is being injected
 * @returns {number}
 */
function calculateTokenBudget(patterns, engine, isLottie, hasComponentSource) {
  // Static sections
  if (patterns === null) return 4096;

  // Component source injection needs more room
  if (hasComponentSource) return 8192;

  const complexPatterns = ['character-reveal', 'count-up', 'staggered-timeline'];
  const hasComplex = patterns.some(function (p) { return complexPatterns.includes(p); });

  if (patterns.length > 1 && hasComplex) return 8192;
  if (isLottie && engine === 'gsap') return 6144;
  if (hasComplex && engine === 'gsap') return 6144;
  return 4096;
}

/**
 * Build the dependency list for a section.
 * @param {string} engine
 * @param {boolean} isLottie
 * @param {Object|null} componentDef - Component definition from registry
 * @returns {string[]}
 */
function buildDependencies(engine, isLottie, componentDef) {
  const deps = new Set();

  // Component-specific dependencies
  if (componentDef && componentDef.dependencies) {
    componentDef.dependencies.forEach(function (d) { deps.add(d); });
  } else if (engine === 'gsap') {
    deps.add('gsap');
    deps.add('framer-motion');
  } else {
    deps.add('framer-motion');
  }

  if (isLottie) {
    deps.add('@lottiefiles/dotlottie-react');
  }

  return Array.from(deps);
}

// ---------------------------------------------------------------------------
// Component injection context builder
// ---------------------------------------------------------------------------

/**
 * Build an animation context block using a library component.
 * @param {Object} componentDef - Component definition from registry
 * @param {string} source - Component source code
 * @param {Object} propOverrides - Props to override on the component
 * @param {string} patternName - The pattern name
 * @returns {string} Context block for the section prompt
 */
function buildComponentContext(componentDef, source, propOverrides, patternName) {
  const lines = [];

  lines.push('## Animation Context — Component Library Injection');
  lines.push(`Engine: ${componentDef.engine}`);
  lines.push(`Pattern: ${patternName}`);
  lines.push(`Category: ${componentDef.category}`);
  lines.push('');

  // Component source code
  lines.push('### Animation Component Source');
  lines.push('Copy this component file exactly to `src/components/animations/' + patternName + '.tsx`:');
  lines.push('```tsx');
  lines.push(source.trim());
  lines.push('```');
  lines.push('');

  // Import instruction (use registry so named vs default and export name are correct)
  const componentName = componentDef.export_name || patternName
    .split('-')
    .map(function (w) { return w.charAt(0).toUpperCase() + w.slice(1); })
    .join('');
  lines.push('### Usage');
  lines.push('Import: `' + (componentDef.import_statement || ('import ' + componentName + ' from "@/components/animations/' + patternName + '"')) + '";');
  lines.push('');

  // Props with overrides
  const mergedProps = Object.assign({}, componentDef.defaultProps || {}, propOverrides);
  const propsEntries = Object.entries(mergedProps);

  if (propsEntries.length > 0) {
    lines.push('### Props (customized from source site extraction)');
    lines.push('```tsx');
    const propsStr = propsEntries
      .map(function (entry) {
        const val = typeof entry[1] === 'string' ? `"${entry[1]}"` : `{${JSON.stringify(entry[1])}}`;
        return `  ${entry[0]}=${val}`;
      })
      .join('\n');
    lines.push(`<${componentName}`);
    lines.push(propsStr);
    lines.push('>');
    lines.push('  {/* section content here */}');
    lines.push(`</${componentName}>`);
    lines.push('```');
    lines.push('');
  } else {
    lines.push(`Wrap section content with \`<${componentName}>{children}</${componentName}>\``);
    lines.push('');
  }

  lines.push('IMPORTANT: Use this component exactly as provided. Do NOT re-implement the animation logic inline.');
  lines.push('The component handles all animation setup, cleanup, and ScrollTrigger configuration.');

  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// Lottie block builder (shared)
// ---------------------------------------------------------------------------

function buildLottieBlock(lottieInfo) {
  const filename = lottieInfo.filename || 'animation';
  const lines = [];
  lines.push('## Lottie Animation');
  lines.push('This section includes a Lottie animation player.');
  lines.push(`URL: /lottie/${filename}.json`);
  lines.push('');
  lines.push("Use @lottiefiles/dotlottie-react:");
  lines.push('```tsx');
  lines.push("import { DotLottieReact } from '@lottiefiles/dotlottie-react';");
  lines.push(`<DotLottieReact src="/lottie/${filename}.json" loop autoplay className="w-full h-auto" />`);
  lines.push('```');
  return lines.join('\n');
}

// ---------------------------------------------------------------------------
// GSAP plugin context (identification-driven)
// ---------------------------------------------------------------------------

const PLUGIN_IMPORT_MAP = {
  SplitText:      { import: 'import { SplitText } from "gsap/SplitText"', register: 'SplitText', usage: 'const split = new SplitText(el, { type: "chars" }); gsap.from(split.chars, { ... }); // cleanup: split.revert()' },
  Flip:           { import: 'import { Flip } from "gsap/Flip"', register: 'Flip', usage: 'const state = Flip.getState(targets); /* DOM change */ Flip.from(state, { duration: 0.6, ease: "power1.inOut" })' },
  DrawSVG:        { import: 'import { DrawSVGPlugin } from "gsap/DrawSVGPlugin"', register: 'DrawSVGPlugin', usage: 'gsap.fromTo(path, { drawSVG: "0%" }, { drawSVG: "100%", duration: 2 })' },
  MorphSVG:       { import: 'import { MorphSVGPlugin } from "gsap/MorphSVGPlugin"', register: 'MorphSVGPlugin', usage: 'gsap.to("#shape1", { morphSVG: "#shape2", duration: 1.5 })' },
  MotionPath:     { import: 'import { MotionPathPlugin } from "gsap/MotionPathPlugin"', register: 'MotionPathPlugin', usage: 'gsap.to(el, { motionPath: { path: "#path", autoRotate: true }, duration: 5 })' },
  CustomEase:     { import: 'import { CustomEase } from "gsap/CustomEase"', register: 'CustomEase', usage: 'CustomEase.create("brandEase", "M0,0 C0.175,0.885 0.32,1 1,1"); // then use ease: "brandEase"' },
  Observer:       { import: 'import { Observer } from "gsap/Observer"', register: 'Observer', usage: 'Observer.create({ target: el, type: "touch,pointer", onLeft: fn, onRight: fn })' },
  ScrambleText:   { import: 'import { ScrambleTextPlugin } from "gsap/ScrambleTextPlugin"', register: 'ScrambleTextPlugin', usage: 'gsap.to(el, { scrambleText: { text: "Final", chars: "!@#$%", speed: 0.3 }, duration: 1.5 })' },
  Draggable:      { import: 'import { Draggable } from "gsap/Draggable"', register: 'Draggable', usage: 'Draggable.create(el, { type: "x", bounds: container, inertia: true })' },
  ScrollSmoother: { import: 'import { ScrollSmoother } from "gsap/ScrollSmoother"', register: 'ScrollSmoother', usage: 'ScrollSmoother.create({ smooth: 1.5, effects: true })' },
};

// ---------------------------------------------------------------------------
// Card Micro-Animation Map (for PRODUCT-SHOWCASE demo-cards variant)
// Maps detected GSAP plugin names → card-scoped visual effects
// ---------------------------------------------------------------------------

const CARD_ANIMATION_MAP = {
  DrawSVG:        { effect: 'card-stroke-draw',    description: 'SVG path draws around card border on scroll', gradient: 'from-emerald-500/20 to-transparent', angle: '135deg' },
  MorphSVG:       { effect: 'card-morph-blob',     description: 'Background blob morphs between organic shapes on hover', gradient: 'from-purple-500/20 to-transparent', angle: '225deg' },
  MotionPath:     { effect: 'card-orbit-dot',      description: 'Small element orbits along card border path', gradient: 'from-blue-500/20 to-transparent', angle: '45deg' },
  Flip:           { effect: 'card-flip-preview',   description: 'Card flips to reveal alternate content on hover', gradient: 'from-amber-500/20 to-transparent', angle: '315deg' },
  SplitText:      { effect: 'card-text-scramble',  description: 'Title text reveals character by character on hover', gradient: 'from-rose-500/20 to-transparent', angle: '180deg' },
  ScrambleText:   { effect: 'card-text-scramble',  description: 'Title text scrambles through random characters on hover', gradient: 'from-cyan-500/20 to-transparent', angle: '90deg' },
  ScrollTrigger:  { effect: 'card-3d-rotate',      description: 'Perspective rotation following mouse position', gradient: 'from-orange-500/20 to-transparent', angle: '270deg' },
  Draggable:      { effect: 'card-3d-rotate',      description: 'Card is slightly draggable with inertia snap-back', gradient: 'from-teal-500/20 to-transparent', angle: '160deg' },
  CustomEase:     { effect: 'card-gradient-shift',  description: 'Custom-eased gradient color shift on hover', gradient: 'from-indigo-500/20 to-transparent', angle: '200deg' },
};

// CSS-only fallback effects when no GSAP plugins are detected
const CARD_CSS_FALLBACKS = [
  { effect: 'card-3d-rotate',      description: 'CSS perspective rotate on hover (transform: rotateY/rotateX)', gradient: 'from-slate-500/20 to-transparent', angle: '135deg' },
  { effect: 'card-gradient-shift',  description: 'CSS background-position shift on hover', gradient: 'from-zinc-500/20 to-transparent', angle: '225deg' },
  { effect: 'card-flip-preview',   description: 'CSS transform rotateY flip on hover (preserve-3d)', gradient: 'from-stone-500/20 to-transparent', angle: '45deg' },
  { effect: 'card-particle-burst', description: 'DOM particle burst on hover (GSAP fromTo on dot divs)', gradient: 'from-neutral-500/20 to-transparent', angle: '315deg' },
  { effect: 'card-3d-rotate',      description: 'CSS scale + shadow lift on hover', gradient: 'from-gray-500/20 to-transparent', angle: '180deg' },
  { effect: 'card-gradient-shift',  description: 'CSS hue-rotate filter shift on hover', gradient: 'from-warmGray-500/20 to-transparent', angle: '90deg' },
];

// ---------------------------------------------------------------------------
// Card-Level Embedded Animation Demos (v1.2.0)
// Maps detected GSAP plugins to actual animation library components that can
// be rendered INSIDE product showcase cards as live mini-demos.
// ---------------------------------------------------------------------------

const CARD_EMBEDDED_DEMOS = {
  'ScrollTrigger': { component: 'ScrollProgress',    file: 'scroll/scroll-progress.tsx',       name: 'scroll-progress' },
  'SplitText':     { component: 'WordReveal',         file: 'text/word-reveal.tsx',             name: 'word-reveal' },
  'Flip':          { component: 'FlipExpandCard',     file: 'interactive/flip-expand-card.tsx',  name: 'flip-expand-card' },
  'MotionPath':    { component: 'MotionPathOrbit',    file: 'continuous/motionpath-orbit.tsx',   name: 'motionpath-orbit' },
  'Draggable':     { component: 'DraggableCarousel',  file: 'interactive/draggable-carousel.tsx', name: 'draggable-carousel' },
  'Observer':      { component: 'ObserverSwipe',      file: 'interactive/observer-swipe.tsx',    name: 'observer-swipe' },
  'DrawSVG':       { component: 'DrawSVGReveal',      file: 'entrance/drawsvg-reveal.tsx',       name: 'drawsvg-reveal' },
  'MorphSVG':      { component: 'MorphSVGIcon',       file: 'interactive/morphsvg-icon.tsx',     name: 'morphsvg-icon' },
  'ScrambleText':  { component: 'ScrambleText',       file: 'text/scramble-text.tsx',            name: 'scramble-text' },
  'TextPlugin':    { component: 'WordReveal',         file: 'text/word-reveal.tsx',              name: 'word-reveal' },
  'MotionPathHelper': { component: 'MotionPathOrbit', file: 'continuous/motionpath-orbit.tsx',   name: 'motionpath-orbit' },
  'CustomEase':    { component: 'GradientShift',      file: 'continuous/gradient-shift.tsx',     name: 'gradient-shift' },
  'CustomBounce':  { component: 'Floating',           file: 'continuous/floating.tsx',           name: 'floating' },
  'CustomWiggle':  { component: 'Floating',           file: 'continuous/floating.tsx',           name: 'floating' },
  'EasePack':      { component: 'GradientShift',      file: 'continuous/gradient-shift.tsx',     name: 'gradient-shift' },
  'Inertia':       { component: 'DraggableCarousel',  file: 'interactive/draggable-carousel.tsx', name: 'draggable-carousel' },
  'InertiaPlugin': { component: 'DraggableCarousel',  file: 'interactive/draggable-carousel.tsx', name: 'draggable-carousel' },
  'PixiPlugin':    { component: 'AuroraBackground',   file: 'background/aurora-background.tsx',  name: 'aurora-background' },
  'Physics2D':     { component: 'Floating',           file: 'continuous/floating.tsx',           name: 'floating' },
  'PhysicsPropsPlugin': { component: 'Floating',      file: 'continuous/floating.tsx',           name: 'floating' },
};

// Fallback components when a plugin has no specific demo
const DEMO_FALLBACK_SEQUENCE = [
  { component: 'BlurFade',        file: 'entrance/blur-fade.tsx',          name: 'blur-fade' },
  { component: 'GlowBorder',      file: 'effect/glow-border.tsx',         name: 'glow-border' },
  { component: 'BorderBeam',      file: 'effect/border-beam.tsx',         name: 'border-beam' },
  { component: 'AuroraBackground', file: 'background/aurora-background.tsx', name: 'aurora-background' },
  { component: 'PerspectiveGrid', file: 'background/perspective-grid.tsx', name: 'perspective-grid' },
  { component: 'StaggeredGrid',   file: 'entrance/staggered-grid.tsx',    name: 'staggered-grid' },
];

/**
 * Build a per-card animation assignment block for PRODUCT-SHOWCASE demo-cards.
 * Maps detected plugins to unique card effects. Falls back to CSS-only effects
 * when no plugins are detected.
 *
 * @param {Object|null} identification - Result from pattern-identifier.js
 * @returns {string} Prompt block describing per-card animation assignments, or empty string
 */
function buildCardAnimationBlock(identification) {
  const lines = [];
  lines.push('## Card Micro-Animation Assignments');
  lines.push('');
  lines.push('CRITICAL: Each card MUST use a DIFFERENT effect and gradient from this list.');
  lines.push('DO NOT give all cards the same treatment. The point is visual VARIETY.');
  lines.push('');

  const detectedPlugins = identification?.detectedPlugins || [];

  if (detectedPlugins.length >= 3) {
    // Use plugin-mapped effects
    lines.push('Detected GSAP plugins — assign one per card:');
    lines.push('');
    let cardNum = 1;
    for (const plugin of detectedPlugins) {
      const mapping = CARD_ANIMATION_MAP[plugin];
      if (mapping) {
        lines.push(`Card ${cardNum}: **${plugin}** → \`${mapping.effect}\``);
        lines.push(`  Effect: ${mapping.description}`);
        lines.push(`  Gradient: linear-gradient(${mapping.angle}, ${mapping.gradient})`);
        lines.push('');
        cardNum++;
      }
    }
    // Fill remaining cards with CSS fallbacks if needed
    if (cardNum <= 6) {
      lines.push('Additional cards (CSS effects):');
      lines.push('');
      for (let i = 0; cardNum <= 8 && i < CARD_CSS_FALLBACKS.length; i++) {
        const fb = CARD_CSS_FALLBACKS[i];
        lines.push(`Card ${cardNum}: \`${fb.effect}\``);
        lines.push(`  Effect: ${fb.description}`);
        lines.push(`  Gradient: linear-gradient(${fb.angle}, ${fb.gradient})`);
        lines.push('');
        cardNum++;
      }
    }
  } else {
    // No plugins — use all CSS fallbacks
    lines.push('No GSAP plugins detected — use CSS-only card effects:');
    lines.push('');
    for (let i = 0; i < CARD_CSS_FALLBACKS.length; i++) {
      const fb = CARD_CSS_FALLBACKS[i];
      lines.push(`Card ${i + 1}: \`${fb.effect}\``);
      lines.push(`  Effect: ${fb.description}`);
      lines.push(`  Gradient: linear-gradient(${fb.angle}, ${fb.gradient})`);
      lines.push('');
    }
  }

  lines.push('Refer to animation-patterns.md section "K. Card Micro-Animation Effects" for code snippets.');

  return lines.join('\n');
}

/**
 * Build prompt context for embedding live animation demos inside product showcase cards.
 * Each detected plugin gets its own library component rendered as a mini-demo.
 *
 * @param {string[]} detectedPlugins - Array of plugin names detected from the source site
 * @returns {{ block: string, componentFiles: string[] }}
 */
function buildCardEmbeddedDemos(detectedPlugins) {
  if (!detectedPlugins || detectedPlugins.length === 0) {
    return { block: '', componentFiles: [] };
  }

  const lines = [];
  const componentFiles = [];
  const usedComponents = new Set();
  let fallbackIndex = 0;

  lines.push('═══ CARD EMBEDDED ANIMATION DEMOS ═══');
  lines.push('Each product card MUST render a DIFFERENT live animation component inside it.');
  lines.push('Import from @/components/animations/{name} and render as the card\'s visual content.');
  lines.push('These replace static icons, emoji, or identical gradient backgrounds.');
  lines.push('');

  detectedPlugins.forEach(function (plugin, index) {
    var demo = CARD_EMBEDDED_DEMOS[plugin];

    // If the mapped component was already used, try a fallback
    if (demo && usedComponents.has(demo.name)) {
      demo = null; // fall through to fallback
    }

    if (!demo) {
      // Use fallback sequence, skipping already-used components
      while (fallbackIndex < DEMO_FALLBACK_SEQUENCE.length && usedComponents.has(DEMO_FALLBACK_SEQUENCE[fallbackIndex].name)) {
        fallbackIndex++;
      }
      demo = DEMO_FALLBACK_SEQUENCE[fallbackIndex % DEMO_FALLBACK_SEQUENCE.length] || DEMO_FALLBACK_SEQUENCE[0];
      fallbackIndex++;
    }

    usedComponents.add(demo.name);
    var demoComp = lookupComponent(demo.name);
    var displayName = demoComp ? demoComp.export_name : demo.component;
    var importLine = demoComp ? demoComp.import_statement : ('import { ' + demo.component + ' } from "@/components/animations/' + demo.name + '"');
    var filePath = demoComp ? demoComp.source_file : demo.file;
    lines.push('Card ' + (index + 1) + ' (' + plugin + '):');
    lines.push('  Component: ' + displayName);
    lines.push('  Import: ' + importLine);
    lines.push('  File: ' + filePath);
    lines.push('  Render inside the card as a live animation preview');
    lines.push('');
    componentFiles.push(filePath);
  });

  lines.push('CRITICAL: Each card MUST show a DIFFERENT running animation. Never use identical visuals.');
  lines.push('═════════════════════════════════════');

  return {
    block: lines.join('\n'),
    componentFiles: componentFiles,
  };
}

/**
 * Build a prompt block describing detected GSAP plugins and how to use them.
 * @param {Object} identification - Result from pattern-identifier.js (detectedPlugins, pluginCapabilities)
 * @returns {string} Context block or empty string
 */
function buildPluginContextBlock(identification) {
  if (!identification?.detectedPlugins?.length) return '';

  const plugins = identification.detectedPlugins;
  const capabilities = identification.pluginCapabilities || {};

  let block = '═══ GSAP PLUGIN CONTEXT ═══\n';
  block += `Detected plugins: ${plugins.join(', ')}\n\n`;

  for (const plugin of plugins) {
    const info = PLUGIN_IMPORT_MAP[plugin];
    if (!info) continue;

    block += `${plugin}:\n`;
    block += `  Import: ${info.import}\n`;
    block += `  Register: gsap.registerPlugin(${info.register})\n`;
    block += `  Usage: ${info.usage}\n`;

    const caps = capabilities[plugin];
    if (caps?.recommendedSections?.length) {
      block += `  Best for: ${caps.recommendedSections.join(', ')} sections\n`;
    }
    block += '\n';
  }

  block += 'IMPORTANT: Wrap registerPlugin in typeof window !== "undefined" for SSR safety.\n';
  block += 'IMPORTANT: Always cleanup (revert SplitText, kill Draggable/Observer) in useEffect return.\n';
  block += '═══════════════════════════\n';

  return block;
}

/**
 * Get plugin recommendations for a section archetype from identification.
 * @param {string} archetype - Section archetype (e.g. 'HERO', 'FEATURES')
 * @param {Object} identification - Result from pattern-identifier.js
 * @returns {Array<{ plugin: string, intents?: string[], usage?: string }>}
 */
function getPluginRecommendationsForSection(archetype, identification) {
  if (!identification?.pluginCapabilities) return [];

  const recommendations = [];
  for (const [plugin, caps] of Object.entries(identification.pluginCapabilities)) {
    if (caps.recommendedSections?.includes(archetype)) {
      recommendations.push({
        plugin,
        intents: caps.intents,
        usage: caps.usage,
      });
    }
  }
  return recommendations;
}

/**
 * Adjust token budget for plugin-heavy sections and NAV/FOOTER minimum.
 * @param {number} tokenBudget
 * @param {string} sectionArchetype
 * @param {Object|null} identification
 * @returns {number}
 */
function adjustTokenBudgetForPlugins(tokenBudget, sectionArchetype, identification) {
  let budget = tokenBudget;
  if (identification) {
    const recs = getPluginRecommendationsForSection((sectionArchetype || '').toUpperCase(), identification);
    if (recs.some(function (r) { return r.plugin === 'SplitText' || r.plugin === 'Flip'; })) {
      budget += 2048;
    }
  }
  const normalized = (sectionArchetype || '').toUpperCase();
  if (normalized === 'NAV' || normalized === 'FOOTER') {
    budget = Math.max(budget, 6144);
  }
  return budget;
}

/**
 * Append plugin context block, section recommendations, and demo-cards block to result; adjust token budget.
 * @param {Object} result - { animationContext, tokenBudget, dependencies, componentFiles, selectedPattern }
 * @param {string} sectionArchetype
 * @param {Object|null} identification
 * @param {string} [sectionVariant] - Section variant (e.g. 'demo-cards')
 * @returns {Object} result with possibly updated animationContext and tokenBudget
 */
function augmentResultWithPlugins(result, sectionArchetype, identification, sectionVariant) {
  result.tokenBudget = adjustTokenBudgetForPlugins(result.tokenBudget, sectionArchetype, identification);
  if (!identification) return result;

  let ctx = result.animationContext || '';
  const pluginBlock = buildPluginContextBlock(identification);
  if (pluginBlock) {
    ctx += (ctx ? '\n\n' : '') + pluginBlock;
  }
  const recs = getPluginRecommendationsForSection((sectionArchetype || '').toUpperCase(), identification);
  if (recs.length) {
    ctx += '\n\n## Section plugin recommendations\n';
    ctx += recs.map(function (r) {
      const part = '- ' + r.plugin;
      return (r.intents && r.intents.length) ? part + ' (' + r.intents.join(', ') + ')' : part;
    }).join('\n');
  }

  // PRODUCT-SHOWCASE demo-cards: append per-card micro-animation assignment block
  const normalizedArch = (sectionArchetype || '').toUpperCase();
  const normalizedVariant = (sectionVariant || '').toLowerCase().replace(/\s+/g, '-');
  if (normalizedArch === 'PRODUCT-SHOWCASE' && normalizedVariant === 'demo-cards') {
    const cardBlock = buildCardAnimationBlock(identification);
    if (cardBlock) {
      ctx += (ctx ? '\n\n' : '') + cardBlock;
    }
    // Ensure sufficient token budget for diverse card animations
    result.tokenBudget = Math.max(result.tokenBudget, 8192);
  }

  result.animationContext = ctx;
  return result;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Build the animation context block for a single section.
 *
 * Three-tier strategy:
 * 1. Component Library — if registry has a non-placeholder component
 * 2. Extracted Signature — if perSection data has captured animations
 * 3. Pattern Snippet — fallback reference code
 *
 * @param {Object|null} animationAnalysis
 * @param {string} presetContent
 * @param {string} sectionArchetype
 * @param {number} sectionIndex
 * @param {string[]} [usedPatterns] - Patterns already selected in earlier sections (for dedup)
 * @param {Object|null} [identification] - Result from pattern-identifier.js (for plugin context)
 * @param {string} [sectionVariant] - Section variant (e.g. 'demo-cards', 'grid', 'single-hero')
 * @returns {{ animationContext: string, tokenBudget: number, dependencies: string[], componentFiles: string[], selectedPattern: string|null }}
 */
function buildAnimationContext(animationAnalysis, presetContent, sectionArchetype, sectionIndex, usedPatterns, identification, sectionVariant) {
  usedPatterns = usedPatterns || [];
  const componentFiles = [];

  // Free-design builds: no analysis available — use selectAnimation with affinity
  if (!animationAnalysis) {
    var freeEngine = detectEngine(presetContent);
    var freeIntensity = parsePresetIntensity(presetContent);
    var freeSelected = selectAnimation(
      sectionArchetype, freeIntensity, freeEngine, usedPatterns
    );

    // Try component library injection for selected pattern
    if (freeSelected) {
      var freeCompDef = lookupComponent(freeSelected);
      if (freeCompDef) {
        var freeSource = readComponentSource(freeCompDef.source_file || freeCompDef.file);
        if (freeSource) {
          var freeDeps = buildDependencies(freeEngine, false, freeCompDef);
          componentFiles.push(freeCompDef.source_file || freeCompDef.file);
          return augmentResultWithPlugins({
            animationContext: buildComponentContext(freeCompDef, freeSource, {}, freeSelected),
            tokenBudget: 8192,
            dependencies: freeDeps,
            componentFiles: componentFiles,
            selectedPattern: freeSelected,
          }, sectionArchetype, identification, sectionVariant);
        }
      }

      // Component not available — use snippet for the selected pattern
      var freeSnippet = PATTERN_SNIPPETS[freeSelected];
      if (freeSnippet) {
        var freeLines = [
          '## Animation Context',
          'Engine: ' + freeEngine,
          'Pattern: ' + freeSelected,
          'Intensity: ' + freeIntensity,
          '',
          '### Reference Animation Pattern',
          'Pattern: `' + freeSelected + '`',
          '```tsx',
          freeSnippet,
          '```',
          'Use the above pattern as a reference. Adapt the timing values to match',
          'the Motion line in the style header.',
        ];
        return augmentResultWithPlugins({
          animationContext: freeLines.join('\n'),
          tokenBudget: calculateTokenBudget([freeSelected], freeEngine, false, false),
          dependencies: buildDependencies(freeEngine, false, null),
          componentFiles: componentFiles,
          selectedPattern: freeSelected,
        }, sectionArchetype, identification, sectionVariant);
      }
    }

    // Final fallback: generic framer-motion fade-up
    var fallbackLines = [
      '## Animation Context',
      'Engine: framer-motion',
      'Pattern: fade-up',
      'Intensity: moderate',
      '',
      '### Reference Animation Pattern',
      '```tsx',
      FRAMER_FADE_UP_SNIPPET,
      '```',
      'Use the above pattern as a reference. Adapt the timing values to match',
      'the Motion line in the style header.',
    ];
    return augmentResultWithPlugins({
      animationContext: fallbackLines.join('\n'),
      tokenBudget: 4096,
      dependencies: ['framer-motion'],
      componentFiles: componentFiles,
      selectedPattern: null,
    }, sectionArchetype, identification, sectionVariant);
  }

  const engine = detectEngine(presetContent);
  const overrides = parseSectionOverrides(presetContent);
  const patterns = resolvePatterns(sectionArchetype, overrides);
  const intensity = getIntensity(animationAnalysis);
  const overridePattern = overrides[(sectionArchetype || '').toUpperCase()] || null;
  const lottieInfo = checkLottie(animationAnalysis, sectionArchetype, overridePattern, sectionIndex, null);
  const perSection = animationAnalysis.perSection || {};
  const sectionData = perSection[sectionIndex] || null;

  // Static sections
  if (patterns === null) {
    const tokenBudget = calculateTokenBudget(patterns, engine, lottieInfo.isLottie, false);
    const lines = [
      '## Animation Context',
      'Engine: none (static section)',
      'Pattern: none',
      `Intensity: ${intensity}`,
      '',
      'This section should use CSS transitions only (hover states, focus states).',
      'Do NOT add scroll-triggered animations or GSAP/Framer Motion imports.',
    ];
    return augmentResultWithPlugins({
      animationContext: lines.join('\n'),
      tokenBudget: tokenBudget,
      dependencies: [],
      componentFiles: componentFiles,
      selectedPattern: null,
    }, sectionArchetype, identification, sectionVariant);
  }

  // -----------------------------------------------------------------------
  // TIER 1: Component Library Injection
  // -----------------------------------------------------------------------

  // Determine the best pattern: extracted data → preset override → archetype default
  let selectedPattern = null;

  // Try mapping from extracted data first
  if (sectionData) {
    selectedPattern = mapExtractedToPattern(sectionData);
  }

  // Fall back to first resolved pattern
  if (!selectedPattern && patterns && patterns.length > 0) {
    selectedPattern = patterns[0];
  }

  // Check if we have a real component (not placeholder) in the library
  const componentDef = selectedPattern ? lookupComponent(selectedPattern) : null;

  if (componentDef) {
    const source = readComponentSource(componentDef.source_file || componentDef.file);
    if (source) {
      // We have a real component — inject it
      const propOverrides = extractPropOverrides(sectionData, componentDef);
      const dependencies = buildDependencies(engine, lottieInfo.isLottie, componentDef);
      const tokenBudget = calculateTokenBudget(patterns, engine, lottieInfo.isLottie, true);

      componentFiles.push(componentDef.source_file || componentDef.file);

      const lines = [buildComponentContext(componentDef, source, propOverrides, selectedPattern)];

      // Add Lottie block if needed
      if (lottieInfo.isLottie) {
        lines.push('');
        lines.push(buildLottieBlock(lottieInfo));
      }

      return augmentResultWithPlugins({
        animationContext: lines.join('\n'),
        tokenBudget: tokenBudget,
        dependencies: dependencies,
        componentFiles: componentFiles,
        selectedPattern: selectedPattern,
      }, sectionArchetype, identification, sectionVariant);
    }
  }

  // -----------------------------------------------------------------------
  // TIER 2: Extracted Signature Injection
  // -----------------------------------------------------------------------

  const hasExtractedData = sectionData &&
    ((sectionData.animations && sectionData.animations.length > 0) ||
     (sectionData.lottie && sectionData.lottie.length > 0));

  if (hasExtractedData) {
    const summary = summarizeSection(sectionData, engine);
    const dependencies = buildDependencies(engine, lottieInfo.isLottie, null);
    const tokenBudget = 8192;

    const lines = [summary];

    if (lottieInfo.isLottie && (!sectionData.lottie || sectionData.lottie.length === 0)) {
      lines.push('');
      lines.push(buildLottieBlock(lottieInfo));
    }

    return augmentResultWithPlugins({
      animationContext: lines.join('\n'),
      tokenBudget: tokenBudget,
      dependencies: dependencies,
      componentFiles: componentFiles,
      selectedPattern: selectedPattern,
    }, sectionArchetype, identification, sectionVariant);
  }

  // -----------------------------------------------------------------------
  // TIER 3: Pattern Snippet Fallback
  // -----------------------------------------------------------------------

  // Try affinity-based selection first, fall back to ARCHETYPE_PATTERN_MAP
  var presetIntensity = parsePresetIntensity(presetContent);
  var affinityPattern = selectAnimation(
    (sectionArchetype || '').toUpperCase(),
    presetIntensity,
    engine,
    usedPatterns
  );

  var tier3Patterns = affinityPattern ? [affinityPattern] : patterns;
  var tier3SelectedPattern = affinityPattern || (patterns && patterns.length > 0 ? patterns[0] : null);

  const dependencies = buildDependencies(engine, lottieInfo.isLottie, null);
  const tokenBudget = calculateTokenBudget(tier3Patterns, engine, lottieInfo.isLottie, false);

  const lines = [];
  lines.push('## Animation Context');
  lines.push(`Engine: ${engine}`);
  lines.push(`Pattern: ${tier3Patterns.join(' + ')}`);
  lines.push(`Intensity: ${intensity}`);
  lines.push('');

  for (var pi = 0; pi < tier3Patterns.length; pi++) {
    var pattern = tier3Patterns[pi];
    const snippet = PATTERN_SNIPPETS[pattern];
    if (snippet) {
      lines.push('### Reference Animation Pattern');
      lines.push(`Pattern: \`${pattern}\``);
      lines.push('```tsx');
      lines.push(snippet);
      lines.push('```');
      lines.push('Use the above pattern as a reference. Adapt the timing values to match');
      lines.push('the Motion line in the style header.');
      lines.push('');
    }
  }

  if (lottieInfo.isLottie) {
    lines.push(buildLottieBlock(lottieInfo));
    lines.push('');
  }

  return augmentResultWithPlugins({
    animationContext: lines.join('\n'),
    tokenBudget: tokenBudget,
    dependencies: dependencies,
    componentFiles: componentFiles,
    selectedPattern: tier3SelectedPattern,
  }, sectionArchetype, identification, sectionVariant);
}

/**
 * Build animation context blocks for all sections.
 *
 * @param {Object|null} animationAnalysis
 * @param {string} presetContent
 * @param {Array<{ archetype: string, variant: string, content: any }>} sections
 * @param {Object|null} [identification] - Result from pattern-identifier.js (for plugin context)
 * @returns {{ contexts: Object, allComponentFiles: string[], allDependencies: string[] }}
 */
function buildAllAnimationContexts(animationAnalysis, presetContent, sections, identification) {
  const contexts = {};
  const allComponentFiles = new Set();
  const allDependencies = new Set();
  var usedPatterns = [];

  if (!Array.isArray(sections)) {
    return { contexts: contexts, allComponentFiles: [], allDependencies: [] };
  }

  for (let i = 0; i < sections.length; i++) {
    const section = sections[i];
    const archetype = (section.archetype || '').toUpperCase();
    const variant = section.variant || '';
    const result = buildAnimationContext(animationAnalysis, presetContent, archetype, i, usedPatterns, identification, variant);
    contexts[i] = result;

    // Track selected patterns for deduplication across sections
    if (result.selectedPattern) {
      usedPatterns.push(result.selectedPattern);
    }

    // Collect component files and dependencies across all sections
    result.componentFiles.forEach(function (f) { allComponentFiles.add(f); });
    result.dependencies.forEach(function (d) { allDependencies.add(d); });
  }

  return {
    contexts: contexts,
    allComponentFiles: Array.from(allComponentFiles),
    allDependencies: Array.from(allDependencies),
  };
}

module.exports = {
  buildAnimationContext,
  buildAllAnimationContexts,
  buildPluginContextBlock,
  buildCardAnimationBlock,
  buildCardEmbeddedDemos,
  getPluginRecommendationsForSection,
  loadRegistry,
  CARD_ANIMATION_MAP,
  CARD_EMBEDDED_DEMOS,
  DEMO_FALLBACK_SEQUENCE,
};

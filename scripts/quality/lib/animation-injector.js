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
 * Consumes: animation-analysis.json, registry.json, component .tsx files
 * Produces: animation context strings with token budgets, dependency lists,
 *           and component file paths for stage_deploy() to copy.
 */

const fs = require('fs');
const path = require('path');
const { summarizeSection } = require('./animation-summarizer');

// ---------------------------------------------------------------------------
// Registry management
// ---------------------------------------------------------------------------

const REGISTRY_PATH = path.resolve(__dirname, '../../../skills/animation-components/registry.json');
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
    _registryCache = { components: {} };
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
 * @param {string} relativePath - Relative path within skills/animation-components/
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
function checkLottie(animationAnalysis, archetype, overridePattern) {
  if (overridePattern && overridePattern.startsWith('lottie')) {
    return { isLottie: true, filename: null };
  }

  if (animationAnalysis && animationAnalysis.assets && animationAnalysis.assets.lottie) {
    const normalized = (archetype || '').toLowerCase();
    const match = animationAnalysis.assets.lottie.find(function (l) {
      const name = (l.name || l.url || '').toLowerCase();
      return name.includes(normalized);
    });
    if (match) {
      const url = match.url || '';
      const filename = url.split('/').pop().replace('.json', '');
      return { isLottie: true, filename: filename || null };
    }
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

  // Import instruction
  const componentName = patternName
    .split('-')
    .map(function (w) { return w.charAt(0).toUpperCase() + w.slice(1); })
    .join('');
  lines.push('### Usage');
  lines.push(`Import: \`import ${componentName} from "@/components/animations/${patternName}";\``);
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
 * @returns {{ animationContext: string, tokenBudget: number, dependencies: string[], componentFiles: string[] }}
 */
function buildAnimationContext(animationAnalysis, presetContent, sectionArchetype, sectionIndex) {
  const componentFiles = [];

  // Graceful fallback: no analysis available
  if (!animationAnalysis) {
    const lines = [
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
    return {
      animationContext: lines.join('\n'),
      tokenBudget: 4096,
      dependencies: ['framer-motion'],
      componentFiles: componentFiles,
    };
  }

  const engine = detectEngine(presetContent);
  const overrides = parseSectionOverrides(presetContent);
  const patterns = resolvePatterns(sectionArchetype, overrides);
  const intensity = getIntensity(animationAnalysis);
  const overridePattern = overrides[(sectionArchetype || '').toUpperCase()] || null;
  const lottieInfo = checkLottie(animationAnalysis, sectionArchetype, overridePattern);
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
    return {
      animationContext: lines.join('\n'),
      tokenBudget: tokenBudget,
      dependencies: [],
      componentFiles: componentFiles,
    };
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
    const source = readComponentSource(componentDef.file);
    if (source) {
      // We have a real component — inject it
      const propOverrides = extractPropOverrides(sectionData, componentDef);
      const dependencies = buildDependencies(engine, lottieInfo.isLottie, componentDef);
      const tokenBudget = calculateTokenBudget(patterns, engine, lottieInfo.isLottie, true);

      componentFiles.push(componentDef.file);

      const lines = [buildComponentContext(componentDef, source, propOverrides, selectedPattern)];

      // Add Lottie block if needed
      if (lottieInfo.isLottie) {
        lines.push('');
        lines.push(buildLottieBlock(lottieInfo));
      }

      return {
        animationContext: lines.join('\n'),
        tokenBudget: tokenBudget,
        dependencies: dependencies,
        componentFiles: componentFiles,
      };
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

    return {
      animationContext: lines.join('\n'),
      tokenBudget: tokenBudget,
      dependencies: dependencies,
      componentFiles: componentFiles,
    };
  }

  // -----------------------------------------------------------------------
  // TIER 3: Pattern Snippet Fallback
  // -----------------------------------------------------------------------

  const dependencies = buildDependencies(engine, lottieInfo.isLottie, null);
  const tokenBudget = calculateTokenBudget(patterns, engine, lottieInfo.isLottie, false);

  const lines = [];
  lines.push('## Animation Context');
  lines.push(`Engine: ${engine}`);
  lines.push(`Pattern: ${patterns.join(' + ')}`);
  lines.push(`Intensity: ${intensity}`);
  lines.push('');

  for (const pattern of patterns) {
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

  return {
    animationContext: lines.join('\n'),
    tokenBudget: tokenBudget,
    dependencies: dependencies,
    componentFiles: componentFiles,
  };
}

/**
 * Build animation context blocks for all sections.
 *
 * @param {Object|null} animationAnalysis
 * @param {string} presetContent
 * @param {Array<{ archetype: string, variant: string, content: any }>} sections
 * @returns {{ contexts: Object, allComponentFiles: string[], allDependencies: string[] }}
 */
function buildAllAnimationContexts(animationAnalysis, presetContent, sections) {
  const contexts = {};
  const allComponentFiles = new Set();
  const allDependencies = new Set();

  if (!Array.isArray(sections)) {
    return { contexts: contexts, allComponentFiles: [], allDependencies: [] };
  }

  for (let i = 0; i < sections.length; i++) {
    const section = sections[i];
    const archetype = (section.archetype || '').toUpperCase();
    const result = buildAnimationContext(animationAnalysis, presetContent, archetype, i);
    contexts[i] = result;

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

module.exports = { buildAnimationContext, buildAllAnimationContexts, loadRegistry };

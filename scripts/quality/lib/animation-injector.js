'use strict';

/**
 * Animation Injector Module
 * Transforms animation analysis data + preset config into per-section prompt
 * blocks that get injected into section generation prompts.
 *
 * Consumes: animation-analysis.json (from animation-detector.js)
 * Produces: animation context strings with token budgets and dependency lists
 */

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
};

// ---------------------------------------------------------------------------
// Reference code snippets keyed by pattern name (from animation-patterns.md)
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

// Framer Motion fallback snippet used when engine is framer-motion or as
// the graceful default when animationAnalysis is missing.
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
 * @returns {Object<string, string>} Map of uppercase archetype to override pattern
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
 * Determine the animation pattern(s) for a section archetype, considering
 * preset overrides and the default archetype map.
 * @param {string} archetype - Uppercase section archetype (e.g. "HERO")
 * @param {Object<string, string>} overrides - Parsed preset section overrides
 * @returns {string[]|null} Array of pattern names, or null for static sections
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
 * @returns {string} 'none' | 'subtle' | 'moderate' | 'expressive'
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
  // Override explicitly requests lottie
  if (overridePattern && overridePattern.startsWith('lottie')) {
    return { isLottie: true, filename: null };
  }

  // Check analysis for Lottie files matching this section
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
 * Determine token budget for a section based on its patterns, engine, and
 * whether Lottie is involved.
 * @param {string[]|null} patterns
 * @param {string} engine
 * @param {boolean} isLottie
 * @returns {number}
 */
function calculateTokenBudget(patterns, engine, isLottie) {
  // Static sections
  if (patterns === null) return 4096;

  const complexPatterns = ['character-reveal', 'count-up', 'staggered-timeline'];
  const hasComplex = patterns.some(function (p) { return complexPatterns.includes(p); });

  // Multi-pattern complex section
  if (patterns.length > 1 && hasComplex) return 8192;

  // Lottie + GSAP combo
  if (isLottie && engine === 'gsap') return 6144;

  // Complex pattern with GSAP
  if (hasComplex && engine === 'gsap') return 6144;

  // Simple patterns or framer-motion
  return 4096;
}

/**
 * Build the dependency list for a section.
 * @param {string} engine
 * @param {boolean} isLottie
 * @returns {string[]}
 */
function buildDependencies(engine, isLottie) {
  const deps = [];

  if (engine === 'gsap') {
    deps.push('gsap', 'framer-motion');
  } else {
    deps.push('framer-motion');
  }

  if (isLottie) {
    deps.push('@lottiefiles/dotlottie-react');
  }

  return deps;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Build the animation context block for a single section.
 *
 * @param {Object|null} animationAnalysis - Output from animation-detector's analyzeAnimationEvidence
 * @param {string} presetContent - Full text content of the preset file
 * @param {string} sectionArchetype - Uppercase section archetype (e.g. "HERO", "STATS")
 * @param {number} sectionIndex - Zero-based index of the section
 * @returns {{ animationContext: string, tokenBudget: number, dependencies: string[] }}
 */
function buildAnimationContext(animationAnalysis, presetContent, sectionArchetype, sectionIndex) {
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
    };
  }

  const engine = detectEngine(presetContent);
  const overrides = parseSectionOverrides(presetContent);
  const patterns = resolvePatterns(sectionArchetype, overrides);
  const intensity = getIntensity(animationAnalysis);
  const overridePattern = overrides[(sectionArchetype || '').toUpperCase()] || null;
  const lottieInfo = checkLottie(animationAnalysis, sectionArchetype, overridePattern);
  const tokenBudget = calculateTokenBudget(patterns, engine, lottieInfo.isLottie);
  const dependencies = buildDependencies(engine, lottieInfo.isLottie);

  const lines = [];

  // Static sections
  if (patterns === null) {
    lines.push('## Animation Context');
    lines.push('Engine: none (static section)');
    lines.push('Pattern: none');
    lines.push(`Intensity: ${intensity}`);
    lines.push('');
    lines.push('This section should use CSS transitions only (hover states, focus states).');
    lines.push('Do NOT add scroll-triggered animations or GSAP/Framer Motion imports.');
    return {
      animationContext: lines.join('\n'),
      tokenBudget: tokenBudget,
      dependencies: [],
    };
  }

  // Animated sections
  lines.push('## Animation Context');
  lines.push(`Engine: ${engine}`);
  lines.push(`Pattern: ${patterns.join(' + ')}`);
  lines.push(`Intensity: ${intensity}`);
  lines.push('');

  // Reference snippets for each pattern
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

  // Lottie integration block
  if (lottieInfo.isLottie) {
    const filename = lottieInfo.filename || 'animation';
    lines.push('## Lottie Animation');
    lines.push('This section includes a Lottie animation player.');
    lines.push(`URL: /lottie/${filename}.json`);
    lines.push('');
    lines.push("Use @lottiefiles/dotlottie-react:");
    lines.push("```tsx");
    lines.push("import { DotLottieReact } from '@lottiefiles/dotlottie-react';");
    lines.push(`<DotLottieReact src="/lottie/${filename}.json" loop autoplay className="w-full h-auto" />`);
    lines.push('```');
    lines.push('');
  }

  return {
    animationContext: lines.join('\n'),
    tokenBudget: tokenBudget,
    dependencies: dependencies,
  };
}

/**
 * Build animation context blocks for all sections.
 *
 * @param {Object|null} animationAnalysis - Output from animation-detector's analyzeAnimationEvidence
 * @param {string} presetContent - Full text content of the preset file
 * @param {Array<{ archetype: string, variant: string, content: any }>} sections - Section list
 * @returns {Object<number, { animationContext: string, tokenBudget: number, dependencies: string[] }>}
 */
function buildAllAnimationContexts(animationAnalysis, presetContent, sections) {
  const contexts = {};
  if (!Array.isArray(sections)) return contexts;

  for (let i = 0; i < sections.length; i++) {
    const section = sections[i];
    const archetype = (section.archetype || '').toUpperCase();
    contexts[i] = buildAnimationContext(animationAnalysis, presetContent, archetype, i);
  }
  return contexts;
}

module.exports = { buildAnimationContext, buildAllAnimationContexts };

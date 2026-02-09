'use strict';

/**
 * Animation Summarizer Module
 * Converts raw per-section GSAP call data into concise, token-efficient
 * text blocks for injection into Claude prompts.
 *
 * Input: Per-section animation data from groupAnimationsBySection()
 * Output: Structured text block, capped at ~800 tokens per section
 */

const TAG = '[animation-summarizer]';
const MAX_TIMELINE_STEPS = 3;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Format a single GSAP animation call into a concise one-line string.
 * Example: ".headline → y:40 opacity:0 → duration:0.8 ease:power3.out"
 */
function formatAnimationCall(anim) {
  const target = anim.targetSelector || '(element)';
  const varsParts = [];

  if (anim.vars) {
    for (const [key, val] of Object.entries(anim.vars)) {
      if (val != null && val !== '') {
        varsParts.push(`${key}:${val}`);
      }
    }
  }

  const metaParts = [];
  if (anim.duration != null) metaParts.push(`duration:${anim.duration}`);
  if (anim.ease) metaParts.push(`ease:${anim.ease}`);
  if (anim.stagger != null) metaParts.push(`stagger:${anim.stagger}`);
  if (anim.delay != null) metaParts.push(`offset:${anim.delay}`);

  const varsStr = varsParts.length > 0 ? varsParts.join(' ') : '';
  const metaStr = metaParts.length > 0 ? metaParts.join(' ') : '';

  if (varsStr && metaStr) {
    return `${target} → ${varsStr} → ${metaStr}`;
  } else if (varsStr) {
    return `${target} → ${varsStr}`;
  } else if (metaStr) {
    return `${target} → ${metaStr}`;
  }
  return target;
}

/**
 * Format a ScrollTrigger config into a concise string.
 */
function formatScrollTrigger(st) {
  if (!st) return null;
  const parts = [];
  if (st.start) parts.push(`start "${st.start}"`);
  if (st.end) parts.push(`end "${st.end}"`);
  if (st.scrub) parts.push(`scrub:${st.scrub === true ? 'true' : st.scrub}`);
  if (st.pin) parts.push('pin:true');
  if (st.once) parts.push('once:true');
  return parts.length > 0 ? parts.join(', ') : null;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Summarize animation data for a single section into a token-efficient text block.
 *
 * @param {Object} sectionData - Per-section data from groupAnimationsBySection
 *   { animations: [], lottie: [], cssKeyframes: [] }
 * @param {string} engine - Animation engine ('gsap', 'framer-motion', 'css')
 * @returns {string} Summarized text block, capped at ~800 tokens
 */
function summarizeSection(sectionData, engine) {
  if (!sectionData) return '';

  const lines = [];
  lines.push('## Extracted Animation Signature');
  lines.push('');
  lines.push(`Engine: ${engine || 'gsap'}`);

  const anims = sectionData.animations || [];
  const lotties = sectionData.lottie || [];
  const keyframes = sectionData.cssKeyframes || [];

  if (anims.length === 0 && lotties.length === 0 && keyframes.length === 0) {
    return '';
  }

  // --- Entrance animations (highest priority) ---
  const entranceAnims = anims.filter(a =>
    a.method === 'from' || a.method === 'timeline.from' || a.method === 'timeline'
  );
  const otherAnims = anims.filter(a =>
    a.method !== 'from' && a.method !== 'timeline.from' && a.method !== 'timeline'
  );

  // Timeline sequences
  const timelines = entranceAnims.filter(a => a.method === 'timeline');
  const standalones = entranceAnims.filter(a => a.method !== 'timeline');

  for (const tl of timelines) {
    const steps = tl.steps || [];
    const showCount = Math.min(steps.length, MAX_TIMELINE_STEPS);
    lines.push(`Entrance: timeline (${steps.length} steps)`);

    for (let i = 0; i < showCount; i++) {
      lines.push(`  ${i + 1}. ${formatAnimationCall(steps[i])}`);
    }
    if (steps.length > MAX_TIMELINE_STEPS) {
      lines.push(`  ... +${steps.length - MAX_TIMELINE_STEPS} more`);
    }

    const stStr = formatScrollTrigger(tl.scrollTrigger);
    if (stStr) {
      lines.push(`ScrollTrigger: ${stStr}`);
    }
    lines.push('');
  }

  // Standalone entrance animations
  for (const anim of standalones) {
    lines.push(`Entrance: ${anim.method}`);
    lines.push(`  ${formatAnimationCall(anim)}`);
    const stStr = formatScrollTrigger(anim.scrollTrigger);
    if (stStr) {
      lines.push(`  ScrollTrigger: ${stStr}`);
    }
    lines.push('');
  }

  // Other animations (to, fromTo, etc.)
  if (otherAnims.length > 0) {
    for (const anim of otherAnims.slice(0, 3)) {
      lines.push(`${anim.method}: ${formatAnimationCall(anim)}`);
      const stStr = formatScrollTrigger(anim.scrollTrigger);
      if (stStr) {
        lines.push(`  ScrollTrigger: ${stStr}`);
      }
    }
    if (otherAnims.length > 3) {
      lines.push(`... +${otherAnims.length - 3} more animations`);
    }
    lines.push('');
  }

  // --- Lottie ---
  for (const lottie of lotties) {
    const url = lottie.url || '/lottie/animation.json';
    lines.push(`Lottie: ${url}`);
    if (lottie.width && lottie.height) {
      lines.push(`  Size: ${Math.round(lottie.width)}x${Math.round(lottie.height)}`);
    }
  }
  if (lotties.length > 0) lines.push('');

  // --- CSS Keyframes (only non-trivial ones) ---
  const trivialNames = new Set(['spin', 'pulse', 'bounce', 'fadeIn', 'fadeOut']);
  const interestingKeyframes = keyframes.filter(k => !trivialNames.has(k.name));
  if (interestingKeyframes.length > 0) {
    lines.push('CSS Keyframes:');
    for (const kf of interestingKeyframes.slice(0, 3)) {
      lines.push(`  @keyframes ${kf.name}`);
      if (kf.body) {
        // Show just the first 200 chars of the body
        const shortBody = kf.body.slice(0, 200).replace(/\n/g, ' ');
        lines.push(`    ${shortBody}`);
      }
    }
    if (interestingKeyframes.length > 3) {
      lines.push(`  ... +${interestingKeyframes.length - 3} more keyframes`);
    }
    lines.push('');
  }

  // Add instruction
  lines.push('Adapt the above animation parameters to your component structure.');
  lines.push('Use the exact easing, duration, and stagger values from the source.');

  return lines.join('\n');
}

/**
 * Summarize animation data for all sections.
 *
 * @param {Object} perSection - Per-section data from groupAnimationsBySection
 * @param {string} engine - Animation engine
 * @returns {Object<string, string>} Map of section index to summary text
 */
function summarizeAll(perSection, engine) {
  const summaries = {};
  if (!perSection) return summaries;

  for (const [key, data] of Object.entries(perSection)) {
    const summary = summarizeSection(data, engine);
    if (summary) {
      summaries[key] = summary;
    }
  }
  return summaries;
}

module.exports = { summarizeSection, summarizeAll };

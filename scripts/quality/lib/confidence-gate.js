'use strict';

// ── Confidence Tiers ─────────────────────────────────────────────────

const CONFIDENCE_TIERS = {
  HIGH:   { min: 0.7, action: 'proceed' },
  MEDIUM: { min: 0.5, action: 'proceed_with_warning' },
  LOW:    { min: 0.3, action: 'needs_reanalysis' },
  NONE:   { min: 0.0, action: 'generic_container' }
};

function getTier(confidence) {
  if (confidence >= CONFIDENCE_TIERS.HIGH.min) return 'HIGH';
  if (confidence >= CONFIDENCE_TIERS.MEDIUM.min) return 'MEDIUM';
  if (confidence >= CONFIDENCE_TIERS.LOW.min) return 'LOW';
  return 'NONE';
}

// ── Section Taxonomy Reference ───────────────────────────────────────

const ARCHETYPE_LIST = [
  'NAV', 'ANNOUNCEMENT-BAR', 'FOOTER', 'HERO', 'LOGO-BAR',
  'TESTIMONIALS', 'STATS', 'TRUST-BADGES', 'FEATURES', 'HOW-IT-WORKS',
  'COMPARISON', 'PRICING', 'CTA', 'NEWSLETTER', 'ABOUT', 'TEAM',
  'FAQ', 'PRODUCT-SHOWCASE', 'PORTFOLIO', 'BLOG-PREVIEW',
  'VIDEO', 'GALLERY', 'CONTACT', 'APP-DOWNLOAD', 'INTEGRATIONS'
];

// ── Gate Function ────────────────────────────────────────────────────

/**
 * Apply confidence gates to mapped sections.
 *
 * @param {Array} mappedSections - From archetype-mapper.js (mapped-sections.json)
 * @param {Object} options
 * @param {number} options.minConfidence - Minimum confidence to proceed without review (default: 0.5)
 * @param {boolean} options.verbose - Log details (default: true)
 * @returns {Object} { sections, stats, needsReanalysis }
 */
function applyConfidenceGates(mappedSections, options = {}) {
  const minConfidence = options.minConfidence ?? 0.5;
  const verbose = options.verbose ?? true;

  const stats = { total: 0, high: 0, medium: 0, low: 0, none: 0, reanalysis_needed: 0 };
  const needsReanalysis = [];
  const gatedSections = [];

  for (const section of mappedSections) {
    stats.total++;
    const conf = section.confidence ?? 0;
    const tier = getTier(conf);
    stats[tier.toLowerCase()]++;

    if (conf < minConfidence) {
      stats.reanalysis_needed++;
      needsReanalysis.push({
        index: section.index,
        current_archetype: section.archetype,
        current_variant: section.variant,
        confidence: conf,
        method: section.method,
        label: section.label || '',
        rect: section.rect,
        tier,
      });
    }

    // Apply fallback for truly unmappable sections
    let finalArchetype = section.archetype;
    let finalVariant = section.variant;
    let confidenceNote = '';

    if (tier === 'NONE') {
      // Below 0.3: generic content section
      finalArchetype = 'FEATURES';
      finalVariant = 'icon-grid';
      confidenceNote = 'FALLBACK: confidence too low, defaulted to generic FEATURES';
    } else if (tier === 'LOW') {
      confidenceNote = 'WARNING: low confidence mapping, may need re-analysis';
    } else if (tier === 'MEDIUM') {
      confidenceNote = 'NOTE: moderate confidence, content signals may override archetype template';
    }

    gatedSections.push({
      ...section,
      archetype: finalArchetype,
      variant: finalVariant,
      confidence_tier: tier,
      confidence_note: confidenceNote,
      original_archetype: section.archetype,
      original_variant: section.variant,
    });

    if (verbose && confidenceNote) {
      console.log(`  [confidence-gate] Section ${section.index} (${section.archetype}): ${tier} (${(conf * 100).toFixed(0)}%) — ${confidenceNote}`);
    }
  }

  if (verbose) {
    console.log(`[confidence-gate] Results: ${stats.high} high, ${stats.medium} medium, ${stats.low} low, ${stats.none} unmappable`);
    if (needsReanalysis.length > 0) {
      console.log(`[confidence-gate] ${needsReanalysis.length} sections need re-analysis`);
    }
  }

  return { sections: gatedSections, stats, needsReanalysis };
}

// ── Re-analysis Prompt Builder ───────────────────────────────────────

/**
 * Build a prompt for Claude Vision to re-classify low-confidence sections.
 * The caller crops screenshots for each section and sends them in a single batch call.
 *
 * @param {Array} lowConfSections - Sections that need re-analysis
 * @returns {string} Prompt text for Claude Vision
 */
function buildReanalysisPrompt(lowConfSections) {
  const sectionDescriptions = lowConfSections.map((s, i) =>
    `Section ${i + 1} (index ${s.index}): Currently classified as "${s.current_archetype}|${s.current_variant}" with ${(s.confidence * 100).toFixed(0)}% confidence. Label: "${s.label || 'none'}"`
  ).join('\n');

  return `You are classifying website sections. For each screenshot below, determine the section archetype and variant.

Available archetypes: ${ARCHETYPE_LIST.join(', ')}

Classify each section with:
- archetype: The section type from the list above
- variant: A specific variant (e.g., "sticky-transparent" for NAV, "centered" for HERO)
- confidence: Your confidence in this classification (0.0-1.0)
- reasoning: Brief explanation

Current (low-confidence) classifications:
${sectionDescriptions}

Respond with ONLY valid JSON array:
[
  {
    "section_index": 0,
    "archetype": "HERO",
    "variant": "split-image",
    "confidence": 0.85,
    "reasoning": "Large hero area with product image and headline text"
  }
]`;
}

// ── Confidence Guidance for Section Generation ───────────────────────

/**
 * Generate guidance text for the section generation prompt based on confidence tier.
 *
 * @param {string} tier - HIGH, MEDIUM, LOW, NONE
 * @param {Object} section - The section spec
 * @returns {string} Guidance text to include in the section prompt
 */
function getConfidenceGuidance(tier, section) {
  switch (tier) {
    case 'HIGH':
      return `This section is classified with HIGH confidence as ${section.archetype}|${section.variant}. Follow the archetype specification closely.`;
    case 'MEDIUM':
      return `This section is classified with MODERATE confidence as ${section.archetype}|${section.variant}. The content signals (headings, images, CTAs) should guide the layout more than the archetype template. Adapt the variant to fit the actual content.`;
    case 'LOW':
      return `This section was classified with LOW confidence as ${section.archetype}|${section.variant}. The classification is uncertain. Use the provided content, images, and text as primary layout guides. The archetype is a suggestion, not a mandate.`;
    case 'NONE':
    default:
      return `This section could not be confidently classified. Treat it as a general content section. Use the provided headings, body text, images, and CTAs to create an appropriate layout. Default to a clean, well-spaced design.`;
  }
}

// ── Exports ──────────────────────────────────────────────────────────

module.exports = {
  CONFIDENCE_TIERS,
  ARCHETYPE_LIST,
  getTier,
  applyConfidenceGates,
  buildReanalysisPrompt,
  getConfidenceGuidance,
};

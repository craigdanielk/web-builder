/**
 * Build Site Spec — Deterministic site-spec.json builder
 *
 * Reads extraction artifacts (extraction-data, mapped-sections, animation-analysis,
 * component-registry) and produces a single structured site-spec.json. No Claude calls.
 *
 * Usage: node scripts/quality/build-site-spec.js <extraction-dir> <project-name> [options]
 * Example: node scripts/quality/build-site-spec.js output/extractions/sofi-health-be91e37d sofi-health
 *
 * Options:
 *   --captures <dir>   Audit capture bundle (run dir or its captures/ dir). Adds a
 *                      `pages[]` array — one entry per crawled route, each with its own
 *                      extracted sections. Without it the output is unchanged.
 *   --routes <list>    Comma-separated route paths to keep (e.g. "/,/about,/blog").
 *   --max-pages <n>    Keep at most n pages (in crawl order).
 *   --out <dir>        Directory to write site-spec.json into. Default
 *                      `output/<project-name>` relative to the CWD, which is
 *                      wrong for any caller that re-roots its output tree.
 *
 * @module build-site-spec
 */

'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const { mapSectionsToArchetypes } = require('./lib/archetype-mapper');
const pageHarvest = require('./lib/html-page-harvest');

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

    // Grouped items come only from the embedded (DOM-scoped) path — the
    // sectionIndex fallback below reconstructs content from a flat text list
    // that never carried grouping, so there is nothing there to group. Absent
    // grouping is reported as an empty array, never as an inferred one.
    const embeddedItems = Array.isArray(embeddedContent?.items) ? embeddedContent.items : [];

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

    // metrics.nodes: populated from URL extraction data when available.
    // The CURRENCY-MAP/interactive slot_schema declares source_path: "metrics.nodes",
    // so any structured node/tabular data from URL extraction flows through here.
    const sectionMetrics = embeddedSection?.metrics || {};

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
        // Unchanged flat lists — every existing consumer reads these.
        headings: headings.slice(0, 5),
        body_text: bodyText.slice(0, 10),
        ctas: ctas.slice(0, 5),
        // Additive structure. `items` is the section's repeated content with
        // each item's own fields joined at the DOM, so a repeater no longer
        // has to be reconstructed by pairing heading[i] with body[i]. The
        // section_* lists are the copy no item claimed — a section's own
        // title and intro, identified by subtraction rather than by an
        // off-by-one rule that is right for one archetype and wrong for the next.
        items: embeddedItems,
        item_count: embeddedItems.length,
        item_grouping: embeddedContent?.item_grouping || null,
        section_headings: (embeddedContent?.section_headings || headings).slice(0, 5),
        section_body_text: (embeddedContent?.section_body_text || bodyText).slice(0, 10),
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
      metrics: {
        nodes: sectionMetrics.nodes || [],
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
// Multi-page harvest (v2.1.0)
//
// The single-URL path above learns about exactly one route. `buildPages()`
// enumerates every route the audit engine crawled and gives each one its own
// extracted sections, using the identical section pipeline (archetype mapping →
// confidence gates → buildSections) so a page-scoped `sections[]` is
// shape-identical to the top-level one.
//
// Source: the audit engine's capture bundle. It already crawled the site, so it
// holds both the real information architecture and the raw HTML of every route.
// A second crawl would duplicate the work and let the two views drift.
// ---------------------------------------------------------------------------

/**
 * Stable, content-derived identity for a harvested section.
 *
 * Deliberately NOT positional: this id is what human decisions, audit defects
 * and per-section regeneration key on, so it has to survive both reordering of
 * the page and regeneration of the section's code. Minted once, at harvest.
 *
 * Collisions (a page with two same-archetype sections sharing a first heading,
 * or two with no heading at all) get a `-N` suffix assigned in source order —
 * the only positional residue, and unavoidable when the content is identical.
 */
function mintSectionUid(pageId, archetype, variant, headings, taken) {
  const normalizedHeading = String(headings && headings[0] ? headings[0] : '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
  const digest = crypto
    .createHash('sha1')
    .update(`${pageId}|${archetype}|${variant}|${normalizedHeading}`)
    .digest('hex')
    .slice(0, 12);

  if (!taken.has(digest)) {
    taken.add(digest);
    return digest;
  }
  for (let n = 2; ; n++) {
    const candidate = `${digest}-${n}`;
    if (!taken.has(candidate)) {
      taken.add(candidate);
      return candidate;
    }
  }
}

/**
 * Fields every emitted page section must carry for the downstream reconciler
 * (`orchestrate.py:reconcile_sections`) to function. Enforced, not assumed:
 * a section silently missing `archetype` wires the consumer up to nothing.
 */
const REQUIRED_SECTION_FIELDS = ['archetype', 'variant', 'section_uid', 'source_index'];

/**
 * Fail the build if any section violates the published contract.
 *
 * This exists because the contract is what another agent codes against, and a
 * spec that quietly disagrees with its own artifact is worse than no spec.
 */
function assertSectionContract(pageId, sections) {
  const problems = [];
  const seenUids = new Set();
  for (const section of sections) {
    for (const field of REQUIRED_SECTION_FIELDS) {
      const value = section[field];
      if (value === undefined || value === null || value === '') {
        problems.push(`section ${section.index}: missing "${field}"`);
      }
    }
    if (!section.content || typeof section.content !== 'object' || Array.isArray(section.content)) {
      problems.push(`section ${section.index}: "content" must be a dict`);
    } else {
      for (const key of ['headings', 'body_text', 'ctas', 'items', 'section_headings', 'section_body_text']) {
        if (!Array.isArray(section.content[key])) {
          problems.push(`section ${section.index}: content.${key} must be an array`);
        }
      }
      // item_count exists so arity is readable without walking items[]. If the
      // two ever disagree the consumer's arity is a lie, so it is enforced.
      if (section.content.item_count !== (section.content.items || []).length) {
        problems.push(
          `section ${section.index}: content.item_count (${section.content.item_count}) ` +
          `disagrees with items.length (${(section.content.items || []).length})`
        );
      }
    }
    if (section.section_uid) {
      if (seenUids.has(section.section_uid)) {
        problems.push(`section ${section.index}: duplicate section_uid "${section.section_uid}"`);
      }
      seenUids.add(section.section_uid);
    }
  }
  if (problems.length > 0) {
    throw new Error(
      `[build-site-spec] Page "${pageId}" violates the harvested-section contract:\n  ` +
      problems.join('\n  ')
    );
  }
}

/**
 * Build one page entry from a raw harvested page.
 *
 * Emits the shape `build_site_manifest.harvested_pages_to_manifest_pages()`
 * consumes: {page_id, page_type, nav, sections, source_url, ...}.
 */
function buildPage(rawPage, componentRegistry, animationAnalysis) {
  // dedupe:false — a copy-harvest must reproduce the source page's sections 1:1.
  // The default adjacent-duplicate collapse silently deletes real content sections
  // (e.g. a body section adjacent to the hero that also classifies as HERO).
  const { mappedSections, gaps } = mapSectionsToArchetypes(rawPage.blocks, [], { dedupe: false });

  const { sections: gatedSections, stats, needsReanalysis } = applyConfidenceGates(mappedSections, {
    minConfidence: 0.5,
    verbose: false,
  });

  // buildSections() reads embedded per-section content off `extractionData.sections`,
  // matched by index — the same contract the DOM-scoped extraction satisfies.
  const pageExtraction = {
    url: rawPage.source_url,
    sections: rawPage.blocks,
    textContent: [],
    assets: {
      images: rawPage.blocks.flatMap((b) => b.images || []),
    },
  };

  const sections = buildSections(pageExtraction, gatedSections, componentRegistry, animationAnalysis);

  // content.ctas is a string[] (identical to the single-URL path). Static HTML
  // also yields the link target, which would otherwise be discarded, so it is
  // carried alongside rather than in place of the existing field.
  const ctasByIndex = new Map(rawPage.blocks.map((b) => [b.index, b.content.ctas || []]));
  const takenUids = new Set();
  for (const section of sections) {
    const tier = section.confidence_tier || getTier(section.confidence);
    section.generation_guidance = getConfidenceGuidance(tier, section);
    section.content.cta_links = ctasByIndex.get(section.index) || [];

    // Position of this section in the SOURCE page (0..n-1, source order).
    // `index` carries the same value today, but source_index is explicit and
    // survives any downstream renumbering, so ordering stays traceable.
    section.source_index = section.index;
    section.section_uid = mintSectionUid(
      rawPage.page_id,
      section.archetype,
      section.variant,
      section.content.headings,
      takenUids
    );
  }

  assertSectionContract(rawPage.page_id, sections);

  return {
    // `page_id` is the name build_site_manifest.harvested_pages_to_manifest_pages()
    // reads first; `id` is the same value under the name the manifest itself emits,
    // so orchestrate.py can join on a page id without knowing which side produced it.
    page_id: rawPage.page_id,
    id: rawPage.page_id,
    page_type: rawPage.page_type,
    route: rawPage.route,
    source_url: rawPage.source_url,
    title: rawPage.title,
    nav: rawPage.nav,
    sections,
    confidence_stats: stats,
    gaps,
    reanalysis: {
      needed: needsReanalysis.length > 0,
      sections: needsReanalysis,
    },
    harvest: rawPage.harvest,
  };
}

/**
 * Build `pages[]` from an audit capture bundle.
 *
 * @param {object} options
 * @param {Array}  options.captures   Capture records (from `loadCaptures`).
 * @param {object} [options.componentRegistry]
 * @param {object} [options.animationAnalysis]
 * @param {string[]} [options.routes] Route paths to keep. Omit to keep all.
 * @param {number} [options.maxPages] Cap on page count, applied after filtering.
 * @returns {Array} Page entries in crawl order.
 */
function buildPages(options) {
  const {
    captures,
    componentRegistry = { components: {} },
    animationAnalysis = null,
    routes = null,
    maxPages = null,
  } = options;

  const wanted = routes && routes.length > 0
    ? new Set(routes.map((r) => {
        const trimmed = String(r).replace(/\/+$/, '');
        return trimmed === '' ? '/' : trimmed;
      }))
    : null;

  let usable = pageHarvest.usableCaptures(captures);
  if (wanted) {
    usable = usable.filter((c) => {
      const p = pageHarvest.pathnameOf(c.url).replace(/\/+$/, '');
      return wanted.has(p === '' ? '/' : p);
    });
  }
  if (maxPages != null && maxPages > 0) usable = usable.slice(0, maxPages);

  const pages = [];
  const seenIds = new Set();
  for (const capture of usable) {
    const rawPage = pageHarvest.harvestPage(capture);
    if (rawPage.blocks.length === 0) continue;
    // page_id is the routing key downstream; a collision would silently
    // overwrite a route's app path.
    if (seenIds.has(rawPage.page_id)) continue;
    seenIds.add(rawPage.page_id);
    pages.push(buildPage(rawPage, componentRegistry, animationAnalysis));
  }
  return pages;
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
    captures = null,
    routes = null,
    maxPages = null,
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

  // Multi-page: only present when a capture bundle was supplied, so the
  // single-URL output stays byte-identical to v2.0.x.
  if (captures) {
    siteSpec.pages = buildPages({
      captures,
      componentRegistry,
      animationAnalysis,
      routes,
      maxPages,
    });
  }

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

/** Split argv into positionals and `--flag value` options. */
function parseArgs(argv) {
  const positional = [];
  const flags = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg.startsWith('--')) {
      flags[arg.slice(2)] = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
    } else {
      positional.push(arg);
    }
  }
  return { positional, flags };
}

function runCLI() {
  const { positional, flags } = parseArgs(process.argv.slice(2));
  const extractionDir = positional[0];
  const projectName = positional[1];

  if (!extractionDir || !projectName) {
    console.error('Usage: node build-site-spec.js <extraction-dir> <project-name> [--captures <dir>] [--routes <a,b>] [--max-pages <n>]');
    console.error('Example: node build-site-spec.js output/extractions/sofi-health-be91e37d sofi-health');
    process.exit(1);
  }

  // A capture bundle is a complete source, not a crawl accessory. `buildPages()`
  // reads captures alone, and design tokens come from the compiled benchmark —
  // so requiring crawl artefacts here is what forced `--from-url` onto every
  // captures build, and with it a SECOND crawl of a site the audit had already
  // crawled. With `--captures` the extraction inputs become optional.
  const capturesRequested = typeof flags.captures === 'string';

  const extractionPath = path.join(extractionDir, 'extraction-data.json');
  const extractionData = loadJson(extractionPath, null);
  if (!extractionData && !capturesRequested) {
    console.error(`[build-site-spec] Missing or invalid extraction-data.json in ${extractionDir}`);
    process.exit(1);
  }

  const mappedPath = path.join(extractionDir, 'mapped-sections.json');
  const mappedSections = loadJson(mappedPath, null);
  if ((!mappedSections || !Array.isArray(mappedSections)) && !capturesRequested) {
    console.error(`[build-site-spec] Missing or invalid mapped-sections.json in ${extractionDir}`);
    process.exit(1);
  }

  // Absent extraction, the single-URL `sections[]` and the measured style block
  // have no source. They are left EMPTY and stamped, never defaulted to
  // plausible values — `pages[]` carries the real content in this mode.
  const capturesOnly = capturesRequested && (!extractionData || !Array.isArray(mappedSections));
  if (capturesOnly) {
    console.log('[build-site-spec] No extraction data — building from captures alone (style: NOT_MEASURED)');
  }

  const animationPath = path.join(extractionDir, 'animation-analysis.json');
  const animationAnalysis = loadJson(animationPath, null);

  const registryPath = path.resolve(__dirname, '..', '..', 'skills', 'animation-components', 'component-registry.json');
  const componentRegistry = loadJson(registryPath, { components: {} });

  // Multi-page harvest is opt-in. A malformed or HTML-less bundle must fail the
  // run loudly — silently emitting a one-page spec is what starved the builder.
  let captures = null;
  if (typeof flags.captures === 'string') {
    captures = pageHarvest.loadCaptures(flags.captures);
    console.log(`[build-site-spec] Loaded ${captures.length} capture(s) from ${flags.captures}`);
  }

  const routes = typeof flags.routes === 'string'
    ? flags.routes.split(',').map((r) => r.trim()).filter(Boolean)
    : null;
  const maxPages = typeof flags['max-pages'] === 'string' ? parseInt(flags['max-pages'], 10) : null;

  const siteSpec = buildSiteSpec({
    extractionData: extractionData || { assets: {} },
    mappedSections: Array.isArray(mappedSections) ? mappedSections : [],
    animationAnalysis,
    componentRegistry,
    projectName,
    captures,
    routes,
    maxPages,
  });

  if (capturesOnly) {
    // Stamped so no downstream reader mistakes an unmeasured palette for a
    // measured one. The design compiler overwrites this from the benchmark.
    siteSpec.style = Object.assign({}, siteSpec.style, { source: 'NOT_MEASURED' });
  }

  // `output/<project>` is relative to the CWD, which is the web-builder repo.
  // Under `--output-root` the orchestrator reads the spec from the re-rooted
  // directory instead, so writing to the default put the spec somewhere the
  // caller never looked: `site_spec` came back None, `pages[]` with it, and a
  // 6-page captures build silently took the single-page path. `--out` lets the
  // caller name the directory it will actually read from.
  const outputDir = typeof flags.out === 'string' && flags.out
    ? flags.out
    : path.join('output', projectName);
  fs.mkdirSync(outputDir, { recursive: true });
  const outputPath = path.join(outputDir, 'site-spec.json');
  fs.writeFileSync(outputPath, JSON.stringify(siteSpec, null, 2), 'utf8');
  const pageNote = siteSpec.pages ? `, ${siteSpec.pages.length} pages` : '';
  console.log(`[build-site-spec] Written to ${outputPath} (${siteSpec.sections.length} sections${pageNote})`);
}

if (require.main === module) {
  runCLI();
} else {
  module.exports = {
    buildSiteSpec,
    buildPages,
    buildPage,
    assertSectionContract,
    mintSectionUid,
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

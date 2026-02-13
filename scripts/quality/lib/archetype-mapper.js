/**
 * Archetype Mapper
 * Maps extracted visual sections from a reference site to web-builder
 * taxonomy archetypes using heuristics: tag, role, position, heading keywords.
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// Taxonomy loader
// ---------------------------------------------------------------------------

const TAXONOMY_PATH = path.resolve(__dirname, '../../../skills/section-taxonomy.md');

function loadArchetypes() {
  const content = fs.readFileSync(TAXONOMY_PATH, 'utf-8');
  const archetypes = [];
  let current = null;

  for (const line of content.split('\n')) {
    if (line.startsWith('### ')) {
      const name = line.replace('### ', '').trim();
      current = { name, variants: [], purpose: '' };
      archetypes.push(current);
    } else if (current && line.startsWith('**Purpose:**')) {
      current.purpose = line.replace('**Purpose:**', '').trim();
    } else if (current && line.startsWith('- `')) {
      const match = line.match(/`([^`]+)`/);
      if (match) current.variants.push(match[1]);
    }
  }
  return archetypes;
}

// ---------------------------------------------------------------------------
// Keyword maps for heuristic matching
// ---------------------------------------------------------------------------

const TAG_MAP = {
  nav: 'NAV',
  header: 'HERO',
  footer: 'FOOTER',
};

const ROLE_MAP = {
  navigation: 'NAV',
  banner: 'HERO',
  contentinfo: 'FOOTER',
  main: null,
};

const HEADING_KEYWORDS = {
  NAV: [],
  HERO: [],
  ABOUT: ['about', 'our story', 'who we are', 'our mission', 'our history', 'meet us'],
  FEATURES: ['features', 'what we offer', 'capabilities', 'solutions', 'services', 'what you get', 'why choose',
    'why', 'benefits', 'advantages', 'animate', 'build'],
  'HOW-IT-WORKS': ['how it works', 'how we work', 'our process', 'steps', 'getting started', 'simple steps',
    'get started', 'quick start', 'installation', 'setup', 'minutes'],
  PRICING: ['pricing', 'plans', 'packages', 'subscription', 'choose your plan', 'get started'],
  TESTIMONIALS: ['testimonials', 'what people say', 'reviews', 'customer stories', 'what our', 'hear from'],
  FAQ: ['faq', 'frequently asked', 'questions', 'common questions', 'have questions'],
  TEAM: ['team', 'our people', 'leadership', 'founders', 'who we are'],
  CONTACT: ['contact', 'get in touch', 'reach us', 'talk to us', 'lets talk', "let's connect"],
  'PRODUCT-SHOWCASE': ['products', 'shop', 'collection', 'our range', 'menu', 'catalog', 'browse',
    'tools', 'platform', 'explore', 'discover', 'our stack'],
  PORTFOLIO: ['portfolio', 'our work', 'case studies', 'projects', 'gallery'],
  'BLOG-PREVIEW': ['blog', 'articles', 'news', 'latest', 'insights', 'resources'],
  CTA: ['get started', 'try it', 'sign up', 'join', 'start your', 'ready to',
    'free', 'create account', 'begin', 'launch'],
  NEWSLETTER: ['newsletter', 'subscribe', 'stay updated', 'join our list', 'stay in the loop'],
  STATS: ['numbers', 'impact', 'results', 'by the numbers', 'achievements',
    'metrics', 'performance', 'speed', 'data'],
  'LOGO-BAR': ['trusted by', 'partners', 'as seen in', 'our clients', 'featured in',
    'brands', 'trusted', 'companies', 'used by', 'powered by', 'built with'],
  GALLERY: ['gallery', 'photos', 'images', 'moments',
    'showcase', 'examples', 'community', 'inspiration', 'showreel'],
  COMPARISON: ['compare', 'vs', 'versus', 'difference', 'before and after'],
  VIDEO: ['watch', 'video', 'see it in action', 'demo'],
  'TRUST-BADGES': ['certified', 'guarantee', 'secure', 'trusted'],
  'APP-DOWNLOAD': ['download', 'get the app', 'available on'],
  INTEGRATIONS: ['integrations', 'works with', 'connect with', 'compatible'],
  'ANNOUNCEMENT-BAR': [],
};

// ---------------------------------------------------------------------------
// Class name + ID signals (v0.9.0 — Track B)
// ---------------------------------------------------------------------------

const CLASS_NAME_SIGNALS = {
  // Direct matches
  'hero': 'HERO', 'banner': 'HERO',
  'nav': 'NAV', 'header': 'NAV', 'navbar': 'NAV', 'navigation': 'NAV',
  'footer': 'FOOTER',
  'about': 'ABOUT',
  'features': 'FEATURES', 'feature': 'FEATURES',
  'pricing': 'PRICING', 'price': 'PRICING', 'plan': 'PRICING',
  'testimonial': 'TESTIMONIALS', 'review': 'TESTIMONIALS', 'reviews': 'TESTIMONIALS',
  'faq': 'FAQ',
  'team': 'TEAM',
  'contact': 'CONTACT',
  'cta': 'CTA',
  'newsletter': 'NEWSLETTER',
  'blog': 'BLOG-PREVIEW',
  'stats': 'STATS', 'counter': 'STATS', 'metric': 'STATS',

  // Product/showcase
  'product': 'PRODUCT-SHOWCASE', 'shop': 'PRODUCT-SHOWCASE',
  'catalog': 'PRODUCT-SHOWCASE', 'tools': 'PRODUCT-SHOWCASE',
  'collection': 'PRODUCT-SHOWCASE',

  // Logo/trust
  'brand': 'LOGO-BAR', 'brands': 'LOGO-BAR',
  'logo': 'LOGO-BAR', 'logos': 'LOGO-BAR',
  'partner': 'LOGO-BAR', 'partners': 'LOGO-BAR',
  'client': 'LOGO-BAR', 'clients': 'LOGO-BAR',
  'trust': 'TRUST-BADGES',

  // Gallery/showcase
  'showcase': 'GALLERY', 'gallery': 'GALLERY',
  'portfolio': 'PORTFOLIO', 'work': 'PORTFOLIO', 'works': 'PORTFOLIO',
  'case': 'PORTFOLIO',

  // Interactive/demo (mapped to FEATURES with variant override handled in selectVariant)
  'demo': 'FEATURES', 'playground': 'FEATURES', 'interactive': 'FEATURES',

  // Process
  'process': 'HOW-IT-WORKS', 'steps': 'HOW-IT-WORKS', 'how': 'HOW-IT-WORKS',

  // Video
  'video': 'VIDEO', 'showreel': 'VIDEO',

  // Comparison
  'compare': 'COMPARISON', 'comparison': 'COMPARISON',

  // Integrations
  'integrations': 'INTEGRATIONS', 'integration': 'INTEGRATIONS',
};

// ---------------------------------------------------------------------------
// Variant selection heuristics
// ---------------------------------------------------------------------------

/**
 * Extract class name fragments from a classNames string and/or id.
 * Splits on spaces, hyphens, and underscores.
 * @param {string} classNames - Space-separated class names
 * @param {string} id - Element ID
 * @returns {string[]} Lowercased fragments
 */
function extractClassFragments(classNames, id) {
  const raw = [classNames || '', id || ''].join(' ');
  return raw.toLowerCase().split(/[\s\-_]+/).filter(Boolean);
}

/**
 * Match a section's classNames/id against CLASS_NAME_SIGNALS.
 * Returns { archetype, confidence: 0.8 } or null.
 */
function matchClassSignals(section) {
  const fragments = extractClassFragments(section.classNames, section.id);
  for (const frag of fragments) {
    if (CLASS_NAME_SIGNALS[frag]) {
      return { archetype: CLASS_NAME_SIGNALS[frag], confidence: 0.8, method: 'class-signal' };
    }
  }
  return null;
}

function selectVariant(archetype, section, archetypes) {
  const arch = archetypes.find((a) => a.name === archetype);
  if (!arch || arch.variants.length === 0) return arch?.variants[0] || 'default';

  const label = (section.label || '').toLowerCase();
  const tag = (section.tag || '').toLowerCase();
  const classStr = ((section.classNames || '') + ' ' + (section.id || '')).toLowerCase();
  const height = section.rect?.height || 0;
  const width = section.rect?.width || 0;

  switch (archetype) {
    case 'NAV':
      return 'sticky-transparent';
    case 'HERO':
      if (height > 700) return 'full-bleed-overlay';
      if (height > 500) return 'split-image';
      return 'centered';
    case 'FOOTER':
      if (height > 300) return 'mega';
      return 'minimal';
    case 'FEATURES':
      // Content-aware variant selection (v0.9.0)
      if (/demo|interactive|playground/.test(classStr)) return 'interactive-demo';
      if (/alternate|zigzag/.test(classStr)) return 'alternating-rows';
      if (height > 1500) return 'alternating-rows';
      return 'icon-grid';
    case 'TESTIMONIALS':
      return 'carousel';
    case 'PRICING':
      return 'three-tier';
    case 'FAQ':
      return 'accordion';
    case 'ABOUT':
      return 'editorial-split';
    case 'HOW-IT-WORKS':
      return 'numbered-steps';
    case 'PRODUCT-SHOWCASE':
      return 'hover-cards';
    case 'NEWSLETTER':
      return 'inline';
    case 'CTA':
      return 'centered';
    case 'STATS':
      return 'counter-animation';
    case 'LOGO-BAR':
      if (height < 200) return 'inline';
      return 'scrolling-marquee';
    case 'CONTACT':
      return 'simple-form';
    case 'PORTFOLIO':
      return 'filtered-grid';
    case 'BLOG-PREVIEW':
      return 'card-grid';
    case 'TEAM':
      return 'grid-with-hover';
    case 'GALLERY':
      if (/reel|video|showreel/.test(classStr)) return 'showcase-reel';
      return 'lightbox-grid';
    default:
      return arch.variants[0];
  }
}

// ---------------------------------------------------------------------------
// Main mapping function
// ---------------------------------------------------------------------------

/**
 * Map extracted sections to taxonomy archetypes.
 *
 * @param {object[]} sections - Sections from extractReference().sections
 * @param {object[]} textContent - Text content from extractReference().textContent
 * @returns {{ mappedSections: object[], gaps: object[] }} Mapped sections + gap records for low-confidence mappings
 */
function mapSectionsToArchetypes(sections, textContent) {
  const archetypes = loadArchetypes();
  const archetypeNames = archetypes.map((a) => a.name);
  const mapped = [];
  const gaps = [];

  for (let i = 0; i < sections.length; i++) {
    const sec = sections[i];
    let archetype = null;
    let confidence = 0;
    let method = 'unknown';

    // 1. Tag-based matching (highest confidence for nav/header/footer)
    if (TAG_MAP[sec.tag]) {
      archetype = TAG_MAP[sec.tag];
      confidence = 0.9;
      method = 'tag';
    }

    // 2. Role-based matching
    if (!archetype && sec.role && ROLE_MAP[sec.role]) {
      archetype = ROLE_MAP[sec.role];
      confidence = 0.85;
      method = 'role';
    }

    // 3. Class name / ID signal matching (v0.9.0 — Track B)
    if (!archetype) {
      const classMatch = matchClassSignals(sec);
      if (classMatch) {
        archetype = classMatch.archetype;
        confidence = classMatch.confidence;
        method = classMatch.method;
      }
    }

    // 4. Label/heading keyword matching
    if (!archetype && sec.label) {
      const labelLower = sec.label.toLowerCase();
      for (const [arch, keywords] of Object.entries(HEADING_KEYWORDS)) {
        if (keywords.some((kw) => labelLower.includes(kw))) {
          archetype = arch;
          confidence = 0.75;
          method = 'heading-keyword';
          break;
        }
      }
    }

    // 5. Check embedded per-section content headings (v2.0.2 — DOM-scoped)
    // Preferred over rect-based text filtering because content is guaranteed
    // to belong to this section (extracted via DOM containment).
    if (!archetype && sec.content?.headings?.length > 0) {
      for (const heading of sec.content.headings) {
        const hLower = heading.toLowerCase();
        for (const [arch, keywords] of Object.entries(HEADING_KEYWORDS)) {
          if (keywords.some((kw) => hLower.includes(kw))) {
            archetype = arch;
            confidence = 0.75;
            method = 'embedded-heading-keyword';
            break;
          }
        }
        if (archetype) break;
      }
    }

    // 5b. Also check embedded body text for strong keyword signals
    if (!archetype && sec.content?.body_text?.length > 0) {
      const allBodyLower = sec.content.body_text.join(' ').toLowerCase();
      for (const [arch, keywords] of Object.entries(HEADING_KEYWORDS)) {
        if (keywords.some((kw) => allBodyLower.includes(kw))) {
          archetype = arch;
          confidence = 0.6;
          method = 'embedded-body-keyword';
          break;
        }
      }
    }

    // 5c. Fallback: rect-based text matching (for legacy extraction data without embedded content)
    if (!archetype) {
      const sectionTexts = (textContent || []).filter((t) => {
        const textY = t.rect?.y || 0;
        return textY >= sec.rect.y && textY <= sec.rect.y + sec.rect.height;
      });

      const headings = sectionTexts.filter((t) => t.isHeading);
      for (const heading of headings) {
        const hLower = heading.text.toLowerCase();
        for (const [arch, keywords] of Object.entries(HEADING_KEYWORDS)) {
          if (keywords.some((kw) => hLower.includes(kw))) {
            archetype = arch;
            confidence = 0.7;
            method = 'text-content-keyword';
            break;
          }
        }
        if (archetype) break;
      }
    }

    // 6. Position-based and structural heuristics
    if (!archetype) {
      // v2.0.2: Use structural signals from embedded content
      const hasImages = (sec.content?.image_count || 0) > 0 || (sec.images || []).length > 0;
      const headingCount = (sec.content?.headings || []).length;
      const bodyCount = (sec.content?.body_text || []).length;
      const ctaCount = (sec.content?.ctas || []).length;
      const height = sec.rect?.height || 0;

      if (i === 0) {
        // First section: almost always HERO or NAV
        if (sec.tag === 'nav') {
          archetype = 'NAV';
          confidence = 0.9;
          method = 'position-first-nav';
        } else {
          archetype = 'HERO';
          confidence = height > 400 ? 0.8 : 0.6;
          method = 'position-first-hero';
        }
      } else if (i === sections.length - 1) {
        archetype = 'FOOTER';
        confidence = 0.5;
        method = 'position-last';
      } else if (i === 1 && mapped[0]?.archetype === 'NAV') {
        archetype = 'HERO';
        confidence = 0.6;
        method = 'position-after-nav';
      } else if (hasImages && headingCount <= 3 && height > 600) {
        // Large section with images → likely product showcase or about
        archetype = 'PRODUCT-SHOWCASE';
        confidence = 0.45;
        method = 'structural-images';
      } else if (headingCount >= 3 && bodyCount >= 3) {
        // Multiple headings + body text → features or how-it-works
        archetype = 'FEATURES';
        confidence = 0.45;
        method = 'structural-multi-heading';
      } else if (bodyCount < 3 && headingCount === 1 && ctaCount > 0) {
        // Single heading + CTA → CTA section
        archetype = 'CTA';
        confidence = 0.45;
        method = 'structural-cta';
      } else {
        archetype = 'FEATURES';
        confidence = 0.3;
        method = 'fallback';
      }
    }

    // Select best variant
    const variant = selectVariant(archetype, sec, archetypes);

    mapped.push({
      index: i,
      archetype,
      variant,
      confidence,
      method,
      label: sec.label || '',
      tag: sec.tag,
      classNames: sec.classNames || '',
      id: sec.id || '',
      rect: sec.rect,
      original: sec,
    });

    // Gap flagging: record any section mapped below 50% confidence (v0.9.0)
    if (confidence < 0.5) {
      gaps.push({
        type: 'low_confidence_mapping',
        sectionIndex: i,
        label: sec.label || '',
        classNames: sec.classNames || '',
        assignedArchetype: archetype,
        assignedVariant: variant,
        confidence,
        method,
        rawSignals: {
          tag: sec.tag,
          id: sec.id || '',
          classNames: sec.classNames || '',
          label: sec.label || '',
          height: sec.rect?.height,
        },
        suggestion: `Section "${sec.label || '(unnamed)'}" (class: ${sec.classNames || 'none'}) mapped to ${archetype} via ${method} at ${(confidence * 100).toFixed(0)}% confidence. Review and add keywords or class signals if a better archetype exists.`,
      });
    }
  }

  // Deduplicate: if two adjacent sections map to the same archetype,
  // keep the one with higher confidence
  const deduped = [];
  for (let i = 0; i < mapped.length; i++) {
    const curr = mapped[i];
    const prev = deduped[deduped.length - 1];

    if (prev && prev.archetype === curr.archetype && curr.archetype !== 'FEATURES') {
      if (curr.confidence > prev.confidence) {
        deduped[deduped.length - 1] = curr;
      }
    } else {
      deduped.push(curr);
    }
  }

  return { mappedSections: deduped, gaps };
}

module.exports = { mapSectionsToArchetypes, loadArchetypes };

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
  FEATURES: ['features', 'what we offer', 'capabilities', 'solutions', 'services', 'what you get', 'why choose'],
  'HOW-IT-WORKS': ['how it works', 'how we work', 'our process', 'steps', 'getting started', 'simple steps'],
  PRICING: ['pricing', 'plans', 'packages', 'subscription', 'choose your plan', 'get started'],
  TESTIMONIALS: ['testimonials', 'what people say', 'reviews', 'customer stories', 'what our', 'hear from'],
  FAQ: ['faq', 'frequently asked', 'questions', 'common questions', 'have questions'],
  TEAM: ['team', 'our people', 'leadership', 'founders', 'who we are'],
  CONTACT: ['contact', 'get in touch', 'reach us', 'talk to us', 'lets talk', "let's connect"],
  'PRODUCT-SHOWCASE': ['products', 'shop', 'collection', 'our range', 'menu', 'catalog', 'browse'],
  PORTFOLIO: ['portfolio', 'our work', 'case studies', 'projects', 'gallery'],
  'BLOG-PREVIEW': ['blog', 'articles', 'news', 'latest', 'insights', 'resources'],
  CTA: ['get started', 'try it', 'sign up', 'join', 'start your', 'ready to'],
  NEWSLETTER: ['newsletter', 'subscribe', 'stay updated', 'join our list', 'stay in the loop'],
  STATS: ['numbers', 'impact', 'results', 'by the numbers', 'achievements'],
  'LOGO-BAR': ['trusted by', 'partners', 'as seen in', 'our clients', 'featured in'],
  GALLERY: ['gallery', 'photos', 'images', 'moments'],
  COMPARISON: ['compare', 'vs', 'versus', 'difference', 'before and after'],
  VIDEO: ['watch', 'video', 'see it in action', 'demo'],
  'TRUST-BADGES': ['certified', 'guarantee', 'secure', 'trusted'],
  'APP-DOWNLOAD': ['download', 'get the app', 'available on'],
  INTEGRATIONS: ['integrations', 'works with', 'connect with', 'compatible'],
  'ANNOUNCEMENT-BAR': [],
};

// ---------------------------------------------------------------------------
// Variant selection heuristics
// ---------------------------------------------------------------------------

function selectVariant(archetype, section, archetypes) {
  const arch = archetypes.find((a) => a.name === archetype);
  if (!arch || arch.variants.length === 0) return arch?.variants[0] || 'default';

  const label = (section.label || '').toLowerCase();
  const tag = (section.tag || '').toLowerCase();
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
 * @returns {object[]} Mapped sections with archetype, variant, confidence, and original data
 */
function mapSectionsToArchetypes(sections, textContent) {
  const archetypes = loadArchetypes();
  const archetypeNames = archetypes.map((a) => a.name);
  const mapped = [];

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

    // 3. Label/heading keyword matching
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

    // 4. Check text content within this section's vertical range for keywords
    if (!archetype) {
      const sectionTexts = textContent.filter((t) => {
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

    // 5. Position-based fallback
    if (!archetype) {
      if (i === 0) {
        archetype = sec.tag === 'nav' ? 'NAV' : 'HERO';
        confidence = 0.5;
        method = 'position-first';
      } else if (i === sections.length - 1) {
        archetype = 'FOOTER';
        confidence = 0.5;
        method = 'position-last';
      } else if (i === 1 && mapped[0]?.archetype === 'NAV') {
        archetype = 'HERO';
        confidence = 0.6;
        method = 'position-after-nav';
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
      rect: sec.rect,
      original: sec,
    });
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

  return deduped;
}

module.exports = { mapSectionsToArchetypes, loadArchetypes };

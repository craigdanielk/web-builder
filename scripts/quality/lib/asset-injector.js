/**
 * Asset Injector
 * Categorizes extracted images and builds per-section asset context blocks
 * for injection into section generation prompts.
 *
 * @module asset-injector
 */

'use strict';

const crypto = require('crypto');
const path = require('path');
const { URL } = require('url');

// ── Category Keywords ────────────────────────────────────────────────────────

/**
 * URL path segments that signal a specific category.
 * Checked first (highest priority).
 */
const URL_CATEGORY_SIGNALS = {
  hero: ['/hero/', '/banner/', '/header-image/', '/splash/'],
  product: ['/product/', '/products/', '/item/', '/shop/', '/catalog/'],
  about: ['/about/', '/story/', '/process/', '/mission/'],
  team: ['/team/', '/staff/', '/people/', '/founders/', '/crew/'],
  location: ['/location/', '/store/', '/cafe/', '/office/', '/map/'],
  testimonial: ['/testimonial/', '/review/', '/customer/', '/avatar/'],
  logo: ['/logo/', '/brand/', '/partner/'],
  icon: ['/icon/', '/badge/', '/cert/'],
  background: ['/bg/', '/background/', '/texture/', '/pattern/'],
};

/**
 * Alt-text keywords that signal a specific category.
 * Checked second.
 */
const ALT_CATEGORY_SIGNALS = {
  hero: ['hero', 'banner', 'main image', 'splash'],
  product: ['product', 'item', 'coffee', 'bean', 'roast', 'blend', 'bag', 'package'],
  about: ['about', 'story', 'process', 'behind the scenes', 'our mission', 'how we'],
  team: ['team', 'staff', 'founder', 'ceo', 'owner', 'barista', 'chef', 'portrait'],
  location: ['store', 'storefront', 'interior', 'cafe', 'office', 'location', 'visit', 'map'],
  testimonial: ['testimonial', 'review', 'customer', 'quote', 'feedback'],
  logo: ['logo', 'brand', 'partner', 'client'],
  icon: ['icon', 'badge', 'certification', 'award'],
  background: ['background', 'texture', 'pattern', 'ambiance', 'atmosphere'],
};

/**
 * Section-to-category mapping from image-extraction.md.
 * Each archetype lists primary categories and fallback categories.
 */
const SECTION_CATEGORY_MAP = {
  HERO: { primary: ['hero', 'background'], fallback: ['product', 'about'] },
  ABOUT: { primary: ['about', 'team'], fallback: ['location', 'background'] },
  'PRODUCT-SHOWCASE': { primary: ['product'], fallback: ['background', 'about'] },
  FEATURES: { primary: ['about', 'product'], fallback: ['background'] },
  PRICING: { primary: ['product'], fallback: ['background'] },
  'HOW-IT-WORKS': { primary: ['about', 'product'], fallback: ['background'] },
  STATS: { primary: ['product'], fallback: ['background'] },
  TEAM: { primary: ['team'], fallback: ['about', 'background'] },
  TESTIMONIALS: { primary: ['testimonial'], fallback: ['team', 'about'] },
  CTA: { primary: ['hero', 'location'], fallback: ['background', 'about'] },
  CONTACT: { primary: ['location'], fallback: ['background'] },
  GALLERY: { primary: ['product', 'about', 'location'], fallback: ['background'] },
  NAV: { primary: ['logo'], fallback: [] },
  FOOTER: { primary: ['logo'], fallback: [] },
};

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Generate a content-addressed local path for an asset URL.
 * Format: /images/{sha256-first8}-{originalFilename}.{ext}
 *
 * @param {string} url - Original asset URL
 * @returns {{ localPath: string, sha8: string }}
 */
function buildLocalPath(url) {
  const sha8 = crypto.createHash('sha256').update(url).digest('hex').slice(0, 8);
  let filename;
  try {
    const parsed = new URL(url);
    filename = path.basename(parsed.pathname);
  } catch (_) {
    filename = 'image.jpg';
  }

  // Ensure the filename has an extension
  const ext = path.extname(filename);
  if (!ext) {
    filename = filename + '.jpg';
  }

  const isLottie = filename.endsWith('.json') || url.includes('lottie');
  const dir = isLottie ? '/lottie' : '/images';

  return {
    localPath: `${dir}/${sha8}-${filename}`,
    sha8,
  };
}

/**
 * Extract a URL string from a CSS background-image value.
 * Handles url("..."), url('...'), and url(...) formats.
 *
 * @param {string} bgValue - CSS background-image value
 * @returns {string|null} Extracted URL or null
 */
function extractUrlFromBgImage(bgValue) {
  if (!bgValue || bgValue === 'none') return null;
  const match = bgValue.match(/url\(["']?([^"')]+)["']?\)/);
  return match ? match[1] : null;
}

/**
 * Determine if a URL is a data URI or tracking pixel that should be filtered.
 *
 * @param {string} src - Image source URL
 * @returns {boolean} True if the image should be excluded
 */
function shouldFilter(src) {
  if (!src) return true;
  if (src.startsWith('data:')) return true;
  if (src.includes('pixel') || src.includes('beacon') || src.includes('tracker')) return true;
  return false;
}

// ── Core Functions ───────────────────────────────────────────────────────────

/**
 * Categorize all images from extraction data into one of 10 categories.
 *
 * Categorization signals (in priority order):
 *   1. URL-path segments (e.g. /hero/, /products/, /team/)
 *   2. Alt-text keywords
 *   3. Y-position relative to section boundaries
 *   4. Dimensions (large landscape=hero, square=product/team, small=icon)
 *
 * Filters out: images < 50x50px, tracking pixels, base64 data URIs.
 * Deduplicates by URL.
 *
 * @param {object} extractionData - Full extraction result from extractReference()
 * @returns {Array<{ url: string, alt: string, width: number, height: number, category: string, sectionIndex: number }>}
 */
function categorizeImages(extractionData) {
  if (!extractionData) return [];

  const sections = extractionData.sections || [];
  const rawImages = extractionData.assets?.images || [];
  const rawBgImages = extractionData.assets?.backgroundImages || [];
  const seenUrls = new Set();
  const results = [];

  // Helper: find which section an image belongs to based on Y position
  function findSectionIndex(yPosition) {
    for (let i = 0; i < sections.length; i++) {
      const s = sections[i];
      if (s.rect && yPosition >= s.rect.y && yPosition <= s.rect.y + s.rect.height) {
        return i;
      }
    }
    return -1;
  }

  // Helper: categorize a single image by signals
  function categorize(src, alt, width, height) {
    const srcLower = (src || '').toLowerCase();
    const altLower = (alt || '').toLowerCase();

    // Signal 1: URL path segments (highest priority)
    for (const [category, patterns] of Object.entries(URL_CATEGORY_SIGNALS)) {
      if (patterns.some((p) => srcLower.includes(p))) {
        return category;
      }
    }

    // Signal 2: Alt-text keywords
    for (const [category, keywords] of Object.entries(ALT_CATEGORY_SIGNALS)) {
      if (keywords.some((kw) => altLower.includes(kw))) {
        return category;
      }
    }

    // Signal 3: Dimensions-based heuristics
    const w = width || 0;
    const h = height || 0;

    // Very small = icon
    if (w > 0 && h > 0 && w <= 80 && h <= 80) {
      return 'icon';
    }

    // Small square = logo or icon
    if (w > 0 && h > 0 && w <= 200 && h <= 200 && Math.abs(w - h) < 30) {
      return 'logo';
    }

    // Large landscape = hero or background
    if (w >= 1200 && h > 0 && w / h > 1.5) {
      return 'hero';
    }

    // Medium square-ish = product or team
    if (w > 200 && h > 200 && Math.abs(w - h) < w * 0.3) {
      return 'product';
    }

    return 'other';
  }

  // Process <img> elements
  for (const img of rawImages) {
    const src = img.src || '';
    if (shouldFilter(src)) continue;
    if (img.width < 50 && img.height < 50 && img.width > 0 && img.height > 0) continue;
    if (seenUrls.has(src)) continue;
    seenUrls.add(src);

    const category = categorize(src, img.alt, img.width, img.height);
    // Use a rough Y estimate: we don't have per-image Y from extraction,
    // so we assign sectionIndex -1 and let position-based logic handle it
    // if we had element positions. For now, use heuristic ordering.
    results.push({
      url: src,
      alt: img.alt || '',
      width: img.width || 0,
      height: img.height || 0,
      category,
      sectionIndex: -1,
    });
  }

  // Process background images
  for (const bg of rawBgImages) {
    const url = extractUrlFromBgImage(bg.backgroundImage);
    if (!url || shouldFilter(url)) continue;
    if (seenUrls.has(url)) continue;
    seenUrls.add(url);

    results.push({
      url,
      alt: '',
      width: 0,
      height: 0,
      category: 'background',
      sectionIndex: -1,
    });
  }

  return results;
}

/**
 * Build an asset context text block for a specific section.
 *
 * Looks up the section archetype in SECTION_CATEGORY_MAP to determine which
 * image categories are relevant. Returns a formatted text block listing
 * available assets and usage instructions.
 *
 * @param {Array} categorizedImages - Output from categorizeImages()
 * @param {string} sectionArchetype - The section archetype (e.g. "HERO", "ABOUT")
 * @param {number} sectionIndex - Index of the section
 * @returns {string} Formatted asset context block, or empty string if no matches
 */
function buildAssetContext(categorizedImages, sectionArchetype, sectionIndex) {
  if (!categorizedImages || categorizedImages.length === 0) return '';

  const archetype = (sectionArchetype || '').toUpperCase();
  const mapping = SECTION_CATEGORY_MAP[archetype] || { primary: ['background'], fallback: ['other'] };

  // Find matching images: try primary categories first, then fallback
  let matchingImages = categorizedImages.filter((img) =>
    mapping.primary.includes(img.category)
  );

  if (matchingImages.length === 0) {
    matchingImages = categorizedImages.filter((img) =>
      mapping.fallback.includes(img.category)
    );
  }

  if (matchingImages.length === 0) return '';

  // Prefer higher-resolution images when multiple match
  matchingImages.sort((a, b) => (b.width * b.height) - (a.width * a.height));

  const lines = [];
  lines.push(`## Available Assets for This Section (${archetype})`);
  lines.push('');
  lines.push('### Images');

  for (let i = 0; i < matchingImages.length; i++) {
    const img = matchingImages[i];
    const { localPath } = buildLocalPath(img.url);
    const dims = img.width && img.height ? ` (${img.width}x${img.height})` : '';
    lines.push(`${i + 1}. ${localPath}${dims}`);
    if (img.alt) {
      lines.push(`   Alt: "${img.alt}"`);
    }
  }

  lines.push('');
  lines.push('### Instructions');
  lines.push('- Use these local asset paths in your component (they will exist at build time)');
  lines.push('- For images: use CSS backgroundImage with role="img" and aria-label');
  lines.push('- If no assets are listed above, use a gradient placeholder with descriptive aria-label');

  return lines.join('\n');
}

/**
 * Build asset contexts for all sections.
 *
 * Calls categorizeImages once, then buildAssetContext for each section.
 *
 * @param {object} extractionData - Full extraction result from extractReference()
 * @param {Array<{ archetype: string, variant: string, content: object }>} sections - Mapped sections
 * @returns {object} Map of section index to { assetContext: string, downloadManifest: Array }
 */
function buildAllAssetContexts(extractionData, sections) {
  const categorized = categorizeImages(extractionData);
  const result = {};

  for (let i = 0; i < sections.length; i++) {
    const section = sections[i];
    const assetContext = buildAssetContext(categorized, section.archetype, i);

    // Build per-section download manifest from the images that matched
    const archetype = (section.archetype || '').toUpperCase();
    const mapping = SECTION_CATEGORY_MAP[archetype] || { primary: ['background'], fallback: ['other'] };
    const allCategories = [...mapping.primary, ...mapping.fallback];
    const sectionImages = categorized.filter((img) => allCategories.includes(img.category));

    const downloadManifest = sectionImages.map((img) => {
      const { localPath } = buildLocalPath(img.url);
      return {
        url: img.url,
        localPath,
        category: img.category,
      };
    });

    result[i] = {
      assetContext,
      downloadManifest,
    };
  }

  return result;
}

/**
 * Get a download manifest for all categorized images.
 *
 * @param {Array} categorizedImages - Output from categorizeImages()
 * @returns {Array<{ url: string, localPath: string, category: string }>}
 */
function getDownloadManifest(categorizedImages) {
  if (!categorizedImages) return [];

  return categorizedImages.map((img) => {
    const { localPath } = buildLocalPath(img.url);
    return {
      url: img.url,
      localPath,
      category: img.category,
    };
  });
}

module.exports = {
  categorizeImages,
  buildAssetContext,
  buildAllAssetContexts,
  getDownloadManifest,
};

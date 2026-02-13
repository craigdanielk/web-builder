/**
 * @fileoverview Semantic icon mapping from extracted icon names and section
 * archetypes to Lucide React icon component names. Used by the pipeline to
 * inject icon context into section prompts and ban emoji in favor of Lucide.
 * @module quality/lib/icon-mapper
 */

'use strict';

// ---------------------------------------------------------------------------
// SEMANTIC_ICON_MAP — concept keywords → Lucide React icon names
// ---------------------------------------------------------------------------

/** @type {Record<string, string>} */
const SEMANTIC_ICON_MAP = {
  // Performance / Speed
  performance: 'Zap',
  speed: 'Gauge',
  fast: 'Zap',
  lightning: 'Zap',
  accelerate: 'Zap',
  quick: 'Gauge',
  efficient: 'Gauge',
  optimize: 'Settings',

  // Security
  security: 'Shield',
  lock: 'Lock',
  safe: 'ShieldCheck',
  protect: 'Shield',
  encrypt: 'Lock',
  privacy: 'Eye',
  guard: 'Shield',
  firewall: 'Shield',

  // Global / World
  global: 'Globe',
  world: 'Globe',
  international: 'Globe',
  worldwide: 'Globe',
  earth: 'Globe',
  network: 'Network',

  // Community / Users
  community: 'Users',
  team: 'Users',
  people: 'Users',
  developer: 'Code',
  group: 'Users',
  collaborate: 'Users',
  social: 'MessageCircle',

  // Documents / Content
  docs: 'BookOpen',
  documentation: 'BookOpen',
  guide: 'BookOpen',
  learn: 'GraduationCap',
  tutorial: 'BookOpen',
  article: 'FileText',
  blog: 'Newspaper',

  // Communication
  email: 'Mail',
  phone: 'Phone',
  chat: 'MessageCircle',
  message: 'MessageSquare',
  contact: 'Mail',
  send: 'Send',
  reply: 'Reply',

  // Navigation
  next: 'ArrowRight',
  previous: 'ArrowLeft',
  expand: 'ChevronDown',
  menu: 'Menu',
  search: 'Search',
  filter: 'Filter',
  sort: 'ArrowUpDown',

  // Media
  video: 'Play',
  audio: 'Volume2',
  image: 'Image',
  camera: 'Camera',
  music: 'Music',
  mic: 'Mic',
  podcast: 'Radio',

  // Commerce
  cart: 'ShoppingCart',
  buy: 'CreditCard',
  price: 'DollarSign',
  payment: 'Wallet',
  order: 'Package',
  shipping: 'Truck',
  store: 'Store',

  // Data
  chart: 'BarChart3',
  analytics: 'TrendingUp',
  data: 'Database',
  report: 'FileBarChart',
  metric: 'Activity',
  stats: 'PieChart',
  growth: 'TrendingUp',

  // Design
  design: 'Palette',
  color: 'Paintbrush',
  layout: 'Layout',
  grid: 'Grid3x3',
  responsive: 'Smartphone',
  theme: 'Sun',

  // Development
  code: 'Code',
  api: 'Webhook',
  deploy: 'Rocket',
  build: 'Hammer',
  test: 'FlaskConical',
  debug: 'Bug',
  terminal: 'Terminal',
  git: 'GitBranch',

  // Time
  time: 'Clock',
  calendar: 'Calendar',
  schedule: 'CalendarDays',
  deadline: 'Timer',
  history: 'History',
  update: 'RefreshCw',

  // Location
  location: 'MapPin',
  map: 'Map',
  address: 'MapPin',
  directions: 'Navigation',
  gps: 'Compass',

  // Status
  success: 'CheckCircle',
  error: 'XCircle',
  warning: 'AlertTriangle',
  info: 'Info',
  new: 'Sparkles',
  popular: 'Star',
  verified: 'BadgeCheck',

  // Features
  feature: 'Star',
  plugin: 'Plug',
  extension: 'Puzzle',
  tool: 'Wrench',
  setting: 'Settings',
  config: 'Sliders',
  customize: 'Palette',

  // Misc
  download: 'Download',
  upload: 'Upload',
  share: 'Share2',
  bookmark: 'Bookmark',
  heart: 'Heart',
  like: 'ThumbsUp',
  award: 'Award',
  trophy: 'Trophy',
  target: 'Target',
  infinity: 'Infinity',
  crown: 'Crown',
  check: 'Check',
  x: 'X',
  layers: 'Layers',
  cpu: 'Cpu',
  eye: 'Eye',
  sparkles: 'Sparkles',
  rocket: 'Rocket',
};

// ---------------------------------------------------------------------------
// ARCHETYPE_ICON_DEFAULTS — section archetype → default Lucide icons
// ---------------------------------------------------------------------------

/** @type {Record<string, string[]>} */
const ARCHETYPE_ICON_DEFAULTS = {
  FEATURES: ['Zap', 'Shield', 'Globe', 'Users', 'Code', 'Gauge', 'Lock', 'Layers', 'Cpu', 'Rocket', 'Eye', 'Sparkles'],
  PRICING: ['Check', 'X', 'Star', 'Crown', 'Infinity', 'BadgeCheck', 'CircleDot', 'Minus'],
  'HOW-IT-WORKS': ['CircleDot', 'ArrowRight', 'ChevronDown', 'Play', 'Lightbulb', 'Settings'],
  TRUST: ['Award', 'BadgeCheck', 'ShieldCheck', 'Trophy', 'ThumbsUp', 'Star'],
  'SOCIAL-PROOF': ['Award', 'BadgeCheck', 'ShieldCheck', 'Trophy', 'Quote', 'Star'],
  STATS: ['TrendingUp', 'BarChart3', 'Activity', 'Target', 'Percent', 'Hash'],
  CONTACT: ['Mail', 'Phone', 'MapPin', 'Clock', 'MessageCircle', 'Send'],
  FAQ: ['HelpCircle', 'MessageSquare', 'ChevronDown', 'Search', 'BookOpen', 'Info'],
  CTA: ['ArrowRight', 'Rocket', 'Sparkles', 'Send', 'ChevronRight', 'ExternalLink'],
  ABOUT: ['Users', 'Heart', 'Target', 'Lightbulb', 'Award', 'Calendar'],
  HERO: ['ArrowRight', 'Play', 'ChevronDown', 'Sparkles'],
  NAV: ['Menu', 'Search', 'User', 'ShoppingCart'],
  FOOTER: ['Mail', 'Phone', 'MapPin', 'ExternalLink'],
  'PRODUCT-SHOWCASE': ['Star', 'Eye', 'Sparkles', 'Zap', 'Code', 'Palette'],
  GALLERY: ['Image', 'Eye', 'Maximize', 'ChevronLeft', 'ChevronRight'],
  TESTIMONIALS: ['Quote', 'Star', 'ThumbsUp', 'MessageCircle', 'Heart'],
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Look up a single token (word) in SEMANTIC_ICON_MAP (case-insensitive).
 * @param {string} token - Single word, e.g. "shield" or "lock"
 * @returns {string | undefined} Lucide icon name or undefined
 */
function lookupToken(token) {
  if (!token || typeof token !== 'string') return undefined;
  const key = token.toLowerCase().replace(/\s+/g, '');
  return SEMANTIC_ICON_MAP[key];
}

/**
 * Map a single extracted icon name to a Lucide icon (full match, then word-by-word).
 * @param {string} extractedName - Raw name from extraction, e.g. "shield-check" or "lock icon"
 * @returns {string | undefined} Lucide icon name or undefined
 */
function mapOneExtractedIcon(extractedName) {
  if (!extractedName || typeof extractedName !== 'string') return undefined;
  const normalized = extractedName.trim().toLowerCase().replace(/[\s_-]+/g, ' ');
  const fullKey = normalized.replace(/\s/g, '');
  if (SEMANTIC_ICON_MAP[fullKey]) return SEMANTIC_ICON_MAP[fullKey];
  const words = normalized.split(/\s+/).filter(Boolean);
  for (const word of words) {
    const icon = lookupToken(word);
    if (icon) return icon;
  }
  return undefined;
}

// ---------------------------------------------------------------------------
// mapExtractedIcons
// ---------------------------------------------------------------------------

/**
 * Maps extracted icon name strings to Lucide React icon names using
 * SEMANTIC_ICON_MAP. Tries full match (normalized) then word-by-word.
 * If no icons map, falls back to ARCHETYPE_ICON_DEFAULTS for the given archetype.
 *
 * @param {string[]} extractedIcons - Array of raw icon names from extraction
 * @param {string} sectionArchetype - Section archetype (e.g. FEATURES, PRICING)
 * @returns {string[]} Array of Lucide icon names (deduplicated, order preserved)
 */
function mapExtractedIcons(extractedIcons, sectionArchetype) {
  const seen = new Set();
  const result = [];
  if (Array.isArray(extractedIcons)) {
    for (const name of extractedIcons) {
      const icon = mapOneExtractedIcon(name);
      if (icon && !seen.has(icon)) {
        seen.add(icon);
        result.push(icon);
      }
    }
  }
  if (result.length > 0) return result;
  const defaults = ARCHETYPE_ICON_DEFAULTS[sectionArchetype];
  return Array.isArray(defaults) ? [...defaults] : ARCHETYPE_ICON_DEFAULTS.FEATURES;
}

// ---------------------------------------------------------------------------
// getIconsForSection
// ---------------------------------------------------------------------------

const MIN_ICONS = 4;

/**
 * Returns the list of Lucide icon names to use for a section. If extracted
 * icons are provided and non-empty, maps them via mapExtractedIcons.
 * Otherwise returns a slice of ARCHETYPE_ICON_DEFAULTS for the archetype,
 * offset by sectionIndex to avoid repetition across sections of the same type.
 * Always returns at least MIN_ICONS (4) icon names; pads with defaults if needed.
 *
 * @param {string} archetype - Section archetype (e.g. FEATURES, PRICING)
 * @param {number} sectionIndex - Zero-based section index (used to offset default slice)
 * @param {string[]} [extractedIcons] - Optional array of extracted icon names
 * @returns {string[]} At least 4 Lucide icon names
 */
function getIconsForSection(archetype, sectionIndex, extractedIcons) {
  const defaults = ARCHETYPE_ICON_DEFAULTS[archetype] || ARCHETYPE_ICON_DEFAULTS.FEATURES;
  let icons;
  if (Array.isArray(extractedIcons) && extractedIcons.length > 0) {
    icons = mapExtractedIcons(extractedIcons, archetype);
  } else {
    const offset = Math.max(0, sectionIndex) % Math.max(1, defaults.length);
    icons = defaults.slice(offset).concat(defaults.slice(0, offset));
  }
  while (icons.length < MIN_ICONS) {
    const pad = defaults.filter((d) => !icons.includes(d));
    const source = pad.length > 0 ? pad : defaults;
    icons.push(source[icons.length % source.length]);
  }
  return icons;
}

// ---------------------------------------------------------------------------
// buildIconContextBlock
// ---------------------------------------------------------------------------

/**
 * Builds the icon context block string for inclusion in section prompts.
 * Instructs the model to use the given Lucide icons and never use emoji.
 *
 * @param {string} archetype - Section archetype
 * @param {number} sectionIndex - Zero-based section index
 * @param {string[]} [extractedIcons] - Optional extracted icon names
 * @returns {string} Formatted prompt block
 */
function buildIconContextBlock(archetype, sectionIndex, extractedIcons) {
  const icons = getIconsForSection(archetype, sectionIndex, extractedIcons);
  const list = icons.join(', ');
  return [
    '═══ ICON CONTEXT ═══',
    "Use these Lucide React icons for this section (import from 'lucide-react'):",
    `Available icons: ${list}`,
    "Example: import { Zap, Shield, Globe } from 'lucide-react';",
    'Render as: <Zap className="w-6 h-6 text-green-500" />',
    'NEVER use emoji — always use these Lucide components.',
    '═══════════════════',
  ].join('\n');
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

module.exports = {
  mapExtractedIcons,
  getIconsForSection,
  buildIconContextBlock,
  SEMANTIC_ICON_MAP,
  ARCHETYPE_ICON_DEFAULTS,
};

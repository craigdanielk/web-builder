/**
 * Aurelix Commerce Contract v1.0
 *
 * Canonical type definitions for commerce data flowing between modules.
 * This file serves two purposes:
 *
 * 1. REFERENCE — Section generation prompts cite these types when generating
 *    prop-driven commerce sections. The Web Builder (Module 2) reads this
 *    to know the shape of data that commerce sections must accept.
 *
 * 2. RUNTIME — stage_deploy copies this into each generated site at
 *    src/types/commerce.ts so the built project has the actual TypeScript types.
 *
 * Types mirror Shopify's Storefront API (2024-01 version).
 * Reference: Vercel Next.js Commerce (lib/shopify/types.ts)
 *
 * DO NOT add visual/style types here — those live in style-schema.md.
 * DO NOT add animation types here — those live in animation-patterns.md.
 * DO NOT add pipeline/build types here — those are internal to orchestrate.py.
 */

// ─────────────────────────────────────────────────────────────
// CORE SHOPIFY TYPES (Storefront API)
// ─────────────────────────────────────────────────────────────

export interface Money {
  amount: string;
  currencyCode: string;
}

export interface Image {
  url: string;
  altText: string;
  width: number;
  height: number;
}

export interface SEO {
  title: string;
  description: string;
}

export interface ShopifyProduct {
  handle: string;
  title: string;
  description: string;
  descriptionHtml: string;
  priceRange: {
    minVariantPrice: Money;
    maxVariantPrice: Money;
  };
  featuredImage: Image;
  images: Image[];
  variants: ShopifyVariant[];
  tags: string[];
  availableForSale: boolean;
  seo: SEO;
}

export interface ShopifyVariant {
  id: string;
  title: string;
  availableForSale: boolean;
  price: Money;
  compareAtPrice?: Money;
  selectedOptions: Array<{
    name: string;
    value: string;
  }>;
  image?: Image;
}

export interface ShopifyCollection {
  handle: string;
  title: string;
  description: string;
  image?: Image;
  seo: SEO;
  products?: ShopifyProduct[];
}

export interface ShopifyCart {
  id: string;
  checkoutUrl: string;
  totalQuantity: number;
  cost: {
    subtotalAmount: Money;
    totalAmount: Money;
    totalTaxAmount?: Money;
  };
  lines: ShopifyCartLine[];
}

export interface ShopifyCartLine {
  id: string;
  quantity: number;
  merchandise: {
    id: string;
    title: string;
    selectedOptions: Array<{ name: string; value: string }>;
    product: ShopifyProduct;
  };
  cost: {
    totalAmount: Money;
  };
}

export interface ShopifyMenu {
  title: string;
  items: ShopifyMenuItem[];
}

export interface ShopifyMenuItem {
  title: string;
  url: string;
  items?: ShopifyMenuItem[];
}

// ─────────────────────────────────────────────────────────────
// SECTION PROP CONTRACTS
// ─────────────────────────────────────────────────────────────
//
// These interfaces define the data contract between the Web Builder
// (which generates the visual components) and Module 3 (which passes
// real Shopify data into them).
//
// Rule: If a section's data mode is 'prop-driven' or 'hybrid',
// it MUST accept one of these prop interfaces.
// ─────────────────────────────────────────────────────────────

/** Collection page — product grid with filters */
export interface ProductGridProps {
  products: ShopifyProduct[];
  collection: ShopifyCollection;
}

/** Product detail page — single product with related */
export interface ProductDetailProps {
  product: ShopifyProduct;
  relatedProducts?: ShopifyProduct[];
}

/** Homepage or landing page — featured products widget */
export interface FeaturedProductsProps {
  products: ShopifyProduct[];
  heading?: string;
  subheading?: string;
}

/** Collection page hero — collection metadata display */
export interface CollectionHeroProps {
  collection: ShopifyCollection;
}

/** Navigation — dynamic menu from Shopify */
export interface NavigationProps {
  menu: ShopifyMenu;
  logo?: Image;
}

/** Footer — dynamic footer menu + optional newsletter */
export interface FooterProps {
  menu: ShopifyMenu;
  socialLinks?: Array<{ platform: string; url: string }>;
}

// ─────────────────────────────────────────────────────────────
// SECTION DATA MODE CLASSIFICATION
// ─────────────────────────────────────────────────────────────
//
// Determines how the section generation prompt handles each archetype:
//
// 'static'      — Self-contained. Hardcoded content. No props needed.
//                  Section generation prompt: generate as today (unchanged).
//
// 'prop-driven' — Receives commerce data via props. No hardcoded content
//                  for the data fields. Must import types from this file.
//                  Section generation prompt: "accept [XProps], render from props,
//                  include empty-state handling."
//
// 'hybrid'      — Receives optional props. Works standalone with fallback
//                  content, but can be enhanced with real data when available.
//                  Section generation prompt: "accept optional [XProps],
//                  provide sensible defaults/fallbacks."
// ─────────────────────────────────────────────────────────────

export type SectionDataMode = 'static' | 'prop-driven' | 'hybrid';

/**
 * Maps section archetypes to their data mode.
 *
 * The data mode is CONTEXT-DEPENDENT — the same archetype can be static on
 * one page type and prop-driven on another. This map defines the DEFAULT mode.
 * Page templates can override per-section when the context demands it.
 *
 * Example: PRODUCT-SHOWCASE is always prop-driven on collection/product pages,
 * but on a homepage it could be hybrid (featured products with fallback).
 */
export const SECTION_DATA_MODES: Record<string, SectionDataMode> = {
  // ── Always static ──────────────────────────────────────────
  'HERO':              'static',
  'ABOUT':             'static',
  'TESTIMONIALS':      'static',
  'CTA':               'static',
  'FAQ':               'static',
  'CONTACT':           'static',
  'STATS':             'static',
  'HOW-IT-WORKS':      'static',
  'NEWSLETTER':        'static',
  'VIDEO':             'static',
  'GALLERY':           'static',
  'TEAM':              'static',
  'TRUST-BADGES':      'static',
  'COMPARISON':        'static',
  'BLOG-PREVIEW':      'static',
  'ANNOUNCEMENT-BAR':  'static',
  'APP-DOWNLOAD':      'static',
  'INTEGRATIONS':      'static',
  'PORTFOLIO':         'static',

  // ── Always prop-driven (commerce data required) ────────────
  'PRODUCT-SHOWCASE':  'prop-driven',   // → ProductGridProps | ProductDetailProps
  'PRICING':           'prop-driven',   // → product variants/pricing from API

  // ── Context-dependent (hybrid) ─────────────────────────────
  'NAV':               'hybrid',        // → optional NavigationProps (static fallback links)
  'FOOTER':            'hybrid',        // → optional FooterProps (static fallback links)
  'LOGO-BAR':          'hybrid',        // → static brand logos OR dynamic vendor list
  'FEATURES':          'hybrid',        // → static on homepage, product features on PDP
};

/**
 * Maps prop-driven section archetypes to their prop interface.
 * Used by the section generation prompt to know which types to import.
 */
export const SECTION_PROP_MAP: Record<string, string> = {
  'PRODUCT-SHOWCASE': 'ProductGridProps | ProductDetailProps',
  'PRICING':          'ProductDetailProps',
  'NAV':              'NavigationProps',
  'FOOTER':           'FooterProps',
  'LOGO-BAR':         'FeaturedProductsProps',
  'FEATURES':         'FeaturedProductsProps',
};

// ─────────────────────────────────────────────────────────────
// PAGE TEMPLATE DATA REQUIREMENTS
// ─────────────────────────────────────────────────────────────
//
// Declares which Shopify data entities each page template type requires.
// The Calculator (Module 1) uses this to validate data availability.
// Module 3 uses this to know what Storefront API queries to wire up.
// ─────────────────────────────────────────────────────────────

export type PageIntent =
  | 'index'       // Homepage
  | 'collection'  // Collection / category page
  | 'product'     // Product detail page
  | 'landing'     // Campaign or custom landing page
  | 'about'       // Brand story / about page
  | 'contact'     // Contact form + info
  | 'legal'       // Privacy, terms, shipping policy
  | 'blog'        // Blog listing page
  | 'article';    // Single blog article

export type RequiredData =
  | 'product'
  | 'products'
  | 'collection'
  | 'collections'
  | 'relatedProducts'
  | 'menu'
  | 'cart'
  | 'blog'
  | 'article';

export interface PageTemplateMetadata {
  intent: PageIntent;
  requiredData: RequiredData[];
  routePattern: string;
  dynamic: boolean;
}

/**
 * Page template data requirements.
 *
 * Static pages (requiredData: []) → Web Builder generates fully, no Module 3 wiring needed.
 * Dynamic pages (dynamic: true) → Web Builder generates 1 template, Next.js dynamic routes handle N instances.
 * Pages with requiredData → Module 3 must wire Storefront API queries for these data entities.
 */
export const PAGE_TEMPLATES: Record<PageIntent, PageTemplateMetadata> = {
  index: {
    intent: 'index',
    requiredData: [],
    routePattern: '/',
    dynamic: false,
  },
  collection: {
    intent: 'collection',
    requiredData: ['collection', 'products'],
    routePattern: '/collections/[handle]',
    dynamic: true,
  },
  product: {
    intent: 'product',
    requiredData: ['product', 'relatedProducts'],
    routePattern: '/products/[handle]',
    dynamic: true,
  },
  landing: {
    intent: 'landing',
    requiredData: [],
    routePattern: '/pages/[handle]',
    dynamic: false,  // each landing page is individually generated
  },
  about: {
    intent: 'about',
    requiredData: [],
    routePattern: '/about',
    dynamic: false,
  },
  contact: {
    intent: 'contact',
    requiredData: [],
    routePattern: '/contact',
    dynamic: false,
  },
  legal: {
    intent: 'legal',
    requiredData: [],
    routePattern: '/pages/[handle]',
    dynamic: false,
  },
  blog: {
    intent: 'blog',
    requiredData: ['blog'],
    routePattern: '/blog',
    dynamic: false,
  },
  article: {
    intent: 'article',
    requiredData: ['article'],
    routePattern: '/blog/[handle]',
    dynamic: true,
  },
};

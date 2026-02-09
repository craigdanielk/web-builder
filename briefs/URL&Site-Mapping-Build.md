# Site Discovery & Migration Mapping Engine — Build Plan

**Status:** Planned (future upgrade)
**Depends on:** `scripts/quality/` toolset (completed 2026-02-08)
**Target location:** `scripts/discovery/`

---

## Overview

Full-site discovery, classification, and migration mapping engine. Given a starting
domain, automatically discovers all publicly reachable URLs, classifies each by page
intent, fingerprints layout variants, and produces a machine-readable migration routing
map suitable for a custom frontend backed by Shopify data and CDN.

Designed for e-commerce migration (100K+ URLs, multi-language, mixed content + commerce).

**This system complements the existing URL Clone Mode (`--from-url`) which handles
single-page visual reproduction. The discovery engine handles full-site information
architecture mapping.**

---

## Relationship to Existing Tools

### What Already Exists (can piggyback)

| Existing Module | Reuse For | Adaptation Needed |
|----------------|-----------|-------------------|
| `lib/extract-reference.js` | Per-page DOM extraction, text capture, section ID | Add `mode: 'light'` — skip screenshots/scroll for speed at scale |
| `lib/archetype-mapper.js` | Classification heuristic pattern (tag, role, keywords) | Extend from section-level to page-level intent taxonomy |
| `lib/design-tokens.js` | Layout consolidation report (pages sharing visual treatment) | Minor — use `collectTokens()` to compare pages |
| `lib/section-context.js` | DOM structure capture for fingerprinting | Formalize into deterministic hash instead of text block |
| Playwright browser context | Headless browsing for crawling | Reuse launch/context config, add queue-based architecture |

### What's Net-New (must be built)

7 new modules organized into pipeline stages.

---

## Pipeline Architecture

```
Domain
  |
[Stage 1: Crawler] --> Canonical Page Inventory (JSON)
  |
[Stage 2: Page Classifier] --> Intent Classification (JSON)
  |
[Stage 3: Layout Fingerprinter] --> DOM Fingerprints (JSON)
  |
[Stage 4: Layout Clusterer] --> Cluster Assignments (JSON)
  |
[Stage 5: Routing Mapper] --> Migration Routing Map (JSON/CSV)
  |
[Stage 6: Consolidation Reporter] --> Layout Report (Markdown)
  |
[Stage 7: Orchestration Layer] --> n8n-compatible webhooks/CLI
```

---

## Stage 1: Multi-Page Crawler — `lib/crawler.js`

**Status:** Net-new
**Reuses:** Playwright browser context from `extract-reference.js`

### Responsibilities
- Sitemap XML parsing (`/sitemap.xml`, `/sitemap_index.xml`, nested sitemaps)
- BFS crawl via internal link following with depth tracking
- Redirect chain resolution (301/302, up to 10 hops)
- Canonical tag detection and URL deduplication
- robots.txt respect
- Rate limiting (configurable requests/sec) and retry logic (3 retries, exponential backoff)
- Soft-404 detection (200 status but thin/error content — word count < 50, boilerplate ratio > 0.8)
- Incremental re-crawl capability (store last-crawl timestamps, skip unchanged pages)

### Output Schema: Canonical Page Inventory

```json
{
  "source_url": "https://example.com/products/blue-widget",
  "final_url_after_redirects": "https://example.com/products/blue-widget",
  "http_status": 200,
  "canonical_url": "https://example.com/products/blue-widget",
  "inlink_count": 14,
  "crawl_depth": 2,
  "indexable_flag": true,
  "title": "Blue Widget - Example Store",
  "word_count": 842,
  "crawled_at": "2026-02-08T12:00:00Z"
}
```

### Key Design Decisions
- Queue-based BFS with visited set (Map of url to crawlResult)
- Concurrent page limit (default 5 simultaneous Playwright pages)
- Single browser context shared across pages for cookie/session consistency
- Domain-locked: only follow links within the starting domain
- Checkpoint to disk every 100 pages for crash recovery

---

## Stage 2: Page Intent Classifier — `lib/page-classifier.js`

**Status:** Net-new (extends `archetype-mapper.js` pattern)
**Reuses:** Keyword matching heuristic pattern, DOM element detection from extraction

### Page Intent Taxonomy

Every URL classified into exactly one of:

| Intent | Signals |
|--------|---------|
| `product` | Price element, add-to-cart button, variant selector, Product schema.org |
| `collection` | Product grid, filter sidebar, pagination, CollectionPage schema.org |
| `editorial_article` | Long-form text, author byline, publish date, Article schema.org |
| `commercial_landing` | Hero + CTA-heavy, short-form, no commerce components |
| `hub_index` | Link-dense, minimal body content, serves as navigation gateway |
| `static_info` | Legal text, About/Contact, low link density, no commerce |
| `system_ignore` | Login, cart, checkout, search results, 404, thin pages |

### Classification Features (hybrid scoring)
1. **URL pattern features** — `/products/`, `/collections/`, `/blog/`, `/pages/`, `/account/`
2. **DOM structure features** — presence of commerce components (price, add-to-cart, variants, filters, pagination)
3. **Schema.org / JSON-LD** — `@type: Product`, `@type: Article`, `@type: CollectionPage`, etc.
4. **Content density** — word count, image ratio, link density, heading structure
5. **Navigation graph** — is this page in the main nav? In breadcrumbs? In footer?
6. **Commerce component detection** — price regex patterns, button text matching ("Add to Cart", "Buy Now", "Add to Bag")

### Output Schema

```json
{
  "source_url": "https://example.com/products/blue-widget",
  "page_intent": "product",
  "confidence_score": 0.95,
  "classification_features_used": ["url_pattern", "schema_org", "commerce_components"]
}
```

### Design Notes
- Each feature produces a score per intent type
- Weighted sum across features: highest score wins
- Confidence = winning score / sum of all scores
- Schema.org signals get highest weight (0.4) when present
- URL patterns get medium weight (0.25)
- DOM signals fill in when schema/URL are ambiguous
- Platform-agnostic: NO Magento/Woo/Shopify-specific assumptions

---

## Stage 3: Layout Fingerprinter — `lib/layout-fingerprint.js`

**Status:** Net-new (extends DOM walking from `extract-reference.js`)
**Reuses:** TreeWalker pattern from extraction, section identification logic

### Algorithm
1. Extract the DOM tag tree (strip all text content, attributes, and inline styles)
2. Normalize: collapse consecutive identical siblings, strip data-* attributes
3. Keep only structural tags: html, body, header, nav, main, section, article, aside, footer, div, ul, ol, form, table
4. Build a structural signature string: `body>header>nav+main>section*3>article+aside>footer`
5. Hash the signature (SHA-256 truncated to 12 chars) = `layout_signature_id`
6. Capture layout features alongside: column count, has-sidebar, has-hero, has-grid, etc.

### Output Schema

```json
{
  "source_url": "https://example.com/products/blue-widget",
  "layout_signature_id": "a7f3b2c91d4e",
  "layout_features": {
    "has_sidebar": false,
    "has_hero": true,
    "has_product_grid": false,
    "column_count": 1,
    "section_count": 7,
    "has_form": false
  },
  "dom_fingerprint_hash": "a7f3b2c91d4e"
}
```

### Properties
- **Stable across content changes:** Same template with different product data = same hash
- **Sensitive to structural differences:** 2-column vs 1-column layout = different hash
- **Robust to minor markup noise:** Extra wrapper divs collapsed by normalization

---

## Stage 4: Layout Clusterer — `lib/layout-clusterer.js`

**Status:** Net-new
**Reuses:** Nothing directly (pure algorithm)

### Algorithm
1. Group pages by `page_intent` (only cluster within the same intent)
2. Within each intent group, group by exact `layout_signature_id` match
3. For near-matches (Jaccard similarity of layout features > 0.85), merge clusters
4. Assign cluster IDs: `{intent}_{cluster_index}` (e.g., `product_0`, `product_1`)
5. Flag outlier layouts (clusters with < 3 pages) for manual review

### Output
- Cluster assignments per page
- Cluster summary: cluster_id, page_count, representative_url, layout_features

---

## Stage 5: Migration Routing Mapper — `lib/routing-mapper.js`

**Status:** Net-new
**Reuses:** Nothing directly (business logic)

### Mapping Rules

| Page Intent | Target Route Type | Handle Extraction |
|-------------|-------------------|-------------------|
| `product` | `product_route` | Last URL segment (slug) |
| `collection` | `collection_route` | Last URL segment |
| `editorial_article` | `content_route` | Full path after `/blog/` or similar |
| `commercial_landing` | `landing_route` | Full path |
| `hub_index` | `hub_route` | Path segment |
| `static_info` | `static_route` | Path segment |
| `system_ignore` | (excluded) | n/a |

### Output Schema

```json
{
  "source_url": "https://example.com/products/blue-widget",
  "page_intent": "product",
  "layout_signature_id": "a7f3b2c91d4e",
  "target_route_type": "product_route",
  "target_route_handle": "blue-widget",
  "redirect_required": false,
  "redirect_target": null
}
```

### Redirect Logic
- If `source_url !== canonical_url` then redirect required, target = canonical
- If page is `system_ignore` but has inlink_count > 5 then redirect to parent hub
- If multiple source URLs resolve to the same canonical then collapse, redirect extras
- Redirect chains > 2 hops get flattened to final destination

---

## Stage 6: Consolidation Reporter — `lib/consolidation-reporter.js`

**Status:** Net-new (extends enrichment report pattern from `enrich-preset.js`)
**Reuses:** Report generation pattern

### Output (Markdown)
- Layout variants per intent (e.g., "product has 3 layout variants across 2,450 pages")
- Consolidation recommendations ("product_1 (12 pages) can merge into product_0")
- Distinct component requirements ("collection has 2 different layouts: grid vs list")
- Visual token comparison across layouts (reuses `collectTokens()` from `design-tokens.js`)

---

## Stage 7: n8n Orchestration Layer — `discover-site.js`

**Status:** Net-new
**Reuses:** CLI pattern from existing quality tools

### CLI Interface

```bash
node discover-site.js <domain> [options]

Options:
  --output-dir <dir>     Output directory (default: output/discovery/<domain>/)
  --max-pages <n>        Max pages to crawl (default: 10000)
  --concurrency <n>      Simultaneous pages (default: 5)
  --rate-limit <n>       Requests per second (default: 2)
  --resume               Resume from last checkpoint
  --stages <list>        Run specific stages (crawl,classify,fingerprint,cluster,route,report)
  --json                 Output structured JSON to stdout (for n8n webhook consumption)
```

### n8n Compatibility
- Each stage reads JSON input, writes JSON output
- Stages can run independently via `--stages` flag
- Exit codes: 0 = success, 1 = partial failure (some pages failed), 2 = fatal
- Progress written to `<output-dir>/progress.json` for polling
- Supports `--resume` for crash recovery mid-crawl

---

## Data Flow Between Stages

```
crawl-results.json        (Stage 1)
       |
classifications.json      (Stage 2 -- reads crawl-results, adds intent)
       |
fingerprints.json         (Stage 3 -- reads crawl-results, adds layout hash)
       |
clusters.json             (Stage 4 -- reads fingerprints + classifications)
       |
routing-map.json          (Stage 5 -- reads crawl-results + classifications + clusters)
       |
consolidation-report.md   (Stage 6 -- reads everything, produces human report)
```

All intermediate artifacts are JSON files with clear schemas. Any stage can be
re-run independently if its input files exist.

---

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| Crawling | Playwright (headless Chromium) | Already installed, handles JS-rendered pages, reuses existing setup |
| HTTP requests | Node.js http/https + Playwright | Light requests for sitemap/robots.txt, Playwright for rendered DOM |
| Queue | In-memory BFS queue + disk checkpointing | Simple, sufficient for 100K URLs, no external deps |
| Hashing | Node.js crypto (SHA-256) | Built-in, deterministic |
| Clustering | Custom Jaccard similarity | No ML needed for deterministic fingerprints |
| Output | JSON + Markdown | Machine-readable + human-readable |
| Orchestration | CLI flags + JSON stdin/stdout | n8n webhook/exec compatible |

---

## Scale Considerations

| Metric | Target | Strategy |
|--------|--------|----------|
| URLs | 100K+ | Disk-checkpointed queue, stream processing |
| Crawl time | ~14 hours at 2 req/s for 100K | Configurable concurrency + rate limit |
| Memory | < 2GB | Stream results to disk, don't hold full DOM in memory |
| Crash recovery | Resume from last checkpoint | Checkpoint every 100 pages |
| Multi-language | Supported | hreflang detection, language-aware URL grouping |
| Redirect chains | Up to 10 hops | Chain flattening with loop detection |

---

## Build Priority (when ready to implement)

| Priority | Module | Effort | Depends On |
|----------|--------|--------|------------|
| 1 | `lib/crawler.js` | Large (2-3 days) | `extract-reference.js` (Playwright reuse) |
| 2 | `lib/page-classifier.js` | Medium (1 day) | `archetype-mapper.js` (pattern), crawler output |
| 3 | `lib/layout-fingerprint.js` | Medium (1 day) | `extract-reference.js` (DOM walking), crawler output |
| 4 | `lib/layout-clusterer.js` | Small (half day) | fingerprint output |
| 5 | `lib/routing-mapper.js` | Medium (1 day) | classifier + clusterer output |
| 6 | `lib/consolidation-reporter.js` | Small (half day) | all previous stages |
| 7 | `discover-site.js` | Medium (1 day) | all modules |

**Total estimated effort:** 7-8 days of focused development.

---

## Original System Prompt (Reference)

The original Aurelix discovery engine prompt is preserved below for reference.
The build plan above adapts it to the web-builder architecture.

### Core Objectives (from original prompt)

Given a starting domain, the system must:
1. Discover all publicly reachable URLs that represent real pages
2. Classify each URL by page intent, not by legacy CMS template
3. Detect layout / structural variants for each intent
4. Build a deterministic mapping from legacy URLs to new frontend route types
5. Output a complete redirect and routing map suitable for automated deployment

### Explicit Non-Goals
- NOT required to reproduce legacy CMS templates
- NOT required to mirror Shopify theme constraints
- NOT required to reverse-engineer backend models of the source CMS
- IS required to understand: information architecture, user intent, SEO intent, layout intent

### Design Constraint
The system must be capable of processing 100,000+ URLs, multi-language stores,
mixed content + commerce sites, and aggressive redirect chains. Designed as if it
will be productised and sold to agencies performing automated Shopify-backed
migrations with strict SEO-retention requirements.

Focus on correctness, determinism and operational robustness.

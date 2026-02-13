# AURELIX: COMPLETE SYSTEM PLAN & NORTH STAR

## WHAT AURELIX IS

Aurelix is **three composable modules** that chain together through clean file-based interfaces to take a source e-commerce URL and output a live headless Shopify storefront:

```
┌─────────────────────────────────────────────────────┐
│  MODULE 1: CALCULATOR                                │
│  Status: Framework exists, needs generalization      │
│  Input: Source URL or structured store data           │
│  Output: Architecture spec + brief + constraints     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼  (architecture.json + brief.md + products.csv + media-manifest.json)
                       │
┌──────────────────────┴──────────────────────────────┐
│  MODULE 2: WEB BUILDER                               │
│  Status: BUILT, TESTED, PRODUCTION-READY             │
│  Input: Brief + Industry Preset                      │
│  Output: Production Next.js site deployed to Vercel  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼  (deployed Vercel project URL)
                       │
┌──────────────────────┴──────────────────────────────┐
│  MODULE 3: SHOPIFY INTEGRATION LAYER                 │
│  Status: NOT YET BUILT                               │
│  Input: Architecture spec + Vercel project           │
│  Output: Live headless Shopify storefront            │
└─────────────────────────────────────────────────────┘
```

**Critical design principle:** Each module has a single responsibility and communicates through file-based interfaces (JSON specs, markdown briefs). No module needs internal knowledge of another module's implementation. The Calculator does not know about section archetypes. The Web Builder does not know about Shopify collections. The Shopify Integration Layer does not know about Tailwind classes.

### Repository Architecture (5 Independent Repos)

```
aurelix-mvp/              → Web Builder (Node.js + Python orchestrator) — THIS REPO
aurelix-calculator/       → Calculator (Python) — crawls sites, outputs architecture.json + brief.md
site-mapper repo          → Calculates required pages, templates, navigation, collections
url-mapper repo           → Maps source URLs → Shopify URLs, multi-market, imports redirects
bulk-graphql-importer repo → Imports 50k products into Shopify in ~120 minutes
```

**Integration pattern:** Each tool exposes a CLI interface. The pipeline orchestrator calls them sequentially via subprocess. Artifacts pass between them as files on disk (JSON, CSV, markdown) in a shared `output/{project}/` directory. This is the permanent architecture, not a temporary arrangement.

---

## MODULE 1: CALCULATOR

### Purpose
Analyze a source website or structured data export and output a deterministic architecture specification that defines what needs to be built, how it should be structured, and what content populates it.

### Current State
- Framework exists from the Turm Kaffee case study (`aurelix_calculator_real.py`)
- Proven on one project (265 products, 3 markets, 6 collections, 19 landing pages)
- Not generalized — hardcoded to Turm's CSV format and Magento structure
- URL crawling and page classification logic validated (379 URLs, 86% classification accuracy)
- Navigation extraction validated (60-item hierarchical menu)

### What the Calculator Outputs (4 Artifacts)

**Artifact 1: `architecture.json`** — The complete store blueprint (primary output)
```json
{
  "project_id": "turm-kaffee",
  "source_url": "https://shop.turmkaffee.ch",
  "source_platform": "magento",
  "collections": [
    {
      "handle": "kaffee",
      "title": "Kaffee",
      "type": "main_collection",
      "product_count": 120,
      "smart_rules": [{ "field": "tag", "condition": "equals", "value": "tag:collection:kaffee" }]
    }
  ],
  "pages": [
    {
      "handle": "kaffee-bohnen",
      "title": "Kaffeebohnen",
      "type": "landing_page",
      "template": "collection_landing",
      "sections": ["hero", "collection_grid", "featured_products", "brand_story"]
    }
  ],
  "navigation": { "main_menu": [...], "footer_menu": [...] },
  "markets": [
    { "code": "CH", "currency": "CHF", "domain_prefix": "/ch/" },
    { "code": "AT", "currency": "EUR", "domain_prefix": "/at/" },
    { "code": "DE", "currency": "EUR", "domain_prefix": "/de/" }
  ],
  "redirects": [
    { "source": "/kaffee.html", "target": "/ch/collections/kaffee", "type": 301 }
  ]
}
```

**Artifact 2: `brief.md`** — Interface between Calculator and Web Builder
```markdown
# {Project Name}
## Business
{Company name, location, founding year, product focus}
## What They Need
{E-commerce storefront with N collections, N landing pages, multi-market support}
## Key Requirements
{Product categories, navigation structure, hero sections, featured products}
## Target Audience
{Inferred from product data and pricing}
## Brand Personality
{Color palette, typography, imagery style, tone extracted from source}
## Specific Requests
{Derived from source site hero sections, CTAs, visual patterns}
## Technical Notes
{Platform: Shopify headless via Storefront API. Markets. Currency. Product count.}
```

**Artifact 3: `products.csv`** — Shopify-compatible product import CSV

**Artifact 4: `media-manifest.json`** — Complete mapping of all source media URLs
```json
{
  "product_images": [
    { "product_handle": "kenner", "source_url": "https://...", "position": 1, "alt_text": "..." }
  ],
  "hero_images": [
    { "page_handle": "kaffee-bohnen", "source_url": "https://...", "usage": "hero_banner", "dimensions": "1920x600" }
  ],
  "brand_assets": [
    { "type": "logo", "source_url": "https://...", "deployment": "repo_public_dir" }
  ]
}
```

### What Needs Building in Calculator

**PRIORITY 1: URL Mapper & Site Architecture Module** (the critical missing piece)
- Accept any URL as input
- Crawl sitemap.xml and/or follow internal links (depth-limited)
- Classify pages by type (product, category, content, legal, contact)
- Count products per category
- Extract navigation hierarchy
- Extract brand identity signals (colors, fonts, imagery style)
- Determine optimal collection structure
- Platform detection via HTML signatures (wp-content, cdn.shopify.com, etc.)
- Output architecture.json and brief.md

**PRIORITY 2: Product Data Extraction**
- Extract via API when available (Magento GraphQL, Shopify Storefront API)
- Fallback to HTML scraping when API unavailable
- Output Shopify-compatible CSV format
- Handle variants (size, color) where detectable
- Flag incomplete records for manual review

**PRIORITY 3: Media Inventory**
- Discover all product images, category images, hero banners, brand assets
- Classify each by usage type
- Record source URLs, dimensions, alt text
- Map each asset to its destination (Shopify CDN via fileCreate, or repo /public for brand assets)

---

## MODULE 2: WEB BUILDER

### Purpose
Take a brief and industry preset, generate a production-quality Next.js website through a multi-pass pipeline, and deploy it to Vercel.

### Current State: PRODUCTION-READY for visual sites (v1.1.2); commerce page templates pending ✅
- **35 industry presets** covering major verticals
- **25 section archetypes** with 99+ variants
- 7-dimension style schema (color, type, space, radius, motion, density, imagery)
- Compact style header mechanism prevents visual drift across sections
- Dual animation engine: **GSAP 3.14 + ScrollTrigger** (20 plugins detectable) or **Framer Motion 12**
- **1,034-component animation library** with machine-usable registry (search index, taxonomy, capability matrix)
- URL clone mode: Playwright extraction → auto-generated preset + brief → build
- **Pattern identification pipeline** (Stage 0d): color intelligence, archetype mapping, animation/UI pattern matching, gap reporting
- Python + Node.js hybrid orchestration (7 stages + injection wiring + pre-flight validation)
- Multi-agent support (Architect, Builder, Reviewer, Fixer roles)
- Automated Vercel deployment with post-deploy verification
- JSX truncation auto-repair (two-layer: generation-time + pre-flight)
- Cost: ~$0.55-1.15 per page in API calls
- Fully isolated builds — 100 agents can build in parallel
- **13 completed builds** deployed to Vercel across diverse industries
- **8 completed engineering plans** (v0.4.0 → v1.1.2)
- Commerce prop contract defined (`skills/commerce-contract.ts`) — Shopify Storefront API types

### Interface Contract
- **Input 1:** `briefs/{project}.md` (Calculator generates this, or human-written)
- **Input 2:** Preset selection (`skills/presets/{preset}.md`)
- **Input 3:** `output/{project}/architecture.json` (optional — Calculator generates this for Shopify migrations)
- **Output:** Deployed Next.js site at `output/{project}/site/`

The Web Builder reads `architecture.json` for: page template count (how many templates to generate), collection structure (for navigation and collection page template design), market configuration (locale-aware routing if needed), and page list (which landing pages to generate). The brief.md is the primary interface; architecture.json provides the structural data the brief references.

The site is a **standalone frontend** — it does NOT contain Shopify API connections, cart logic, or checkout flow. Those are added by Module 3. Commerce sections are generated as **prop-driven components** that accept typed Shopify data (see `skills/commerce-contract.ts`), ready for Module 3 to wire real data without modifying the generated code.

### What Does NOT Need Building in Web Builder
Do not add: Shopify Storefront API client code, cart/checkout logic, product data fetching, collection page routing, Supabase integration, media upload pipelines. These belong in Module 3.

### Parallel Paths: Visual-Only vs. Full Shopify Migration

The Web Builder operates in two modes:

**Visual-only mode** (`--from-url`): Remains as a standalone path for non-Shopify builds. Extracts visual DNA via Playwright, generates preset + brief, builds and deploys a static site. No Calculator needed.

**Shopify migration mode** (brief-driven): The Calculator runs first, generates brief.md + architecture.json, then the Web Builder runs in standard brief-driven mode. The Calculator wraps the existing extraction pipeline — it calls it for brand identity extraction (colors, fonts, imagery) while adding page structure analysis on top.

### Multi-Page Generation

The Web Builder generates a **template set** per store (5-8 page templates), not individual pages per product:

| Page Type | Generation | Route | Data Model |
|-----------|-----------|-------|------------|
| Homepage | Static, self-contained | `/` | Hardcoded content |
| About | Static, self-contained | `/about` | Hardcoded content |
| Contact | Static, self-contained | `/contact` | Hardcoded content |
| Landing pages | Static, individually generated | `/pages/[handle]` | Hardcoded per-page |
| Legal pages | Static, self-contained | `/pages/[handle]` | Hardcoded content |
| Collection page | Prop-driven visual shell | `/collections/[handle]` | `collection`, `products[]` from Storefront API |
| Product page | Prop-driven visual shell | `/products/[handle]` | `product`, `variants[]`, `relatedProducts` from Storefront API |
| Cart | Module 3 pre-built component | Cart drawer or `/cart` | Storefront Cart API |

Static pages are generated fully by the Web Builder. Commerce pages (collection, product) are generated as visual shells with prop-driven sections — Module 3 owns the data layer. Cart is entirely Module 3's responsibility (pre-built component inheriting design tokens via Tailwind/CSS variables).

### Commerce Section Contract

Commerce sections accept typed props matching Shopify's Storefront API. Defined in `skills/commerce-contract.ts`:

- **Static sections** (Hero, About, CTA, FAQ, etc.) — self-contained, hardcoded content
- **Prop-driven sections** (ProductGrid, ProductDetail, CollectionHero) — accept typed Shopify data via props
- **Hybrid sections** (Nav, Footer, FeaturedProducts) — work standalone with fallback content, enhanced with real data when available

### Current Work: Pipeline Maturation Complete — Page Templates Next
The Web Builder's visual pipeline (v1.1.2) is production-ready for single-page static sites. The next step is building page-level preset templates that define section sequences for each page type (homepage, collection, product, landing, about, contact, legal), with sections correctly marked as static or prop-driven using the commerce contract.

---

## MODULE 3: SHOPIFY INTEGRATION LAYER

### Purpose
Take the Calculator's architecture spec and the Web Builder's deployed Vercel project, and wire them together into a live headless Shopify storefront.

### Current State: NOT YET BUILT (architecture fully specified)

### Static → Dynamic Integration (Option D: Hybrid)

The Web Builder generates two kinds of output that Module 3 handles differently:

- **Static pages** (homepage, about, contact, legal, landing): Generated fully by the Web Builder. Module 3 injects a lightweight data fetching layer only for minor dynamic elements (e.g., featured products widget on homepage).
- **Commerce pages** (product detail, collection grid): Use pre-built page templates from Module 3 that contain Storefront API wiring. The Web Builder provides the visual shell — style tokens, color palette, typography, animation preferences, component styling. Module 3 owns the data layer and commerce logic entirely.
- **Cart**: Pre-built by Module 3 (based on Vercel's Next.js Commerce reference). Inherits design tokens via Tailwind/CSS variables from the Web Builder's output.

### Dev Store Strategy

- **Reusable test stores:** For pipeline development and validation (wipe and rebuild repeatedly)
- **Fresh dev stores:** Per client project for actual deliverables (clean slate, transfer to client via Shopify Partner Dashboard)
- The pipeline supports both via an `--existing-store` flag for test stores and default fresh store creation for production use

### Supabase Scope

Stays contained to Module 3 for MVP. Filesystem-based artifact passing (`output/{project}/`) between modules. Supabase stores project state, deployment history, and media URL mappings within Module 3 only. Post-MVP, if multi-agent coordination or resumable cross-module workflows are needed, Supabase becomes the coordination layer.

### Infrastructure Decisions (LOCKED — do not revisit)
- **Frontend:** Next.js deployed to Vercel
- **Backend:** Shopify Storefront API (headless)
- **Hosting:** Vercel (free tier → Pro at $20/seat)
- **State/Persistence:** Supabase (free tier)
- **Media CDN:** Shopify CDN + Vercel next/image (NO Cloudinary)
- **Payments:** Shopify hosted checkout (zero payment code in frontend)

### What Needs Building

**PRIORITY 1: Shopify Storefront API Client**
```
lib/shopify/
├── client.ts          # Storefront API GraphQL client
├── queries.ts         # Product, collection, cart queries
├── mutations.ts       # Cart create, add, update, remove, get checkout URL
├── types.ts           # TypeScript types
└── utils.ts           # Price formatting, image URL helpers
```
Reference: Vercel's Next.js Commerce (`lib/shopify/`). Use as starting template.

**PRIORITY 2: Shopify Admin API Orchestration**
```
scripts/shopify-deploy/
├── orchestrator.ts       # Main pipeline coordinator
├── create-collections.ts # Create collections with smart rules
├── import-products.ts    # Product CSV import or API creation
├── upload-media.ts       # fileCreate for all media assets
├── create-navigation.ts  # Menu structure from architecture.json
├── create-redirects.ts   # URL redirect import
├── install-headless.ts   # Install Headless channel, get Storefront API token
├── validate.ts           # Post-deployment data integrity checks
└── rollback.ts           # Delete created resources on failure
```
Requirements: Pre-flight validation, per-step validation, error handling, rollback, idempotent (safe to re-run), rate limiting (40 req/sec Shopify Admin API).

**PRIORITY 3: Vercel Project Wiring**
- Set env vars on Vercel project via API (SHOPIFY_STORE_DOMAIN, STOREFRONT_ACCESS_TOKEN, SUPABASE vars)
- Connect custom domain
- Trigger redeployment after env var changes

**PRIORITY 4: Supabase Project State**
```sql
projects (id, name, source_url, source_platform, architecture jsonb, media_manifest jsonb, preset_used, timestamps)
deployments (id, project_id, vercel_url, shopify_store, status, step_results jsonb, timestamps)
media_mappings (id, project_id, source_url, shopify_cdn_url, asset_type, upload_status, timestamp)
```

---

## ADDITIONAL TOOLS TO INTEGRATE (BUILT INDEPENDENTLY)

These are **existing tools** in separate GitHub repos that need to be wired into the pipeline via CLI subprocess calls. Each tool exposes a CLI interface; the orchestrator calls them sequentially. Artifacts pass as files in `output/{project}/`.

### Tool 1: Site-Mapping & Architecture Structure System
For migrations, this calculates:
- Required number of pages
- Landing pages needed
- Templates required
- Site navigation mapping
- Collections for the Shopify store

**Integration point:** Feeds INTO the Calculator (Module 1), providing the structural analysis that the Calculator incorporates into `architecture.json`. Called by the Calculator as a subprocess step.

### Tool 2: URL Mapping System
- Maps from existing store URLs to new Shopify store URLs
- Handles multi-market mapping (CH/AT/DE etc.)
- Imports redirect mappings directly into the store
- Produces the `redirects` section of `architecture.json`

**Integration point:** Called by the Calculator during architecture generation (to produce redirect mappings) and by Module 3's `create-redirects.ts` (to import redirects into Shopify).

### Tool 3: Bulk GraphQL Product Importer
- Can import 50,000 products into Shopify in approximately 120 minutes
- Uses bulk GraphQL operations for maximum throughput
- Handles rate limiting and error recovery

**Integration point:** Called by Module 3 as a subprocess, replacing the built-in `import-products.ts` for large catalogs. For stores with <1,000 products, Module 3's native Admin API import may be sufficient.

### Remaining Puzzle Pieces
- **CDN Media Asset Mapping:** For migration stores, mapping source CDN image URLs to Shopify CDN destinations. Covered by `media-manifest.json` architecture — implementation needed in `upload-media.ts` using Shopify's `fileCreate` (accepts source URL, Shopify downloads and processes).
- **Payments Integration:** Handled entirely by Shopify's hosted checkout. No code needed in the frontend. Customer clicks checkout → redirected to Shopify checkout page → all payment methods configured in Shopify admin work automatically (Shopify Payments/Stripe, Shop Pay, Apple Pay, PayPal, Klarna, etc.).

---

## END-TO-END PIPELINE (THE NORTH STAR)

When all modules and tools are wired together:

```
1. HUMAN provides: Source URL + Shopify dev store credentials

2. CALCULATOR runs:
   ├── Crawl source URL
   ├── Classify pages, extract structure
   ├── Extract product data
   ├── Inventory media assets
   ├── Analyze brand identity
   ├── Generate architecture.json
   ├── Generate brief.md
   ├── Generate products.csv
   └── Generate media-manifest.json

3. HUMAN reviews: architecture.json + brief.md
   └── Approves or adjusts

4. WEB BUILDER runs:
   ├── Read brief.md
   ├── Match industry preset
   ├── Generate scaffold
   ├── Generate sections (one at a time, style header restated)
   ├── Assemble page
   ├── Consistency review
   └── Deploy to Vercel

5. SHOPIFY INTEGRATION LAYER runs:
   ├── Create collections from architecture.json
   ├── Import products (bulk GraphQL — 50k in ~120 min)
   ├── Upload media via fileCreate from media-manifest.json
   ├── Create navigation menus
   ├── Import redirects (URL mapping system)
   ├── Install Headless channel
   ├── Get Storefront API token
   ├── Set env vars on Vercel project
   ├── Inject Storefront API client into generated site
   ├── Trigger Vercel redeployment
   └── Validate: products load, collections display, cart works, checkout redirects

6. HUMAN reviews: Live storefront
   └── Approves for client handoff

7. CLIENT HANDOFF:
   ├── Transfer Shopify dev store to client
   ├── Client upgrades to paid plan
   ├── Transfer or retain Vercel project
   └── Connect client's custom domain
```

**Total automated time:** ~2-4 hours
**Total human review time:** ~1-2 hours
**Infrastructure cost:** ~$50-100/month
**Per-project API cost:** ~$1-2

---

## MEDIA ASSET ARCHITECTURE

Three CDNs, zero redundancy, no Cloudinary:

| Asset Type | Upload Method | Served From | Referenced By |
|---|---|---|---|
| Product images | Shopify Admin API `productCreateMedia` | cdn.shopify.com | Storefront API returns URLs dynamically |
| Hero banners, category images, videos | Shopify Admin API `fileCreate` (accepts source URL, Shopify downloads) | cdn.shopify.com | URLs stored in Supabase project config |
| Brand assets (logo, favicon) | Committed to repo `/public` | Vercel edge CDN | Static import in code |

`next/image` optimizes all remote URLs on delivery regardless of source.

---

## PAYMENT MODEL

The headless frontend **never touches payment data**:
1. Next.js storefront manages cart via Shopify Storefront Cart API
2. Customer clicks "Checkout"
3. Frontend fetches `checkoutUrl` from cart object
4. Customer redirected to Shopify's hosted checkout page
5. All payment methods configured in client's Shopify admin work automatically
6. After payment, customer returns to storefront confirmation page

No payment code, no PCI compliance burden, no payment gateway configuration.

---

## IMPLEMENTATION SEQUENCE

Build in this order. Parallel tracks where noted. Each phase is independently valuable.

### Phase 0: Commerce Contract + Page Templates (Web Builder)
- Define commerce prop contract (`skills/commerce-contract.ts`) ✅ DONE
- Pipeline maturation: v0.1.0 → v1.1.2 ✅ DONE (animation library, GSAP ecosystem, pattern identification, build reliability)
- Build page template structures into presets (homepage, collection, product, landing, about, contact, legal) — NOT STARTED
- Mark sections as static / prop-driven / hybrid within presets — NOT STARTED
- Validate section generation produces prop-driven commerce components — NOT STARTED
- Update section generation prompt for commerce-aware output — NOT STARTED

**Deliverable:** Web Builder generates a complete template set (5-8 page types) with commerce sections accepting typed Shopify props

**Note:** Pipeline maturation (animation systems, extraction quality, build reliability) was prioritized over page template work. The commerce contract types and data mode classifications are complete — the remaining work is preset structure upgrades and orchestrator integration.

### Phase 1: Parallel Tracks (Weeks 1-2)

**Track A: Calculator Generalization**
- Generalize URL crawler beyond Turm/Magento
- Implement platform detection (Magento, Shopify, WooCommerce, generic)
- Build page classifier (product, category, content, legal, contact)
- Build architecture.json generator
- Build brief.md auto-generator
- Build media-manifest.json generator
- Test on 10-20 diverse sites

**Deliverable:** Given any e-commerce URL → outputs architecture.json + brief.md + media-manifest.json

**Track B: Module 2→3 Handoff Spike (1-2 days)**
- Take one existing Web Builder output (e.g., turm-kaffee-v3)
- Manually wire it to a Shopify dev store via Storefront API
- Validate the Option D hybrid approach: static pages as-is, commerce pages with injected data layer
- Document: what works, what breaks, what the Web Builder output needs to change
- De-risk weeks of downstream integration work

**Deliverable:** Validated proof that Web Builder output can receive Shopify data injection

### Phase 2: Shopify Admin API Orchestration (Weeks 2-3)
- Build collection creator (with smart rules)
- Build product importer (integrate bulk GraphQL tool)
- Build media uploader (fileCreate pipeline)
- Build navigation creator
- Build redirect importer (integrate URL mapping tool)
- Build pre-flight validation, post-deployment verification, rollback
- Test on Shopify dev store

**Deliverable:** Given architecture.json + products.csv + media-manifest.json + Shopify creds → fully populated Shopify store

### Phase 3: Storefront API Client (Week 3)
- Build reusable lib/shopify/ module
- Product queries, collection queries, cart mutations
- Checkout URL generation
- Type-safe, error-handled
- Template for injection into Web Builder output

**Deliverable:** Drop-in module connecting any Next.js site to a Shopify backend

### Phase 4: Vercel Wiring & Supabase Persistence (Week 4)
- Vercel API: set env vars, connect domains, trigger redeployment
- Supabase schema creation
- Project state persistence
- Media URL mapping storage
- Resumable deployment workflows

**Deliverable:** Full pipeline automation from Calculator output to live storefront

### Phase 5: Pump-and-Break Testing (Weeks 4-6)
- Run 10-20 diverse sites end-to-end
- Document every failure
- Add rules to Calculator for each edge case
- Harden error handling
- Measure: time per build, success rate, manual intervention rate

**Deliverable:** System handles common archetype (200-500 products, 4-8 categories, 1-3 markets) reliably

---

## WHAT NOT TO BUILD

Items explicitly removed or deferred:

| Item | Status | Reason |
|---|---|---|
| Cloudinary integration | REMOVED | Shopify CDN + Vercel next/image covers all cases |
| Figma extraction pipeline | DEFERRED | Web Builder achieves sufficient quality with Playwright + style header |
| Custom Liquid theme generation | REMOVED | Headless approach eliminates need for Shopify themes |
| UWR (Universal Web Representation) | REMOVED | Over-engineered; direct structured extraction is simpler |
| Per-product static page generation | DEFERRED | 1 template per page type, Next.js dynamic routes handle N instances |
| CMS integration (Sanity/Strapi) | DEFERRED post-MVP | Shopify is the CMS for commerce content |
| A/B testing framework | DEFERRED post-MVP | Build core pipeline first |
| White-label / SaaS pricing | DEFERRED post-MVP | Validate with 10-20 builds first |

---

## SUCCESS CRITERIA

The system is production-ready when:

- Given any mid-market e-commerce URL, Calculator outputs valid architecture spec in **under 5 minutes**
- Web Builder generates a visually professional frontend in **under 10 minutes**
- Shopify Integration Layer populates a complete store in **under 30 minutes**
- End-to-end: source URL → live headless storefront in **under 2 hours** (including human review)
- Manual intervention rate **below 15%** of total build time
- **10 consecutive builds** complete without critical failures
- Client handoff takes **under 30 minutes**

---

## COST SUMMARY

### Monthly Infrastructure
| Service | Cost |
|---|---|
| Shopify Partner account | $0 |
| Vercel Pro | $20/seat |
| Supabase (free tier) | $0 |
| Anthropic API | $30-80 |
| **Total** | **~$50-100/month** |

### Per-Project
| Item | Cost |
|---|---|
| Web Builder API calls | $0.55-1.15 |
| Calculator API calls | ~$0.50 |
| Shopify Integration | ~$0.00 |
| **Total** | **~$1-2** |

### Client Revenue
| Item | Revenue |
|---|---|
| Project fee | $12,000-15,000 |
| Shopify Partner commission | 20% recurring on client's monthly plan |
| Optional maintenance retainer | $500-1,000/month |
| **Effective hourly rate** | **$2,000-2,500/hour** |

---

## WHERE YOU (CURSOR AGENT) FIT RIGHT NOW

You are working on **Module 2: Web Builder**. The visual pipeline is production-ready (v1.1.2, 13 builds deployed). The next planned step is Phase 0's remaining work: page preset template structures with commerce-aware section generation.

### Completed
- Commerce prop contract defined (`skills/commerce-contract.ts`) — Shopify Storefront API types, section data mode classification, page template metadata
- Pipeline maturation v0.1.0 → v1.1.2: animation library (1,034 components), GSAP ecosystem (20 plugins), pattern identification (Stage 0d), build reliability (JSX auto-repair), 8 engineering plans closed
- 13 successful builds deployed to Vercel across diverse industries
- VISION.md sync mechanism wired into doc-sync-checklist, close-checklist, and CLAUDE.md update protocol

### Not Started (Next)
- Page template structures in presets (homepage, collection, product, landing, about, contact, legal)
- Section generation prompt updates for prop-driven commerce sections
- Orchestrator multi-page generation support

### Context for Decision-Making
1. **Understand the interfaces** — your output (deployed Next.js site with prop-driven commerce sections) feeds into Module 3
2. **Keep scope clean** — don't add Shopify API client code, cart logic, or product data fetching. Generate components that ACCEPT data via props. Module 3 provides the data.
3. **Commerce contract** — `skills/commerce-contract.ts` defines the prop shapes. Commerce sections must import and use these types.
4. **Static vs. prop-driven** — check `SECTION_DATA_MODES` in the commerce contract before generating any section. Static sections: generate as today. Prop-driven: accept typed props, render from props, include empty-state handling.
5. **See what's coming** — the three additional tools (site-mapping, URL mapping, bulk GraphQL) integrate into Modules 1 and 3, not the Web Builder
6. **Know the north star** — source URL → live headless storefront in under 2 hours

---

*Document created: 2026-02-11*
*Last updated: 2026-02-11*
*Web Builder version: v1.1.2*
*Status: Active — Phase 0 page templates not started (pipeline maturation complete)*
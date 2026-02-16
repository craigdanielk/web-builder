Here it is. One document, one agent, full orchestration.

---

# AURELIX: Layer Integration Build Plan

## ⚠️ DO NOT RUN PIPELINE — TESTING REQUIRED

**This plan is complete for build-out and validation. Do not execute the full pipeline (Phases A through E) until testing is signed off.** Run verification gates after each phase and fix issues before proceeding. The pipeline can be executed top-to-bottom once testing is complete.

---

## How to Execute This Plan (Master Orchestrator)

When an agent runs this plan, use the **master-orchestrator** flow:

1. **Discover** — Ensure capability registry is current: `python3 scripts/discover.py` (or equivalent in your environment). Confirms skills and MCP tools available for Shopify, Web Builder, deployment.
2. **Triage** — For each phase or sub-task, analyze intent and complexity: `python3 scripts/orchestrator.py --explain "<phase or step description>"`. Use this to decide direct_skill vs skill_chain vs agent_team.
3. **Execute** — Generate execution steps only when ready to run: `python3 scripts/execute.py "<phase or step>"`. Use `--dry-run` to see the plan without running. **Do not run the full pipeline end-to-end until testing is complete.**
4. **Verify** — After each phase, run that phase’s VERIFY GATE before starting the next. If a gate fails, fix and re-verify; do not proceed.

**Syntax patterns:** Use `PLAN: <task>` for plan-only (no execution). Use `ORCHESTRATE: <task>` when you want the orchestrator to show the execution plan. Use natural language for phase descriptions when calling orchestrator/execute.

**Note:** The master-orchestrator scripts (`discover.py`, `orchestrator.py`, `agent_teams.py`, `execute.py`) may live in `~/.claude/skills/master-orchestrator/scripts/` or in a separate repo. Run the above commands from the directory or environment where those scripts exist; if they are not in AURELIX_AG, execute this plan manually phase-by-phase and use each phase’s verification gate before proceeding.

---

## Orchestration Overview

You are building Layers 4–9 of the Aurelix system. Layer 6 (Multi-Page App Generation) is complete. This document is your single source of truth for execution order, verification gates, and specs.

```
PHASE A: Brief Compiler ← YOU ARE HERE
         │
         ├─── VERIFY GATE A ───┐
         │                     │
PHASE B: Layer 4 (Store Setup) │ Layer 5 (Media Pipeline)  ← PARALLEL
         │                     │
         ├─── VERIFY GATE B ───┘
         │
PHASE C: Layer 7 (Data-Connected Templates)  ← SEQUENTIAL
         │
         ├─── VERIFY GATE C
         │
PHASE D: Layer 8 (Cart + Checkout)  ← SEQUENTIAL
         │
         ├─── VERIFY GATE D
         │
PHASE E: Layer 9 (Go-Live)  ← SEQUENTIAL
```

**Module locations within AURELIX_AG/:**
- Phase A → Calculator module
- Phase B (both) → New: Shopify Integration Layer module
- Phase C, D → Web Builder module (injecting into generated site)
- Phase E → Deployment scripts (top-level or Integration Layer)

---

## Implementation status (as of 2026-02-12)

| Phase / Layer | Implemented? | Where / notes |
|---------------|---------------|----------------|
| **Phase A: Brief Compiler** | ✅ Yes | `aurelix-calculator/brief_compiler.py` — reads `architecture.json` (+ optional `products.csv`), writes `brief.md`, `brand.json`, `media-manifest.json`. |
| **VERIFY GATE A** | ✅ Yes | `aurelix-calculator/verify_gate_a.py` — checks brief sections, brand.json, media-manifest, product_images vs products.csv. |
| **Step 0 (token)** | ✅ Yes | `shopify-integration-layer/step0_token.py` — client-credentials grant, verify shop, write `SHOPIFY_ADMIN_ACCESS_TOKEN` to .env. |
| **VERIFY GATE B-0** | ✅ Yes | `shopify-integration-layer/verify_gate_b0.py` — token present, shop query returns name. |
| **Phase B: Layer 4 (Store setup)** | ✅ Yes | `shopify-integration-layer/layer4_store_setup.py` — collections, products, menus, redirects, `shopify_config.json`. Headless/storefront token from env or manual. |
| **Phase B: Layer 5 (Media pipeline)** | ✅ Yes | `shopify-integration-layer/layer5_media_pipeline.py` — fileCreate for section media, brand assets to public, `cdn_url_map.json`. |
| **VERIFY GATE B** | ✅ Yes | `shopify-integration-layer/verify_gate_b.py` — config + CDN map + Storefront API check. |
| **Layer 6 (Multi-page)** | ✅ Yes | `web-builder/scripts/orchestrate.py` — multipage stages; deploy manifest-aware. |
| **Phase C: Layer 7 (Data-connected)** | ✅ Yes | `web-builder/lib/shopify/` — client.ts, queries.ts, mutations.ts, types.ts, utils.ts, cdn-config.ts. Copy into output/PROJECT/site/src/lib/shopify when deploying with commerce. |
| **VERIFY GATE C** | ✅ Yes | `web-builder/scripts/verify_gate_c.py` — client.ts exists, optional npm run build. |
| **Phase D: Layer 8 (Cart + Checkout)** | ✅ Yes | `web-builder/lib/shopify/cart.ts`, `CartDrawer.tsx` — create/add/update/remove cart, getCheckoutUrl, drawer UI. |
| **VERIFY GATE D** | ✅ Yes | `web-builder/scripts/verify_gate_d.py` — cart + drawer exist. |
| **Phase E: Layer 9 (Go-Live)** | ✅ Yes | `web-builder/scripts/layer9_go_live.py` — set Vercel env from shopify_config.json, optional `vercel --prod`. |
| **VERIFY GATE E** | ✅ Yes | `web-builder/scripts/verify_gate_e.py` — prints final manual checklist. |

**Summary:** All phases and verification gates from this plan are implemented. Run scripts in order: Step 0 → Gate B-0 → Layer 4 & 5 → Gate B → (Layer 6 via orchestrate) → copy lib/shopify into site → Gate C → Gate D → Layer 9 → Gate E.

---

## PHASE A: BRIEF COMPILER

**System:** Calculator
**Depends on:** Nothing (uses existing Calculator outputs)
**Blocks:** Everything

### What It Does

A script that takes the Calculator's existing outputs and compiles them into the exact structured formats that the Web Builder and Shopify Integration Layer consume deterministically. The current brief is prose — this makes it machine-actionable.

### Inputs (all exist today)

- `architecture.json` — collections, pages (with `sections_needed`), navigation, redirects, markets
- Brand extraction outputs — color palette hex codes, typography choices, imagery style, tone keywords
- Navigation structure — hierarchical menu with labels and link targets
- Product data — `products.csv` with handles, titles, images, tags, variants
- Source media URLs — product images, category images, hero banners, logos discovered during crawl

### Outputs (3 files)

**Output 1: `brief.md` (structured, not prose)**

Replace the current fluffy brief with a machine-parseable markdown that still follows the Web Builder's expected template headings but contains structured data, not sentences.

```markdown
# Demo / example project

## Business
- Company: (from brief)
- Location: St. Gallen, Switzerland
- Founded: 1761
- Focus: Premium coffee, tea, and accessories
- Heritage: 260+ years of drum roasting tradition

## What They Need
- E-commerce storefront: 6 collections, 20 collection pages, 262 product pages, 5 content pages
- Multi-market: CH (CHF), AT (EUR), DE (EUR)
- Headless architecture: Next.js + Shopify Storefront API

## Key Requirements
- Product categories: Kaffee (120), Tee (45), Maschinen (30), Zubehör (53), Geschenke (55), Abo (16)
- Navigation: 7 top-level items, 2-level depth, 40 total menu items
- Page templates: homepage, collection-parent (5), collection-leaf (15), product-detail (262), content (5)

## Target Audience
- Primary: Swiss coffee enthusiasts, ages 30-60
- Secondary: Gift buyers, specialty coffee professionals
- Price positioning: Premium (CHF 8-45 per product)

## Brand Personality
- Colors: [exact hex values from extraction]
- Typography: [exact font families from extraction]
- Imagery: Warm, artisanal, close-up product photography
- Tone: Heritage-proud, expert, approachable

## Specific Requests
- Hero: Heritage story with "Seit 1761" prominence
- Featured: Bestseller grid from across collections
- Process: Sourcing → Roasting → Freshness → Your Cup
- Social proof: Customer testimonials

## Technical Notes
- Platform: Shopify headless via Storefront API
- Markets: CH/AT/DE with currency switching
- Products: 265 active SKUs
- Preset: artisan-food
```

**Output 2: `brand.json`**

Distinct Calculator output that overrides industry preset defaults in the Builder.

```json
{
  "project_id": "demo",
  "colors": {
    "primary": "#[extracted]",
    "secondary": "#[extracted]",
    "accent": "#[extracted]",
    "background": "#[extracted]",
    "text": "#[extracted]"
  },
  "typography": {
    "heading_font": "[extracted font family]",
    "body_font": "[extracted font family]",
    "heading_weight": "[extracted]",
    "body_size_base": "[extracted]"
  },
  "imagery": {
    "style": "warm-artisanal",
    "treatment": "natural-light",
    "corners": "rounded-sm"
  },
  "tone": {
    "voice": "heritage-expert",
    "keywords": ["tradition", "handcrafted", "seit 1761", "klein-chargen"]
  },
  "logo": {
    "source_url": "https://example-shop.example/media/.../logo.svg",
    "deployment": "repo_public_dir"
  }
}
```

**Output 3: `media-manifest.json` (extended with section-level bindings)**

This is the critical upgrade. The manifest now maps every image not just by asset type, but by the exact page and section it belongs to.

```json
{
  "section_media": {
    "homepage": {
      "hero_banner": {
        "source_url": "https://example-shop.example/media/.../homepage_hero.jpg",
        "alt_text": "Demo brand hero",
        "dimensions": "1920x800",
        "deployment": "shopify_cdn"
      },
      "about_editorial": {
        "source_url": "https://example-shop.example/media/.../roasting.jpg",
        "alt_text": "Traditional drum roasting",
        "dimensions": "960x640",
        "deployment": "shopify_cdn"
      }
    },
    "kaffee": {
      "hero_banner": {
        "source_url": "https://example-shop.example/media/.../kaffee_hero.jpg",
        "alt_text": "Kaffee Kollektion",
        "dimensions": "1920x600",
        "deployment": "shopify_cdn"
      },
      "product_showcase": {
        "source": "dynamic:storefront_api",
        "collection_handle": "kaffee",
        "note": "Product images served via Storefront API response"
      }
    },
    "kaffee-bohnen": {
      "hero_banner": {
        "source_url": "https://example-shop.example/media/.../hero.jpg",
        "alt_text": "Kaffee Bohnen",
        "dimensions": "1920x600",
        "deployment": "shopify_cdn"
      },
      "product_showcase": {
        "source": "dynamic:storefront_api",
        "collection_handle": "kaffee-bohnen"
      }
    }
  },
  "product_images": [
    {
      "product_handle": "example-product",
      "images": [
        {
          "source_url": "https://example-shop.example/media/.../example-product-1000g.jpg",
          "position": 1,
          "alt_text": "Example product 1000g"
        },
        {
          "source_url": "https://example-shop.example/media/.../example-product-250g.jpg",
          "position": 2,
          "alt_text": "Example product 250g"
        }
      ]
    }
  ],
  "brand_assets": [
    {
      "type": "logo",
      "source_url": "https://example-shop.example/media/.../logo.svg",
      "deployment": "repo_public_dir",
      "target_path": "/public/logo.svg"
    },
    {
      "type": "favicon",
      "source_url": "https://example-shop.example/media/.../favicon.ico",
      "deployment": "repo_public_dir",
      "target_path": "/public/favicon.ico"
    }
  ],
  "summary": {
    "total_section_images": 42,
    "total_product_images": 1080,
    "total_brand_assets": 3,
    "images_needing_cdn_upload": 42,
    "images_served_dynamically": 1080
  }
}
```

### Implementation

Language: Python (matches existing Calculator codebase)
Single file: `brief_compiler.py`
CLI: `python brief_compiler.py --project demo --input-dir ./calculator_output/ --output-dir ./compiled/`

The script reads existing Calculator outputs from `--input-dir`, transforms them, writes the three files to `--output-dir`.

### VERIFY GATE A

Before proceeding to Phase B, confirm ALL of the following:

- [ ] `brief.md` exists, contains all 7 sections, all values are populated (no placeholders)
- [ ] `brand.json` exists, valid JSON, all color values are real hex codes (not placeholders), font families are real
- [ ] `media-manifest.json` exists, valid JSON, `section_media` has an entry for every page handle in `architecture.json`
- [ ] Every page in `architecture.json` → `pages[]` has a corresponding key in `media-manifest.json` → `section_media`
- [ ] Every `sections_needed` entry for each page has either a `source_url` (static image) or `source: "dynamic:storefront_api"` (dynamic)
- [ ] `product_images` array has an entry for every product handle in `products.csv`
- [ ] All `source_url` values are valid URLs (not empty, not placeholder text)
- [ ] Run: `python -c "import json; json.load(open('compiled/brand.json')); json.load(open('compiled/media-manifest.json')); print('VALID')"` → prints VALID

**If any check fails: fix in Brief Compiler before proceeding. Do not start Phase B with incomplete outputs.**

---

## PHASE B: LAYER 4 + LAYER 5 (PARALLEL)

**These two layers are independent of each other.** Both consume Calculator outputs. Neither needs the other's output. Run them in parallel — either as two concurrent tasks or sequentially if the agent prefers.

---

### STEP 0: Generate Access Token (runs once, before either layer)

Both Layer 4 and Layer 5 need an Admin API access token. The `.env` file at the **AURELIX_AG/** root contains the Client ID and Client Secret. Use the client credentials grant flow to exchange them for an access token.

**Read from .env (AURELIX_AG/.env):**

- `SHOPIFY_STORE_DOMAIN` (e.g. `aurelix-test-dev.myshopify.com`)
- `SHOPIFY_CLIENT_ID`
- `SHOPIFY_CLIENT_SECRET`

**Client Credentials Grant:**

```bash
curl -X POST \
  "https://shopify.com/authentication/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=${SHOPIFY_CLIENT_ID}" \
  -d "client_secret=${SHOPIFY_CLIENT_SECRET}" \
  -d "scopes=write_products,read_products,write_files,read_files,write_content,read_content,write_online_store_navigation,read_online_store_navigation,write_online_store_pages,read_online_store_pages,read_markets,write_markets,read_publications,write_publications,read_locales,write_locales,read_channels,write_channels"
```

**Expected response:** `access_token` (starts with `shp_`), `expires_in` (typically 86400). Store the token for use in both layers:

- `SHOPIFY_ADMIN_ACCESS_TOKEN=<access_token from response>`

**Verify the token works:**

```bash
curl -X POST \
  "https://${SHOPIFY_STORE_DOMAIN}/admin/api/2024-01/graphql.json" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: ${SHOPIFY_ADMIN_ACCESS_TOKEN}" \
  -d '{"query": "{ shop { name url myshopifyDomain } }"}'
```

Should return the shop name. If 401 or auth error, token generation failed — check Client ID/Secret. Token expires in ~24 hours; re-run grant if build exceeds that.

---

### VERIFY GATE B-0

- [ ] Access token generated successfully (non-empty string starting with `shp_`)
- [ ] Shop query returns store name (e.g. `aurelix-test-dev`)
- [ ] Token stored as `SHOPIFY_ADMIN_ACCESS_TOKEN` accessible to both Layer 4 and Layer 5 scripts

**If this fails: do not proceed. Debug credentials first.**

---

### LAYER 4: SHOPIFY STORE SETUP

**System:** Shopify Integration Layer (new module)
**Depends on:** Phase A outputs (architecture.json, products.csv) + **Step 0 access token** (`SHOPIFY_STORE_DOMAIN`, `SHOPIFY_ADMIN_ACCESS_TOKEN`)
**Blocks:** Layer 7 (provides Storefront API token)

### What It Does

Takes `architecture.json` and `products.csv` and creates a fully populated Shopify dev store via Admin API: collections, products, menus, redirects.

### Inputs

- `architecture.json` — collections (with smart rules), navigation, redirects, markets
- `products.csv` — Shopify-compatible product import data (handles, titles, body_html, vendor, tags, variant_sku, variant_price, image_src)
- Shopify dev store credentials — store domain + Admin API access token (provided as env vars)

### Outputs

- Populated Shopify store with:
  - All collections created with smart rules
  - All products imported with tags, variants, metafields
  - Navigation menus created matching architecture.json hierarchy
  - URL redirects imported
  - Headless channel installed
- `shopify_config.json`:

```json
{
  "store_domain": "example-store.myshopify.com",
  "storefront_access_token": "[generated after headless channel install]",
  "admin_api_token": "[from env]",
  "collections_created": 20,
  "products_imported": 265,
  "menus_created": 1,
  "redirects_imported": 27,
  "headless_channel": "installed",
  "created_at": "2026-02-14T..."
}
```

**Note:** `storefront_access_token` is populated in **Step 6** (Headless channel install), not from Step 0. Step 0 provides only the Admin API token (`SHOPIFY_ADMIN_ACCESS_TOKEN`). Layer 7 and Storefront API usage rely on this storefront token.

### Implementation Steps

**Step 1: Pre-flight validation**
- Verify Shopify credentials from Step 0 work (GET /admin/api/2024-01/shop.json using `SHOPIFY_STORE_DOMAIN` and `SHOPIFY_ADMIN_ACCESS_TOKEN`)
- Verify dev store is empty or confirm overwrite
- Validate architecture.json schema
- Validate products.csv has required columns

**Step 2: Create collections**
- Read `architecture.json` → `collections[]`
- For each collection, POST to `/admin/api/2024-01/smart_collections.json`
- Set title, handle, rules from `smart_rules[]`
- Create parent collections first, then children
- Log: collection handle → Shopify collection ID mapping

**Step 3: Import products**
- Read `products.csv`
- Use Shopify bulk import or iterate via POST `/admin/api/2024-01/products.json`
- Include tags (critical — smart collection rules depend on tags)
- Include variants with pricing
- Include metafields where available
- Log: product handle → Shopify product ID mapping

**Step 4: Create navigation menus**
- Read `architecture.json` → `navigation.main_menu[]`
- POST to `/admin/api/2024-01/menus.json` (or use GraphQL `menuCreate`)
- Create hierarchical menu items with correct link targets
- Links to collections use `/collections/{handle}`
- Links to pages use `/pages/{handle}`

**Step 5: Import redirects**
- Read `architecture.json` → `redirects[]`
- For each, POST to `/admin/api/2024-01/redirects.json`
- Set path (old URL) and target (new URL)

**Step 6: Install headless channel + get Storefront token**
- Install Headless sales channel on dev store
- Generate Storefront API access token
- Record token in `shopify_config.json`

**Step 7: Post-deployment verification**
- GET each collection → verify product count matches expected
- GET product count → verify matches products.csv row count
- GET menus → verify structure matches architecture.json
- GET redirects → verify count matches

### Error Handling

- If a collection creation fails: log error, continue with next, report at end
- If product import fails: log SKU, continue, report failures
- If credential check fails: STOP immediately, report
- All operations should be idempotent — running twice should not create duplicates (check by handle before creating)

### Rollback

- Track all created entity IDs
- If critical failure mid-execution: provide `rollback.json` with entity IDs for manual or scripted cleanup

---

### LAYER 5: MEDIA PIPELINE

**System:** Shopify Integration Layer (same module as Layer 4)
**Depends on:** Phase A outputs (specifically extended media-manifest.json)
**Blocks:** Layer 7 (provides CDN URL map)

### What It Does

Takes the media-manifest.json with section-level bindings, uploads all static images to Shopify CDN via fileCreate Admin API, and outputs a CDN URL map that Layer 7 uses to inject real image URLs into templates.

### Inputs

- `media-manifest.json` — from Brief Compiler (Phase A), with section_media, product_images, brand_assets
- `SHOPIFY_STORE_DOMAIN` and `SHOPIFY_ADMIN_ACCESS_TOKEN` from Step 0 (same as Layer 4)

### Outputs

- All section images uploaded to Shopify CDN
- Brand assets copied to repo `/public/` directory
- `cdn_url_map.json`:

```json
{
  "section_media": {
    "homepage:hero_banner": "https://cdn.shopify.com/s/files/demo/homepage_hero.jpg",
    "homepage:about_editorial": "https://cdn.shopify.com/s/files/demo/roasting.jpg",
    "kaffee:hero_banner": "https://cdn.shopify.com/s/files/demo/kaffee_hero.jpg",
    "kaffee-bohnen:hero_banner": "https://cdn.shopify.com/s/files/demo/hero.jpg"
  },
  "brand_assets": {
    "logo": "/public/logo.svg",
    "favicon": "/public/favicon.ico"
  },
  "product_images": "served_dynamically_via_storefront_api",
  "summary": {
    "uploaded": 42,
    "failed": 0,
    "skipped_dynamic": 1080
  }
}
```

### Implementation Steps

**Step 1: Classify assets by deployment target**
- `section_media` entries with `"deployment": "shopify_cdn"` → upload queue
- `section_media` entries with `"source": "dynamic:storefront_api"` → skip (served at runtime)
- `brand_assets` with `"deployment": "repo_public_dir"` → download and save locally
- `product_images` → skip entirely (these are attached to products during import in Layer 4, served via Storefront API)

**Step 2: Upload section images to Shopify CDN**
- For each image in upload queue:
  - POST to `/admin/api/2024-01/graphql.json` using `fileCreate` mutation
  - Input: `originalSource` = source_url (Shopify downloads from this URL)
  - Input: `contentType` = IMAGE
  - Input: `filename` = derived from page_handle + section_type
  - Wait for processing (poll `fileStatus` or use staged upload)
  - Record: `{page_handle}:{section_type}` → CDN URL returned by Shopify

**Step 3: Download brand assets**
- For each brand_asset:
  - Download from source_url
  - Save to target_path (e.g., `/public/logo.svg`)

**Step 4: Build CDN URL map**
- Compile all uploaded URLs into `cdn_url_map.json`
- Key format: `{page_handle}:{section_type}` for quick lookup
- Include brand asset local paths

**Step 5: Verify uploads**
- For each CDN URL in the map: HTTP HEAD request, confirm 200
- For each brand asset: confirm file exists at target path

### Error Handling

- If an upload fails: retry once, then log failure and continue
- If source URL is unreachable: log as `failed`, include in summary
- If Shopify CDN returns error: log mutation response, retry with staged upload flow
- Never block the entire pipeline on a single image failure

### fileCreate GraphQL Mutation Reference

```graphql
mutation fileCreate($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files {
      id
      alt
      createdAt
      fileStatus
      preview {
        image {
          url
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

Variables:
```json
{
  "files": [
    {
      "alt": "Kaffee Bohnen Hero Banner",
      "contentType": "IMAGE",
      "originalSource": "https://example-shop.example/media/.../hero.jpg"
    }
  ]
}
```

---

### VERIFY GATE B

Before proceeding to Phase C, confirm ALL of the following:

**Layer 4 checks:**
- [ ] `shopify_config.json` exists with valid `storefront_access_token` (not empty)
- [ ] Shopify store has correct product count: `GET /admin/api/2024-01/products/count.json` matches products.csv row count
- [ ] At least 1 collection returns products: query a known collection handle via Storefront API and confirm products array is non-empty
- [ ] Navigation menu exists: `GET /admin/api/2024-01/menus.json` returns at least 1 menu
- [ ] Storefront API works: query `{ shop { name } }` using storefront_access_token → returns shop name

**Layer 5 checks:**
- [ ] `cdn_url_map.json` exists, valid JSON
- [ ] Every key in `section_media` returns HTTP 200 on HEAD request
- [ ] `summary.failed` is 0 (or all failures are documented and non-critical)
- [ ] Brand assets exist at their target paths
- [ ] Total `uploaded` count matches the number of `"deployment": "shopify_cdn"` entries in media-manifest.json

**Cross-check:**
- [ ] The set of page handles in `cdn_url_map.json` matches the set of page handles in `architecture.json`

**If Layer 4 fails but Layer 5 succeeds (or vice versa): do NOT proceed. Both must pass. Fix the failing layer first.**

---

## PHASE C: LAYER 7 — DATA-CONNECTED TEMPLATES

**System:** Web Builder (injecting into generated Next.js site)
**Depends on:** Layer 4 (Storefront token + populated store) + Layer 5 (CDN URL map) + Layer 6 (multi-page routes)
**Blocks:** Layer 8

### What It Does

Takes the static multi-page Next.js site from Layer 6 and wires it to live Shopify data. Sections that were generated with placeholder content now fetch real products, collections, and images at build/request time.

### Inputs

- Generated Next.js site from Layer 6 (the `output/{project}/site/` directory)
- `shopify_config.json` from Layer 4 (store domain + storefront token)
- `cdn_url_map.json` from Layer 5 (static image URLs)
- `architecture.json` (for route → collection handle mapping)

### What Gets Created

**1. Storefront API client: `lib/shopify/`**

```
lib/shopify/
├── client.ts          # GraphQL client initialized with env vars
├── queries.ts         # All read queries (products, collections, cart)
├── mutations.ts       # Cart create, add lines, update lines
├── types.ts           # TypeScript types for all Shopify responses
└── utils.ts           # formatPrice(), getImageUrl(), etc.
```

Reference: Vercel's Next.js Commerce `lib/shopify/` directory. Adapt, don't build from scratch.

Client initialization:
```typescript
const domain = process.env.SHOPIFY_STORE_DOMAIN!;
const token = process.env.SHOPIFY_STOREFRONT_ACCESS_TOKEN!;
const endpoint = `https://${domain}/api/2024-01/graphql.json`;
```

**2. Required GraphQL queries:**

Products by collection:
```graphql
query CollectionProducts($handle: String!, $first: Int!) {
  collectionByHandle(handle: $handle) {
    title description
    image { url altText }
    products(first: $first) {
      edges { node {
        handle title description
        priceRange { minVariantPrice { amount currencyCode } }
        images(first: 4) { edges { node { url altText } } }
        variants(first: 10) { edges { node { id title price { amount } availableForSale } } }
      } }
    }
  }
}
```

Single product:
```graphql
query ProductByHandle($handle: String!) {
  productByHandle(handle: $handle) {
    handle title description descriptionHtml
    priceRange { minVariantPrice { amount currencyCode } }
    images(first: 10) { edges { node { url altText width height } } }
    variants(first: 20) { edges { node {
      id title price { amount } availableForSale
      selectedOptions { name value }
    } } }
    metafields(identifiers: [
      { namespace: "custom", key: "saure" },
      { namespace: "custom", key: "geschmack" },
      { namespace: "custom", key: "herkunft" }
    ]) { key value }
  }
}
```

**3. Dynamic route wiring:**

`app/collections/[handle]/page.tsx` → calls `collectionByHandle` with handle from URL params
`app/products/[handle]/page.tsx` → calls `productByHandle` with handle from URL params

Add `generateStaticParams()` to both for SSG:
```typescript
export async function generateStaticParams() {
  // Fetch all collection/product handles from Storefront API
  // Return array of { handle: string }
}
```

**4. Static image injection:**

For sections that use static images (heroes, about sections), read `cdn_url_map.json` and inject CDN URLs. These can be:
- Imported as a JSON file at build time
- Stored as environment variables
- Loaded from a config file

The key lookup is: `cdn_url_map.section_media["{page_handle}:{section_type}"]` → URL string

**5. Environment variables:**

Add to `.env.local` (and Vercel project):
```
SHOPIFY_STORE_DOMAIN=example-store.myshopify.com
SHOPIFY_STOREFRONT_ACCESS_TOKEN=[from shopify_config.json]
```

### VERIFY GATE C

- [ ] `lib/shopify/client.ts` exists and exports a working `shopifyFetch()` function
- [ ] `npm run build` completes without errors (all dynamic routes resolve)
- [ ] Homepage: featured products section renders real product data (not placeholder)
- [ ] `/collections/kaffee` → loads and displays real products from Shopify
- [ ] `/products/example-product` (or any known handle) → loads and displays real product data
- [ ] All hero banners show real images from CDN (not placeholder URLs)
- [ ] `generateStaticParams()` returns correct handle arrays for both collections and products
- [ ] No `localhost` or placeholder URLs in any rendered output

---

## PHASE D: LAYER 8 — CART + CHECKOUT

**System:** Web Builder (injecting into generated Next.js site)
**Depends on:** Layer 7 (working Storefront API client)
**Blocks:** Layer 9

### What It Does

Adds cart functionality: create cart, add items, update quantities, remove items, and redirect to Shopify's hosted checkout.

### What Gets Created

**1. Cart mutations in `lib/shopify/mutations.ts`:**

```graphql
mutation CartCreate($input: CartInput!) {
  cartCreate(input: $input) {
    cart {
      id
      checkoutUrl
      lines(first: 50) {
        edges { node {
          quantity
          merchandise { ... on ProductVariant {
            id title
            product { title handle }
            image { url }
            price { amount }
          } }
        } }
      }
      cost { totalAmount { amount currencyCode } }
    }
  }
}

mutation CartLinesAdd($cartId: ID!, $lines: [CartLineInput!]!) {
  cartLinesAdd(cartId: $cartId, lines: $lines) {
    cart { id checkoutUrl lines(first: 50) { edges { node { quantity merchandise { ... on ProductVariant { id } } } } } cost { totalAmount { amount currencyCode } } }
  }
}

mutation CartLinesUpdate($cartId: ID!, $lines: [CartLineUpdateInput!]!) {
  cartLinesUpdate(cartId: $cartId, lines: $lines) {
    cart { id lines(first: 50) { edges { node { id quantity } } } cost { totalAmount { amount currencyCode } } }
  }
}

mutation CartLinesRemove($cartId: ID!, $lineIds: [ID!]!) {
  cartLinesRemove(cartId: $cartId, lineIds: $lineIds) {
    cart { id lines(first: 50) { edges { node { id } } } cost { totalAmount { amount currencyCode } } }
  }
}
```

**2. Cart state management: `lib/shopify/cart.ts`**

- Store cart ID in cookie or localStorage
- `createCart()` → returns cart object with ID
- `addToCart(variantId, quantity)` → calls CartLinesAdd
- `updateCartLine(lineId, quantity)` → calls CartLinesUpdate
- `removeFromCart(lineId)` → calls CartLinesRemove
- `getCart()` → fetches current cart state
- `getCheckoutUrl()` → returns `cart.checkoutUrl` for redirect to Shopify checkout

**3. UI Components:**

- `CartDrawer.tsx` — slide-out cart panel showing line items, quantities, total, checkout button
- Add-to-cart button on product pages — calls `addToCart` with selected variant ID
- Cart icon in navigation — shows item count badge
- Checkout button — `window.location.href = checkoutUrl` (redirects to Shopify hosted checkout)

**4. Important: NO payment code.**

The checkout is Shopify's hosted checkout. The frontend's job ends at redirecting to `cart.checkoutUrl`. No payment forms, no PCI compliance, no payment gateway configuration.

### VERIFY GATE D

- [ ] Add a product to cart from a product page → cart drawer opens with correct item
- [ ] Update quantity in cart → total updates correctly
- [ ] Remove item from cart → item disappears, total updates
- [ ] Click checkout → browser redirects to Shopify hosted checkout URL (*.myshopify.com/checkouts/...)
- [ ] Cart persists across page navigation (cart ID stored in cookie/localStorage)
- [ ] Cart icon in nav shows correct item count
- [ ] Cart works on both collection pages and product pages
- [ ] Empty cart state shows appropriate message

---

## PHASE E: LAYER 9 — GO-LIVE

**System:** Deployment scripts
**Depends on:** Everything above passing
**Blocks:** Nothing (this is the finish line)

### What It Does

Final deployment configuration: environment variables on Vercel, custom domain, URL redirects, and validation that the entire system works end-to-end.

### Steps

**Step 1: Set Vercel environment variables**
Via Vercel API or CLI:
```
SHOPIFY_STORE_DOMAIN=example-store.myshopify.com
SHOPIFY_STOREFRONT_ACCESS_TOKEN=[from shopify_config.json]
```

**Step 2: Trigger Vercel redeployment**
```bash
vercel --prod
```

**Step 3: Connect custom domain** (if provided)
- Add domain to Vercel project via API or dashboard
- Configure DNS (CNAME or A record)

**Step 4: Import URL redirects**
- Read `architecture.json` → `redirects[]`
- Configure at Vercel level (vercel.json rewrites) or via middleware
- Each old Magento URL → new Next.js route with 301

**Step 5: End-to-end validation**

### VERIFY GATE E (FINAL)

- [ ] Production URL loads homepage with real content
- [ ] Navigation works — all menu links resolve to correct pages
- [ ] Collection pages load real products from Shopify
- [ ] Product pages load real product data, images from Shopify CDN
- [ ] Hero banners show real images from CDN (not broken/placeholder)
- [ ] Add to cart works on production
- [ ] Checkout redirect works on production (lands on Shopify checkout)
- [ ] Old Magento URLs (e.g., `/kaffee.html`) redirect to new URLs with 301
- [ ] Mobile responsive — test on phone viewport
- [ ] Page load time < 3 seconds on homepage
- [ ] No console errors in browser dev tools
- [ ] All 3 markets accessible (if multi-market configured)

**If all checks pass: the system is live. Report completion.**

---

## REFERENCE: Locked Infrastructure Decisions

Do not revisit or change these. They are final.

| Decision | Choice |
|---|---|
| Shopify account | Partner account (free dev stores) |
| Frontend | Vercel |
| Commerce API | Shopify Storefront API (GraphQL) |
| Checkout | Shopify hosted (redirect) |
| Product media | Shopify CDN via fileCreate |
| Layout media | Shopify CDN via fileCreate |
| Brand assets | Repo /public, Vercel edge |
| Image optimization | next/image |
| Cloudinary | REMOVED |
| Figma pipeline | DEFERRED |
| 21st.dev | DEFERRED |

---

## REFERENCE: File Flow Between Phases

```
Calculator (existing)
    │
    ├── architecture.json
    ├── products.csv
    ├── brand extraction outputs
    └── source media URLs
         │
    PHASE A: Brief Compiler
         │
         ├── brief.md (structured)
         ├── brand.json
         └── media-manifest.json (section-keyed)
              │
    ┌────────┴────────┐
    │                 │
PHASE B1:         PHASE B2:
Layer 4            Layer 5
    │                 │
    ├── shopify_      ├── cdn_url_map.json
    │   config.json   └── /public/ brand assets
    │                 │
    └────────┬────────┘
             │
        PHASE C: Layer 7
             │
             └── lib/shopify/ + wired dynamic routes
                      │
                 PHASE D: Layer 8
                      │
                      └── cart.ts + CartDrawer + checkout redirect
                               │
                          PHASE E: Layer 9
                               │
                               └── LIVE SITE ✓
```
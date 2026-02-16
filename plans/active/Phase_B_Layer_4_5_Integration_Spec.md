# Phase B: Layer 4 + Layer 5 Integration Spec

**Purpose:** Single source for Phase B (post–Calculator). Use this section to replace or extend any existing "Phase B" content in the main build/integration spec.

---

## PHASE B: LAYER 4 + LAYER 5 (PARALLEL)

These two layers are independent of each other. Both consume Calculator outputs. Neither needs the other's output. Run them in parallel — either as two concurrent tasks or sequentially.

### STEP 0: Generate Access Token (runs once, before either layer)

Both Layer 4 and Layer 5 need an Admin API access token. The `.env` file at the **AURELIX_AG/** root contains the Client ID and Client Secret. Use the client credentials grant flow to exchange them for an access token.

**Read from .env:**

- `SHOPIFY_STORE_DOMAIN=aurelix-test-dev.myshopify.com`
- `SHOPIFY_CLIENT_ID=<from .env>`
- `SHOPIFY_CLIENT_SECRET=<from .env>`

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

**Expected response:**

```json
{
  "access_token": "shp_xxxxxxxxxxxxx",
  "token_type": "bearer",
  "expires_in": 86400,
  "scope": "write_products,read_products,..."
}
```

**Store the token for use in both layers:**

```
SHOPIFY_ADMIN_ACCESS_TOKEN=<access_token from response>
```

**Verify the token works:**

```bash
curl -X POST \
  "https://${SHOPIFY_STORE_DOMAIN}/admin/api/2024-01/graphql.json" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Access-Token: ${SHOPIFY_ADMIN_ACCESS_TOKEN}" \
  -d '{"query": "{ shop { name url myshopifyDomain } }"}'
```

Should return the shop name. If it returns 401 or an auth error, the token generation failed — check Client ID/Secret.

**Note on token expiry:** The access token expires (typically 24 hours). If the build takes longer than that, re-run the grant flow. For a production system, build token refresh into the orchestrator. For now, re-run manually if needed.

---

### VERIFY GATE B-0

- [ ] Access token generated successfully (non-empty string starting with `shp_`)
- [ ] Shop query returns store name `aurelix-test-dev`
- [ ] Token stored as `SHOPIFY_ADMIN_ACCESS_TOKEN` accessible to both Layer 4 and Layer 5 scripts

**If this fails: do not proceed. Debug credentials first.**

---

### Then: Layer 4 and Layer 5

Layer 4 and Layer 5 proceed as written in the main spec, with these substitutions:

1. **Credentials:** Replace every reference to *"Shopify Admin API credentials (from env vars)"* with: **use `SHOPIFY_STORE_DOMAIN` and `SHOPIFY_ADMIN_ACCESS_TOKEN` from Step 0.**

2. **Layer 4 output — `shopify_config.json`:** Add a note that the **storefront_access_token** is obtained separately by installing the Headless channel (Step 6 of Layer 4). It is a **different token** from the Admin API token used in Step 0.

---

## LAYER 4: SHOPIFY STORE SETUP

**System:** Shopify Integration Layer (new module within AURELIX_AG/)
**Depends on:** Phase A outputs (architecture.json, products.csv) + Step 0 access token
**Blocks:** Layer 7 (provides Storefront API token via shopify_config.json)

### What It Does

Takes `architecture.json` and `products.csv` from the Brief Compiler output and creates a fully populated Shopify dev store via Admin API: collections, products, menus, redirects.

### Inputs

- `architecture.json` — collections (with smart rules), navigation, redirects, markets
- `products.csv` — Shopify-compatible product import data (handles, titles, body_html, vendor, tags, variant_sku, variant_price, image_src)
- `SHOPIFY_STORE_DOMAIN` and `SHOPIFY_ADMIN_ACCESS_TOKEN` from Step 0

### Output

`shopify_config.json`:

```json
{
  "store_domain": "aurelix-test-dev.myshopify.com",
  "storefront_access_token": "[generated in Step 6 — this is NOT the Admin API token from Step 0]",
  "admin_api_token": "[from Step 0]",
  "collections_created": 20,
  "products_imported": 265,
  "menus_created": 1,
  "redirects_imported": 27,
  "headless_channel": "installed",
  "created_at": "2026-02-14T..."
}
```

### Implementation Steps

**Step 1: Pre-flight validation**
- Verify access token works (should already pass from Gate B-0, but confirm)
- Verify dev store is empty or confirm overwrite
- Validate architecture.json schema (has `collections`, `pages`, `navigation`, `redirects` keys)
- Validate products.csv has required columns (handle, title, body_html, vendor, tags, variant_sku, variant_price, image_src)

**Step 2: Create collections**
- Read `architecture.json` → `collections[]`
- For each collection, use Admin API GraphQL `collectionCreate` mutation (for custom collections) or `collectionCreate` with rules (for smart collections)
- Set title, handle, rules from `smart_rules[]`
- Create parent collections first, then children
- Log: collection handle → Shopify collection ID mapping

**Step 3: Import products**
- Read `products.csv`
- Use `productSet` mutation (supports create with variants, media, and metafields in one call) or iterate via `productCreate` mutation
- Include tags (critical — smart collection rules depend on tags)
- Include variants with pricing
- Include metafields where available
- Log: product handle → Shopify product ID mapping

**Step 4: Create navigation menus**
- Read `architecture.json` → `navigation.main_menu[]`
- Use `menuCreate` mutation via Admin API GraphQL
- Create hierarchical menu items with correct link targets
- Links to collections use `/collections/{handle}`
- Links to pages use `/pages/{handle}`

**Step 5: Import redirects**
- Read `architecture.json` → `redirects[]`
- For each, use `urlRedirectCreate` mutation
- Set path (old URL) and target (new URL)

**Step 6: Install Headless channel + get Storefront token**
- Install Headless sales channel on dev store
- Generate Storefront API access token
- **Important:** This `storefront_access_token` is different from the `SHOPIFY_ADMIN_ACCESS_TOKEN` used in Step 0. The Admin token talks to Admin API. The Storefront token talks to Storefront API. Both are needed downstream.
- Record storefront token in `shopify_config.json`

**Step 7: Post-deployment verification**
- Query each collection → verify product count matches expected from architecture.json
- Query total product count → verify matches products.csv row count
- Query menus → verify structure matches architecture.json navigation
- Query redirects → verify count matches

### Error Handling

- If a collection creation fails: log error, continue with next, report at end
- If product import fails: log SKU, continue, report failures
- If credential check fails: STOP immediately, report
- All operations should be idempotent — check by handle before creating to avoid duplicates on re-run

### Rollback

- Track all created entity IDs in a `rollback.json`
- If critical failure mid-execution: provide rollback.json with entity IDs for manual or scripted cleanup via delete mutations

---

## LAYER 5: MEDIA PIPELINE

**System:** Shopify Integration Layer (same module as Layer 4)
**Depends on:** Phase A outputs (media-manifest.json) + Step 0 access token
**Blocks:** Layer 7 (provides cdn_url_map.json)

### What It Does

Takes the media-manifest.json with section-level bindings from the Brief Compiler, uploads all static images to Shopify CDN via fileCreate Admin API, and outputs a CDN URL map that Layer 7 uses to inject real image URLs into templates.

### Inputs

- `media-manifest.json` — from Brief Compiler (Phase A), with section_media, product_images, brand_assets
- `SHOPIFY_STORE_DOMAIN` and `SHOPIFY_ADMIN_ACCESS_TOKEN` from Step 0

### Output

`cdn_url_map.json`:

```json
{
  "section_media": {
    "homepage:hero_banner": "https://cdn.shopify.com/s/files/demo/homepage_hero.jpg",
    "homepage:about_editorial": "https://cdn.shopify.com/s/files/demo/roasting.jpg",
    "kaffee:hero_banner": "https://cdn.shopify.com/s/files/demo/kaffee_hero.jpg",
    "kaffee-bohnen:hero_banner": "https://cdn.shopify.com/s/files/demo/bohnen_hero.jpg"
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
- `section_media` entries with `"source": "dynamic:storefront_api"` → skip (served at runtime via Storefront API)
- `brand_assets` with `"deployment": "repo_public_dir"` → download and save locally to repo /public/
- `product_images` → skip entirely (these are attached to products during import in Layer 4, served via Storefront API at runtime)

**Step 2: Upload section images to Shopify CDN**
- For each image in upload queue, use the `fileCreate` GraphQL mutation:

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

Variables per image:
```json
{
  "files": [
    {
      "alt": "Kaffee Bohnen Hero Banner",
      "contentType": "IMAGE",
      "originalSource": "https://example-shop.example/media/.../bohnen_hero.jpg"
    }
  ]
}
```

- `originalSource` is the source_url from media-manifest.json — Shopify downloads from this URL and hosts it on their CDN
- `filename` derived from `{page_handle}_{section_type}.{ext}`
- After creation, poll `fileStatus` until it returns `READY`, then record the CDN URL from `preview.image.url`
- Map key format: `{page_handle}:{section_type}` → CDN URL

**Step 3: Download brand assets**
- For each brand_asset in media-manifest.json:
  - Download from source_url
  - Save to target_path (e.g., `/public/logo.svg`, `/public/favicon.ico`)

**Step 4: Build CDN URL map**
- Compile all uploaded URLs into `cdn_url_map.json`
- Key format: `{page_handle}:{section_type}` for direct lookup
- Include brand asset local paths
- Include summary counts

**Step 5: Verify uploads**
- For each CDN URL in the map: HTTP HEAD request, confirm HTTP 200
- For each brand asset: confirm file exists at target path
- Log any failures in summary

### Error Handling

- If an upload fails: retry once with 5-second delay, then log failure and continue
- If source URL is unreachable (404 from Magento source): log as `failed`, include in summary, do not block pipeline
- If Shopify CDN returns error on fileCreate: log full mutation response, retry once
- If fileStatus stays `PROCESSING` for more than 60 seconds: log as `timeout`, continue
- Never block the entire pipeline on a single image failure

---

## VERIFY GATE B

Before proceeding to Phase C (Layer 7), confirm ALL of the following:

### Layer 4 checks:
- [ ] `shopify_config.json` exists with valid `storefront_access_token` (non-empty, different from admin token)
- [ ] Shopify store has correct product count: query `{ productsCount { count } }` via Admin API matches products.csv row count
- [ ] At least 1 collection returns products: query a known collection handle (e.g. `kaffee`) via Storefront API using the storefront_access_token and confirm products array is non-empty
- [ ] Navigation menu exists: query menus via Admin API returns at least 1 menu with items
- [ ] Storefront API works: query `{ shop { name } }` using storefront_access_token from shopify_config.json → returns shop name

### Layer 5 checks:
- [ ] `cdn_url_map.json` exists, valid JSON
- [ ] Every key in `section_media` returns HTTP 200 on HEAD request to the CDN URL
- [ ] `summary.failed` is 0 (or all failures are documented and accepted as non-critical — e.g. source images that no longer exist)
- [ ] Brand assets exist at their target paths in `/public/`
- [ ] Total `uploaded` count matches the number of `"deployment": "shopify_cdn"` entries in media-manifest.json

### Cross-check:
- [ ] The set of page handles present in `cdn_url_map.json` covers every page handle in `architecture.json` that has static media (i.e., no page with a hero_banner is missing from the CDN map)

**If Layer 4 fails but Layer 5 succeeds (or vice versa): do NOT proceed to Phase C. Both must pass. Fix the failing layer first.**

**Once Gate B passes:** The agent has a populated Shopify store (Layer 4), CDN URLs for all static media (Layer 5), and a Storefront API token (shopify_config.json). These are the three inputs Layer 7 needs. Proceed to Phase C.

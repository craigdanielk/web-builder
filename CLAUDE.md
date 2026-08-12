# Web Builder — System Context

**Last Updated:** 2026-02-17
**System Version:** v3.1.0

---

## Sub-Agent Identity

**You are the web-builder sub-agent** — the specialist for Phase D (Build &
Deploy) of the Aurelix pipeline. You own the deep intricacies of the
orchestrator: the 7-stage generation flow, section archetypes, the 8-phase
content-token sanitization, the Shopify RSC injection, and Vercel deploy.

- **Parent:** the **Aurelix agent** (`../CLAUDE.md` at the Aurelix AG repo
  root). This file **rolls up into** that manual — the parent references it as
  the authority for orchestrator internals. When you need whole-system context
  (the 5-service pipeline, Shopify setup, gotchas), read the parent manual;
  when the parent needs build/deploy detail, it defers to **this** file.
- **This is a submodule** — an independently git-tracked repo with its own
  `main`. Keep this file authoritative for everything under `web-builder/`.
- **Scope:** `scripts/orchestrate.py` and everything it drives. Out of scope:
  extraction (aurelix-calculator), import (shopify-bulk-product-importer),
  Shopify verification (shopify-integration-layer), redirects (url-redirect
  toolkit) — those are sibling services under the same parent Aurelix agent.

---

## Quick Reference

| Key | Value |
|-----|-------|
| System Vision | **See `VISION.md`** — full Aurelix platform plan (Shopify migration + new build) |
| Commerce Contract | `skills/commerce-contract.ts` — Shopify Storefront API types + section prop contracts |
| Runtime | Python 3 + Node.js (hybrid pipeline) |
| Generated stack | Next.js 16.1.6 / React 19 / Tailwind CSS 4 / TypeScript 5 |
| Animation engines | GSAP 3.14 + Framer Motion 12 (both can coexist) |
| Pipeline entry | `scripts/orchestrate.py` — single-page or Layer 6 multi-page |
| API | Anthropic Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) |
| Deployment | Vercel CLI (`vercel --yes`) |
| API key | `ANTHROPIC_API_KEY` in `.env` (gitignored) |
| Preset DB | Supabase `aurelix-presets` (eu-west-1) — 842 presets, 25 industries |
| DB docs | `DATABASE.md` — schema, usage, adding industries |
| Templates | `SECTION_TEMPLATES.md` — local + Supabase `code_template` (72 in DB, 1 local HERO) |

---

## Architecture

### Pipeline Overview

```
User Input (brief + preset OR --from-url URL)
    │
    ▼
Stage 0: URL Extraction (--from-url only)
    ├── url-to-preset.js     → skills/presets/{project}.md
    ├── url-to-brief.js      → briefs/{project}.md
    ├── section-context      → per-section reference data
    └── pattern-identifier   → color system, archetype gaps, animation/UI patterns, gap report
    │
    ▼
Stage 1: Scaffold Generation
    ├── Input: brief + preset + taxonomy
    ├── Output: output/{project}/scaffold.md
    └── Checkpoint: manual review (unless --no-pause)
    │
    ▼
Stage 2: Section Generation (one per section, sequential)
    ├── Input: scaffold + style header + section context
    ├── Output: output/{project}/sections/{NN}-{name}.tsx
    └── Each section: 4096 max_tokens, Claude Sonnet 4.5
    │
    ▼
Stage 3: Assembly
    └── Output: output/{project}/page.tsx (imports all sections)
    │
    ▼
Stage 4: Consistency Review
    └── Output: output/{project}/review.md
    │
    ▼
Stage 5: Deploy (--deploy flag)
    ├── Creates Next.js project at output/{project}/site/
    ├── When industry ecommerce + multipage: copies lib/shopify, writes Storefront-wired collection/product pages (Layer 7)
    ├── Installs deps, generates layout/globals/page
    └── Ready for: cd site && vercel --yes
```

### Data Flow (URL Clone Mode — v2.0.0)

```
extract-reference.js (v2: cookie dismiss + lazy scroll + sectionIndex)
    ├── Playwright headless Chromium (1440x900)
    ├── Cookie modal dismissal → full-page lazy scroll → DOM extraction
    ├── Images and text have sectionIndex for per-section assignment
    └── Output: extraction-data.json
         │
         ├── archetype-mapper.js → mapped-sections.json
         ├── animation-detector.js → animation-analysis.json
         ├── pattern-identifier.js → identification.json
         ├── confidence-gate.js → gates low-confidence mappings
         └── build-site-spec.js → site-spec.json (1 structured JSON, zero AI)
              │ ← component-registry.json (unified, 48 components)
              │
              ↓
         site-spec.json (single source of truth)
              ├── style: { palette (hex), fonts, spacing, radius, animation }
              ├── sections: [ { archetype, variant, confidence, content, images, components } ]
              ├── component_map: { exact import_statements }
              └── confidence_stats + reanalysis prompt
```

### Database Integration (v2.1.0)

The `--industry` flag enables Supabase-backed preset selection:

```
python scripts/orchestrate.py my-project --industry artisan-food --page homepage --deploy
```

**Data flow:**
1. `BuildCache` makes exactly 2 Supabase reads at build start (section sequence + industry style)
2. Data is cached in memory for the entire build
3. For each section, `check_template_exists(archetype, variant, cache)` resolves template in order: (1) local file `section-templates/{ARCHETYPE}/{variant}.tsx`, (2) Supabase `section_archetypes.code_template` (when `has_template = true`), (3) else LLM fallback. Results are cached per build in `BuildCache.template_cache`.
4. If template found (Path or str) → brand token injection, skip LLM
5. If nothing found → fall through to existing LLM pipeline unchanged
6. Build log written to `build_log` with three-way counts: `sections_from_template` (local), `db_template_count` (Supabase), `sections_from_llm`

**Layer 6 (v3.0.0) — Multi-page generation:** When `--industry` is set (and optionally `--site-manifest`), the pipeline can run in multi-page mode: a site manifest defines pages (homepage, collection, product, content, 404). NAV and FOOTER are generated once as shared layout components; per-page section sequences come from `get_section_sequence(industry, page_type)` with NAV/FOOTER filtered. Output is a full `src/app/` tree with `layout.tsx` (Navigation + Footer), route directories (`collections/[handle]/`, `products/[handle]/`, `pages/[handle]/`), and `not-found.tsx`. See `plans/active/Layer_6_Multi_Page_App_Generation.md`.

**Key files:**
- `scripts/lib/supabase_client.py` — REST client, `BuildCache`, `get_industry_metadata`, `get_section_sequence`, `get_all_page_sections`
- `scripts/lib/site_manifest.py` — manifest schema, `generate_site_manifest()`, `load_site_manifest()`, `filter_nav_footer_from_sections()`
- `section-templates/` — 25 archetype dirs, local templates optional; Supabase `section_archetypes.code_template` used when no local file, `manifest.json`
- `supabase/migrations/` — migration files for schema (incl. `code_template`, `db_template_count`)
- `scripts/seed_supabase.py` — Data seeding script
- `scripts/validate_integration.py` — 70-test validation suite

### Consistency Mechanisms (v2.0.0)

**JSON path (--from-url):** `site-spec.json` contains hex colors, font names, and spacing values as JSON. The style tokens are injected directly into section prompts — no markdown prose, no re-interpretation.

**Legacy path (--preset):** Compact style header from preset markdown is restated in every section prompt:
```
═══ STYLE CONTEXT ═══
Palette: warm-earth | stone-50/white/green-700
Type: Aeonik/Aeonik · 600/400 · 1.25 ratio
...
═══════════════════════
```

**Unified Component Registry:** All import statements come from `component-registry.json` with verified export names. Zero AI-constructed imports.

---

## File Map

```
web-builder/
├── CLAUDE.md                          ← THIS FILE — read first every session
├── README.md                          ← Human-facing onboarding guide
├── .cursorrules (214 lines)           ← Agent instructions for non-Claude-Code agents
├── .env                               ← API keys (gitignored)
├── .gitignore
│
├── skills/                            ← Design knowledge (read-only during generation)
│   ├── section-taxonomy.md            ← 25 section archetypes, 99+ variants
│   ├── style-schema.md                ← 7 style dimensions with Tailwind mappings
│   ├── animation-patterns.md          ← 20+ named GSAP/Framer Motion patterns
│   ├── image-extraction.md            ← Image categorization spec (10 categories)
│   ├── animation-components/            ← Pre-built animation component library (1034 total)
│   │   ├── component-registry.json (794) ← NEW v2.0.0: Unified registry with export names (48 components)
│   │   ├── registry.json                ← DELETED v2.0.0 (legacy, no export names — replaced by component-registry.json)
│   │   ├── registry/                    ← Comprehensive machine-usable registry
│   │   │   ├── animation_registry.json (1.6MB) ← Full analysis of all 1034 components
│   │   │   ├── animation_taxonomy.json  ← Controlled vocabulary (motion intents, triggers, roles)
│   │   │   ├── animation_search_index.json ← Query-optimised lookup by intent/trigger/section/framework
│   │   │   ├── animation_capability_matrix.csv ← Tabular capabilities (189KB)
│   │   │   └── analysis_log/ (1034 files) ← Per-component classification rationale
│   │   ├── entrance/                    ← Scroll-triggered entrance animations (11 slots)
│   │   ├── scroll/                      ← Scroll-linked animations (6 slots, incl. gsap-pinned-horizontal)
│   │   ├── interactive/                 ← User-triggered animations (7 slots)
│   │   ├── continuous/                  ← Always-running animations (5 slots)
│   │   ├── text/                        ← Text-specific animations (5 slots)
│   │   ├── effect/                      ← Border/glow/decoration effects (2 slots)
│   │   ├── background/                  ← Full-section background animations (2 slots)
│   │   └── 21st-dev-library/ (986 .tsx) ← Community components from 21st.dev
│   ├── presets/ (35 presets + _template)
│   │   ├── _template.md
│   │   ├── artisan-food.md            ← Coffee, bakery, artisan food
│   │   ├── beauty-cosmetics.md
│   │   ├── construction-trades.md
│   │   ├── creative-studios.md
│   │   ├── education.md
│   │   ├── events-venues.md
│   │   ├── farm-minerals-anim.md      ← Agricultural tech (GSAP + Lottie)
│   │   ├── farm-minerals-promo-v2.md
│   │   ├── fashion-apparel.md
│   │   ├── health-wellness.md
│   │   ├── home-lifestyle.md
│   │   ├── hotels-hospitality.md
│   │   ├── jewelry-watches.md
│   │   ├── medical-dental.md
│   │   ├── nicola-romei.md              ← Creative portfolio / digital studio
│   │   ├── nike-golf.md
│   │   ├── nonprofits-social.md
│   │   ├── outdoor-adventure.md
│   │   ├── pet-products.md
│   │   ├── professional-services.md
│   │   ├── real-estate.md
│   │   ├── restaurants-cafes.md
│   │   ├── saas.md
│   │   ├── sports-fitness.md
│   │   └── {preset}.md
│   └── components/
│       ├── cursor-trail.md            ← Mouse-following trail effect
│       └── image-patterns.md          ← CSS backgroundImage rendering patterns
│
├── benchmarks/                        ← NEW 2026-08-13: market design benchmarks
│   └── crypto-exchange.json           ← measured, provenance-stamped, patterns-only
│
├── templates/                         ← Prompt templates per pipeline stage
│   ├── scaffold-prompt.md             ← Stage 1 prompt template
│   ├── section-prompt.md              ← Stage 2 prompt template
│   ├── section-instructions-framer.md ← Framer Motion section instructions
│   ├── section-instructions-gsap.md   ← GSAP + ScrollTrigger section instructions
│   └── assembly-checklist.md          ← Stage 4 review checklist
│
├── briefs/                            ← Client briefs (human or auto-generated)
│   ├── _template.md
│   └── {project}.md                   ← One per project
│
├── docs/ (auto-generated — do not edit)
│   ├── api-reference.md               ← Function signatures + caller graph
│   ├── dependencies.md                ← NPM packages + configuration constants
│   └── data-flow.md                   ← Module I/O contracts + require graph
│
├── scripts/
│   ├── generate-docs.js               ← Generates docs/ from source code
│   ├── orchestrate.py                 ← Main pipeline — single-page or Layer 6 multi-page
│   ├── lib/                           ← Python lib (orchestrator)
│   │   ├── supabase_client.py         ← BuildCache, get_section_sequence, get_industry_metadata, get_all_page_sections
│   │   └── site_manifest.py           ← Layer 6: manifest schema, generate/load_site_manifest, filter_nav_footer
│   └── quality/                       ← URL extraction + validation tools
│       ├── build-site-spec.js (587)   ← NEW v2.0.0: Deterministic site-spec.json builder (zero AI)
│       ├── build-unified-registry.js (207) ← NEW v2.0.0: Auto-generates component-registry.json from .tsx files
│       ├── url-to-preset.js (303)     ← URL → preset markdown (kept for --preset mode)
│       ├── url-to-brief.js (201)      ← URL → brief markdown (kept for --preset mode)
│       ├── enrich-preset.js (161)     ← Enrich preset with extracted tokens
│       ├── validate-build.js (287)    ← Post-build quality validation
│       ├── test-animation-detector.js (196) ← Standalone animation test
│       ├── test-pattern-pipeline.js (394) ← Pattern identification test harness (66 assertions)
│       ├── build-animation-registry.js     ← Analyzes 1022 components → registry artifacts
│       ├── fixtures/                       ← Synthetic test data for pipeline testing
│       │   ├── gsap-extraction-data.json   ← Simulated extraction output
│       │   └── gsap-animation-analysis.json ← Simulated animation analysis
│       └── lib/
│           ├── extract-reference.js (824)   ← v2.0.0: + cookie dismiss + lazy scroll + sectionIndex
│           ├── confidence-gate.js (180)     ← NEW v2.0.0: Confidence tiers + re-analysis prompt builder
│           ├── animation-detector.js (750)  ← Animation detection + GSAP interception + section grouping
│           ├── archetype-mapper.js (398)    ← Section → archetype mapping (+ class signals, gap flagging)
│           ├── design-tokens.js (547)       ← CSS → design token collection (+ color intelligence)
│           ├── pattern-identifier.js (925)  ← Pattern identification + unified registry reads
│           ├── animation-injector.js (1334) ← 3-tier injection + unified registry reads
│           ├── icon-mapper.js              ← Semantic icon mapping (Lucide React) + archetype defaults
│           ├── asset-injector.js (554)     ← Per-section asset builder + unified registry reads
│           ├── asset-downloader.js (257)   ← Download + verify extracted assets
│           ├── gsap-extractor.js (454)      ← Static JS bundle GSAP call extraction
│           ├── animation-summarizer.js (209) ← Token-efficient animation signature builder
│           ├── section-context.js (192)     ← Per-section prompt context builder
│           ├── post-process.js (313)        ← Post-generation cleanup
│           ├── visual-validator.js (401)    ← Visual consistency checker
│           ├── registry-extractor.js        ← Feature extraction + classification for registry builder
│           ├── registry-builders.js         ← Registry entry, search index, CSV, analysis log generators
│           └── registry-utils.js            ← File discovery + quality validation for registry builder
│
├── agents/
│   └── roles.md                       ← Multi-agent role definitions
│
├── output/ (gitignored)              ← All build output
│   ├── extractions/{project}-{uuid}/ ← Raw extraction data
│   │   ├── extraction-data.json
│   │   ├── mapped-sections.json
│   │   ├── animation-analysis.json
│   │   └── screenshots/
│   └── {project}/
│       ├── scaffold.md
│       ├── sections/*.tsx             ← Single-page: flat. Layer 6: sections/{page_id}/*.tsx
│       ├── shared/                    ← Layer 6: Navigation.tsx, Footer.tsx
│       ├── pages/                     ← Layer 6: {page_id}.tsx per route
│       ├── site-manifest.json         ← Layer 6: site manifest (when --industry multi-page)
│       ├── page.tsx
│       ├── review.md
│       └── site/                      ← Runnable Next.js project
│
├── plans/
│   ├── _close-checklist.md                    ← Build close protocol template
│   ├── active/
│   │   └── universal-asset-intelligence-pipeline.md ← v1.2.0 — icons, logos, visual fallbacks, UI components
│   ├── backlog/                               ← Future plans (not yet implemented)
│   │   ├── template-library-upgrade-plan.md   ← Aurelix pattern library
│   │   └── url-site-structure-calculator.md   ← Shopify migration calculator
│   └── completed/
│       ├── vision-sync-and-pinned-scroll-reclassification.md ← v1.1.2
│       ├── pinned-horizontal-scroll-and-showcase-cards.md ← v1.1.0
│       ├── animation-classification-vengenceui-integration.md ← v0.7.0
│       ├── animation-extraction-integration.md ← v0.4.0
│       ├── data-injection-pipeline.md          ← v0.5.0
│       ├── generated-reference-docs.md         ← v0.7.1
│       └── system-documentation-automation.md  ← v0.4.1
│
└── retrospectives/                    ← Session documentation
    ├── 2026-02-08-web-builder-first-build-success.md
    ├── (retrospectives — client-specific retros purged)
    ├── 2026-02-08-farm-minerals-rebuild.md
    ├── 2026-02-09-nike-golf-light-theme-rebuild.md
    ├── 2026-02-09-system-docs-automation-success.md
    ├── 2026-02-09-data-injection-pipeline-success.md
    ├── 2026-02-09-animation-component-library-infra-success.md
    ├── 2026-02-10-nicola-romei-portfolio-build.md
    ├── 2026-02-10-cascaid-health-rebuild-from-url.md
    ├── 2026-02-10-cascaid-health-animation-enhancement.md
    ├── 2026-02-10-farm-minerals-v4-animation-library-test.md
    ├── 2026-02-10-animation-library-import-fix.md
    ├── 2026-02-10-animation-registry-build.md
    ├── 2026-02-10-gsap-homepage-stress-test-pipeline-diagnosis.md
    ├── 2026-02-11-pattern-identification-pipeline-v9-success.md
    ├── 2026-02-11-gsap-ecosystem-v10-integration-success.md
    ├── 2026-02-11-pinned-scroll-showcase-cards-v110.md
    └── 2026-02-11-vision-sync-pinned-scroll-reclassification.md
```

---

## Pipeline Stages — Detail

### Stage 0: URL Extraction (`stage_url_extract`, orchestrate.py:134)

**When:** `--from-url` flag is passed
**Runs:** Node.js scripts via subprocess

| Step | Script | Output |
|------|--------|--------|
| 0a | `url-to-preset.js` | `skills/presets/{project}.md` + `output/extractions/{project}-{uuid}/` |
| 0b | `url-to-brief.js` | `briefs/{project}.md` |
| 0c | `section-context.js` | Per-section context dict (passed in memory) |
| 0d | `pattern-identifier.js` | Identification result (color system, archetype gaps, animation patterns, UI components) + `output/{project}/gap-report.json` |

Extraction captures: 500 DOM elements with 24 CSS properties, section boundaries, text content, image URLs, font URLs, animation library globals, Lottie/Rive/3D network assets, CSS keyframes.

**Stage 0d: Pattern Identification** (`stage_identify`, orchestrate.py)

Runs after extraction, before scaffold generation. Calls `pattern-identifier.js` which:
1. Loads extraction data + animation analysis from the extraction directory
2. Runs color intelligence: gradient parsing, color system classification, per-section profiling
3. Runs archetype intelligence: class-signal matching, confidence-based gap flagging
4. Runs animation pattern matching against `animation_search_index.json`
5. Detects UI components (logo-marquee, video-embed, card-grid, etc.) from DOM structure
6. Aggregates all gaps into a structured report with extension tasks
7. Returns identification result that flows into section prompts (per-section accent colors, matched animation patterns, detected UI components)

### Stage 1: Scaffold (`stage_scaffold`, orchestrate.py:236)

**Model:** Claude Sonnet 4.5 | **Max tokens:** 2048
**Input:** Brief + preset section sequence + taxonomy archetype list
**Output:** Numbered section list: `N. ARCHETYPE | variant | content direction`
**Checkpoint:** Interactive review (skipped with `--no-pause`)

### Stage 2: Sections (`stage_sections`, orchestrate.py:465)

**Model:** Claude Sonnet 4.5 | **Max tokens:** dynamic (4096–8192 per section)
**Input per section:** Style header + section spec + structural reference + optional section context + animation context block + asset context block + icon context block (v1.2.0) + visual fallback block (v1.2.0) + card embedded demos block (v1.2.0) + UI component block (v1.2.0) + engine-branched instructions
**Output:** Self-contained React/TypeScript/Tailwind component with correct animation engine
**Post-processing:** Truncation detection & auto-repair (v1.1.1), ensures `"use client"` directive, ensures `export default`
**Injection helpers:** `load_injection_data()`, `get_animation_contexts()`, `get_asset_contexts()` — load extraction data and call Node.js injector modules via subprocess

### Stage 3: Assembly (`stage_assemble`, orchestrate.py:605)

**No API call.** Pure code generation — creates `page.tsx` importing all sections.

### Stage 4: Review (`stage_review`, orchestrate.py:960)

**Model:** Claude Sonnet 4.5 | **Max tokens:** 4096
**Input:** All section code concatenated + style header
**Output:** Consistency report (colors, typography, spacing, radius, animation, buttons)

### Stage 5: Deploy (`stage_deploy`, orchestrate.py)

**No API call.** Creates Next.js project scaffold:
- `package.json` with engine-specific deps (framer-motion always + GSAP conditional + Lottie conditional + clsx/tailwind-merge always)
- Font imports from preset's Type line
- `globals.css` with engine-specific styles
- Generates `src/lib/utils.ts` with `cn()` utility (clsx + tailwind-merge)
- Copies sections to `src/components/sections/`
- Copies animation components from library to `src/components/animations/` (non-placeholder only, matched by archetype)
- **Layer 7 (ecommerce):** When `industry == "ecommerce"` and multipage manifest: copies `lib/shopify` into `site/src/lib/shopify`; writes collection and product pages using `_layer7_collection_page_content()` and `_layer7_product_page_content()` (server components, Storefront API). Homepage is rewritten to fetch collections via `COLLECTIONS_LIST` and pass them to the product-showcase section; `04-product_showcase.tsx` is patched to accept optional `collections` prop and merge with preset styling.
- Downloads verified assets to `public/images/` and `public/lottie/` (via asset-injector + asset-downloader)
- Runs `npm install`

---

## Current System State

### Completed Builds
| Project | Preset | Engine | Deployed |
|---------|--------|--------|----------|
| farm-minerals-promo | farm-minerals-promo-v2 | gsap | Vercel |
| bluebird-coffee-roastery | artisan-food | framer-motion | Vercel |
| nike-golf | nike-golf | gsap | Vercel |
| farm-minerals-anim | farm-minerals-anim | gsap* | Vercel |
| farm-minerals-v3 | farm-minerals-promo-v2 | gsap | Vercel |
| nicola-romei | nicola-romei | gsap | Vercel |
| cascaid-health | health-wellness | gsap+framer | Vercel |
| gsap-homepage | gsap-homepage | gsap | Vercel* |
| gsap-v9-test | gsap-v9-test | gsap | Vercel** |
| gsap-v10 | gsap-v10 | gsap | Vercel |
| gsap-v11 | gsap-v11 | gsap | Vercel |
| sofi-health-v2 | sofi-health-v2 | framer-motion | Local (v2.0.1 validation) |
| sofi-health-v3 | sofi-health-v3 | framer-motion | Local (v2.0.2 validation) |

*sofi-health-v2: First build using v2.0.1 deterministic pipeline. site-spec.json, deterministic scaffold (no Claude), deterministic review, JSON style tokens, checkpoint/retry system all active.
*sofi-health-v3: v2.0.2 validation build. Recursive section detection + DOM-scoped content extraction. All 10 real sections populated with actual sofi-health content (previously all content landed in wrapper Section 0).
*farm-minerals-anim: Built before v0.5.0 injection pipeline — preset says gsap but sections use framer-motion. Rebuild with injection pipeline to fix.
*nicola-romei: Required manual post-build fixes — preset misclassified color (dark vs light #f3f3f3), 0 sections detected in Webflow site broke asset injection, scaffold parser failed on bold markdown. See retro for details.
*gsap-homepage: Stress test build — functional but visually incomplete. Monochrome orange (missing multi-accent), generic animations, blank gallery cards. Used as diagnostic to identify 6 systemic pipeline gaps. See retro for details.
**gsap-v9-test: v0.9.0 validation build against gsap.com. Color intelligence correctly identified 5-accent system, class-signal archetype mapping at 80% confidence, gap report generated. Sections invisible on deploy due to pre-existing GSAP `from()` SSR issue (not a v0.9.0 regression).

### Active Plans
- **[Deterministic Pipeline v2.0.0](plans/active/deterministic-pipeline-v2.md)** — Implemented. All 6 phases complete. Pending validation builds (sofi-health, gsap.com).

### Completed Plans
- **[Universal Asset Intelligence Pipeline](plans/completed/universal-asset-intelligence-pipeline.md)** — v1.2.0. Extended "detect, match, insert, fallback" chain to icons (Lucide React semantic mapping, archetype defaults), logos (inline SVG extraction, raster logo extraction, styled text pill fallback), visual content (library component fallbacks via `SECTION_VISUAL_FALLBACK_MAP` and `CARD_VISUAL_COMPONENTS`), card-level animation embedding (`CARD_EMBEDDED_DEMOS` with 20 GSAP plugin mappings + fallback sequence), and UI component injection (`UI_COMPONENT_LIBRARY_MAP` with 25 patterns + search index lookup). Emoji ban enforced globally. New `icon-mapper.js` module. 5 new Python helpers in orchestrate.py. Extraction upgraded with SVG/icon-library/logo detection. ~11 files modified/created.
- **[VISION.md Sync & PINNED-SCROLL Reclassification](plans/completed/vision-sync-and-pinned-scroll-reclassification.md)** — v1.1.2. PINNED-SCROLL removed as section archetype, reclassified as animation component/technique (25 archetypes). VISION.md added to doc-sync-checklist, close-checklist, CLAUDE.md update protocol. VISION.md one-time refresh to v1.1.2 reality. 
- **[Pinned Horizontal Scroll & Showcase Card Differentiation](plans/completed/pinned-horizontal-scroll-and-showcase-cards.md)** — v1.1.0. GSAP pinned horizontal scroll component and detection pipeline (PINNED-SCROLL archetype added in v1.1.0, reclassified as animation component in v1.1.2). GSAP pinned horizontal scroll component (176 lines, ScrollTrigger pin+scrub, matchMedia mobile fallback). Detection pipeline for pin+scrub patterns in animation-detector, gsap-extractor, pattern-identifier. Scaffold prompt integration with 8192 min token budget. Demo-cards variant for PRODUCT-SHOWCASE with per-card animation differentiation. 8 card micro-animation patterns. `buildCardAnimationBlock()` in animation-injector. Validated with gsap-v11 rebuild.
- **[GSAP Ecosystem Integration & System Stability](plans/completed/gsap-ecosystem-integration-and-stability.md)** — v1.0.0. 8 bug fixes (from() SSR, parse_scaffold, token truncation, JSX repair, zero-section fallback, color misclassification, font parsing, --force flag). 20 GSAP plugins detectable. 22 new animation patterns documented. 11 new plugin components (SplitText, Flip, DrawSVG, MorphSVG, MotionPath, Draggable, Observer, ScrambleText). Plugin-aware injection + preset generation. Pre-flight validation (Stage 5.5) + post-deploy verification. 66-assertion test harness.
- **[Pattern Identification & Mapping Pipeline](plans/completed/pattern-identification-mapping-pipeline.md)** — v0.9.0. Color intelligence (hue-aware mapping, gradient parsing, multi-accent systems), archetype intelligence (class-signal matching, confidence-based gaps), pattern identification (animation registry queries, UI component detection), gap aggregation with extension tasks, pipeline integration as Stage 0d. 688 insertions across 10 files, 57-assertion test harness.
- **[Generated Reference Docs](plans/completed/generated-reference-docs.md)** — v0.7.1. `scripts/generate-docs.js` auto-generates api-reference.md, dependencies.md, data-flow.md from source code. Integrated into close checklist.
- **[Animation Classification + VengenceUI Integration](plans/completed/animation-classification-vengenceui-integration.md)** — v0.7.0. Registry schema upgrade (intensity + affinity scoring for 36 components), 11 VengenceUI components extracted, `selectAnimation()` affinity algorithm, cn() utility in stage_deploy, deduplication across sections.
- **[Data Injection Pipeline](plans/completed/data-injection-pipeline.md)** — v0.5.0. Animation injector + asset injector + engine-branched prompts + dynamic token budgets + dependency fix.
- **[System Documentation Automation](plans/completed/system-documentation-automation.md)** — v0.4.1. CLAUDE.md created, README/cursorrules refreshed, retro skill doc-sync integrated.
- **[Animation Extraction Integration](plans/completed/animation-extraction-integration.md)** — v0.4.0. Animation detection, analysis, preset injection.

### Backlog Plans
- **[URL Site Structure Calculator](plans/backlog/url-site-structure-calculator.md)** — Shopify migration architecture calculator (Aurelix). Not yet implemented.
- **[Aurelix Pattern Library](plans/backlog/template-library-upgrade-plan.md)** — Autonomous pattern recognition system. Not yet implemented.

---

## Known Issues & Workarounds

### Active Issues

> **⚠ This section predates 2026-08-13 and several entries below are RESOLVED or
> WRONG. `../docs/PIPELINE_ARCHITECTURE.md` §10–§11 is canonical where they
> disagree — it is execution-verified. Status as of 2026-08-13:**
>
> | Entry below | Actual status |
> |---|---|
> | Content tokens not populated | **Resolved differently than described.** Tokens are filled from the HARVEST, never from a default table. Slots the harvest cannot fill are left empty and counted; a section with no sourced content is omitted and recorded in `omitted-sections.json`. "Sourced or empty, never invented." |
> | Nav links redirect to store domain | **Resolved.** Harvested hrefs are joined against built routes (`lib/nav_harvest.localise_hrefs`). Measured on cape-crypto: nav 4/8 rewritten local, the rest genuinely external and counted in `link-mapping.json` |
> | Missing default placeholder assets | **Deliberate, not a bug.** An unresolvable asset is never placeheld — it is recorded unresolved in `image-jobs.json` and the element does not render. `<Image src="">` THROWS in next/image, so an empty src must never ship |
>
> **New, and more important than any of the above:** the design-token chain was
> broken in four places until 2026-08-13, the worst being `globals.css` emitting
> two hardcoded stone constants and no `--accent` at all. See §11 of the
> architecture doc. A template only obeys the design system if it reads the CSS
> custom properties; **4 of 74 do.**

**Content tokens not populated in Supabase templates** (v3.1.0)
- Supabase `code_template` entries use `{content_token}` syntax (e.g., `{feature_1_title}`, `{testimonial_1_quote}`, `{stat_1_value}`) for placeholder content. When templates are pulled directly (bypassing LLM generation in `--industry` mode), these tokens render as visible text on the deployed site.
- Brand tokens (`{{brand.accent}}`) are handled by brand token injection, but content tokens have no population mechanism.
- Fix options: (a) content defaults table per archetype in orchestrate.py, (b) LLM batch content generation per page, (c) Shopify metafield integration
- Workaround: None. All static sections (features, testimonials, stats, FAQ, comparison, badges, logo bar) show raw tokens.

**Nav links redirect to Shopify store domain** (v3.1.0)
- Shopify Storefront API `menu(handle: "main-menu")` returns items with absolute URLs (`https://store.myshopify.com/collections/all`). NavigationWrapper passes these through to the Navigation component without rewriting to relative paths.
- On password-protected dev stores, clicking nav links hits the Shopify password wall and redirects to `/undefined`.
- Fix: URL rewriting in NavigationWrapper.tsx — strip store domain, convert to relative paths.

**Missing default placeholder assets** (v3.1.0)
- Generated sites reference `/logo.svg` and `/placeholder.jpg` in public/ but these files are never created.
- All logo images and fallback product images show as broken.

### Resolved Issues (Keep for Reference)

**Wrapper Section Swallows All Content** (FIXED v2.0.2)
- Was: `extract-reference.js` identified a full-page `<div>` (24243px, 98% of page) as "Section 0". The first-match sectionIndex loop assigned ALL 96/97 text items and ALL 19 images to Section 0 (wrapper). Downstream, `build-site-spec.js` populated Section 0 with all content, leaving sections 1-10 empty. Claude generated filler.
- Fix: Recursive `collectSections()` descends into wrapper divs. Per-section DOM-scoped content extraction (headings, body, CTAs, images via `querySelectorAll`). Post-filter removes remaining wrappers (>70% page + 0 content). Smallest-first sectionIndex assignment. `build-site-spec.js` prefers embedded content over sectionIndex. `archetype-mapper.js` uses embedded content for classification.
- Validation: sofi-health-v3 — 10 sections, text distributed `{1:17, 2:2, 3:13, 4:6, 5:23, 6:4, 7:2, 8:18, 9:4, 10:7}`, all sections show real sofihealth.com content.

**Lossy Telephone Game: 3 layers of LLM interpretation** (FIXED v2.0.0)
- Was: extraction-data.json -> Claude -> preset.md -> Claude -> scaffold.md -> Claude -> sections. Each layer lost fidelity. 7/11 sofi-health sections at 30% confidence with "fallback" method. Component import/export mismatches (GradientShift vs GradientBackground).
- Fix: `build-site-spec.js` produces `site-spec.json` from extraction data with zero AI calls. `stage_scaffold_v2()` reads JSON directly. `stage_sections()` accepts JSON style tokens. Confidence gates block low-confidence sections. Unified component registry has verified export names.
- New artifacts: `site-spec.json` (single SoT), `component-registry.json` (48 components), `confidence-gate.js`, `checkpoint.json`
- Resolved: 2026-02-11

**JSX truncation auto-repair not wired** (FIXED v1.1.1)
- Was: `detectAndRepairTruncation()` existed in post-process.js but was never called from orchestrate.py. 42% of sections truncated on complex builds (gsap-v11: 5 of 12), requiring manual two-pass repair.
- Fix: `_detect_and_repair_truncation()` Python helper calls Node.js subprocess. Wired into section generation loop (Stage 2, immediately after markdown cleanup). Also wired into Stage 5.5 pre-flight validation with auto-repair + file rewrite. Fallback to basic brace check if Node.js call fails.
- Two layers: (1) immediate repair at generation time, (2) safety net at pre-flight validation before deployment.
- Resolved: 2026-02-11

**All 8 v0.9.0 active issues** (FIXED v1.0.0)
- GSAP `from()` SSR invisibility → Hybrid pattern enforced: Framer Motion for entrances, GSAP for interactive/scrub/continuous
- `parse_scaffold()` bold markdown → Regex updated to `\*{0,2}(\w[\w-]*)\*{0,2}`
- Zero-section asset injection bypass → Heuristic distribution fallback in `asset-injector.js`
- Color temperature misclassification → First DOM element priority + dark text cross-check in Claude prompt
- `parse_fonts()` corruption → YAML leak detection + Inter fallback
- `hexToTailwindApprox()` hue loss → Replaced with HSL-based `hexToTailwindHue()` in v0.9.0
- Archetype mapper class blindness → Class-signal matching added in v0.9.0
- Gradient color extraction → `collectGradientColors()` added in v0.9.0
- Additionally: NAV token truncation (6144 budget), JSX truncation detection/repair, `--force` flag, pre-flight validation (Stage 5.5), post-deploy verification
- Resolved: 2026-02-11

**Animation library components broken — 0 of 32 imported** (FIXED v0.7.2)
- Was: Library components copied by stage_deploy but never validated. 6/9 key components had wrong export names, 4 imported from `motion/react` instead of `framer-motion`, 4 required missing `@/lib/utils.ts`, 1 contained wrong component entirely (hover-lift had ZoomImageUI).
- Fix: Rewrote 6 key components (word-reveal, count-up, blur-fade, magnetic-button, hover-lift, magnetic-button), created `@/lib/utils.ts`, refactored 8 sections to import from library, added Phase 0 to animation-upgrade skill. 8 unique components now imported across the build.
- Prevention: Add post-copy `tsc --noEmit` validation to stage_deploy; add registry validator.
- Resolved: 2026-02-10

**Gap 1: Animation data doesn't reach section output** (FIXED v0.5.0)
- Was: hardcoded framer-motion in section prompt, either/or dependency bug
- Fix: animation-injector.js builds engine-specific prompt blocks, engine-branched instruction templates, framer-motion always included + GSAP when detected
- Resolved: 2026-02-09

**Gap 2: No image/media asset pipeline** (FIXED v0.5.0)
- Was: "use neutral gradient div" hardcoded, no asset download mechanism
- Fix: asset-injector.js categorizes extracted images, asset-downloader.js downloads to public/, per-section asset context injected into prompts
- Resolved: 2026-02-09

**NODE_ENV conflict with Next.js 16 build**
- `next build` fails with `useContext null` error when `NODE_ENV=development` is set in shell
- Fix: `NODE_ENV=production npm run build`
- Discovered: nike-golf build (2026-02-09)

**Next.js 15.x CVE blocking on Vercel**
- All Next.js 15.x versions flagged as vulnerable (CVE-2025-66478)
- Fix: Use Next.js 16.1.6 + React 19
- Discovered: farm-minerals-anim build (2026-02-09)

**Framer Motion TypeScript ease type errors**
- `ease: [0.22, 1, 0.36, 1]` typed as `number[]` not `[number, number, number, number]`
- Fix: Add `// @ts-nocheck` to section files + `typescript: { ignoreBuildErrors: true }` in next.config.ts
- Discovered: farm-minerals-anim build (2026-02-09)

**Lenis scroll hijacking conflicts with ScrollTrigger**
- Lenis fights with GSAP ScrollTrigger causing flickering
- Fix: Removed Lenis entirely. Use native browser scroll. `html { scroll-behavior: smooth; }` for anchor scrolling.
- Discovered: farm-minerals-promo rebuild (2026-02-08)

**Claude max_tokens truncation**
- 4096 tokens can truncate complex sections mid-string
- Symptoms: missing closing tags, unclosed strings, incomplete JSX
- Fix: Post-process to detect/repair, or increase token budget for complex sections
- Discovered: farm-minerals-anim build (sections 05, 14)

**parse_fonts() fails on new preset format**
- `parse_fonts()` (orchestrate.py:506) uses regex that can fail on unusual preset formatting
- Symptoms: Preset YAML content leaks into layout.tsx
- Fix: Manually verify layout.tsx after deployment
- Discovered: farm-minerals-anim build (2026-02-09)

---

## Working Conventions

### Build Isolation
- Each project lives in `output/{project}/site/` with its own `package.json` and `node_modules`
- NEVER read files from another project's output directory
- Extraction data uses UUID suffixes for parallel safety: `output/extractions/{project}-{uuid}/`

### Atomic File Writes
- Quality scripts use temp-file + rename pattern to prevent race conditions
- Pattern: `fs.writeFileSync(path + '.tmp-' + Date.now(), content)` then `fs.renameSync()`

### Token Budgets
| Stage | Budget | Model |
|-------|--------|-------|
| Scaffold | 2048 | claude-sonnet-4-5-20250929 |
| Section (simple/framer) | 4096 | claude-sonnet-4-5-20250929 |
| Section (complex GSAP/Lottie) | 6144 | claude-sonnet-4-5-20250929 |
| Section (multi-pattern or component injection) | 8192 | claude-sonnet-4-5-20250929 |
| Section (PINNED-SCROLL archetype) | 8192 (min) | claude-sonnet-4-5-20250929 |
| Section (PRODUCT-SHOWCASE demo-cards) | 8192 (min) | claude-sonnet-4-5-20250929 |
| Review | 4096 | claude-sonnet-4-5-20250929 |

Section token budgets are dynamic — `animation-injector.js` calculates per-section based on pattern complexity, engine, Lottie usage, and whether a library component is being injected (always 8192 for component injection). PINNED-SCROLL and demo-cards archetypes enforce 8192 minimum via orchestrate.py and animation-injector.js respectively.

### Running the Pipeline

```bash
# URL clone mode (most common)
python3 scripts/orchestrate.py my-project --from-url https://example.com --deploy --no-pause

# Manual brief mode
python3 scripts/orchestrate.py my-project --preset artisan-food --deploy

# Resume from a specific stage
python3 scripts/orchestrate.py my-project --preset artisan-food --skip-to sections --deploy

# Test animation detection standalone
node scripts/quality/test-animation-detector.js https://example.com
```

### Deploying to Vercel

```bash
cd output/{project}/site
vercel --yes                    # Preview deployment
vercel --yes --prod             # Production deployment
```

### Common Modification Points

| Task | File(s) to Change |
|------|-------------------|
| Add new preset | `skills/presets/{name}.md` (copy from `_template.md`) |
| Change section prompt | `orchestrate.py:530-580` (stage_sections prompt) |
| Change scaffold prompt | `orchestrate.py:268-302` (stage_scaffold prompt) |
| Add new archetype | `skills/section-taxonomy.md` |
| Add animation pattern | `skills/animation-patterns.md` |
| Change token budget | `orchestrate.py:75-79` (MAX_TOKENS dict) + `animation-injector.js:234-252` (dynamic budgets) |
| Change model | `orchestrate.py:69-73` (MODELS dict) |
| Change Next.js version | `orchestrate.py:680` (deps dict in stage_deploy) |
| Fix dependency resolution | `orchestrate.py:684-700` (engine deps in stage_deploy) |
| Add animation pattern | `animation-injector.js:220-240` (ARCHETYPE_PATTERN_MAP) + `skills/animation-patterns.md` |
| Add animation component | `skills/animation-components/{category}/{name}.tsx` + rerun `node scripts/quality/build-unified-registry.js` + `node scripts/quality/build-animation-registry.js` |
| Rebuild animation registry | `node scripts/quality/build-animation-registry.js` → regenerates all 5 artifacts in `skills/animation-components/registry/` |
| Add image category | `asset-injector.js:21-47` (URL/ALT category signals) + `asset-injector.js:53-68` (section map) |
| Add extraction CSS properties | `scripts/quality/lib/extract-reference.js:73-76` |
| Add class-signal archetype mapping | `archetype-mapper.js` (`CLASS_NAME_SIGNALS` map) |
| Add color hue family | `design-tokens.js` (`HUE_FAMILIES` array) |
| Add UI component detector | `pattern-identifier.js` (`matchUIComponents()` function) |
| Add icon mapping | `icon-mapper.js` (`SEMANTIC_ICON_MAP` + `ARCHETYPE_ICON_DEFAULTS`) |
| Add visual fallback | `asset-injector.js` (`SECTION_VISUAL_FALLBACK_MAP` + `CARD_VISUAL_COMPONENTS`) |
| Add card embedded demo | `animation-injector.js` (`CARD_EMBEDDED_DEMOS`) |
| Add UI component library match | `pattern-identifier.js` (`UI_COMPONENT_LIBRARY_MAP`) |
| Run pattern pipeline tests | `node scripts/quality/test-pattern-pipeline.js` |

---

## System Version

**Current:** v3.1.0 (2026-02-17)

### Changelog
| Version | Date | Changes |
|---------|------|---------|
| v3.1.0 | 2026-02-17 | **Layer 7: RSC Data Flow Wiring.** Wire Shopify Storefront API data into pipeline-generated components. New files: `lib/shopify/NavigationWrapper.tsx` (RSC wrapper for Navigation — fetches SHOP_MENU + SHOP_INFO), `lib/shopify/FooterWrapper.tsx` (RSC wrapper for Footer). New queries in `queries.ts`: SHOP_MENU, SHOP_INFO, COLLECTION_BY_HANDLE, FEATURED_PRODUCTS, SHOP_PAGE + types. Orchestrator: `_inject_nav_props()` / `_inject_footer_props()` (build-time prop injection with displayLinks/displayColumns override pattern), `_patch_showcase_section_props()` (Shopify→template field mapping via `Array.from()`), `_layer7_collections_index_page_content()` (/collections index page), global placeholder token sanitization sweep. Generated routes: `/api/revalidate` (HMAC webhook), `/[page]` (Shopify pages), `/collections` (index). `.env.local` auto-generation from `shopify_config.json`. `next.config.ts` with Shopify CDN `remotePatterns`. **Known issues**: Content tokens (`{feature_1_title}` etc.) not populated, nav URLs are absolute Shopify domain links (need rewriting), no default placeholder assets in public/. |
| v3.0.0 | 2026-02-14 | **Layer 6: Multi-Page App Generation.** With `--industry` (and optional `--site-manifest`), pipeline runs in multi-page mode. New `scripts/lib/site_manifest.py`: manifest schema, `generate_site_manifest()`, `load_site_manifest()`, `filter_nav_footer_from_sections()`. Supabase: `get_industry_metadata(industry)`, `get_all_page_sections(industry)`. Orchestrator: `stage_shared_components()` (Navigation + Footer once), `stage_scaffold_multipage()`, `stage_sections_multipage()`, `stage_assemble_multipage()`. `stage_deploy()` accepts `site_manifest` + `section_files_by_page`; writes layout with Nav/Footer, per-page sections under `src/components/sections/{page_id}/`, route dirs `collections/[handle]/`, `products/[handle]/`, `pages/[handle]/`, `not-found.tsx`. Legacy path (`--preset` only) unchanged. See `plans/active/Layer_6_Multi_Page_App_Generation.md`. |
| v2.0.2 | 2026-02-11 | **Content Extraction Fix: Recursive Section Detection + DOM-Scoped Content.** Root cause: wrapper `<div>` covering entire page was identified as "Section 0," causing ALL text (96/97 items) and ALL images (19/19) to be assigned to it — leaving all other sections empty. Claude then generated filler instead of real content. **Fix 1 (extract-reference.js):** Recursive `collectSections()` descends into wrapper elements (>80% page height with multiple tall children) instead of treating them as sections. **Fix 2:** Per-section DOM-scoped content extraction — headings, body text, CTAs, images extracted via `querySelectorAll()` inside each section element (DOM containment, not rect overlap). Each section now carries embedded `content: { headings, body_text, ctas, image_count }` and `images[]`. **Fix 3:** Post-filter removes any remaining wrapper sections (>70% page height + zero content). Re-indexes after removal. **Fix 4:** Smallest-first sectionIndex assignment — `sectionsBySize` sort ensures inner sections match before outer wrappers for text/image/DOM elements. **Fix 5 (archetype-mapper.js):** Uses embedded per-section content for classification. New methods: `embedded-heading-keyword`, `embedded-body-keyword`, `structural-images`, `structural-multi-heading`, `structural-cta`. HERO always assigned to first section. **Fix 6 (build-site-spec.js):** Prefers embedded per-section content/images over sectionIndex-based filtering. Falls back to sectionIndex only for legacy extraction data. Validated: sofi-health-v3 build — 10 real sections detected (1 wrapper filtered), text distributed across all sections, real content from sofihealth.com renders in every section. |
| v2.0.1 | 2026-02-11 | **v2 Pipeline Wiring Fix.** Critical fix: `stage_url_extract()` now actually calls `build-site-spec.js` and returns 5 values (was returning 4, causing crash). `stage_sections()` now uses JSON style tokens from `site-spec.json` when available (was ignoring `site_spec` param entirely). `--skip-to` path now uses rich sections from `site-spec.json` instead of `parse_scaffold()`. Legacy `registry.json` fallback in `stage_deploy` removed. Invalid package name filter added (`@gsap`, `motion` blocked from npm deps). `orchestrate.py` 2417->2504 lines. Validated with sofi-health-v2 build: 11 sections, deterministic scaffold, deterministic review (0 errors), API retry caught 529 overload. |
| v2.0.0 | 2026-02-11 | **Deterministic Pipeline: Eliminate the Lossy Telephone Game.** 6-phase architectural rewrite. **Phase 0 (Extraction):** Cookie modal dismissal (16 selectors), full-page lazy scroll before measurement, sectionIndex on all images and text content. `extract-reference.js` 706->824 lines. **Phase 1 (Registry):** New `build-unified-registry.js` auto-generates `component-registry.json` (48 components with verified export_name + import_statement). Legacy `registry.json` deleted. `animation-injector.js`, `asset-injector.js`, `pattern-identifier.js` all read from unified registry. 66 test assertions pass. **Phase 2 (JSON Spec):** New `build-site-spec.js` (587 lines) — deterministic style token extraction, section building with sectionIndex, component matching from registry. Produces `site-spec.json` (single source of truth) with zero AI calls. New `stage_scaffold_v2()` reads site-spec directly (no Claude scaffold call). `stage_sections()` gains JSON style tokens path alongside legacy compact header. **Phase 3 (Confidence):** New `confidence-gate.js` (180 lines) — 4-tier confidence system (HIGH/MEDIUM/LOW/NONE), gates sections below 0.5 for re-analysis, builds Claude Vision prompt for low-confidence batches. Wired into build-site-spec.js. **Phase 4 (Deterministic Review):** New `stage_review_v2()` — deterministic checks (use-client, export-default, brace balance, emoji, placeholder URLs, import validity, truncation). Writes both review.json and review.md. Zero Claude calls. **Phase 5 (Resilience):** `call_claude_with_retry()` wrapper (90s timeout, 3 retries with exponential backoff). `save_checkpoint()`/`load_checkpoint()` after every stage. `--clean` flag for directory deletion, `--force` now non-destructive. `orchestrate.py` 1404->2417 lines. |
| v1.2.0 | 2026-02-11 | **Universal Asset Intelligence Pipeline.** Extended the "detect, match, insert, fallback" chain to all visual asset types. **Phase 1 (Prompt Hardening):** Emoji ban in all 3 template files (section-prompt, section-instructions-gsap, section-instructions-framer). Lucide React icon mapping reference (12 section types, ~60 icons). Logo bar rendering rules (styled text pills when no URLs). `lucide-react` added as always-included dependency. **Phase 2 (Extraction Upgrades):** Inline SVG extraction in extract-reference.js (logo + icon SVGs with size filtering). Icon library detection (Lucide, Font Awesome, Heroicons, Material Icons). Enhanced logo image extraction from brand containers. New fields in extraction-data.json: `assets.svgs`, `assets.iconLibrary`, `assets.logos`. **Phase 3a (Icon Mapping):** New `icon-mapper.js` module — `SEMANTIC_ICON_MAP` (~120 concepts), `ARCHETYPE_ICON_DEFAULTS` (16 archetypes), `mapExtractedIcons()`, `getIconsForSection()`, `buildIconContextBlock()`. **Phase 3b (Visual Fallback):** `SECTION_VISUAL_FALLBACK_MAP` (12 archetypes), `CARD_VISUAL_COMPONENTS` (8 decorative components), `getVisualFallback()` in asset-injector.js. **Phase 3c (Card Demos):** `CARD_EMBEDDED_DEMOS` (20 GSAP plugin mappings), `DEMO_FALLBACK_SEQUENCE` (6 components), `buildCardEmbeddedDemos()` in animation-injector.js. **Phase 3d (UI Injection):** `UI_COMPONENT_LIBRARY_MAP` (25 patterns), `matchUIComponents()`, `buildUIComponentBlock()`, `searchIndexLookup()` in pattern-identifier.js. **Phase 4 (Pipeline Wiring):** 5 new Python helper functions in orchestrate.py (`get_icon_context`, `get_visual_fallback`, `get_card_embedded_demos`, `get_ui_component_matches`, enriched identification with icon/logo/SVG data). Section prompt gains `icon_block`, `visual_fallback_block`, `card_embed_block`, `ui_component_block`. Extra component manifest (`extra-components.json`) saved per build, consumed by stage_deploy to copy visual fallback and demo components alongside animation components. |
| v1.1.2 | 2026-02-11 | **VISION.md Sync & PINNED-SCROLL Reclassification.** Track A: PINNED-SCROLL removed as section archetype (25 archetypes, was 26). Pinned horizontal scroll reclassified as animation component/technique applicable to PRODUCT-SHOWCASE, FEATURES, GALLERY, HERO, HOW-IT-WORKS. `gsap-pinned-horizontal.tsx` component unchanged. orchestrate.py triggers pinned scroll rules on animation assignment (not archetype name). section-instructions-gsap.md reframed as technique. Track B: VISION.md added to doc-sync-checklist, close-checklist, and CLAUDE.md update protocol. Track C: VISION.md one-time refresh — Module 2 stats updated (35 presets, 25 archetypes, 1034 animation components, 13 builds, 8 plans), Phase 0 status corrected (page templates not started), pipeline maturation documented. |
| v1.1.1 | 2026-02-11 | JSX truncation auto-repair wired into pipeline. New `_detect_and_repair_truncation()` helper in orchestrate.py calls `post-process.js:detectAndRepairTruncation()` via Node.js subprocess. Wired at two layers: (1) Stage 2 section generation loop — repairs truncation immediately after Claude returns, before "use client" and export default checks; (2) Stage 5.5 pre-flight validation — second-pass safety net that auto-repairs and rewrites truncated section files, with fallback to basic brace balance if Node.js unavailable. Closes the #1 reliability issue (42% truncation rate on gsap-v11). |
| v1.1.0 | 2026-02-11 | Pinned Horizontal Scroll & Showcase Card Differentiation. **Track A:** New `gsap-pinned-horizontal.tsx` component (176 lines, ScrollTrigger pin+scrub, gsap.matchMedia() mobile fallback, progress indicator, snap-to-panel). New PINNED-SCROLL archetype in section-taxonomy (4 variants: horizontal-showcase, animated-scene, timeline-journey, comparison-before-after). Detection in animation-detector (`detectPinnedHorizontalScroll`), gsap-extractor (`_pinnedHorizontalScroll`), pattern-identifier (`pinnedScrollDetected`). Scaffold prompt instruction #5 for PINNED-SCROLL recommendation. Section prompt `pinned_scroll_block` with containerAnimation rules. 8192 min token budget for PINNED-SCROLL. Updated animation-patterns.md with `pinned-horizontal-scene` pattern + "K. Card Micro-Animation Effects". Updated section-instructions-gsap.md with pinned scroll rules. **Track B:** PRODUCT-SHOWCASE `demo-cards` variant. `CARD_ANIMATION_MAP` (8 plugin-specific micro-animations). `buildCardAnimationBlock()` in animation-injector.js. 8192 min token for demo-cards. Animation registry rebuilt: 1,034 components. 66/66 tests pass. Validated with gsap-v11 build (12 sections, both new archetypes used). |
| v1.0.0 | 2026-02-11 | GSAP Ecosystem Integration & System Stability. **Phase 1:** 8 bug fixes — parse_scaffold bold markdown, GSAP from() SSR hybrid rule, NAV/FOOTER 6144 token budget, zero-section asset heuristic fallback, color temp misclassification guard, parse_fonts YAML leak detection, JSX truncation detection+repair, --force CLI flag. **Phase 2:** 20 GSAP plugin detection (window globals + script pattern matching in animation-detector.js), plugin call classification in gsap-extractor.js (SplitText/Flip/DrawSVG/MorphSVG/MotionPath/Draggable/CustomEase/Observer/ScrambleText/matchMedia), plugin pattern matching in pattern-identifier.js. **Phase 3:** 22 new animation patterns in animation-patterns.md, full plugin instructions in section-instructions-gsap.md, 11 new animation components (splittext-chars/words/lines, scramble-text, flip-grid-filter, flip-expand-card, drawsvg-reveal, morphsvg-icon, motionpath-orbit, draggable-carousel, observer-swipe). **Phase 4:** Plugin-aware injection blocks in animation-injector.js, gsap-setup.ts generation in stage_deploy, plugin context in section prompts, plugin-aware preset generation in url-to-preset.js, token budget +2048 for SplitText/Flip sections. **Phase 5:** Pre-flight validation (Stage 5.5), post-deploy verification (validate-build.js), component copy validation with auto-fix for motion/react imports. 66-assertion test harness. |
| v0.9.0 | 2026-02-11 | Pattern Identification Pipeline: New identification layer (Stage 0d) between extraction and generation. Color intelligence: hue-aware Tailwind mapping (`hexToTailwindHue`), gradient color extraction (`collectGradientColors`), color system classification (`identifyColorSystem`), per-section profiling (`profileSectionColors`). Archetype intelligence: class-signal matching (`CLASS_NAME_SIGNALS`), content-aware variant selection, confidence-based gap flagging. New `pattern-identifier.js`: animation pattern matching via registry search index, UI component detection (logo-marquee, video-embed, card-grid, accordion, tabs), section mapping, gap aggregation with extension tasks. Preset format extended with `accent_secondary`, `accent_tertiary`, `section_accents`. 688 insertions across 10 files. Test harness: 57 assertions. Validated against live gsap.com. |
| v0.8.0 | 2026-02-10 | Animation Registry: `build-animation-registry.js` analyzes all 1022 components (36 curated + 986 21st-dev), generates 5 artifacts: `animation_registry.json` (1.6MB, full analysis), `animation_taxonomy.json` (controlled vocabulary), `animation_search_index.json` (query-optimised by intent/trigger/section/framework), `animation_capability_matrix.csv`, `analysis_log/` (1022 .md files). Classification: 335 animation, 613 UI, 74 hybrid. Fixed 5 broken source library components. Zero quality gate failures. |
| v0.7.2 | 2026-02-10 | Animation library import fix: rewrote 6 broken components (word-reveal, count-up, blur-fade, magnetic-button, hover-lift), created @/lib/utils.ts, refactored 8 sections to use library imports instead of inline copies. 8 unique animation components now actively imported. Updated animation-upgrade skill with Phase 0 component inventory and import-first mandate. |
| v0.7.1 | 2026-02-10 | Generated reference docs: `scripts/generate-docs.js` produces `docs/api-reference.md` (488 lines, all exported functions with signatures + caller graph), `docs/dependencies.md` (NPM packages + config constants), `docs/data-flow.md` (module I/O + require graph). Integrated into close checklist. |
| v0.7.0 | 2026-02-10 | Animation classification: registry schema upgrade (intensity + affinity on 36 components), 11 VengenceUI components extracted (character-flip, border-beam, glow-border, staggered-grid, spotlight-follow, cursor-trail, page-loader, perspective-grid, aurora-background + count-up/marquee replacements), `selectAnimation()` affinity algorithm with deduplication, cn() utility generation in stage_deploy, new `effect/` and `background/` component categories |
| v0.6.0 | 2026-02-09 | Animation component library: registry (27 patterns), 3-tier injection (library > extracted > snippet), gsap-extractor, animation-summarizer, per-section grouping, component copy in stage_deploy |
| v0.5.0 | 2026-02-09 | Data injection pipeline: animation injector, asset injector/downloader, engine-branched prompts, dynamic token budgets, dependency fix |
| v0.4.1 | 2026-02-09 | Doc-sync integration into retrospective skill; CLAUDE.md, README.md, .cursorrules refresh |
| v0.4.0 | 2026-02-09 | Animation extraction integration (detector, analyzer, preset injection) |
| v0.3.0 | 2026-02-08 | URL clone mode (`--from-url`), auto-generated presets and briefs |
| v0.2.0 | 2026-02-08 | Multi-agent builds, build isolation, Vercel deployment, 18 industry presets |
| v0.1.0 | 2026-02-08 | Initial pipeline: brief → scaffold → sections → assembly → review |

---

## Generated Reference Docs

Run `node scripts/generate-docs.js` to regenerate. Always current.
- `docs/api-reference.md` — Function signatures, params, return types, caller graph
- `docs/dependencies.md` — NPM packages, versions, configuration constants
- `docs/data-flow.md` — Module input/output contracts, require graph, artifact flow

---

## Build Close Protocol

When a plan is complete, follow `plans/_close-checklist.md` or this summary:

1. **Verify** — all success criteria met, code committed
2. **Retrospective** — create `retrospectives/YYYY-MM-DD-{name}.md` with: what shipped, what worked, what didn't, carry-forward items
3. **Move plan** — `mv plans/active/{name}.md plans/completed/`
4. **Update CLAUDE.md** — use the checklist below
5. **Update dependent docs** — `.cursorrules` if stages changed, `README.md` if user-facing info changed

## CLAUDE.md Update Protocol

After every build, integration session, or plan close:

1. Run the retrospective skill to capture session learnings
2. Update this file using the checklist below:
   - [ ] **Quick Reference**: version bumps, model changes, dependency versions
   - [ ] **File Map**: new/deleted/moved files with line counts
   - [ ] **Pipeline Stages**: function signatures, line numbers if changed
   - [ ] **Current System State**: completed builds, move closed plans from Active to Completed
   - [ ] **Known Issues**: add new issues, mark resolved ones
   - [ ] **System Version**: bump version, add changelog entry
3. If pipeline stages changed, also update `.cursorrules`
4. If user-facing info changed (presets, tech stack), also update `README.md`
5. If module capabilities, phase status, or build count changed, also update `VISION.md`

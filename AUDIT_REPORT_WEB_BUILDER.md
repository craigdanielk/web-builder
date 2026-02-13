# AUDIT REPORT: Aurelix Web Builder (Module 2)

**Audit Date:** 2026-02-12
**System Version:** v2.0.2 (as documented in CLAUDE.md; changelog says v2.0.0 is "Current")
**Auditor:** System Auditor (automated)
**Scope:** Interface contract, automation readiness, preset coverage, pipeline integration points

---

## 1. Executive Summary

The Web Builder is production-proven with **15 completed builds** (13 deployed to Vercel, 2 local validation). Its interface contract is clean: it consumes a **brief markdown + preset markdown** and produces a **deployable Next.js project**. The pipeline can run fully unattended (`--no-pause --deploy`) but Vercel deployment itself is a **manual post-step** (`vercel --yes` in the output directory). For Calculator integration, the critical gap is that `orchestrate.py` is CLI-only — there is no Python-importable API, so upstream orchestrators must invoke it via `subprocess`. The file-based interface (`briefs/{project}.md` + `skills/presets/{preset}.md`) is simple enough for any upstream service to produce.

---

## 2. Interface Contract (Detailed)

### 2.1 INPUTS

#### Input 1: Brief (`briefs/{project}.md`) — REQUIRED

Markdown file with this exact structure:

```markdown
# Brief: [Project Name]

## Business
[What the business does, where they're located, what makes them unique]

## What They Need
[The website's primary purpose and goals]

## Key Requirements
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

## Target Audience
- [Audience segment 1]
- [Audience segment 2]

## Brand Personality
- [Trait 1]
- [Trait 2]
- [Trait 3]

## Specific Requests
- [Any specific design, content, or functional requests from the client]

## Technical Notes
- [Platform, performance requirements, integrations, constraints]
```

**All 7 sections are expected.** The brief is consumed by the scaffold stage (Stage 1) to determine section sequence and content direction. It is the primary interface between Calculator (Module 1) and Web Builder (Module 2).

#### Input 2: Preset (`skills/presets/{preset}.md`) — REQUIRED

Markdown file defining visual design system + section sequence. Structure:

| Section | Purpose | Required? |
|---------|---------|-----------|
| `# Preset: [Name]` | Title + industries list | Yes |
| `## Default Section Sequence` | Ordered archetype list in code block | Yes |
| `## Style Configuration` | Full YAML block with palette, typography, whitespace, radius, animation, density | Yes |
| `## Compact Style Header` | Single-block summary injected into every section prompt | Yes |
| `## Content Direction` | Tone, hero copy pattern, CTA language | Yes |
| `## Photography / Visual Direction` | Image guidance | Yes |
| `## Known Pitfalls` | Industry-specific warnings | Optional |
| `## Maintenance Log` | Change history | Optional |

**Key YAML fields in Style Configuration:**

```yaml
color_temperature: warm | cool | neutral
palette:
  bg_primary: [tailwind class]
  bg_secondary: [tailwind class]
  accent: [tailwind class]
  accent_hover: [tailwind class]
  accent_secondary: [optional]
  accent_tertiary: [optional]
  text_primary: [tailwind class]
  text_heading: [tailwind class]
  border: [tailwind class]
section_accents: [optional per-section overrides]

typography:
  heading_font: [Google Font name]
  body_font: [Google Font name]
  heading_weight: [number]
  body_weight: [number]
  scale_ratio: [number]

animation_engine: framer-motion | gsap
animation_intensity: none | subtle | moderate | expressive
gsap_plugins: [optional list]
```

#### Input 3: `architecture.json` — OPTIONAL (for Shopify migrations)

Placed at `output/{project}/architecture.json`. Read by Web Builder for:
- Page template count
- Collection structure (for navigation)
- Market configuration (locale routing)
- Page list (landing pages to generate)

**Not yet consumed by orchestrate.py** — the interface is defined in VISION.md but the multi-page generation code is NOT STARTED.

#### Input 4: `site-spec.json` — AUTO-GENERATED (URL clone mode only)

Produced by `build-site-spec.js` during Stage 0. Contains extracted style tokens, section definitions, and component mappings as structured JSON. **This is the v2.0.0 deterministic path** — replaces the "lossy telephone game" of extraction → Claude → preset → Claude → scaffold → Claude → sections.

### 2.2 OUTPUTS

| Artifact | Path | Format | Description |
|----------|------|--------|-------------|
| Scaffold | `output/{project}/scaffold.md` | Markdown | Numbered section list with archetypes and content direction |
| Sections | `output/{project}/sections/{NN}-{name}.tsx` | React/TSX | Individual section components |
| Page | `output/{project}/page.tsx` | React/TSX | Assembled page importing all sections |
| Review | `output/{project}/review.md` (or `review.json`) | Markdown/JSON | Consistency check results |
| Site | `output/{project}/site/` | Next.js project | Complete deployable project with `package.json`, `src/`, `public/` |
| Checkpoint | `output/{project}/checkpoint.json` | JSON | Pipeline progress state (stage, timestamp) |
| Extraction data | `output/extractions/{project}-{uuid}/` | JSON + screenshots | Raw extraction artifacts (URL mode only) |
| Gap report | `output/{project}/gap-report.json` | JSON | Pattern identification gaps (URL mode only) |
| Identification | `output/{project}/identification.json` | JSON | Color/archetype/animation analysis (URL mode only) |
| Site spec | `output/{project}/site-spec.json` | JSON | Deterministic style + section spec (URL mode only) |
| Extra components | `output/{project}/extra-components.json` | JSON | Visual fallback/demo components manifest |

**The critical output for downstream integration is `output/{project}/site/`** — a fully scaffolded Next.js 16.1.6 project with:
- `package.json` with all dependencies
- `src/components/sections/*.tsx` — generated sections
- `src/components/animations/*.tsx` — animation library components
- `src/app/page.tsx` — main page
- `src/app/layout.tsx` — layout with font imports
- `src/app/globals.css` — Tailwind + engine-specific styles
- `src/lib/utils.ts` — `cn()` utility
- `public/images/` — downloaded assets
- `public/lottie/` — Lottie animation files
- `node_modules/` — installed dependencies

### 2.3 Programmatic Invocation

**Can `orchestrate.py` be imported and called from Python?**

**No — CLI only.** The pipeline is invoked via:

```bash
python3 scripts/orchestrate.py <project-name> [flags]
```

The `main()` function uses `argparse` and calls `sys.exit()` on errors. Individual stage functions (`stage_scaffold()`, `stage_sections()`, `stage_deploy()`, etc.) ARE importable in theory, but:
- They depend on module-level globals (`ROOT`, `SKILLS_DIR`, `OUTPUT_DIR`, etc.)
- They call `sys.exit(1)` on failures instead of raising exceptions
- The `call_claude()` helper instantiates `Anthropic()` client per-call
- No `__init__.py` exists for the `scripts/` package

**Recommendation for pipeline integration:** Use `subprocess.run()` to call `orchestrate.py`. This is consistent with the Aurelix design principle: "Each tool exposes a CLI interface. The pipeline orchestrator calls them sequentially via subprocess."

### 2.4 Environment Variables

| Variable | Source | Required? | Purpose |
|----------|--------|-----------|---------|
| `ANTHROPIC_API_KEY` | `.env` file or environment | **Yes** | Claude API access (Sonnet 4.5) |
| `NODE_ENV` | Shell environment | No (but critical) | Must NOT be `development` during `next build` |
| `PATH` | System | Yes | Must include `node`, `python3`, `npm` |

The `.env` loader (`load_env_file()`) reads `web-builder/.env` and sets variables only if not already in `os.environ`. The Anthropic client uses `ANTHROPIC_API_KEY` implicitly (SDK default behavior).

**No Vercel token is required** — `vercel` CLI uses interactive login or `VERCEL_TOKEN` if set, but this is not managed by orchestrate.py.

### 2.5 Two Modes of Operation

| Mode | Flag | When to Use | What Happens |
|------|------|-------------|--------------|
| **URL Clone** | `--from-url <URL>` | Cloning an existing site's visual DNA | Stage 0 extracts via Playwright → auto-generates preset + brief → standard pipeline |
| **Brief-Driven** | `--preset <name>` | Building from a human/Calculator brief | Reads existing brief + preset → scaffold → sections → assemble → review → deploy |

**For Calculator integration, use Brief-Driven mode.** The Calculator would:
1. Generate `briefs/{project}.md` (matching the template format above)
2. Either select an existing preset or generate one at `skills/presets/{project}.md`
3. Call: `python3 scripts/orchestrate.py {project} --preset {preset} --deploy --no-pause`

---

## 3. Automation Readiness Assessment

### 3.1 Can It Run Fully Unattended?

**Yes, with `--no-pause --deploy`.** The only human intervention point is the scaffold review checkpoint (Stage 1), which is skipped with `--no-pause`.

Full unattended command:
```bash
python3 scripts/orchestrate.py my-project --preset artisan-food --deploy --no-pause
```

Or for URL clone:
```bash
python3 scripts/orchestrate.py my-project --from-url https://example.com --deploy --no-pause
```

### 3.2 Human Intervention Points

| Point | Stage | Can Skip? | How |
|-------|-------|-----------|-----|
| Scaffold review | Stage 1 | Yes | `--no-pause` flag |
| Pre-flight validation failure | Stage 5.5 | Yes | `--force` flag |
| Preset selection (if no `--preset`) | Pre-pipeline | Yes | Always pass `--preset` |
| Vercel deployment | Post-pipeline | **No** | Must run `vercel --yes` manually |
| Project collision detection | Pre-pipeline | Partial | Use `--clean` to remove existing output |

**Critical finding:** `stage_deploy` does NOT run `vercel`. It creates the Next.js project at `output/{project}/site/`, runs `npm install`, then prints instructions. Vercel deployment requires a separate manual step:

```bash
cd output/{project}/site && vercel --yes
```

**For full automation, the upstream orchestrator must add this step after `orchestrate.py` completes.**

### 3.3 Build Timing

Based on retrospectives and code analysis:

| Phase | Estimated Duration | Notes |
|-------|-------------------|-------|
| Stage 0 (URL extraction) | 30-90 seconds | Playwright headless Chrome + 4 Node.js scripts |
| Stage 0d (Pattern identification) | 5-15 seconds | Pure computation, no API calls |
| Stage 1 (Scaffold) | 5-10 seconds | 1 Claude API call, 2048 tokens |
| Stage 2 (Sections) | 2-5 minutes | 8-15 sequential Claude API calls, 4096-8192 tokens each |
| Stage 3 (Assembly) | <1 second | Pure code generation, no API |
| Stage 4 (Review) | 5-15 seconds | 1 Claude call (legacy) or deterministic (v2) |
| Stage 5 (Deploy) | 30-60 seconds | File generation + `npm install` |
| **Total (URL mode)** | **4-8 minutes** | |
| **Total (Brief mode)** | **3-6 minutes** | |

API cost per build: **~$0.55-1.15** (Claude Sonnet 4.5).

### 3.4 Failure Rate and Causes

Based on 15 builds and retrospectives:

| Failure Type | Frequency | Auto-Recovery? | Notes |
|--------------|-----------|----------------|-------|
| API timeout/overload | Occasional | **Yes** — `call_claude_with_retry()` with 3 retries + exponential backoff | 529 overload caught in sofi-health-v2 build |
| JSX truncation | Was 42% pre-v1.1.1 | **Yes** — two-layer auto-repair (generation-time + pre-flight) | Fixed in v1.1.1 |
| Import mismatches | Rare post-v2.0.0 | **Yes** — unified component registry with verified export names | Fixed in v2.0.0 |
| Content in wrong sections | Was common | **Yes** — recursive section detection + DOM-scoped extraction | Fixed in v2.0.2 |
| Color misclassification | Occasional | Partial — Claude prompt guard + DOM priority | Edge cases remain |
| Webflow/SPA extraction | Rare | **No** — 0 sections detected in some SPAs | Known limitation |

**Overall reliability:** High for brief-driven mode (well-defined inputs). URL clone mode has inherent variance from extraction quality.

### 3.5 Does `--deploy` Auto-Deploy to Vercel?

**No.** The `--deploy` flag creates the Next.js project scaffold and runs `npm install`. It does NOT invoke `vercel`. The user/orchestrator must separately run `vercel --yes` (or `vercel --yes --prod` for production) inside the site directory.

---

## 4. Preset Coverage Table

### 4.1 Industry Presets (18 general-purpose)

| # | Preset File | Industry | Animation Engine |
|---|-------------|----------|-----------------|
| 1 | `artisan-food.md` | Coffee, bakery, artisan food | framer-motion |
| 2 | `beauty-cosmetics.md` | Beauty, skincare, cosmetics | — |
| 3 | `construction-trades.md` | Construction, trades | — |
| 4 | `creative-studios.md` | Design studios, agencies | — |
| 5 | `education.md` | Schools, courses, e-learning | — |
| 6 | `events-venues.md` | Events, conferences, venues | — |
| 7 | `fashion-apparel.md` | Fashion, clothing, apparel | — |
| 8 | `health-wellness.md` | Health, wellness, fitness | gsap |
| 9 | `home-lifestyle.md` | Home goods, lifestyle products | — |
| 10 | `hotels-hospitality.md` | Hotels, hospitality, travel | — |
| 11 | `jewelry-watches.md` | Jewelry, watches, luxury accessories | — |
| 12 | `medical-dental.md` | Medical practices, dental | — |
| 13 | `nonprofits-social.md` | Nonprofits, social causes | — |
| 14 | `outdoor-adventure.md` | Outdoor gear, adventure tourism | — |
| 15 | `pet-products.md` | Pet products, veterinary | — |
| 16 | `professional-services.md` | Law, consulting, accounting | — |
| 17 | `real-estate.md` | Real estate, property | — |
| 18 | `restaurants-cafes.md` | Restaurants, cafes, dining | — |

### 4.2 Project-Specific Presets (21 from builds/tests)

| # | Preset File | Source | Engine |
|---|-------------|--------|--------|
| 19 | `saas.md` | Industry preset | — |
| 20 | `sports-fitness.md` | Industry preset | — |
| 21 | `nike-golf.md` | Nike Golf clone | gsap |
| 22 | `nicola-romei.md` | Portfolio clone | gsap |
| 23 | `cascaid-health.md` | Health site clone | gsap+framer |
| 24 | `turm-kaffee-v3.md` | Coffee shop iteration | framer-motion |
| 25 | `farm-minerals-promo-v2.md` | Agricultural tech | gsap |
| 26 | `farm-minerals-anim.md` | Agricultural + Lottie | gsap |
| 27 | `farm-minerals-v2.md` | Farm minerals iteration | — |
| 28 | `farm-minerals-v3.md` | Farm minerals iteration | — |
| 29 | `farm-minerals-v4.md` | Farm minerals iteration | — |
| 30 | `farm-minerals-v5.md` | Farm minerals iteration | — |
| 31 | `farm-minerals-v6.md` | Farm minerals iteration | — |
| 32 | `arclin.md` | Project-specific | — |
| 33 | `gsap-homepage.md` | GSAP.com clone | gsap |
| 34 | `gsap-v9-test.md` | Pipeline test | gsap |
| 35 | `gsap-v10.md` | Pipeline test | gsap |
| 36 | `gsap-v11.md` | Pipeline test | gsap |
| 37 | `sofi-health.md` | Health site v1 | — |
| 38 | `sofi-health-v2.md` | v2.0.1 validation | framer-motion |
| 39 | `sofi-health-v3.md` | v2.0.2 validation | framer-motion |

**Total: 39 preset files** (excluding `_template.md`). Of these, ~18-20 are reusable industry presets; the rest are project-specific or test iterations.

### 4.3 Industry Coverage Gaps

| Missing Industry | Priority | Notes |
|------------------|----------|-------|
| Automotive / Dealerships | Medium | High-value vertical |
| Legal / Law Firms | Low | Covered partially by `professional-services` |
| Food & Beverage (non-artisan) | Low | Partially covered by `restaurants-cafes` |
| Technology / Electronics | Medium | `saas.md` covers SaaS but not hardware/electronics retail |
| Children / Baby Products | Low | — |
| Sustainability / Eco | Low | Could be a modifier on existing presets |
| Luxury / High-End General | Medium | `jewelry-watches` covers one vertical |
| Grocery / Supermarket | Low | — |
| Automotive Parts | Low | — |
| Financial Services / Fintech | Medium | — |

### 4.4 Auto-Generating Presets from Calculator Output

**What would it take?**

The Calculator already outputs `brief.md` which contains brand personality, color palette, typography, and imagery style. To auto-generate a preset:

1. **Match existing preset** — Use the industry classification from Calculator to select the closest industry preset as a base template
2. **Override style tokens** — Replace the YAML palette, typography, and animation values with extracted brand identity from the source site
3. **The URL clone path already does this** — `url-to-preset.js` extracts design tokens from a URL and generates a preset. The Calculator could reuse this logic by calling `url-to-preset.js` with the source URL, or by writing the preset YAML directly from its brand identity analysis

**Effort estimate:** Low (1-2 days). The existing `url-to-preset.js` script is the template. Calculator just needs to output the same YAML structure.

---

## 5. Integration Points for Pipeline Orchestration

### 5.1 Calculator → Web Builder

```
Calculator Output:                    Web Builder Input:
────────────────                      ─────────────────
architecture.json  ─────────────────→ output/{project}/architecture.json (NOT YET CONSUMED)
brief.md           ─────────────────→ briefs/{project}.md ✅ READY
products.csv       ─────────────────→ (not consumed — Module 3)
media-manifest.json ────────────────→ (not consumed — Module 3)
[auto-generated preset] ────────────→ skills/presets/{project}.md ✅ READY
```

**Current state:**
- `brief.md` interface is **fully operational** — format is well-defined, consumed by scaffold stage
- `preset` interface is **fully operational** — format is well-defined with YAML template
- `architecture.json` interface is **defined but not wired** — orchestrate.py does not read it yet; needed for multi-page generation (Phase 0 remaining work)

**Integration command:**
```bash
# 1. Calculator writes files
cp calculator-output/brief.md web-builder/briefs/{project}.md
cp calculator-output/preset.md web-builder/skills/presets/{project}.md

# 2. Web Builder runs
cd web-builder
python3 scripts/orchestrate.py {project} --preset {project} --deploy --no-pause

# 3. Vercel deployment (not done by orchestrate.py)
cd output/{project}/site
vercel --yes --prod
```

### 5.2 Brief Auto-Generation Path

**Yes, it exists.** Two paths:

1. **URL Clone mode** — `url-to-brief.js` auto-generates `briefs/{project}.md` from a URL extraction
2. **Calculator** — VISION.md defines `brief.md` as a Calculator output artifact with exact format

The brief format from Calculator (VISION.md) adds two fields not in the Web Builder template:
- `## Brand Personality` includes "Color palette, typography, imagery style, tone extracted from source"
- `## Technical Notes` includes "Platform: Shopify headless via Storefront API. Markets. Currency. Product count."

These are **compatible** with the Web Builder's brief parser — extra detail in any section is consumed by the scaffold prompt (Claude reads the whole brief).

### 5.3 Commerce Contract (`skills/commerce-contract.ts`)

This file defines the **type contract between Module 2 and Module 3**:

- **Core Shopify types:** `ShopifyProduct`, `ShopifyVariant`, `ShopifyCollection`, `ShopifyCart`, `ShopifyMenu`
- **Section prop interfaces:** `ProductGridProps`, `ProductDetailProps`, `FeaturedProductsProps`, `CollectionHeroProps`, `NavigationProps`, `FooterProps`
- **Section data modes:** `SECTION_DATA_MODES` maps 25 archetypes to `static` / `prop-driven` / `hybrid`
- **Page template metadata:** `PAGE_TEMPLATES` maps 9 page intents to route patterns and required data

**Current integration status:** The commerce contract TypeScript file EXISTS and is comprehensive, but the Web Builder does NOT yet generate prop-driven commerce sections. This is the Phase 0 remaining work (page template structures + section prompt updates). Currently, ALL sections are generated as static (hardcoded content).

**Shopify product data connection:** Products flow from Shopify Storefront API → Module 3 → component props. The Web Builder generates the visual shell; Module 3 provides the data layer. The commerce-contract.ts serves as the formal interface.

### 5.4 Web Builder → Bulk Importer (post-deploy)

After Web Builder deploys to Vercel, the Bulk Importer needs:

| Data | Source | Notes |
|------|--------|-------|
| Vercel project URL | Output of `vercel --yes` | Not captured by orchestrate.py; must be captured by upstream orchestrator |
| Deployed site structure | `output/{project}/site/src/` | Page routes, section components |
| Design tokens | Preset YAML or `site-spec.json` | For Module 3 to inherit styling |

**Gap:** orchestrate.py does not capture or output the Vercel deployment URL. An upstream orchestrator would need to parse the `vercel --yes` stdout or use `vercel inspect` to get the URL.

---

## 6. Current State Snapshot

### 6.1 Build History

| # | Project | Date | Mode | Engine | Deployed To | Notes |
|---|---------|------|------|--------|------------|-------|
| 1 | turm-kaffee-v2 | 2026-02-08 | preset | framer-motion | Vercel | First build |
| 2 | bluebird-coffee-roastery | 2026-02-08 | preset | framer-motion | Vercel | |
| 3 | farm-minerals-promo | 2026-02-08 | preset | gsap | Vercel | |
| 4 | nike-golf | 2026-02-09 | preset | gsap | Vercel | |
| 5 | farm-minerals-anim | 2026-02-09 | preset | gsap | Vercel | Pre-injection pipeline |
| 6 | farm-minerals-v3 | 2026-02-09 | preset | gsap | Vercel | |
| 7 | nicola-romei | 2026-02-10 | preset | gsap | Vercel | Required manual fixes |
| 8 | cascaid-health | 2026-02-10 | from-url | gsap+framer | Vercel | |
| 9 | turm-kaffee-v3 | 2026-02-10 | preset | framer-motion | Vercel | |
| 10 | gsap-homepage | 2026-02-10 | from-url | gsap | Vercel | Stress test, incomplete |
| 11 | gsap-v9-test | 2026-02-11 | from-url | gsap | Vercel | SSR visibility issue |
| 12 | gsap-v10 | 2026-02-11 | from-url | gsap | Vercel | |
| 13 | gsap-v11 | 2026-02-11 | from-url | gsap | Vercel | |
| 14 | sofi-health-v2 | 2026-02-11 | from-url | framer-motion | Local | v2.0.1 validation |
| 15 | sofi-health-v3 | 2026-02-11 | from-url | framer-motion | Local | v2.0.2 validation |

**15 total builds** over 4 days (Feb 8-11, 2026). 13 deployed to Vercel.

### 6.2 System Version

- **CLAUDE.md header says:** v2.0.2 (Last Updated: 2026-02-11)
- **Changelog "Current" says:** v2.0.0 (2026-02-11)
- **VISION.md says:** v1.1.2

There is a minor version documentation inconsistency — the changelog table lists v2.0.0 as "Current" while the Quick Reference table at the top correctly states v2.0.2.

### 6.3 Active Issues for Automation

Per CLAUDE.md "Active Issues" section: **None.** All previously identified issues are marked as resolved.

**Known limitations for automation:**

1. **No Vercel auto-deploy** — `stage_deploy` creates the project but does not run `vercel`
2. **No programmatic Python API** — CLI subprocess only
3. **No Vercel URL capture** — deployment URL not returned/saved by the pipeline
4. **architecture.json not consumed** — multi-page generation not implemented
5. **Commerce sections not generated** — all sections are currently static (Phase 0 remaining work)
6. **SPA/Webflow extraction fragility** — URL clone mode may fail on some site architectures
7. **No build duration tracking** — pipeline does not log total elapsed time

### 6.4 Retrospective Count

**19 retrospective files** in `web-builder/retrospectives/`, covering:
- 4 from 2026-02-08 (initial builds)
- 4 from 2026-02-09 (infrastructure improvements)
- 6 from 2026-02-10 (builds + animation library work)
- 5 from 2026-02-11 (pipeline improvements + validation builds)

---

## 7. Recommendations for Pipeline Integration

### 7.1 Immediate (Can Do Now)

| # | Recommendation | Effort | Impact |
|---|---------------|--------|--------|
| 1 | **Wrap `orchestrate.py` invocation in subprocess call** — The Calculator or pipeline orchestrator should call it via `subprocess.run(["python3", "scripts/orchestrate.py", project, "--preset", preset, "--deploy", "--no-pause"], cwd=web_builder_dir)` | Low | Enables automated pipeline |
| 2 | **Add Vercel deployment step to upstream orchestrator** — After `orchestrate.py` completes, run `subprocess.run(["vercel", "--yes", "--prod"], cwd=site_dir)` and capture the URL from stdout | Low | Completes the deploy chain |
| 3 | **Calculator brief output should match template exactly** — Use the 7-section structure from `briefs/_template.md` | Low | Ensures compatibility |
| 4 | **Calculator preset output should match template exactly** — Use the YAML structure from `skills/presets/_template.md`, or select from 18 existing industry presets | Low-Medium | Ensures compatibility |

### 7.2 Short-Term (1-2 Days)

| # | Recommendation | Effort | Impact |
|---|---------------|--------|--------|
| 5 | **Add `--output-json` flag to orchestrate.py** — Print a JSON summary on completion (project path, section count, site dir, elapsed time, errors) for machine consumption | Low | Enables structured pipeline feedback |
| 6 | **Capture Vercel URL in orchestrate.py** — Add optional `vercel --yes` execution inside `stage_deploy` gated on a `--vercel-deploy` flag, capturing the URL | Medium | Eliminates manual Vercel step |
| 7 | **Add elapsed time tracking** — `time.time()` around each stage, print summary at end | Low | Enables SLA monitoring |
| 8 | **Add `--brief-path` and `--preset-path` flags** — Allow passing absolute paths instead of requiring files be placed in `briefs/` and `skills/presets/` | Low | Cleaner integration (no file copying) |

### 7.3 Medium-Term (Phase 0 Completion)

| # | Recommendation | Effort | Impact |
|---|---------------|--------|--------|
| 9 | **Consume `architecture.json` for multi-page generation** — Implement page template structures per VISION.md Phase 0 | High | Enables full Shopify migration pipeline |
| 10 | **Generate prop-driven commerce sections** — Use `commerce-contract.ts` types in section generation prompts | High | Enables Module 3 data injection |
| 11 | **Refactor `main()` for importability** — Replace `sys.exit()` with exceptions, return results instead of printing, make state explicit | Medium | Enables Python-native orchestration |

### 7.4 CLI Quick Reference for Orchestrators

```bash
# Full unattended build from brief + preset
python3 scripts/orchestrate.py {project} \
  --preset {preset} \
  --deploy \
  --no-pause

# Full unattended URL clone
python3 scripts/orchestrate.py {project} \
  --from-url {url} \
  --deploy \
  --no-pause

# Resume from a specific stage
python3 scripts/orchestrate.py {project} \
  --preset {preset} \
  --skip-to sections \
  --deploy

# Clean start (delete existing output)
python3 scripts/orchestrate.py {project} \
  --preset {preset} \
  --deploy \
  --no-pause \
  --clean

# Force past validation failures
python3 scripts/orchestrate.py {project} \
  --preset {preset} \
  --deploy \
  --no-pause \
  --force

# Exit codes: 0 = success, 1 = failure (all errors are sys.exit(1))
```

**Required environment setup:**
```bash
# In web-builder/.env
ANTHROPIC_API_KEY=sk-ant-...

# System requirements
pip install anthropic
cd scripts/quality && npm install
npx playwright install chromium  # Only for --from-url mode
```

---

*End of audit report. Generated 2026-02-12.*

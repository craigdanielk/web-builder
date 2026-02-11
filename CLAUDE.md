# Web Builder — System Context

**Last Updated:** 2026-02-11
**System Version:** v0.9.0

---

## Quick Reference

| Key | Value |
|-----|-------|
| Runtime | Python 3 + Node.js (hybrid pipeline) |
| Generated stack | Next.js 16.1.6 / React 19 / Tailwind CSS 4 / TypeScript 5 |
| Animation engines | GSAP 3.14 + Framer Motion 12 (both can coexist) |
| Pipeline entry | `scripts/orchestrate.py` (1211 lines) |
| API | Anthropic Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) |
| Deployment | Vercel CLI (`vercel --yes`) |
| API key | `ANTHROPIC_API_KEY` in `.env` (gitignored) |

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
    ├── Installs deps, generates layout/globals/page
    └── Ready for: cd site && vercel --yes
```

### Data Flow (URL Clone Mode)

```
extract-reference.js
    ├── Playwright headless Chromium (1440x900)
    ├── Scroll-captures, DOM extraction (500 elements, 24 CSS properties)
    ├── Animation detection (libraries, keyframes, scroll triggers, network assets)
    └── Output: extraction-data.json
         │
         ├── design-tokens.js → fonts, colors, radii, animation tokens
         ├── archetype-mapper.js → section archetypes + variants
         ├── animation-detector.js → intensity, engine, Lottie/Rive/3D URLs
         └── url-to-preset.js → Claude prompt → preset markdown file
              │
              ├── animation-analysis.json (score, engine, section overrides)
              └── mapped-sections.json (archetype assignments)
```

### Key Consistency Mechanism

Every section generation prompt includes a **compact style header** extracted from the preset:

```
═══ STYLE CONTEXT ═══
Palette: warm-earth | stone-50/white/green-700
Type: Aeonik/Aeonik · 600/400 · 1.25 ratio
Space: generous (6rem/3rem)
Radius: pill (buttons) · 3xl (cards)
Motion: expressive/gsap — entrance:fade-up-stagger hover:lift-glow timing:0.6s-ease-out
Density: airy | Images: natural-rounded
═══════════════════════
```

This header is restated in every section prompt. It is the mechanism that prevents cross-section visual inconsistency.

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
│   ├── section-taxonomy.md            ← 25 section archetypes, 95+ variants
│   ├── style-schema.md                ← 7 style dimensions with Tailwind mappings
│   ├── animation-patterns.md          ← 20+ named GSAP/Framer Motion patterns
│   ├── image-extraction.md            ← Image categorization spec (10 categories)
│   ├── animation-components/            ← Pre-built animation component library (1022 total)
│   │   ├── registry.json (1016)         ← Legacy pattern → component file mapping (36 entries)
│   │   ├── registry/                    ← NEW: Comprehensive machine-usable registry
│   │   │   ├── animation_registry.json (1.6MB) ← Full analysis of all 1022 components
│   │   │   ├── animation_taxonomy.json  ← Controlled vocabulary (motion intents, triggers, roles)
│   │   │   ├── animation_search_index.json ← Query-optimised lookup by intent/trigger/section/framework
│   │   │   ├── animation_capability_matrix.csv ← Tabular capabilities (189KB)
│   │   │   └── analysis_log/ (1022 files) ← Per-component classification rationale
│   │   ├── entrance/                    ← Scroll-triggered entrance animations (11 slots)
│   │   ├── scroll/                      ← Scroll-linked animations (5 slots)
│   │   ├── interactive/                 ← User-triggered animations (7 slots)
│   │   ├── continuous/                  ← Always-running animations (5 slots)
│   │   ├── text/                        ← Text-specific animations (5 slots)
│   │   ├── effect/                      ← Border/glow/decoration effects (2 slots)
│   │   ├── background/                  ← Full-section background animations (2 slots)
│   │   └── 21st-dev-library/ (986 .tsx) ← Community components from 21st.dev
│   ├── presets/ (32 presets + _template)
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
│   │   └── sports-fitness.md
│   └── components/
│       ├── cursor-trail.md            ← Mouse-following trail effect
│       └── image-patterns.md          ← CSS backgroundImage rendering patterns
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
│   ├── orchestrate.py (1404 lines)    ← Main pipeline — 7 stages + injection wiring + component copy + cn() utility
│   └── quality/                       ← URL extraction + validation tools
│       ├── url-to-preset.js (303)     ← URL → preset markdown (+ color system integration)
│       ├── url-to-brief.js (201)      ← URL → brief markdown
│       ├── enrich-preset.js (161)     ← Enrich preset with extracted tokens
│       ├── validate-build.js (287)    ← Post-build quality validation
│       ├── test-animation-detector.js (196) ← Standalone animation test
│       ├── test-pattern-pipeline.js (394) ← Pattern identification test harness (57 assertions)
│       ├── build-animation-registry.js     ← Analyzes 1022 components → registry artifacts
│       ├── fixtures/                       ← Synthetic test data for pipeline testing
│       │   ├── gsap-extraction-data.json   ← Simulated extraction output
│       │   └── gsap-animation-analysis.json ← Simulated animation analysis
│       └── lib/
│           ├── extract-reference.js (556)   ← Playwright extraction engine
│           ├── animation-detector.js (750)  ← Animation detection + GSAP interception + section grouping
│           ├── archetype-mapper.js (398)    ← Section → archetype mapping (+ class signals, gap flagging)
│           ├── design-tokens.js (547)       ← CSS → design token collection (+ color intelligence)
│           ├── pattern-identifier.js (577)  ← Pattern identification, animation/UI matching, gap aggregation
│           ├── animation-injector.js (956)  ← 3-tier animation injection + selectAnimation() affinity algorithm
│           ├── asset-injector.js (378)     ← Per-section asset prompt builder
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
│       ├── sections/*.tsx
│       ├── page.tsx
│       ├── review.md
│       └── site/                     ← Runnable Next.js project
│
├── plans/
│   ├── _close-checklist.md                    ← Build close protocol template
│   ├── active/
│   │   └── pattern-identification-mapping-pipeline.md ← 6-phase pipeline upgrade
│   ├── backlog/                               ← Future plans (not yet implemented)
│   │   ├── template-library-upgrade-plan.md   ← Aurelix pattern library
│   │   └── url-site-structure-calculator.md   ← Shopify migration calculator
│   └── completed/
│       ├── animation-classification-vengenceui-integration.md ← v0.7.0
│       ├── animation-extraction-integration.md ← v0.4.0
│       ├── data-injection-pipeline.md          ← v0.5.0
│       ├── generated-reference-docs.md         ← v0.7.1
│       └── system-documentation-automation.md  ← v0.4.1
│
└── retrospectives/                    ← Session documentation
    ├── 2026-02-08-web-builder-first-build-success.md
    ├── 2026-02-08-turm-kaffee-v2-build-deploy.md
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
    └── 2026-02-11-pattern-identification-pipeline-v9-success.md
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
**Input per section:** Style header + section spec + structural reference + optional section context + animation context block + asset context block + engine-branched instructions
**Output:** Self-contained React/TypeScript/Tailwind component with correct animation engine
**Post-processing:** Ensures `"use client"` directive, ensures `export default`
**Injection helpers:** `load_injection_data()`, `get_animation_contexts()`, `get_asset_contexts()` — load extraction data and call Node.js injector modules via subprocess

### Stage 3: Assembly (`stage_assemble`, orchestrate.py:605)

**No API call.** Pure code generation — creates `page.tsx` importing all sections.

### Stage 4: Review (`stage_review`, orchestrate.py:960)

**Model:** Claude Sonnet 4.5 | **Max tokens:** 4096
**Input:** All section code concatenated + style header
**Output:** Consistency report (colors, typography, spacing, radius, animation, buttons)

### Stage 5: Deploy (`stage_deploy`, orchestrate.py:654)

**No API call.** Creates Next.js project scaffold:
- `package.json` with engine-specific deps (framer-motion always + GSAP conditional + Lottie conditional + clsx/tailwind-merge always)
- Font imports from preset's Type line
- `globals.css` with engine-specific styles
- Generates `src/lib/utils.ts` with `cn()` utility (clsx + tailwind-merge)
- Copies sections to `src/components/sections/`
- Copies animation components from library to `src/components/animations/` (non-placeholder only, matched by archetype)
- Downloads verified assets to `public/images/` and `public/lottie/` (via asset-injector + asset-downloader)
- Runs `npm install`

---

## Current System State

### Completed Builds
| Project | Preset | Engine | Deployed |
|---------|--------|--------|----------|
| turm-kaffee-v2 | artisan-food | framer-motion | Vercel |
| farm-minerals-promo | farm-minerals-promo-v2 | gsap | Vercel |
| bluebird-coffee-roastery | artisan-food | framer-motion | Vercel |
| nike-golf | nike-golf | gsap | Vercel |
| farm-minerals-anim | farm-minerals-anim | gsap* | Vercel |
| farm-minerals-v3 | farm-minerals-promo-v2 | gsap | Vercel |
| nicola-romei | nicola-romei | gsap | Vercel |
| cascaid-health | health-wellness | gsap+framer | Vercel |
| turm-kaffee-v3 | artisan-food | framer-motion | Vercel |
| gsap-homepage | gsap-homepage | gsap | Vercel* |
| gsap-v9-test | gsap-v9-test | gsap | Vercel** |

*farm-minerals-anim: Built before v0.5.0 injection pipeline — preset says gsap but sections use framer-motion. Rebuild with injection pipeline to fix.
*nicola-romei: Required manual post-build fixes — preset misclassified color (dark vs light #f3f3f3), 0 sections detected in Webflow site broke asset injection, scaffold parser failed on bold markdown. See retro for details.
*gsap-homepage: Stress test build — functional but visually incomplete. Monochrome orange (missing multi-accent), generic animations, blank gallery cards. Used as diagnostic to identify 6 systemic pipeline gaps. See retro for details.
**gsap-v9-test: v0.9.0 validation build against gsap.com. Color intelligence correctly identified 5-accent system, class-signal archetype mapping at 80% confidence, gap report generated. Sections invisible on deploy due to pre-existing GSAP `from()` SSR issue (not a v0.9.0 regression).

### Active Plans
- **[GSAP Ecosystem Integration & System Stability](plans/active/gsap-ecosystem-integration-and-stability.md)** — v1.0.0. 5-phase plan: Phase 1 fixes 8 active bugs (from() SSR, parse_scaffold, token truncation, JSX repair, zero-section fallback, color misclassification, font parsing). Phase 2 extends detection to all 20 GSAP plugins. Phase 3 adds knowledge base (30+ animation patterns, 11 new plugin components, plugin section instructions). Phase 4 wires plugin-aware injection into generation. Phase 5 adds build reliability (pre-flight validation, post-deploy verification).

### Completed Plans
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

**GSAP `from()` causes invisible elements in Next.js SSR**
- `gsap.from({ opacity: 0 })` immediately sets elements to the "from" state. In SSR/hydration context, ScrollTrigger `once: true` may never fire, leaving elements permanently invisible.
- Symptoms: Cards, rows, or other content completely invisible on deployed site despite correct HTML
- Workaround: Use Framer Motion `whileInView` for all entrance animations. Use GSAP only for interactive effects (hover tilt, continuous pulse) and scroll-linked parallax (`scrub: true`).
- Hit in: cascaid-health build (2026-02-10) — sections 03-problem, 08-comparison, 09-team
- Fix: Update section prompt templates to enforce Framer Motion for entrance animations
- Priority: High — affects any build using GSAP entrance animations

**parse_scaffold() fails on bold markdown formatting**
- `parse_scaffold()` regex `\d+\.\s+(\w[\w-]*)` requires archetype to start with `\w`, but Claude sometimes generates `**NAV**` with bold markers
- Symptoms: "Could not parse any sections from scaffold" error, pipeline exits
- Workaround: Manually strip `**` from scaffold.md, resume with `--skip-to sections`
- Hit in: nicola-romei build (2026-02-10)
- Fix: Change regex to `\d+\.\s+\*{0,2}(\w[\w-]*)\*{0,2}` to handle optional bold
- Priority: High — breaks every build where Claude uses bold formatting

**Zero-section extraction silently bypasses asset injection**
- When Playwright extraction finds 0 visual `<section>` elements (common on JS-heavy Webflow/WebGL sites), the entire asset injection pipeline is skipped
- Symptoms: Sections receive no image URLs in prompts → Claude hallucmates fabricated Unsplash URLs that may not load
- Workaround: Manually insert extracted `assets.images` URLs into section components post-build
- Hit in: nicola-romei (Webflow + Three.js), potentially any heavily JS-rendered site
- Fix: Add fallback in asset-injector that distributes `assets.images` heuristically even when section count is 0
- Priority: High — affects all JS-heavy site clones

**Preset generator misclassifies color temperature on overlay-heavy sites**
- `url-to-preset.js` → Claude prompt can classify a light site (#f3f3f3) as "dark-neutral" when the site uses dark overlays/modals/tooltips
- Symptoms: Generated preset has `bg_primary: black` when actual page bg is light
- Workaround: Manually correct preset palette or fix section colors post-build
- Hit in: nicola-romei (2026-02-10) — artboard tooltip was dark, page bg was light
- Fix: Add explicit instruction in url-to-preset.js prompt: prioritize body/wrapper background over overlay backgrounds; cross-check with extracted `renderedDOM[0].styles.backgroundColor`
- Priority: Medium — requires manual review of every preset for now

**parse_fonts() recurring corruption (2 occurrences)**
- `parse_fonts()` (orchestrate.py) regex fails on certain preset formatting
- Symptoms: Preset YAML content leaks into layout.tsx font imports, causing build failure
- Workaround: Manually overwrite layout.tsx with clean font setup after deploy
- Hit in: farm-minerals-v2, farm-minerals-v3
- Priority: Medium — fix the regex or add layout.tsx validation

**`hexToTailwindApprox()` loses all hue information**
- `url-to-preset.js` maps hex colors to Tailwind names using brightness only — no hue detection
- Symptoms: Bright green (`#0ae448`) → `gray-200`, vivid blue (`#0077ff`) → `gray-400`. ALL non-gray colors from ANY site lose their hue. Presets describe sites as "monochrome gray" when they have rich color palettes
- Workaround: Manually edit preset palette after extraction
- Hit in: gsap-homepage (2026-02-10) — green/blue/purple/pink all mapped to grays
- Fix: Planned in Phase 1C of pattern-identification-mapping-pipeline.md — HSL-based mapping with hue buckets
- Priority: High — affects every URL-mode build

**Archetype mapper ignores class names and IDs**
- `archetype-mapper.js` only examines tag names, ARIA roles, and heading text. Class names (the strongest semantic signal on most sites) are completely ignored
- Symptoms: Sections with class `brands` mapped to `FEATURES | icon-grid`, class `showcase` mapped to `FOOTER`, class `home-tools` mapped to `FEATURES | icon-grid` — all at 30% confidence
- Workaround: Manually expand/correct preset section sequence after extraction
- Hit in: gsap-homepage (2026-02-10) — 4 of 6 sections incorrectly mapped
- Fix: Planned in Phase 2A of pattern-identification-mapping-pipeline.md — add class/ID heuristic layer
- Priority: High — wrong archetype mapping cascades into wrong section generation

**Gradient colors not parsed from extraction data**
- `design-tokens.js` extracts `color` and `backgroundColor` as flat hex values but ignores CSS gradients in `backgroundImage`
- Symptoms: Gradient-defined accent colors (e.g., `linear-gradient(114deg, rgb(10,228,72)...)` on GSAP scroll section) never appear in design tokens or preset
- Workaround: None — gradient colors are silently lost
- Hit in: gsap-homepage (2026-02-10) — green gradient defining the Scroll section was captured by extraction but never tokenized
- Fix: Planned in Phase 1A of pattern-identification-mapping-pipeline.md — add gradient color extraction to `design-tokens.js`
- Priority: Medium — affects sites that define accent colors via gradients rather than flat backgrounds

### Resolved Issues (Keep for Reference)

**Animation library components broken — 0 of 32 imported** (FIXED v0.7.2)
- Was: Library components copied by stage_deploy but never validated. 6/9 key components had wrong export names, 4 imported from `motion/react` instead of `framer-motion`, 4 required missing `@/lib/utils.ts`, 1 contained wrong component entirely (hover-lift had ZoomImageUI).
- Fix: Rewrote 6 key components (word-reveal, count-up, blur-fade, magnetic-button, hover-lift, magnetic-button), created `@/lib/utils.ts`, refactored 8 sections to import from library, added Phase 0 to animation-upgrade skill. 8 unique components now imported across turm-kaffee-v3.
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
| Review | 4096 | claude-sonnet-4-5-20250929 |

Section token budgets are dynamic — `animation-injector.js` calculates per-section based on pattern complexity, engine, Lottie usage, and whether a library component is being injected (always 8192 for component injection).

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
| Add animation component | `skills/animation-components/{category}/{name}.tsx` + update `registry.json` + rerun `node scripts/quality/build-animation-registry.js` |
| Rebuild animation registry | `node scripts/quality/build-animation-registry.js` → regenerates all 5 artifacts in `skills/animation-components/registry/` |
| Add image category | `asset-injector.js:21-47` (URL/ALT category signals) + `asset-injector.js:53-68` (section map) |
| Add extraction CSS properties | `scripts/quality/lib/extract-reference.js:73-76` |
| Add class-signal archetype mapping | `archetype-mapper.js` (`CLASS_NAME_SIGNALS` map) |
| Add color hue family | `design-tokens.js` (`HUE_FAMILIES` array) |
| Add UI component detector | `pattern-identifier.js` (`matchUIComponents()` function) |
| Run pattern pipeline tests | `node scripts/quality/test-pattern-pipeline.js` |

---

## System Version

**Current:** v0.9.0 (2026-02-11)

### Changelog
| Version | Date | Changes |
|---------|------|---------|
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

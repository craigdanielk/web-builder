# Web Builder — System Context

**Last Updated:** 2026-02-09
**System Version:** v0.4.1

---

## Quick Reference

| Key | Value |
|-----|-------|
| Runtime | Python 3 + Node.js (hybrid pipeline) |
| Generated stack | Next.js 16.1.6 / React 19 / Tailwind CSS 4 / TypeScript 5 |
| Animation engines | GSAP 3.14 + Framer Motion 12 (both can coexist) |
| Pipeline entry | `scripts/orchestrate.py` (957 lines) |
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
    ├── url-to-preset.js  → skills/presets/{project}.md
    ├── url-to-brief.js   → briefs/{project}.md
    └── section-context   → per-section reference data
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
│   ├── presets/ (23 presets + _template)
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
│   └── assembly-checklist.md          ← Stage 4 review checklist
│
├── briefs/                            ← Client briefs (human or auto-generated)
│   ├── _template.md
│   └── {project}.md                   ← One per project
│
├── scripts/
│   ├── orchestrate.py (957 lines)     ← Main pipeline — 6 stages
│   └── quality/                       ← URL extraction + validation tools
│       ├── url-to-preset.js (275)     ← URL → preset markdown
│       ├── url-to-brief.js (201)      ← URL → brief markdown
│       ├── enrich-preset.js (161)     ← Enrich preset with extracted tokens
│       ├── validate-build.js (287)    ← Post-build quality validation
│       ├── test-animation-detector.js (196) ← Standalone animation test
│       └── lib/
│           ├── extract-reference.js (556)   ← Playwright extraction engine
│           ├── animation-detector.js (454)  ← Animation library detection
│           ├── archetype-mapper.js (269)    ← Section → archetype mapping
│           ├── design-tokens.js (265)       ← CSS → design token collection
│           ├── section-context.js (192)     ← Per-section prompt context builder
│           ├── post-process.js (313)        ← Post-generation cleanup
│           └── visual-validator.js (401)    ← Visual consistency checker
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
│   ├── active/
│   │   ├── data-injection-pipeline.md       ← Animation + asset injection
│   │   └── system-documentation-automation.md ← This documentation plan
│   └── completed/
│       ├── animation-extraction-integration.md ← v0.4.0
│       ├── template-library-upgrade-plan.md    ← v0.2.0
│       └── url-site-structure-calculator.md    ← v0.3.0
│
└── retrospectives/                    ← Session documentation
    ├── 2026-02-08-web-builder-first-build-success.md
    ├── 2026-02-08-turm-kaffee-v2-build-deploy.md
    ├── 2026-02-08-farm-minerals-rebuild.md
    ├── 2026-02-09-nike-golf-light-theme-rebuild.md
    └── 2026-02-09-system-docs-automation-success.md
```

---

## Pipeline Stages — Detail

### Stage 0: URL Extraction (`stage_url_extract`, orchestrate.py:133)

**When:** `--from-url` flag is passed
**Runs:** Node.js scripts via subprocess

| Step | Script | Output |
|------|--------|--------|
| 0a | `url-to-preset.js` | `skills/presets/{project}.md` + `output/extractions/{project}-{uuid}/` |
| 0b | `url-to-brief.js` | `briefs/{project}.md` |
| 0c | `section-context.js` | Per-section context dict (passed in memory) |

Extraction captures: 500 DOM elements with 24 CSS properties, section boundaries, text content, image URLs, font URLs, animation library globals, Lottie/Rive/3D network assets, CSS keyframes.

### Stage 1: Scaffold (`stage_scaffold`, orchestrate.py:235)

**Model:** Claude Sonnet 4.5 | **Max tokens:** 2048
**Input:** Brief + preset section sequence + taxonomy archetype list
**Output:** Numbered section list: `N. ARCHETYPE | variant | content direction`
**Checkpoint:** Interactive review (skipped with `--no-pause`)

### Stage 2: Sections (`stage_sections`, orchestrate.py:356)

**Model:** Claude Sonnet 4.5 | **Max tokens:** 4096 per section
**Input per section:** Style header + section spec + structural reference + optional section context
**Output:** Self-contained React/TypeScript/Tailwind component
**Post-processing:** Ensures `"use client"` directive, ensures `export default`

### Stage 3: Assembly (`stage_assemble`, orchestrate.py:471)

**No API call.** Pure code generation — creates `page.tsx` importing all sections.

### Stage 4: Review (`stage_review`, orchestrate.py:757)

**Model:** Claude Sonnet 4.5 | **Max tokens:** 4096
**Input:** All section code concatenated + style header
**Output:** Consistency report (colors, typography, spacing, radius, animation, buttons)

### Stage 5: Deploy (`stage_deploy`, orchestrate.py:520)

**No API call.** Creates Next.js project scaffold:
- `package.json` with engine-specific deps (GSAP or Framer Motion)
- Font imports from preset's Type line
- `globals.css` with engine-specific styles
- Copies sections to `src/components/sections/`
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

*farm-minerals-anim: Preset says gsap but sections use framer-motion due to Gap 1 (see Known Gaps).

### Active Plans
- **[Data Injection Pipeline](plans/active/data-injection-pipeline.md)** — Closes the loop between extracted animation/image data and built output. Animation injector + asset injector + engine-branched prompts.
- **[System Documentation Automation](plans/active/system-documentation-automation.md)** — Implemented v0.4.1. CLAUDE.md created, README/cursorrules refreshed, retro skill doc-sync integrated.

---

## Known Issues & Workarounds

### Active Issues

**Gap 1: Animation data doesn't reach section output**
- Detection works (GSAP, Lottie, intensity scoring all correct)
- Preset contains correct `animation_engine` and `section_overrides`
- BUT `stage_sections` prompt (orchestrate.py:400-436) hardcodes `import { motion } from "framer-motion"` and `Use Framer Motion motion components` regardless of detected engine
- Additionally, `stage_deploy` (line 549-552) installs GSAP **or** Framer Motion (either/or), causing missing dependency when prompt hardcodes framer-motion but engine is gsap
- **Status:** Fix planned in data-injection-pipeline.md (Phase 1 + 3)

**Gap 2: No image/media asset pipeline**
- Extraction captures image URLs, Lottie file URLs, background images
- But `stage_sections` prompt says "use neutral gradient div" (line 428)
- No download/proxy mechanism exists for extracted assets
- **Status:** Fix planned in data-injection-pipeline.md (Phase 2)

### Resolved Issues (Keep for Reference)

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
| Section | 4096 | claude-sonnet-4-5-20250929 |
| Review | 4096 | claude-sonnet-4-5-20250929 |

### Running the Pipeline

```bash
# URL clone mode (most common)
python scripts/orchestrate.py my-project --from-url https://example.com --deploy --no-pause

# Manual brief mode
python scripts/orchestrate.py my-project --preset artisan-food --deploy

# Resume from a specific stage
python scripts/orchestrate.py my-project --preset artisan-food --skip-to sections --deploy

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
| Change section prompt | `orchestrate.py:400-436` (stage_sections prompt) |
| Change scaffold prompt | `orchestrate.py:267-301` (stage_scaffold prompt) |
| Add new archetype | `skills/section-taxonomy.md` |
| Add animation pattern | `skills/animation-patterns.md` |
| Change token budget | `orchestrate.py:75-79` (MAX_TOKENS dict) |
| Change model | `orchestrate.py:69-73` (MODELS dict) |
| Change Next.js version | `orchestrate.py:545` (deps dict in stage_deploy) |
| Fix dependency resolution | `orchestrate.py:549-552` (engine deps in stage_deploy) |
| Add extraction CSS properties | `scripts/quality/lib/extract-reference.js:73-76` |

---

## System Version

**Current:** v0.4.1 (2026-02-09)

### Changelog
| Version | Date | Changes |
|---------|------|---------|
| v0.4.1 | 2026-02-09 | Doc-sync integration into retrospective skill; CLAUDE.md, README.md, .cursorrules refresh |
| v0.4.0 | 2026-02-09 | Animation extraction integration (detector, analyzer, preset injection) |
| v0.3.0 | 2026-02-08 | URL clone mode (`--from-url`), auto-generated presets and briefs |
| v0.2.0 | 2026-02-08 | Multi-agent builds, build isolation, Vercel deployment, 18 industry presets |
| v0.1.0 | 2026-02-08 | Initial pipeline: brief → scaffold → sections → assembly → review |

---

## CLAUDE.md Update Protocol

After every build or integration session:

1. Run the retrospective skill to capture session learnings
2. Update this file using the checklist below:
   - [ ] **Quick Reference**: version bumps, model changes, dependency versions
   - [ ] **File Map**: new/deleted/moved files with line counts
   - [ ] **Pipeline Stages**: function signatures, line numbers if changed
   - [ ] **Current System State**: completed builds, plan status changes
   - [ ] **Known Issues**: add new issues, mark resolved ones
   - [ ] **System Version**: bump version, add changelog entry
3. If pipeline stages changed, also update `.cursorrules`
4. If user-facing info changed (presets, tech stack), also update `README.md`

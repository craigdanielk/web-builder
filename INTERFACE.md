# Web Builder — Input/Output Contract

**Version:** v3.1.0
**Last Updated:** 2026-03-02

---

## CLI Entry Point

```bash
python scripts/orchestrate.py <project-name> [OPTIONS]
```

### Required Arguments

| Argument | Description |
|----------|-------------|
| `project` | Project name. Must match a brief file at `briefs/{project}.md` (unless `--brief` or `--compiled-dir` is used) |

### Optional Flags

| Flag | Type | Description |
|------|------|-------------|
| `--preset <name>` | string | Override preset selection (loads `skills/presets/{name}.md`) |
| `--industry <slug>` | string | Select industry from Supabase preset DB (alternative to `--preset`) |
| `--page <type>` | string | Page type for `--industry` mode (default: `homepage`) |
| `--from-url <URL>` | string | Clone mode: extract visual data from URL, auto-generate preset + brief |
| `--brief <path>` | string | Path to brief.md file (overrides default lookup) |
| `--compiled-dir <path>` | string | Path to Calculator compiled dir (`architecture.json`); enables multi-route generation |
| `--site-manifest <path>` | string | Path to `site-manifest.json` for multi-page build (Layer 6) |
| `--shopify-config <path>` | string | Path to `shopify_config.json` (from Layer 4 output) |
| `--no-pause` | flag | Skip scaffold review checkpoint |
| `--skip-to <stage>` | choice | Resume from stage: `sections`, `assemble`, `review`, `deploy` |
| `--deploy` | flag | Also deploy to a runnable Next.js project at `output/{project}/site/` |
| `--clean` | flag | Delete existing output and start fresh |
| `--force` | flag | Ignore warnings (low confidence, validation issues) |
| `--set-vercel-env` | flag | Auto-set Shopify env vars on Vercel + register webhooks after deploy |
| `--output-root <path>` | string | Override the base output directory. Default: `<web-builder>/output`. When set, all build artifacts write under `<output-root>/{project}/...` (same subtree layout, re-rooted). Accepts absolute or relative paths (resolved to absolute); the tree is created if missing and validated for writability. Absent = no-op (default behavior). |

---

## Input Files

### Brief (required)

**Location:** `briefs/{project}.md` (or custom path via `--brief`)

**Template:** `briefs/_template.md`

**Structure:**
```markdown
# Brief: [Project Name]

## Business
[What the business does, location, unique value]

## What They Need
[Website purpose and goals]

## Key Requirements
- [Requirement 1]

## Target Audience
- [Audience segment]

## Brand Personality
- [Trait]

## Specific Requests
- [Design/content/functional requests]

## Technical Notes
- [Platform, performance, integrations, constraints]
```

### Preset (one of the following)

**Option A — Markdown preset:** `skills/presets/{preset-name}.md` (via `--preset`)
- 39 presets available across 25+ industries
- Contains style dimensions, color palette, typography, animation engine, section sequence

**Option B — Supabase industry:** Database lookup (via `--industry`)
- 25 industries configured in Supabase
- Returns section sequence, style config, font mappings
- BuildCache loads 2 queries at build start, caches for entire build

**Option C — URL clone:** Auto-extracted (via `--from-url`)
- Playwright headless extraction at 1440x900
- Outputs: `extraction-data.json`, `mapped-sections.json`, `animation-analysis.json`, `site-spec.json`

### Architecture (optional, for multi-route)

**Location:** Provided via `--compiled-dir` (from Calculator output)

**File:** `architecture.json` within the compiled directory

---

## Environment Requirements

### Required
| Dependency | Version | Install |
|-----------|---------|---------|
| Python 3 | 3.10+ | System |
| `anthropic` | latest | `pip install anthropic` |
| `ANTHROPIC_API_KEY` | — | Set in `.env` |

### Optional (for URL clone mode)
| Dependency | Install |
|-----------|---------|
| Node.js | System |
| Playwright + Chromium | `cd scripts/quality && npm install && npx playwright install chromium` |

### Optional (for Supabase integration)
| Dependency | Install |
|-----------|---------|
| `supabase` | `pip install supabase` |
| `SUPABASE_URL` | Set in `.env` |
| `SUPABASE_KEY` | Set in `.env` |

---

## Pipeline Stages

| Stage | Input | Output | API Calls |
|-------|-------|--------|-----------|
| 0: URL Extract | `--from-url URL` | `extraction-data.json`, preset, brief, `site-spec.json` | Playwright + Claude |
| 1: Scaffold | brief + preset/industry | `output/{project}/scaffold.md` | 1 Claude call |
| 2: Sections | scaffold + style header | `output/{project}/sections/{NN}-{name}.tsx` | 1 Claude call per section |
| 2a: Copy Resolution | harvested `content.{headings,body_text,ctas}` (+ optional `--copy-findings`) | verbatim source copy threaded into each section prompt; `output/{project}/copy-manifest.json` (reproduced/revised/generated), `copy-trace.json` for revised slots | 0 (deterministic; folds into stage 2 calls) |
| 3: Assembly | all section files | `output/{project}/page.tsx` | 0 (deterministic) |
| 4: Review | assembled page | `output/{project}/review.md` | 1 Claude call |
| 5: Deploy | page.tsx + sections | `output/{project}/site/` (Next.js project) | 0 (npm install) |

---

## Output Structure

> **Base directory is overridable.** By default all output is rooted at
> `output/` (i.e. `<web-builder>/output/{project}/...`). Passing
> `--output-root <path>` re-roots the entire subtree below to
> `<output-root>/{project}/...` — the layout shown is identical, only the base
> changes. The paths below use the default `output/` base.

### Single-Page Build
```
output/{project}/
  scaffold.md              # Page specification
  sections/
    01-HERO.tsx             # Individual section components
    02-FEATURES.tsx
    ...
  page.tsx                  # Assembled page (imports all sections)
  review.md                 # Consistency review
  site/                     # Runnable Next.js project (--deploy only)
    src/app/page.tsx
    src/components/sections/
    package.json
    ...
```

### Multi-Page Build (Layer 6, `--industry` + `--site-manifest`)
```
output/{project}/
  site-manifest.json        # Site manifest
  shared/
    Navigation.tsx           # Shared nav component
    Footer.tsx               # Shared footer component
  sections/{page_id}/
    01-HERO.tsx
    ...
  pages/
    {page_id}.tsx            # Per-route page files
  site/
    src/app/
      layout.tsx             # Navigation + Footer
      page.tsx               # Homepage
      collections/[handle]/page.tsx
      products/[handle]/page.tsx
      pages/[handle]/page.tsx
      not-found.tsx
```

### URL Clone Mode (additional outputs)
```
output/extractions/{project}-{uuid}/
  extraction-data.json       # Raw DOM extraction
  mapped-sections.json       # Archetype-mapped sections
  animation-analysis.json    # Detected animations
  site-spec.json             # Deterministic site specification
  screenshots/               # Visual captures
```

---

## API Model Configuration

| Stage | Model | Max Tokens |
|-------|-------|------------|
| Scaffold | `claude-sonnet-4-5-20250929` | 2048 |
| Section | `claude-sonnet-4-5-20250929` | 4096 |
| Review | `claude-sonnet-4-5-20250929` | 4096 |

Retry: 3 attempts with exponential backoff, 90s timeout per call.

---

## Validation Suites

### Python: `scripts/validate_integration.py`
- 71 tests across 9 suites
- Tests: Supabase client, DB queries (25 industries), BuildCache, template system, orchestrator integration, legacy path preservation, build log, directory structure, schema migrations
- **No API tokens consumed**

### JavaScript: `scripts/quality/test-pattern-pipeline.js`
- 66 assertions
- Tests: color conversion, gradient parsing, color system classification, archetype mapping, GSAP animation classification, UI component detection, gap reporting, plugin pattern detection
- **No API tokens consumed**

---

## Validation Results (2026-03-02)

| Suite | Result |
|-------|--------|
| Python validate_integration.py | **68/71 passed** (3 failures) |
| JS test-pattern-pipeline.js | **66/66 passed** |

### Known Failures
1. **`get_industry_style('automotive')` test stale** — DB now has a style row; test expected NULL
2. **`BuildCache import` check** — test looks for single-line import but orchestrate.py uses multi-line
3. **`log_build` HTTP 400** — Supabase build_log write fails (schema/payload mismatch)

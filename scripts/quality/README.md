# Quality Tools for Web-Builder

## Overview

These tools provide automated quality checking for the web-builder pipeline. They slot into the existing 6-step generation process as additive capabilities — no changes to the core pipeline.

Three capabilities:

1. **Preset Enrichment** — Analyze real reference sites to validate and improve preset accuracy
2. **Visual Validation** — Compare generated sites against reference site screenshots
3. **Post-Processing** — Safety fixes for generated TSX components

## Setup

```bash
cd scripts/quality
npm install
npx playwright install chromium
```

## Tools

### `enrich-preset.js` — Preset Ground-Truthing

- **Purpose:** Extracts design tokens from the reference sites listed in each preset and compares them to the preset's claimed values
- **Usage:** `node enrich-preset.js <preset-name> [--output-dir <dir>] [--max-sites <n>]`
- **Example:** `node enrich-preset.js artisan-food`
- **Output:** Enrichment report with accuracy score, confirmed values, discrepancies, and discoveries
- **When to use:** After creating a new preset, or periodically to validate existing presets against live sites

### `validate-build.js` — Visual Quality Gate

- **Purpose:** Screenshots a generated site and compares each section against reference site screenshots using pixel-level diffing
- **Usage:** `node validate-build.js <project-dir> [--reference-dir <dir>] [--port <port>] [--threshold <0-1>]`
- **Example:** `node validate-build.js ../../output/turm-kaffee --reference-dir ./refs --threshold 0.25`
- **Output:** Per-section similarity scores and overall pass/fail verdict
- **When to use:** After Step 5 (Assembly) and before Step 6 (Consistency Review)

### `url-to-preset.js` — Auto-Generate Preset from URL

- **Purpose:** Extracts visual identity from any URL and generates a complete web-builder preset
- **Usage:** `node url-to-preset.js <url> <preset-name> [--output-dir <dir>]`
- **Example:** `node url-to-preset.js https://www.tradecoffee.com trade-coffee-clone`
- **Output:** Complete preset `.md` file saved to `skills/presets/`
- **When to use:** As part of URL clone mode, or standalone to create presets from reference sites

### `url-to-brief.js` — Auto-Generate Brief from URL

- **Purpose:** Extracts text content from any URL and generates a web-builder brief
- **Usage:** `node url-to-brief.js <url> <project-name> [--extraction-dir <dir>]`
- **Example:** `node url-to-brief.js https://www.tradecoffee.com trade-coffee-clone`
- **Output:** Complete brief `.md` file saved to `briefs/`
- **When to use:** As part of URL clone mode, or standalone to bootstrap briefs

## Library Modules (`scripts/quality/lib/`)

| Module | Exports | Purpose |
|--------|---------|---------|
| `extract-reference.js` | `extractReference(url, outputDir?)` | Playwright-based extraction of visual/structural data from any URL |
| `design-tokens.js` | `collectTokens(data)`, `compareToPreset(tokens, presetPath)`, `rgbToHex(rgb)` | Design token aggregation and preset comparison |
| `visual-validator.js` | `validateBuild(projectDir, referenceScreenshots, options)` | pixelmatch-based visual comparison with dev server management |
| `post-process.js` | `cleanComponent(code, name)`, `validateComponent(code, name)`, `processAllSections(dir)` | TSX post-processing safety |
| `archetype-mapper.js` | `mapSectionsToArchetypes(sections, textContent)` | Maps extracted sections to taxonomy archetypes via heuristics |
| `section-context.js` | `buildSectionContext(data, index, mapped)`, `buildAllSectionContexts(data, mapped)` | Formats per-section reference context for section prompts |

## Integration with Web-Builder Pipeline

The tools are designed to be additive. The existing pipeline:

```
Step 1: Read Brief → Step 2: Match Preset → Step 3: Scaffold → Step 4: Generate Sections → Step 5: Assemble → Step 6: Review
```

With quality tools:

```
Step 1 → Step 2 → Step 3 → Step 4 → [Post-Process] → Step 5 → [Visual Validate] → Step 6
```

For preset maintenance:

```
[Enrich Preset] → Update preset file → Better generation next time
```

### URL Clone Mode (`--from-url`)

The full URL-to-site pipeline:

```
python scripts/orchestrate.py my-project --from-url https://example.com --no-pause
```

```
URL → Extract → [Auto-Preset + Auto-Brief + Section Contexts]
                        ↓
         Scaffold (uses auto-generated preset sequence)
                        ↓
         Section Gen (style header + archetype + PER-SECTION CONTEXT)
                        ↓
         Assembly → Review
```

Each section generator receives not just the style header, but also the specific layout, structure, and content composition of the corresponding section on the reference site.

## Architecture Notes

- All tools use CommonJS (`require`) for Node.js compatibility
- Extraction uses Playwright headless Chromium (must be installed via `npx playwright install chromium`)
- Visual comparison uses pixelmatch with 0.1 threshold, ignoring anti-aliasing
- The tools read preset files directly from `skills/presets/` using relative paths
- No changes to the Python orchestrator or any existing files
- Source of truth remains the web-builder system — these tools validate against it, never modify it autonomously

## Origin

Adapted from the aurelix-mvp extraction/validation system. Key adaptations:

- Removed cloning-specific logic (arbitrary Tailwind values, Figma pipeline)
- Added preset comparison (web-builder specific)
- Focused on analysis and reporting rather than generation
- All tools are read-only against the existing pipeline — they report but don't modify

# Future Integration Plans

## Planned

- Bulk product importer system
- Supabase/Pinecone for RAG retrieval of data
- URL ingestion of any target site and instant build of said site
- **Site Discovery & Migration Mapping Engine** — Full-site crawling, page intent
  classification, layout fingerprinting, and migration routing map generation.
  7-stage pipeline with n8n orchestration support. Piggybacks on existing
  `extract-reference.js`, `archetype-mapper.js`, and `design-tokens.js`.
  Full build plan: `briefs/URL&Site-Mapping-Build.md` | Est. effort: 7-8 days

---

## Completed: Quality Tools Integration (2026-02-08)

### Source
Adapted from `aurelix-mvp` extraction/validation system. The web-builder
system remains the source of truth — these tools validate against it.

### What Was Added

**`scripts/quality/`** — Self-contained Node.js toolset with 4 library modules
and 2 CLI scripts:

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `enrich-preset.js` | Analyze reference sites to validate preset accuracy | After creating new presets |
| `validate-build.js` | Visual diff of generated site vs reference screenshots | After assembly, before review |
| `lib/extract-reference.js` | Playwright extraction of styles, sections, assets from any URL | Called by enrich-preset |
| `lib/design-tokens.js` | Aggregate design tokens, compare to preset claims | Called by enrich-preset |
| `lib/visual-validator.js` | pixelmatch comparison + dev server management | Called by validate-build |
| `lib/post-process.js` | TSX cleanup: fence stripping, "use client", default exports | Can be called standalone |

**`scripts/orchestrate.py`** — Post-processing logic integrated directly into
the section generation stage (Stage 2). Every generated section now automatically:
- Gets "use client" directive injected if framer-motion or hooks detected
- Gets default export verification and repair
- Gets markdown code fence cleanup

### Setup
```bash
cd scripts/quality && npm install && npx playwright install chromium
```

### Pipeline Integration
```
Step 1 → Step 2 → Step 3 → Step 4 → [Post-Process] → Step 5 → [Visual Validate] → Step 6
```

### Architecture
- No changes to core pipeline architecture
- Quality tools are purely additive
- All tools are read-only against existing files
- Node.js toolset (quality) runs alongside Python orchestrator

---

## Completed: URL Clone Mode (2026-02-08)

### What Was Added

**`--from-url` flag in `orchestrate.py`** — Give a URL, get a matching site.

```bash
python scripts/orchestrate.py my-project --from-url https://example.com --no-pause
```

Pipeline: URL → Extract → Auto-Preset → Auto-Brief → Scaffold → Section Gen (with per-section context) → Assembly → Review

**New library modules:**

| Module | Purpose |
|--------|---------|
| `lib/archetype-mapper.js` | Maps extracted sections to taxonomy archetypes via tag, role, heading keywords, and position heuristics |
| `lib/section-context.js` | Formats per-section reference context (layout, structure, text, styles) for injection into section prompts |
| `url-to-preset.js` | Extracts tokens from URL → calls Claude → produces complete preset `.md` file |
| `url-to-brief.js` | Extracts text content from URL → calls Claude → produces complete brief `.md` file |

**Updated template:** `templates/section-prompt.md` now has optional `{REFERENCE_SECTION_CONTEXT}` block.

### How It Works
1. Playwright extracts DOM, styles, sections, text, and assets from the URL
2. Archetype mapper classifies each section (NAV, HERO, FEATURES, etc.)
3. Claude generates a preset (visual identity) and brief (content requirements)
4. Standard pipeline runs with per-section context injected into each section prompt
5. Each section generator "knows" the layout, structure, and content composition of the original

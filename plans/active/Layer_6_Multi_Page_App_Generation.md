# Layer 6: Multi-Page App Generation

**Created:** 2026-02-14  
**Status:** Active  
**Target Version:** v3.0.0  
**Depends On:** v2.1.0 (Supabase preset DB, deterministic pipeline)  
**Scope:** Upgrade Web Builder from single-page to multi-page Next.js app generation. Pipeline produces a complete `src/app/` directory with multiple routes, shared layout components, and per-page section sequences from Supabase.

**Note:** Specific store builds will be completed after Layer 6 is integrated and validated. This plan covers only the pipeline changes required for multi-page generation.

---

## Problem Statement

The pipeline currently produces **one** `page.tsx` with N sections. There is no:

- Site manifest concept (orchestrator doesn't know about multiple pages)
- Shared layout components (Nav and Footer are inline sections, not extracted)
- Per-route page generation (only one `page.tsx` is ever created)
- Route directory creation under `src/app/` (e.g. `collections/[handle]/`, `products/[handle]/`)
- Multi-page CLI interface

The Supabase preset database already has **842 rows** across **7 page types** (homepage, collection, product, about, contact, blog, landing). `get_section_sequence(industry, page_type)` returns different section sequences per page type. The pipeline does not yet use this to generate multiple pages in one build.

---

## Target Architecture

```
Current (single-page):
  BuildCache(industry, page_type="homepage") → one section list
  stage_scaffold → one scaffold
  stage_sections → output/{project}/sections/*.tsx (flat)
  stage_assemble → one page.tsx
  stage_deploy → src/app/page.tsx, one layout.tsx

Target (multi-page, when site manifest active):
  Site manifest (default or from file) → list of pages + shared_components
  stage_shared_components → Navigation.tsx, Footer.tsx in components/layout/
  stage_scaffold_multipage → per-page section sequences from Supabase (NAV/FOOTER filtered)
  stage_sections_multipage → output/{project}/sections/{page_id}/*.tsx
  stage_assemble_multipage → output/{project}/pages/{page_id}.tsx per page
  stage_deploy (manifest-aware) → full src/app/ tree + layout with Nav/Footer
```

**Output structure (target):**

```
src/app/
├── layout.tsx              ← Imports Navigation + Footer from components/layout/
├── page.tsx                 ← Homepage
├── collections/[handle]/page.tsx
├── products/[handle]/page.tsx
├── pages/[handle]/page.tsx
└── not-found.tsx
src/components/layout/
├── Navigation.tsx
└── Footer.tsx
src/components/sections/
├── homepage/
├── collection-template/
├── product-template/
└── content-template/
```

---

## Architecture Decisions (Locked)

| Decision | Rule |
|----------|------|
| Shared components | `src/components/layout/Navigation.tsx`, `Footer.tsx`. Imported in `layout.tsx`, wrap `{children}`. |
| NAV/FOOTER | Removed from per-page section sequences. Generated once as shared components. Variants come from manifest (Supabase `industries.default_nav_variant`, `default_footer_variant` or filtered from section_presets). |
| Per-page sections | Section generation pipeline unchanged. Runs once per page type; output path is `sections/{page_id}/`. |
| Dynamic routes | Static template shells only. No data fetching (Layer 7). `generateStaticParams()` returns `[]`. Placeholder content. |
| Site manifest | Single source of truth. All downstream stages read from it. No stage independently decides what pages to generate. |
| Legacy path | When no manifest and no `--industry`, pipeline behaves exactly as today (single page, flat sections, no route dirs). |

---

## Phase 1: Discovery & Audit (Complete)

Confirmed from code:

1. **stage_scaffold output:** Returns markdown string; `parse_scaffold()` produces `list[dict]` with `archetype`, `variant`, `content`. With site-spec, `stage_scaffold_v2()` returns richer sections from JSON.
2. **stage_assemble:** Reads `sections` + `section_files` from `output/{project}/sections/`, writes single `output/{project}/page.tsx`.
3. **stage_deploy:** Creates `site/src/app/layout.tsx`, `page.tsx`, `globals.css`; `src/components/sections/` (flat). layout.tsx is bare (fonts, metadata, `{children}` only).
4. **--industry + --page:** `BuildCache(industry, page_type)` loads once; `get_section_sequence(industry, page_type)` + `get_industry_style(industry)`; flows into scaffold and sections.
5. **Supabase:** `section_presets` has `page_type`. `get_page_sections(industry, page_type)` returns per-page-type sequences. `industries` has `default_nav_variant`, `default_footer_variant`. No Python wrapper for `industries` or `get_build_spec` yet.
6. **Site specification:** Not required for Layer 6. Default manifest uses 5 pages: homepage, collection, product, content, 404.

---

## Phase 2: Site Manifest Schema

### 2.1 Define manifest format

Create **`scripts/lib/site_manifest.py`** with:

- Schema (dict/dataclass) for site manifest:
  - `project`, `industry`
  - `shared_components`: `{ "navigation": { "archetype": "NAV", "variant": "…" }, "footer": { "archetype": "FOOTER", "variant": "…" } }`
  - `pages`: list of `{ "id", "route", "app_path", "page_type", "title", "dynamic"?: bool }`

### 2.2 Manifest generator

- **`generate_site_manifest(project, industry, …)`**
  - If architecture path provided (future): read route structure from Calculator output.
  - Else: default manifest = homepage + collection template + product template + content template + not-found.
  - Query Supabase for NAV/FOOTER variants: add `get_industry_metadata(industry)` in `supabase_client.py` (reads `industries` table) **or** derive from first page's section sequence (filter NAV/FOOTER).
  - Return dict; optionally write `output/{project}/site-manifest.json`.
- **`load_site_manifest(path)`** — load from JSON file.

### 2.3 Supabase helpers

In **`scripts/lib/supabase_client.py`**:

- **`get_industry_metadata(industry)`** — query `industries` table, return `default_nav_variant`, `default_footer_variant`, `display_name`.
- **`get_all_page_sections(industry)`** (optional) — call `get_build_spec` RPC to fetch all page types in one go; cache per build.

### 2.4 CLI

In **`scripts/orchestrate.py`** `main()`:

- Add **`--site-manifest <path>`**.
- Logic: if `--site-manifest` given → load from file. If `--industry` without `--site-manifest` → auto-generate default manifest. If neither → legacy single-page path.

---

## Phase 3: Shared Component Generation

### 3.1 Extract Nav and Footer from section pipeline

- **New `stage_shared_components(manifest, preset, project_name, build_cache, …)`** in `orchestrate.py`.
- Read NAV and FOOTER from `manifest["shared_components"]`.
- Generate each using **existing** section mechanism: same template-first check (`check_template_exists`), same LLM fallback, same prompt style.
- Write to `output/{project}/shared/Navigation.tsx` and `Footer.tsx`.
- Run **before** per-page section generation.

### 3.2 Filter NAV/FOOTER from per-page sequences

When building per-page section lists from Supabase, **exclude** rows where `section_archetype IN ('NAV', 'FOOTER')`. They are not rendered as numbered sections on any page.

### 3.3 Layout shell

In **`stage_deploy`**, when manifest is active:

- Generate `layout.tsx` that imports `Navigation` and `Footer` from `@/components/layout/`.
- Render: `<Navigation />` above `{children}`, `<Footer />` below.
- Keep existing font config and metadata.

### 3.4 Brand tokens

Navigation and Footer get brand tokens from brief (company name, contact) and industry style config (colors, fonts). Hardcoded for now; Layer 7 will add data connection.

---

## Phase 4: Per-Page Section Generation

### 4.1 Scaffold (multi-page)

- **New `stage_scaffold_multipage(manifest, project_name, build_cache)`**.
- For each page in manifest: `get_section_sequence(industry, page["page_type"])`, then filter NAV/FOOTER.
- Attach resulting section list to each page (e.g. `page["sections"]`).
- Write enriched manifest to `output/{project}/site-manifest.json`.

### 4.2 Sections (multi-page)

- **New `stage_sections_multipage(manifest, preset, project_name, …)`**.
- For each page: call existing section-generation logic with that page's section list.
- Write sections to **`output/{project}/sections/{page_id}/`** (e.g. `01-hero.tsx`, `02-features.tsx`).
- Return `dict[str, list[Path]]` (page_id → section files).
- Inner section loop unchanged (same prompts, template check, LLM).

### 4.3 Naming

Within each page dir, sections numbered as now (e.g. `01-hero.tsx`). Numbering resets per page.

---

## Phase 5: Multi-Route Assembly & Deploy

### 5.1 Assembly (multi-page)

- **New `stage_assemble_multipage(manifest, section_files_by_page, project_name)`**.
- For each page: read sections from `output/{project}/sections/{page_id}/`, compose one `page.tsx` (same import/render pattern as current single page).
- Write to `output/{project}/pages/{page_id}.tsx`.

### 5.2 Deploy (manifest-aware)

When manifest is active, **`stage_deploy`** (or a manifest-aware branch):

- Create `src/app/` directory structure from manifest `app_path` values (e.g. `collections/[handle]/`, `products/[handle]/`, `pages/[handle]/`).
- Copy each assembled page to its `app_path`.
- Copy shared components to `src/components/layout/`.
- Copy per-page sections to `src/components/sections/{page_id}/`.
- Fix import paths in each `page.tsx` to `@/components/sections/{page_id}/…`.
- Generate layout with Navigation + Footer.
- Generate **`not-found.tsx`** (simple 404).
- For dynamic routes: include `generateStaticParams() { return []; }` and `params: { handle: string }`. Add `// TODO: Layer 7 — Connect to Shopify Storefront API` at data point.
- Keep existing: package.json, globals.css, lib/utils.ts, animation copy, asset download, GSAP setup, npm install.

### 5.3 Dynamic route shells

No data fetching. Template structure and sections are correct; placeholders for handle/content. Layer 7 adds Storefront API.

---

## Phase 6: Build Logging & Legacy Preservation

### 6.1 Build log

Extend Supabase `build_log` (or metadata) with:

- `pages_generated`
- `sections_per_page` (page_id → count)
- `shared_components` (e.g. `["Navigation", "Footer"]`)

### 6.2 Legacy path

- When **no** site manifest and **no** `--industry`: use existing code path only (`stage_scaffold`, `stage_sections`, `stage_assemble`, `stage_deploy` as today).
- No changes to existing single-page functions; add **branch** in `main()` on presence of manifest.
- **Validation:** Run build with `--preset artisan-food --deploy --no-pause` (no `--industry`, no `--site-manifest`). Confirm single `page.tsx`, flat `sections/`, no route dirs, no shared layout components.

---

## Phase 7: Validation

1. **Default manifest build:** `python scripts/orchestrate.py <project> --industry artisan-food --deploy --no-pause`. Expect: multi-route app, shared Nav/Footer, per-page sections, build log with multi-page metrics.
2. **Legacy build:** `python scripts/orchestrate.py <project> --preset artisan-food --deploy --no-pause`. Expect: identical to pre–Layer 6 single-page output.
3. **Comparative report:** Single-page vs multi-page (sections count, build time, output structure).

Store-specific builds are out of scope for this plan and will be done after Layer 6 is integrated.

---

## Files to Create

| File | Purpose |
|------|---------|
| `scripts/lib/site_manifest.py` | Manifest schema, `generate_site_manifest()`, `load_site_manifest()` |

## Files to Modify

| File | Changes |
|------|---------|
| `scripts/lib/supabase_client.py` | `get_industry_metadata()`, optionally `get_all_page_sections()` |
| `scripts/orchestrate.py` | `--site-manifest`; `stage_shared_components`, `stage_scaffold_multipage`, `stage_sections_multipage`, `stage_assemble_multipage`; manifest-aware `stage_deploy`; `main()` branching |
| `CLAUDE.md` | Version, architecture, file map (after implementation) |

---

## Success Criteria

- [ ] With `--industry` and no `--site-manifest`, default manifest is generated and a full multi-route Next.js app is produced.
- [ ] With `--site-manifest <path>`, manifest is loaded and used for the build.
- [ ] Shared Navigation and Footer are generated once and used in layout; no NAV/FOOTER in per-page section lists.
- [ ] Each page type gets its own `page.tsx` at the correct `src/app/` path.
- [ ] Dynamic routes exist as static shells with placeholder content and Layer 7 TODO.
- [ ] Legacy path (`--preset` only) is unchanged and produces identical single-page output.
- [ ] Build log records multi-page metrics when manifest is used.

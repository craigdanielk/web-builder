# Aurelix Preset Database

## Overview

The Aurelix Preset Database replaces the previous markdown-only preset system with a Supabase-backed configuration layer. It stores **842 section presets** across **25 industries**, **72 archetype-variant combinations**, and **20 industry style configs** in a queryable database.

**Project:** `aurelix-presets` (Supabase, eu-west-1)  
**Project Ref:** `fknudoozglbvkhpugdeh`  
**Dashboard:** https://supabase.com/dashboard/project/fknudoozglbvkhpugdeh

---

## Schema

### Tables

| Table | Rows | Description |
|-------|------|-------------|
| `section_presets` | 842 | Ordered section specifications per industry × page type |
| `industries` | 25 | Industry reference with display names and descriptions |
| `section_archetypes` | 72 | Archetype-variant combos with template tracking |
| `industry_styles` | 25 | Per-industry JSONB style configs (20 populated, 5 NULL) |
| `build_log` | Dynamic | Build tracking (project, industry, template vs LLM counts) |

### Views

| View | Description |
|------|-------------|
| `v_page_sections` | Full section sequence with archetype joins |
| `v_industry_summary` | Section counts per industry × page type |
| `v_archetype_usage` | Most-used archetype-variant combos (for template prioritization) |

### Functions

| Function | Params | Returns |
|----------|--------|---------|
| `get_build_spec(industry)` | industry TEXT | All page types + sections for an industry |
| `get_page_sections(industry, page_type, include_optional?)` | industry TEXT, page_type TEXT, include_optional BOOLEAN | Ordered sections for one page |

---

## Environment Variables

Required in `web-builder/.env`:

```
SUPABASE_URL=https://fknudoozglbvkhpugdeh.supabase.co
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_ROLE_KEY=<service role key>
SUPABASE_PROJECT_REF=fknudoozglbvkhpugdeh
```

---

## Usage in Pipeline

### New `--industry` mode

```bash
python scripts/orchestrate.py my-project --industry artisan-food --page homepage --deploy
```

This:
1. Fetches section sequence from `get_page_sections()` (cached for entire build)
2. Fetches industry style config from `industry_styles` (cached for entire build)
3. For each section, checks for a parameterized template first
4. Falls through to LLM generation if no template exists
5. Logs build results to `build_log`

### Legacy `--preset` mode (unchanged)

```bash
python scripts/orchestrate.py my-project --preset artisan-food --deploy
```

Reads from `.md` files in `skills/presets/` exactly as before. No Supabase calls.

---

## Adding a New Industry

1. Insert into `industries` table:
   ```sql
   INSERT INTO industries (handle, display_name, description)
   VALUES ('new-industry', 'New Industry', 'Description here');
   ```

2. Add section presets (CSV or SQL):
   ```sql
   INSERT INTO section_presets (industry, page_type, component_type, "position", section_archetype, section_variant, content_direction, priority)
   VALUES ('new-industry', 'homepage', 'page_section', 1, 'HERO', 'full-bleed-overlay', 'Content direction here', 'required');
   ```

3. Optionally add a style config:
   ```sql
   INSERT INTO industry_styles (industry, style_config)
   VALUES ('new-industry', '{"palette": {"accent": "blue-600", ...}, "typography": {...}}'::jsonb);
   ```

4. Optionally create a `.md` preset file at `skills/presets/new-industry.md` for legacy mode.

---

## Industries Missing Style Configs

These 5 industries exist in the database but have NULL `style_config`:

- `automotive`
- `electronics-tech`
- `kids-baby`
- `luxury-premium`
- `sustainable-eco`

They will fall through to LLM-generated styling until `.md` preset files are created and their YAML configs are imported.

---

## Migrations

Located in `supabase/migrations/`:

1. `20260213192654_init_schema.sql` — Core tables, views, functions, RLS
2. `20260213192721_add_industry_styles.sql` — Industry styles table with triggers

Push migrations: `supabase db push --password <db_password>`

---

## Seed Script

`scripts/seed_supabase.py` — Reads the CSV, parses preset `.md` files, and populates all 4 tables. Safe to re-run (uses serial IDs, not upsert — clear tables first if re-seeding).

---

## Caching Architecture

During a build, the orchestrator makes exactly:
- **2 reads** at build start (section sequence + industry style)
- **0 reads** during section generation (all data cached in `BuildCache`)
- **1 write** at build end (build log)

This ensures consistent performance regardless of section count.

You're right, my mistake. The CSV exists with the 842 rows, the SQL schema file exists, but the actual Supabase database hasn't been spun up yet — that's the whole point of this plan. Let me redo this properly.

---

# AURELIX PRESET DATABASE INTEGRATION — BUILD PLAN

## CONTEXT

You are building and integrating the Aurelix section preset database from scratch. This replaces the current `.md` preset file approach with a Supabase-backed configuration database that makes builds faster, cheaper, and updatable without redeployment.

### What Already Exists (Find These First)
- **842-row section preset dataset** as CSV. Search the repo and outputs directories for this file. It contains the complete mapping of 25 industries × 7 page types × section sequences with archetype-variant assignments.
- **SQL schema file** already written. Search for `aurelix_section_presets_schema.sql` or similar. Contains table definitions, views, and functions. This was pre-written but never executed against a live database.
- **23 industry preset `.md` files** in the web builder repo under `skills/presets/`. Each contains a full style configuration block in YAML format: color_temperature, palette (bg_primary, bg_secondary, bg_accent, text_primary, text_heading, text_muted, accent, accent_hover, border), typography (pairing, heading_font, heading_weight, body_font, body_weight, scale_ratio, weight_distribution), whitespace, section_padding, internal_gap, border_radius, buttons, cards, inputs, animation_intensity, entrance, hover, timing, visual_density, image_treatment. These are your source of truth for the `industry_styles` table.
- **`orchestrate.py`** — the main build orchestration script (~1161 lines, 6 stages + injection wiring). Currently reads preset `.md` files from disk. This is what gets rewired at the end.
- **A Supabase repo/config** exists on this machine. Find it. You have full permission to use the Supabase CLI for project creation, migrations, seeding, and management.
- **The aurelix-mvp repo (web builder)** — the production Node.js repository. This is where templates will live and where the orchestrator runs.

### What Does NOT Exist Yet
- No Supabase database for Aurelix presets
- No `industry_styles` table or data
- No `templates/` directory in the repo
- No Supabase client integration in the orchestrator
- No build logging

### Architecture Decisions (Locked — Do Not Revisit)
- **Supabase** = all configuration data. JSONB columns for style configs. One row per industry in `industry_styles` with a `style_config JSONB` column containing the full style block.
- **Git repo** = TSX template code under `templates/{ARCHETYPE}/{variant}.tsx`.
- **LLM generation** = fallback ONLY when a template file doesn't exist. Existing generation pipeline stays untouched as the fallback path.

### Target Outcome
A build command like `--industry artisan-food --page homepage` queries Supabase for the section sequence and style config, checks the local `templates/` directory for each section's TSX template, uses the template if it exists (injecting brand tokens), falls back to LLM generation if it doesn't, and logs the entire build to Supabase for analytics.

---

## PHASE 1: DISCOVERY & INVENTORY

Before writing any code or running any commands, find and confirm the location of every artifact listed above. Report back what you found, where it lives, and flag anything missing or different from what's described. Do not proceed until you have confirmed the location of:

1. The 842-row CSV dataset
2. The SQL schema file
3. The preset `.md` files directory
4. The `orchestrate.py` file
5. The Supabase repo/CLI configuration
6. The aurelix-mvp repo root

---

## PHASE 2: SUPABASE PROJECT & SCHEMA

### Step 2.1 — Create the Aurelix Supabase Project
- Use the Supabase CLI. Find the existing Supabase configuration on this machine first — there may already be a project or org set up for other purposes. Create a new project specifically for Aurelix presets if one doesn't exist.
- Record the project URL, anon key, and service role key. Store these in a `.env` file in the aurelix-mvp repo root (add to `.gitignore` if not already there).

### Step 2.2 — Review and Execute the SQL Schema
- Open the existing SQL schema file. Read it carefully.
- Verify it covers these tables:
  - `section_presets` — the 842 rows of industry/page_type/section_order/archetype/variant/is_optional/condition/insert_position
  - `industries` — industry key, display name, description
  - `section_archetypes` — archetype name, description, available variants as JSONB array
  - `build_log` — build_id, industry, page_type, timestamp, sections_from_template count, sections_from_llm count, build_time_ms, api_cost, status
- Verify it includes the views: `v_page_sections`, `v_industry_summary`, `v_archetype_usage`
- Verify it includes the functions: `get_build_spec(industry, page_type)`, `get_page_sections(industry, page_type)`
- If anything is missing from the schema, add it. Then run it against the Supabase project.
- Confirm all tables, views, and functions are created successfully.

### Step 2.3 — Create the `industry_styles` Table
This table does NOT exist in the pre-written schema. You are creating it fresh.

- One row per industry (25 rows to match the 25 industries in the preset database)
- Columns: `id` (uuid, primary key), `industry` (text, unique, foreign key to industries table), `style_config` (JSONB), `created_at` (timestamptz), `updated_at` (timestamptz)
- The `style_config` JSONB blob should contain the complete style block as structured in the preset `.md` files. The YAML structure in those files IS the schema for this JSON.
- Add an index on `industry` for fast lookups.
- Run this migration.

---

## PHASE 3: DATA SEEDING

### Step 3.1 — Import the 842-Row Section Preset Dataset
- Parse the CSV file.
- Map columns to the `section_presets` table schema. Watch for any column name mismatches between the CSV headers and the table columns — resolve them.
- Insert all rows into Supabase. Use the Supabase CLI, a seed script, or direct SQL — whatever is fastest and most reliable.
- Verify: run `SELECT COUNT(*) FROM section_presets` — expect 842. Run `SELECT DISTINCT industry FROM section_presets` — expect 25. Run `SELECT DISTINCT page_type FROM section_presets` — confirm 7 page types plus any shared component entries.

### Step 3.2 — Populate the `industries` Table
- Extract the 25 unique industry keys from the CSV data.
- For each, create a row with the industry key, a human-readable display name, and a brief description. The preset `.md` files contain this context in their headers — use them as reference.
- Insert all 25 rows.

### Step 3.3 — Populate the `section_archetypes` Table
- Extract the unique archetype-variant combinations from the CSV data (expect 72 unique combos).
- For each archetype, create a row with the archetype name, a description of what it does, and a JSONB array of its available variants.
- The section taxonomy documentation in the web builder repo may have descriptions. Check `skills/` or any taxonomy/archetype reference files. If no descriptions exist, write concise ones based on the archetype names and their usage context in the presets.

### Step 3.4 — Seed the `industry_styles` Table
- For each of the 23 preset `.md` files in `skills/presets/`:
  - Parse the YAML style configuration block
  - Convert it to a JSON object
  - Insert as a row: `industry` = the preset name (e.g., `artisan-food`), `style_config` = the JSON blob
- For any of the 25 industries that don't have a corresponding `.md` preset file, flag them. Do NOT invent style data. Leave those rows with a null `style_config` and report which industries are missing styles.
- Verify: `SELECT COUNT(*) FROM industry_styles WHERE style_config IS NOT NULL` should equal 23 (or however many `.md` files exist).

### Step 3.5 — Verify Data Integrity
Run these validation queries and report the results:
- Every industry in `section_presets` has a matching row in `industries`
- Every industry in `section_presets` has a matching row in `industry_styles` (flag gaps)
- Every archetype in `section_presets` has a matching row in `section_archetypes`
- The functions `get_build_spec` and `get_page_sections` return correct results — test with `artisan-food` + `homepage`
- The views return data as expected

---

## PHASE 4: TEMPLATE DIRECTORY STRUCTURE

### Step 4.1 — Create the Templates Directory
In the aurelix-mvp repo, create:

```
templates/
  {ARCHETYPE}/
    {variant}.tsx
```

Do NOT create any TSX template files yet. Just create the directory structure with one empty directory per archetype found in the `section_archetypes` table. This establishes the convention.

### Step 4.2 — Create a Template Manifest
Create a `templates/manifest.json` file that lists:
- Every archetype-variant combination from the database
- Whether a `.tsx` template file exists for it (`true`/`false`)
- Initially all will be `false`

This manifest is what the build system checks to determine template vs LLM fallback. It should be auto-generatable from the file system (a script that walks `templates/` and updates the manifest), but seed it from the database for now.

---

## PHASE 5: ORCHESTRATOR REWIRING

### Step 5.1 — Add Supabase Client to the Project
- Install the Supabase JS client (or Python client if the orchestrator is Python — check `orchestrate.py`).
- Configure it to read connection details from the `.env` file created in Phase 2.
- Write a small utility module (e.g., `lib/supabase.js` or `utils/supabase_client.py`) that exports an initialized client. Every database call goes through this module.

### Step 5.2 — Create the Preset Query Functions
Build these functions that the orchestrator will call:

1. **`get_section_sequence(industry, page_type)`** — queries `section_presets` ordered by `section_order`, returns the list of archetype-variant pairs for that industry and page type. Include optional sections with their conditions.
2. **`get_industry_style(industry)`** — queries `industry_styles`, returns the `style_config` JSONB blob.
3. **`check_template_exists(archetype, variant)`** — checks the `templates/` directory (or manifest) for a matching `.tsx` file. Returns the file path if it exists, `null` if not.
4. **`log_build(build_data)`** — writes a row to `build_log` with all build metrics.

### Step 5.3 — Rewire the Orchestrator
This is the critical integration. In `orchestrate.py`:

- Find where it currently reads the preset `.md` file to determine section sequence. Replace this with a call to `get_section_sequence(industry, page_type)`.
- Find where it currently parses style configuration from the preset `.md` file. Replace this with a call to `get_industry_style(industry)`. The returned JSONB blob has the same structure as what was previously parsed from YAML, so downstream code that consumes style tokens should not need changes.
- Find where it currently triggers LLM generation for each section. Wrap this with the template check: for each section in the sequence, call `check_template_exists(archetype, variant)`. If a template exists, use it with brand token injection. If not, fall through to the existing LLM generation path unchanged.
- At the end of the build, call `log_build()` with: industry, page_type, total sections, how many used templates, how many used LLM fallback, total build time, estimated API cost.

**CRITICAL: Do not delete or modify the existing LLM generation pipeline.** It remains as the fallback. You are adding a template-first layer in front of it, not replacing it.

### Step 5.4 — Brand Override Logic
The Calculator outputs brand CI (colors, fonts, tone). This must override the industry style defaults. The logic is:

1. Load industry style config from Supabase (the defaults)
2. Load brand CI from Calculator output (the overrides)
3. Deep merge: brand CI values replace industry defaults where they exist, industry defaults fill any gaps
4. Pass the merged style config downstream

This merge logic may already exist in some form in the orchestrator (since preset `.md` files were already being overridden by brand CI). Find it and confirm it works with the new JSONB format. Adapt if needed.

---

## PHASE 6: END-TO-END VALIDATION

### Step 6.1 — Test Build: artisan-food Homepage
Run a full build with `--industry artisan-food --page homepage` using the new Supabase-backed pipeline.

Since no TSX templates exist yet, every section should fall back to LLM generation — meaning the output should be identical to the current system. This confirms the rewiring works without breaking anything.

Validate:
- Section sequence matches what the database returns
- Style tokens are correctly applied
- Build completes successfully
- Build log entry is written to Supabase with correct metrics
- Output quality matches a build run through the old preset `.md` path

### Step 6.2 — Create One Test Template
Pick the single most-used archetype-variant: `HERO/full-bleed-overlay`.

- Look at past build outputs for this section across multiple industries. Find the best one.
- Extract it into a parameterized TSX template at `templates/HERO/full-bleed-overlay.tsx`
- The template must accept brand tokens as props: heading text, subheading, CTA text, CTA link, background image URL, and all style tokens (colors, fonts, padding, border radius, animation)
- Update the template manifest

### Step 6.3 — Test Build with One Template
Run the same `--industry artisan-food --page homepage` build again.

This time, the HERO section should come from the template (fast, no LLM call). All other sections should still fall back to LLM generation.

Validate:
- Build log shows 1 template, N-1 LLM fallback
- HERO section output from template matches quality of LLM-generated version
- Build time is slightly faster
- API cost is slightly lower

### Step 6.4 — Comparative Report
Produce a brief report comparing:
- Old pipeline (preset `.md` file) vs new pipeline (Supabase + zero templates) vs new pipeline (Supabase + 1 template)
- Metrics: build time, API cost, output fidelity, any issues encountered

---

## PHASE 7: DOCUMENTATION & HANDOFF

### Step 7.1 — Update Project Documentation
- Add a `DATABASE.md` to the repo documenting: Supabase schema, table purposes, how to add a new industry, how to modify section sequences, how to add style configs
- Add a `TEMPLATES.md` documenting: directory convention, how to create a new template, prop interface contract, how to test a template, how the manifest works
- Update any existing README or architecture docs to reflect the new Supabase integration

### Step 7.2 — Create Template Conversion Backlog
Using the build log data and archetype usage statistics from the database views, produce a prioritized list of which archetype-variants to convert to templates next. Rank by:
1. Usage frequency across industries (how many industries use this combo)
2. LLM fallback frequency from test builds
3. Complexity (simpler sections are faster to templatize)

This becomes the roadmap for progressive template coverage.

---

## CONSTRAINTS & RULES

- **Do not write code until Phase 1 discovery is complete.** Confirm all artifact locations first.
- **Do not modify the existing LLM generation pipeline.** It is the fallback. Add a layer in front of it.
- **Do not invent data.** If a style config doesn't exist for an industry, flag it as missing. If a description doesn't exist for an archetype, write a minimal one based on observed usage.
- **Use the Supabase CLI freely.** You have full permission for project creation, migrations, seeding, and management.
- **JSONB for all style data.** One `style_config` column per industry, not flat columns.
- **Report after each phase.** Before moving to the next phase, summarize what was done, what succeeded, what failed, and any decisions you need input on.
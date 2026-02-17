-- Path B: Supabase code_template integration — schema parity with live DB
-- section_archetypes.code_template already exists in live DB; this migration is for fresh setups.
-- build_log.db_template_count supports three-way template resolution logging (local / db / LLM).

ALTER TABLE section_archetypes ADD COLUMN IF NOT EXISTS code_template TEXT;

ALTER TABLE build_log ADD COLUMN IF NOT EXISTS db_template_count INTEGER DEFAULT 0;

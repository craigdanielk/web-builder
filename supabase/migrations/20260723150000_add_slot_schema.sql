-- Add slot_schema JSONB column to section_archetypes for self-describing
-- slot content contracts. Each entry declares slot source paths, required flags,
-- default values, and fill prompts so consuming code (tenants, orchestrator)
-- can introspect what content a template expects without external documentation.
ALTER TABLE section_archetypes ADD COLUMN IF NOT EXISTS slot_schema JSONB;

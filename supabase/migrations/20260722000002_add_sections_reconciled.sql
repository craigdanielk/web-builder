-- Section reconciliation column for build_log
--
-- End-state assertion [2]: build records reconciliation
-- (db_column_exists on build_log.sections_reconciled).
--
-- sections_reconciled stores the reconciliation metadata: how many sections
-- came from registry (required), how many from harvest, what was gap-filled,
-- and which duplicates were resolved. Written by reconcile_sections() at
-- build end. This enables the attractor test to verify the brief's end state.

ALTER TABLE build_log ADD COLUMN IF NOT EXISTS sections_reconciled JSONB DEFAULT NULL;

COMMENT ON COLUMN build_log.sections_reconciled
  IS 'Reconciliation metadata from reconcile_sections(): {total, registry_count, harvest_count, gap_filled_count, duplicates_resolved}. Written once at build end.';

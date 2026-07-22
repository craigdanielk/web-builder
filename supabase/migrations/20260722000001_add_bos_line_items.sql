-- Bill of Sale line-items column for build_log
--
-- End-state assertion [2]: build records BoS line items addressed
-- (db_column_exists on build_log.bos_line_items).
--
-- bos_line_items records how many Bill of Sale line items were addressed
-- during this build. The re-audit loop reads build_trace per item to
-- determine what was (or was not) built.

ALTER TABLE build_log ADD COLUMN IF NOT EXISTS bos_line_items INTEGER DEFAULT 0;

COMMENT ON COLUMN build_log.bos_line_items
  IS 'Number of Bill of Sale line items addressed in this build. Written by BoS orchestration.';

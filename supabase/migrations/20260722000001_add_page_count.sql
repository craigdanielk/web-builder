-- Add page_count column to build_log for multipage build tracking
-- Supports assertions [2] in node_7_end_state_contract:
-- "build records page count"
ALTER TABLE build_log ADD COLUMN IF NOT EXISTS page_count INTEGER DEFAULT 1;

COMMENT ON COLUMN build_log.page_count IS 'Number of pages built for multipage builds (default 1 for single-page).';

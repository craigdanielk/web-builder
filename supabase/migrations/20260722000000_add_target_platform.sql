-- Add target_platform column to build_log for deploy adapter tracking
-- Supports assertions [3] in node_7_end_state_contract:
-- "build_log records deploy target_platform (consumer reads adapter used)"
ALTER TABLE build_log ADD COLUMN IF NOT EXISTS target_platform TEXT DEFAULT 'shopify';

COMMENT ON COLUMN build_log.target_platform IS 'Deploy target platform (shopify|vercel). Selects the deploy adapter used during build.';

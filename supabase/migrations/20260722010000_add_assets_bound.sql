-- Add assets_bound column to build_log for per-section asset binding tracking.
-- Supports BRIEF #33297 node_7_end_state_contract:
-- "build records bound assets" (db_column_exists: build_log.assets_bound)
-- Records how many sections were bound to a tenant creative_asset during generation.
ALTER TABLE build_log ADD COLUMN IF NOT EXISTS assets_bound INTEGER;

COMMENT ON COLUMN build_log.assets_bound IS 'Count of sections bound to a tenant creative_asset (self-hosted path injected) during generation. NULL when no tenant assets present (non-tenant / registry builds).';

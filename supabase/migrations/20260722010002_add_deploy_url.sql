-- Add deploy_url column to build_log for end-to-end deploy tracking.
-- Supports BRIEF #33299 node_7_end_state_contract:
-- "build records the deployed site URL" (db_column_exists: build_log.deploy_url)
-- Records the vercel deployment URL when a composed tenant build deploys.
ALTER TABLE build_log ADD COLUMN IF NOT EXISTS deploy_url TEXT;

COMMENT ON COLUMN build_log.deploy_url IS 'Deployed site URL (e.g. the vercel production URL) recorded when a composed end-to-end tenant build deploys. NULL for build-only runs that do not deploy.';

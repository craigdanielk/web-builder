-- App-route seam scaffolding column for build_log
--
-- BRIEF #33298 — build-the-unified-app-shell-and-exchange-app-route-seams
-- End-state assertion [2]: build records scaffolded app-route seams
-- (db_column_exists on build_log.app_routes_scaffolded).
--
-- app_routes_scaffolded stores the count of app-route seams that were scaffolded
-- for carried-into-unified-app BoS items. Written by the build process when
-- the unified app shell is generated. This enables the attractor test to verify
-- the brief's end state.

ALTER TABLE build_log ADD COLUMN IF NOT EXISTS app_routes_scaffolded INTEGER DEFAULT NULL;

COMMENT ON COLUMN build_log.app_routes_scaffolded
  IS 'Count of app-route seams scaffolded for carried-into-unified-app BoS items. Written during unified app shell generation.';

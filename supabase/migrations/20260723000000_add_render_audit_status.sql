-- Add render_audit_status column to build_log for post-build render audit tracking.
-- Supports BRIEF #33321 node_7_end_state_contract:
-- "web-builder runs render-audit as a mandatory post-build gate whose result
--  is recorded in build_log.render_audit_status"
-- (db_column_exists: build_log.render_audit_status)
ALTER TABLE build_log ADD COLUMN IF NOT EXISTS render_audit_status TEXT CHECK (render_audit_status IN ('passed', 'review_needed', 'failed', 'skipped'));

COMMENT ON COLUMN build_log.render_audit_status IS 'Post-build render audit outcome: passed (no defects), review_needed (unaccepted defect groups exist), failed (audit crashed or didnt run), skipped (audit not available). Recorded automatically by stage_render_audit after deploy.';

-- BRIEF #33280 — wire web-builder to the tenant capture layer.
-- Add a nullable tenant coordinate to build_log so tenant-driven builds can be
-- attributed to the tenant that drove them. Nullable + IF NOT EXISTS keeps this
-- idempotent and non-breaking: existing (non-tenant) builds are unaffected and
-- re-running the migration is a no-op.
ALTER TABLE build_log ADD COLUMN IF NOT EXISTS tenant_id text;

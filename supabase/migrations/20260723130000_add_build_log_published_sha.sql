-- BRIEF #33323 — git-publish source-of-truth: record the published commit SHA.
ALTER TABLE build_log ADD COLUMN IF NOT EXISTS published_sha text;

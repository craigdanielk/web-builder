-- BRIEF #33384 (atomic 2/3) — insertion_events table
-- Tracks section insertion events during the build pipeline.
-- Each row records one insertion attempt for a specific archetype/variant
-- in a specific slot within a build run.

CREATE TABLE IF NOT EXISTS insertion_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    build_run TEXT NOT NULL,
    tenant TEXT,
    archetype TEXT NOT NULL,
    variant TEXT NOT NULL,
    slot INTEGER NOT NULL DEFAULT 0,
    event TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_insertion_events_build_run ON insertion_events(build_run);
CREATE INDEX IF NOT EXISTS idx_insertion_events_tenant ON insertion_events(tenant);
CREATE INDEX IF NOT EXISTS idx_insertion_events_archetype ON insertion_events(archetype);
CREATE INDEX IF NOT EXISTS idx_insertion_events_event ON insertion_events(event);
CREATE INDEX IF NOT EXISTS idx_insertion_events_created_at ON insertion_events(created_at);

-- Composite index for slot-level event queries per build
CREATE INDEX IF NOT EXISTS idx_insertion_events_build_slot ON insertion_events(build_run, slot);

-- Row Level Security
ALTER TABLE insertion_events ENABLE ROW LEVEL SECURITY;

-- Service role has full access
CREATE POLICY "Service role can manage insertion_events" ON insertion_events
    FOR ALL USING (auth.role() = 'service_role');

-- Public read access for build observability
CREATE POLICY "Insertion events are publicly readable" ON insertion_events
    FOR SELECT USING (true);

-- Comments
COMMENT ON TABLE insertion_events IS 'Section insertion events during build pipeline';
COMMENT ON COLUMN insertion_events.build_run IS 'Build run identifier (project name or run ID)';
COMMENT ON COLUMN insertion_events.tenant IS 'Tenant slug or UUID for multi-tenant builds';
COMMENT ON COLUMN insertion_events.archetype IS 'Section archetype (e.g. HERO, FEATURES)';
COMMENT ON COLUMN insertion_events.variant IS 'Section variant (e.g. full-bleed-overlay)';
COMMENT ON COLUMN insertion_events.slot IS 'Section slot/position in the build sequence';
COMMENT ON COLUMN insertion_events.event IS 'Event type (inserted, skipped, replaced, failed)';
COMMENT ON COLUMN insertion_events.reason IS 'Reason for the event outcome';

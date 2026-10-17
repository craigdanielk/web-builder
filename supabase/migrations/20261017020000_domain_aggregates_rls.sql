-- ═══════════════════════════════════════════════════════════════════
-- AURELIX MIGRATION: RLS Policies & Triggers for Consolidated Aggregates
-- ═══════════════════════════════════════════════════════════════════

-- 1. Enable RLS on New Aggregate Root Tables
ALTER TABLE IF EXISTS agency_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS discovery_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS tenant_redirects ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS runtime_deployments ENABLE ROW LEVEL SECURITY;

-- 2. Configure Service Role Policies (Full Administrative Access)
DO $$
DECLARE
    tbl TEXT;
    tbls TEXT[] := ARRAY[
        'agency_executions', 
        'discovery_sessions', 
        'tenant_redirects', 
        'runtime_deployments'
    ];
BEGIN
    FOREACH tbl IN ARRAY tbls LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = tbl) THEN
            EXECUTE format('DROP POLICY IF EXISTS "Service role full access on %I" ON %I;', tbl, tbl);
            EXECUTE format('CREATE POLICY "Service role full access on %I" ON %I FOR ALL USING (auth.role() = ''service_role'');', tbl, tbl);
        END IF;
    END LOOP;
END $$;

-- 3. Attach Automated Updated-At Triggers
DO $$
DECLARE
    tbl TEXT;
    tbls TEXT[] := ARRAY[
        'agency_executions', 
        'discovery_sessions', 
        'tenant_redirects', 
        'runtime_deployments'
    ];
BEGIN
    FOREACH tbl IN ARRAY tbls LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = tbl) THEN
            EXECUTE format('DROP TRIGGER IF EXISTS trg_update_timestamp_%I ON %I;', tbl, tbl);
            EXECUTE format('CREATE TRIGGER trg_update_timestamp_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();', tbl, tbl);
        END IF;
    END LOOP;
END $$;

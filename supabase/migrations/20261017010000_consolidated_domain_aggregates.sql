-- ═══════════════════════════════════════════════════════════════════
-- AURELIX MIGRATION: Consolidated Domain Aggregates (DDD Architecture)
-- ═══════════════════════════════════════════════════════════════════
-- Purpose: Consolidates domain persistence into cohesive Aggregate Roots
-- and non-destructively augments existing Supabase tables.
-- ═══════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ───────────────────────────────────────────────────────────────────
-- 1. AUGMENT EXISTING TABLES
-- ───────────────────────────────────────────────────────────────────

-- Projects: Add pipeline state & agency lifecycle fields
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS agency_status TEXT DEFAULT 'draft' 
        CHECK (agency_status IN ('draft', 'discovery', 'synthesizing', 'verifying', 'provisioning', 'deployed', 'archived')),
    ADD COLUMN IF NOT EXISTS pipeline_config JSONB DEFAULT '{}'::jsonb;

-- Products: Add multi-variant ecommerce matrix & categorization
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS handle TEXT,
    ADD COLUMN IF NOT EXISTS vendor TEXT,
    ADD COLUMN IF NOT EXISTS product_type TEXT,
    ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS variants JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS images JSONB DEFAULT '[]'::jsonb;

-- Verifications: Add cryptographic audit receipt and commit SHA
ALTER TABLE verifications
    ADD COLUMN IF NOT EXISTS receipt_sha TEXT,
    ADD COLUMN IF NOT EXISTS commit_sha TEXT,
    ADD COLUMN IF NOT EXISTS gate_name TEXT;

-- Build Log: Add AST fingerprint and applied token references
ALTER TABLE build_log
    ADD COLUMN IF NOT EXISTS ast_hash TEXT,
    ADD COLUMN IF NOT EXISTS design_tokens_applied JSONB DEFAULT '{}'::jsonb;


-- ───────────────────────────────────────────────────────────────────
-- 2. NEW DOMAIN AGGREGATE ROOT TABLES
-- ───────────────────────────────────────────────────────────────────

-- A. Agency Kernel Aggregate: Multi-Domain Pipeline Executions & Capability Ledger
CREATE TABLE IF NOT EXISTS agency_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    pipeline_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued' 
        CHECK (status IN ('queued', 'running', 'paused', 'completed', 'failed', 'cancelled')),
    current_stage TEXT NOT NULL DEFAULT 'initialization',
    trace_id TEXT NOT NULL,
    inputs JSONB DEFAULT '{}'::jsonb,
    context_state JSONB DEFAULT '{}'::jsonb,
    step_ledger JSONB DEFAULT '[]'::jsonb,
    error_summary TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ae_tenant ON agency_executions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ae_project ON agency_executions(project_id);
CREATE INDEX IF NOT EXISTS idx_ae_status ON agency_executions(status);
CREATE INDEX IF NOT EXISTS idx_ae_trace ON agency_executions(trace_id);


-- B. Discovery Aggregate: Unified Crawl, IA Taxonomy & Brand Token Document
CREATE TABLE IF NOT EXISTS discovery_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    target_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued' 
        CHECK (status IN ('queued', 'crawling', 'completed', 'failed')),
    crawl_depth INTEGER NOT NULL DEFAULT 2,
    pages_discovered INTEGER DEFAULT 0,
    extracted_taxonomies JSONB DEFAULT '{}'::jsonb,
    brand_tokens JSONB DEFAULT '{}'::jsonb,
    harvested_copy JSONB DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ds_tenant ON discovery_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ds_status ON discovery_sessions(status);


-- C. Traffic Router Aggregate: 301/302 URL Normalization & Migration Rules
CREATE TABLE IF NOT EXISTS tenant_redirects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_path TEXT NOT NULL,
    target_path TEXT NOT NULL,
    status_code INTEGER NOT NULL DEFAULT 301 
        CHECK (status_code IN (301, 302, 307, 308)),
    preserve_query_params BOOLEAN NOT NULL DEFAULT TRUE,
    match_type TEXT NOT NULL DEFAULT 'exact' 
        CHECK (match_type IN ('exact', 'prefix', 'regex')),
    status TEXT NOT NULL DEFAULT 'active' 
        CHECK (status IN ('active', 'inactive', 'testing')),
    hit_count INTEGER DEFAULT 0,
    last_hit_at TIMESTAMPTZ,
    sync_state JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, source_path)
);

CREATE INDEX IF NOT EXISTS idx_tr_tenant ON tenant_redirects(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tr_source ON tenant_redirects(source_path);


-- D. Runtime Ops Aggregate: Release Deployments & Synthetic Health Monitoring
CREATE TABLE IF NOT EXISTS runtime_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    target_platform TEXT NOT NULL 
        CHECK (target_platform IN ('shopify', 'vercel', 'cloudflare', 'local_rsc')),
    environment TEXT NOT NULL DEFAULT 'production' 
        CHECK (environment IN ('preview', 'staging', 'canary', 'production')),
    commit_sha TEXT NOT NULL,
    build_artifact_uri TEXT,
    deploy_url TEXT NOT NULL,
    preview_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'deploying', 'healthy', 'degraded', 'failed', 'rolled_back')),
    verification_receipt_sha TEXT,
    health_probes JSONB DEFAULT '[]'::jsonb,
    incident_log JSONB DEFAULT '[]'::jsonb,
    deployed_by TEXT NOT NULL DEFAULT 'aurelix-runtime-operator',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rd_tenant ON runtime_deployments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_rd_status ON runtime_deployments(status);
CREATE INDEX IF NOT EXISTS idx_rd_commit ON runtime_deployments(commit_sha);


-- ───────────────────────────────────────────────────────────────────
-- 3. TYPED VIEWS
-- ───────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW v_agency_projects AS
SELECT 
    p.id,
    p.tenant_id,
    p.name,
    p.domain,
    p.agency_status,
    p.pipeline_config,
    p.github_repo,
    p.created_at,
    p.updated_at
FROM projects p;

-- Add tenant-related tables for multi-tenant web-builder
-- Supports BRIEF #33318: idempotent tenant provisioning

-- Tenants table: core tenant registry with deploy target configuration
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,
    trading_name TEXT,
    entity_name TEXT,
    legal_name TEXT,
    company_name TEXT,
    domain TEXT,
    logo_url TEXT,
    brand_voice TEXT,
    deploy_target TEXT DEFAULT 'shopify' CHECK (deploy_target IN ('shopify', 'vercel')),
    status TEXT DEFAULT 'provisioning' CHECK (status IN ('provisioning', 'active', 'suspended')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Phase0 field values: brand/domain/etc. key/value capture rows
CREATE TABLE IF NOT EXISTS phase0_field_values (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    field_key TEXT NOT NULL,
    value JSONB NOT NULL,
    fill_status TEXT DEFAULT 'complete' CHECK (fill_status IN ('pending', 'partial', 'complete')),
    source TEXT DEFAULT 'manual',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, field_key)
);

-- Creative assets: tenant media (logos, imagery, campaign assets)
CREATE TABLE IF NOT EXISTS creative_assets (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('logo', 'image', 'document', 'other')),
    storage_path TEXT,
    cdn_url TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Competitor profiles: benchmark / competitor data
CREATE TABLE IF NOT EXISTS competitor_profiles (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    competitor_name TEXT NOT NULL,
    competitor_url TEXT,
    analysis_notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);
CREATE INDEX IF NOT EXISTS idx_phase0_tenant_id ON phase0_field_values(tenant_id);
CREATE INDEX IF NOT EXISTS idx_phase0_field_key ON phase0_field_values(field_key);
CREATE INDEX IF NOT EXISTS idx_creative_assets_tenant_id ON creative_assets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_competitor_profiles_tenant_id ON competitor_profiles(tenant_id);

-- Row Level Security
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE phase0_field_values ENABLE ROW LEVEL SECURITY;
ALTER TABLE creative_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitor_profiles ENABLE ROW LEVEL SECURITY;

-- Service role has full access
CREATE POLICY "Service role can manage tenants" ON tenants
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage phase0_field_values" ON phase0_field_values
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage creative_assets" ON creative_assets
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage competitor_profiles" ON competitor_profiles
    FOR ALL USING (auth.role() = 'service_role');

-- Public read access for tenant resolution
CREATE POLICY "Tenants are publicly readable" ON tenants
    FOR SELECT USING (true);

CREATE POLICY "Phase0 values are publicly readable" ON phase0_field_values
    FOR SELECT USING (true);

CREATE POLICY "Creative assets are publicly readable" ON creative_assets
    FOR SELECT USING (true);

CREATE POLICY "Competitor profiles are publicly readable" ON competitor_profiles
    FOR SELECT USING (true);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_phase0_field_values_updated_at BEFORE UPDATE ON phase0_field_values
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_creative_assets_updated_at BEFORE UPDATE ON creative_assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_competitor_profiles_updated_at BEFORE UPDATE ON competitor_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments
COMMENT ON TABLE tenants IS 'Core tenant registry with deploy target configuration';
COMMENT ON COLUMN tenants.deploy_target IS 'Deploy target platform (shopify|vercel)';
COMMENT ON TABLE phase0_field_values IS 'Brand/domain/etc. key/value capture rows per tenant';
COMMENT ON TABLE creative_assets IS 'Tenant media (logos, imagery, campaign assets)';
COMMENT ON TABLE competitor_profiles IS 'Benchmark / competitor data per tenant';

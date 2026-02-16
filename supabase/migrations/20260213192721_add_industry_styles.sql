-- ═══════════════════════════════════════════════════════════════
-- INDUSTRY STYLES TABLE
-- Stores per-industry style configurations (JSONB)
-- Not in original schema — added as separate migration
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE industry_styles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    industry TEXT UNIQUE NOT NULL,
    style_config JSONB,
    compact_style_header TEXT,
    content_direction JSONB,
    photography_direction JSONB,
    known_pitfalls TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fast lookup by industry name
CREATE INDEX idx_industry_styles_industry ON industry_styles(industry);

-- RLS
ALTER TABLE industry_styles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Industry styles are publicly readable" ON industry_styles
    FOR SELECT USING (true);

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_industry_styles_updated_at
    BEFORE UPDATE ON industry_styles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

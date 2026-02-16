-- ═══════════════════════════════════════════════════════════════
-- AURELIX SECTION PRESET DATABASE
-- Supabase PostgreSQL Schema
-- ═══════════════════════════════════════════════════════════════

-- Main presets table
CREATE TABLE section_presets (
    id SERIAL PRIMARY KEY,
    industry TEXT NOT NULL,
    page_type TEXT NOT NULL,
    component_type TEXT NOT NULL DEFAULT 'page_section',
    "position" INTEGER NOT NULL DEFAULT 0,
    section_archetype TEXT NOT NULL,
    section_variant TEXT NOT NULL,
    content_direction TEXT,
    priority TEXT NOT NULL DEFAULT 'required' CHECK (priority IN ('required', 'recommended', 'optional')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX idx_presets_industry ON section_presets(industry);
CREATE INDEX idx_presets_page_type ON section_presets(page_type);
CREATE INDEX idx_presets_industry_page ON section_presets(industry, page_type);
CREATE INDEX idx_presets_archetype ON section_presets(section_archetype);

-- Composite unique constraint (prevent duplicates)
CREATE UNIQUE INDEX idx_presets_unique ON section_presets(industry, page_type, component_type, "position");

-- Industry reference table
CREATE TABLE industries (
    id SERIAL PRIMARY KEY,
    handle TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    color_temperature TEXT,
    default_nav_variant TEXT DEFAULT 'sticky-transparent',
    default_footer_variant TEXT DEFAULT 'mega',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Section archetype reference table
CREATE TABLE section_archetypes (
    id SERIAL PRIMARY KEY,
    archetype TEXT NOT NULL,
    variant TEXT NOT NULL,
    description TEXT,
    animation_engine TEXT DEFAULT 'framer-motion',
    has_template BOOLEAN DEFAULT FALSE,
    template_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(archetype, variant)
);

-- Build log - tracks which presets were used for each project
CREATE TABLE build_log (
    id SERIAL PRIMARY KEY,
    project_name TEXT NOT NULL,
    industry TEXT NOT NULL,
    page_type TEXT NOT NULL,
    sections_from_template INTEGER DEFAULT 0,
    sections_from_llm INTEGER DEFAULT 0,
    total_sections INTEGER DEFAULT 0,
    was_customized BOOLEAN DEFAULT FALSE,
    build_timestamp TIMESTAMPTZ DEFAULT NOW(),
    build_duration_ms INTEGER,
    api_cost_usd NUMERIC(6,4),
    status TEXT DEFAULT 'completed' CHECK (status IN ('completed', 'failed', 'partial'))
);

-- ═══════════════════════════════════════════════════════════════
-- VIEWS for common queries
-- ═══════════════════════════════════════════════════════════════

-- Get full section sequence for a specific industry + page type
CREATE VIEW v_page_sections AS
SELECT 
    sp.industry,
    sp.page_type,
    sp."position",
    sp.section_archetype,
    sp.section_variant,
    sp.content_direction,
    sp.priority,
    sa.animation_engine,
    sa.has_template,
    sa.template_path
FROM section_presets sp
LEFT JOIN section_archetypes sa 
    ON sp.section_archetype = sa.archetype 
    AND sp.section_variant = sa.variant
ORDER BY sp.industry, sp.page_type, sp."position";

-- Summary: sections per industry per page type
CREATE VIEW v_industry_summary AS
SELECT 
    industry,
    page_type,
    COUNT(*) as total_sections,
    COUNT(*) FILTER (WHERE priority = 'required') as required_count,
    COUNT(*) FILTER (WHERE priority = 'recommended') as recommended_count,
    COUNT(*) FILTER (WHERE priority = 'optional') as optional_count
FROM section_presets
GROUP BY industry, page_type
ORDER BY industry, page_type;

-- Most common archetype-variant combinations
CREATE VIEW v_archetype_usage AS
SELECT 
    section_archetype,
    section_variant,
    COUNT(*) as usage_count,
    COUNT(DISTINCT industry) as industry_count,
    array_agg(DISTINCT page_type) as page_types
FROM section_presets
GROUP BY section_archetype, section_variant
ORDER BY usage_count DESC;

-- ═══════════════════════════════════════════════════════════════
-- FUNCTIONS for the Builder to call
-- ═══════════════════════════════════════════════════════════════

-- Get complete build specification for an industry
CREATE OR REPLACE FUNCTION get_build_spec(p_industry TEXT)
RETURNS TABLE (
    out_page_type TEXT,
    out_position INTEGER,
    out_section_archetype TEXT,
    out_section_variant TEXT,
    out_content_direction TEXT,
    out_priority TEXT
) AS $$
    SELECT page_type, "position", section_archetype, section_variant, content_direction, priority
    FROM section_presets
    WHERE industry = p_industry
    ORDER BY page_type, "position";
$$ LANGUAGE SQL STABLE;

-- Get sections for a specific page
CREATE OR REPLACE FUNCTION get_page_sections(p_industry TEXT, p_page_type TEXT, p_include_optional BOOLEAN DEFAULT FALSE)
RETURNS TABLE (
    out_position INTEGER,
    out_section_archetype TEXT,
    out_section_variant TEXT,
    out_content_direction TEXT,
    out_priority TEXT
) AS $$
    SELECT "position", section_archetype, section_variant, content_direction, priority
    FROM section_presets
    WHERE industry = p_industry 
      AND page_type = p_page_type
      AND (p_include_optional OR priority != 'optional')
    ORDER BY "position";
$$ LANGUAGE SQL STABLE;

-- ═══════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ═══════════════════════════════════════════════════════════════

ALTER TABLE section_presets ENABLE ROW LEVEL SECURITY;
ALTER TABLE build_log ENABLE ROW LEVEL SECURITY;

-- Public read access to presets (they're not sensitive)
CREATE POLICY "Presets are publicly readable" ON section_presets
    FOR SELECT USING (true);

-- Service role can insert build logs (orchestrator uses service_role key)
CREATE POLICY "Service role can insert build logs" ON build_log
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Build logs are publicly readable" ON build_log
    FOR SELECT USING (true);

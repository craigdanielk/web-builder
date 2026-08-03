-- ═══════════════════════════════════════════════════════════════
-- SEED: adventure-tours industry preset  (AAH-02)
-- Target: web-builder section-preset database (section_presets / industries)
-- Schema: aurelix_section_presets_schema.sql
-- Idempotent — safe to re-run. Source preset: skills/presets/adventure-tours.md
-- ═══════════════════════════════════════════════════════════════

-- Industry reference row
INSERT INTO industries (handle, display_name, description, color_temperature,
                        default_nav_variant, default_footer_variant)
VALUES (
    'adventure-tours',
    'Adventure Tours & Experiences',
    'Booking-led guided adventure & ocean/coastal experience operators (the catalogue is bookable tours, not retail gear).',
    'cool-coastal',
    'sticky-transparent',
    'mega'
)
ON CONFLICT (handle) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    color_temperature = EXCLUDED.color_temperature,
    default_nav_variant = EXCLUDED.default_nav_variant,
    default_footer_variant = EXCLUDED.default_footer_variant;

-- Homepage section sequence (NAV/FOOTER come from the 'shared' page-type preset)
INSERT INTO section_presets
    (industry, page_type, component_type, position, section_archetype, section_variant, content_direction, priority)
VALUES
    ('adventure-tours','homepage','page_section', 1,'HERO',            'video-background','Epic coastline / on-water action footage; experience-led tagline over motion (video-parallax).','required'),
    ('adventure-tours','homepage','page_section', 2,'ABOUT',           'editorial-split', 'Who we are — local certified guides and the promise of the day.','required'),
    ('adventure-tours','homepage','page_section', 3,'PRODUCT-SHOWCASE','hover-cards',     'Tours as bookable cards: name, one-line hook, duration, group size, difficulty, from-price. CTA: Check availability.','required'),
    ('adventure-tours','homepage','page_section', 4,'HOW-IT-WORKS',    'numbered-steps',  'Book in 3 calm steps: choose experience, pick a date, confirm. Name whats included + cancellation.','required'),
    ('adventure-tours','homepage','page_section', 5,'FEATURES',        'icon-grid',       'Why book with us: certified guides, small groups, safety-first, gear & transfers included.','recommended'),
    ('adventure-tours','homepage','page_section', 6,'STATS',           'counter',         'Years operating, guests hosted, tours run, 5-star reviews (count-up).','optional'),
    ('adventure-tours','homepage','page_section', 7,'TESTIMONIALS',    'wall',            'Guest reviews with trip name + rating.','required'),
    ('adventure-tours','homepage','page_section', 8,'GALLERY',         'masonry',         'Real trip photography from past adventures (reveal-stagger).','recommended'),
    ('adventure-tours','homepage','page_section', 9,'FAQ',             'accordion',       'Booking, cancellation, fitness/safety, what to bring.','recommended'),
    ('adventure-tours','homepage','page_section',10,'CTA',             'split-image',     'Primary booking band: Book your adventure / Enquire — warm amber CTA over coastal image.','required')
ON CONFLICT (industry, page_type, component_type, position) DO UPDATE SET
    section_archetype = EXCLUDED.section_archetype,
    section_variant   = EXCLUDED.section_variant,
    content_direction = EXCLUDED.content_direction,
    priority          = EXCLUDED.priority,
    updated_at        = NOW();

-- Verify:
--   SELECT * FROM get_page_sections('adventure-tours','homepage', true);

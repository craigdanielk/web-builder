-- BRIEF #33317 / #33320 — record the pipeline's own quality outcomes on build_log.
-- contrast_defect_count: WCAG contrast defect groups from stage_render_audit / semantic tokens.
-- broken_image_count: broken/placeholder images detected by the render audit.
ALTER TABLE build_log ADD COLUMN IF NOT EXISTS contrast_defect_count integer;
ALTER TABLE build_log ADD COLUMN IF NOT EXISTS broken_image_count integer;

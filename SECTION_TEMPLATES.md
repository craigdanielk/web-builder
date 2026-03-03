# Section Templates

## Overview

Section templates are parameterized React (TSX) components that replace LLM generation for specific archetype-variant combinations. When a template exists for a section in the build sequence, the orchestrator uses it directly with brand token injection — skipping the Claude API call entirely.

**Status:** 72 code_template entries in Supabase `section_archetypes` table. 1 local template file (HERO/full-bleed-overlay). When building, the orchestrator checks: (1) local file first, (2) Supabase code_template, (3) LLM fallback.

---

## Directory Structure

```
web-builder/section-templates/
├── manifest.json          ← Registry of all 72 variants and their template status
├── ABOUT/
│   └── .gitkeep
├── BLOG-PREVIEW/
│   └── .gitkeep
├── HERO/
│   ├── .gitkeep
│   └── full-bleed-overlay.tsx   ← First template
├── FEATURES/
│   └── .gitkeep
├── ... (25 archetype directories total)
└── VIDEO/
    └── .gitkeep
```

---

## Template Convention

### File naming

Templates must be named `{variant}.tsx` inside the archetype directory:

```
section-templates/{ARCHETYPE}/{variant}.tsx
```

Example: `section-templates/HERO/full-bleed-overlay.tsx`

### Component interface

All templates must:

1. Be `"use client"` components
2. Export a default function named `Section{NN}{Archetype}` (NN = section number, injected at build time)
3. Accept props for customizable content (headline, images, CTAs)
4. Use brand token placeholders for styling

### Brand token placeholders

The orchestrator replaces these placeholders with actual values from the industry style config:

| Placeholder | Example Value | Description |
|-------------|---------------|-------------|
| `{{brand.bg_primary}}` | `stone-50` | Primary background color |
| `{{brand.bg_secondary}}` | `white` | Secondary background |
| `{{brand.text_heading}}` | `stone-950` | Heading text color |
| `{{brand.text_primary}}` | `stone-900` | Body text color |
| `{{brand.text_muted}}` | `stone-500` | Muted/secondary text |
| `{{brand.accent}}` | `amber-700` | Primary accent/CTA color |
| `{{brand.accent_hover}}` | `amber-800` | Accent hover state |
| `{{brand.heading_font}}` | `DM Serif Display` | Heading font family |
| `{{brand.body_font}}` | `DM Sans` | Body font family |

Token values come from the `industry_styles.style_config` JSONB column, specifically the `palette` and `typography` sub-objects.

### Example template

```tsx
"use client";

import { motion } from "framer-motion";

export default function Section01HERO({
  headline = "Default Headline",
  ctaText = "Get Started",
}: {
  headline?: string;
  ctaText?: string;
}) {
  return (
    <section className="bg-{{brand.bg_primary}} text-{{brand.text_heading}}">
      <motion.h1
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={{ fontFamily: "'{{brand.heading_font}}'" }}
      >
        {headline}
      </motion.h1>
      <button className="bg-{{brand.accent}} hover:bg-{{brand.accent_hover}}">
        {ctaText}
      </button>
    </section>
  );
}
```

---

## How Templates Are Used

1. **Build cache loads** — `BuildCache` fetches section sequence and style config from Supabase
2. **Section loop** — For each section in the sequence:
   - `check_template_exists(archetype, variant)` checks the filesystem
   - If template found → read file, replace `{{brand.*}}` tokens, write to output
   - If no template → fall through to existing LLM generation pipeline (unchanged)
3. **Build log** — Records how many sections used templates vs LLM

---

## manifest.json

The manifest tracks all 72 archetype-variant combinations and their template status. Note that `templates_available` in the local manifest reflects only local `.tsx` files. Supabase `section_archetypes` entries with `code_template` populated are an additional source of templates resolved at build time by `check_template_exists()`.

```json
{
  "version": "1.0.0",
  "total_archetypes": 25,
  "total_variants": 72,
  "templates_available": 1,
  "archetypes": {
    "HERO": {
      "directory": "section-templates/HERO/",
      "variants": [
        {
          "name": "full-bleed-overlay",
          "has_template": true,
          "template_path": "section-templates/HERO/full-bleed-overlay.tsx"
        },
        ...
      ]
    },
    ...
  }
}
```

Update this file when adding new local templates. Supabase `code_template` entries are managed separately via `seed_supabase.py` or direct SQL.

---

## Template Conversion Backlog

Priority is based on usage frequency across all 25 industries (from `v_archetype_usage` view). To generate the latest backlog:

```sql
SELECT section_archetype, section_variant, usage_count, industry_count
FROM v_archetype_usage
ORDER BY usage_count DESC;
```

The top 10 highest-impact variants to template next are generated in the `TEMPLATE_BACKLOG.md` file.

---

## Adding a New Template

1. Create the `.tsx` file in the appropriate archetype directory
2. Use `{{brand.*}}` placeholders for all brand-specific values
3. Export a default component with props for customizable content
4. Update `manifest.json` to set `has_template: true` and `template_path`
5. Optionally update `section_archetypes` table: `UPDATE section_archetypes SET has_template = true, template_path = 'section-templates/HERO/...' WHERE archetype = 'HERO' AND variant = '...'`
6. Test with: `python scripts/validate_integration.py`

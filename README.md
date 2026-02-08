# Website Builder

A structured skill package and orchestration pipeline for generating
high-quality, industry-aware websites using Claude.

## How It Works

This system uses a **multi-pass generation pipeline** instead of trying to
generate an entire website in one prompt. Each pass focuses on a different
concern, and a compact style header ensures visual consistency across all
passes.

```
Brief → Scaffold → Sections (×N) → Assembly → Review
                        ↑
                  Style Header
                (restated each pass)
```

### The Three Knowledge Layers

1. **Section Taxonomy** (`skills/section-taxonomy.md`) — 25 section archetypes
   with 95+ variants. The structural DNA of every possible website section.

2. **Style Schema** (`skills/style-schema.md`) — 7 configurable style dimensions
   (color, typography, spacing, radius, animation, density, imagery) with
   Tailwind CSS mappings.

3. **Industry Presets** (`skills/presets/`) — Pre-configured combinations of
   section sequences and style settings for specific industries.

### The Pipeline

**Stage 1: Scaffold** — Read the client brief, match to a preset, generate
a numbered section specification. Human reviews before proceeding.

**Stage 2: Sections** — Generate each section as an independent React component.
The compact style header is restated for every section to prevent context
degradation.

**Stage 3: Assembly** — Combine all sections into a single page component.

**Stage 4: Review** — Run a consistency checklist across all sections. Flag
and fix inconsistencies.

## Quick Start

### Prerequisites

```bash
pip install anthropic --break-system-packages
export ANTHROPIC_API_KEY=your-key-here
```

### 1. Write a Brief

Copy `briefs/_template.md` and fill it in:

```bash
cp briefs/_template.md briefs/my-project.md
# Edit briefs/my-project.md with project details
```

### 2. Run the Pipeline

**Sequential (with review checkpoint):**
```bash
python scripts/orchestrate.py my-project --preset artisan-food
```

**Parallel (faster, uses existing scaffold):**
```bash
python scripts/orchestrate_parallel.py my-project --preset artisan-food
```

### 3. Review Output

```
output/my-project/
├── scaffold.md           ← Page specification
├── sections/
│   ├── 01-hero.tsx       ← Individual section components
│   ├── 02-about.tsx
│   └── ...
├── page.tsx              ← Assembled page
└── review.md             ← Consistency review
```

## Using with Cursor

Open this repo in Cursor. The `.cursorrules` file tells Claude Code how to
use the skill package. You can ask Cursor to:

- "Build a website from the turm-kaffee brief"
- "Generate a scaffold for a new SaaS product"
- "Add a testimonials section to the current project"
- "Run the consistency review on the latest output"

## Adding a New Preset

1. Copy `skills/presets/_template.md`
2. Fill in the section sequence, style configuration, and content direction
3. Test it with a real project brief

## Growing the Taxonomy

Section structural descriptions start empty and get populated through real use.
After generating a section type for the first time, update the taxonomy entry
with what you learned about its structure.

## Cost Per Site

Approximate API costs using Claude Sonnet:
- Scaffold: ~$0.05
- Sections (8-12): ~$0.40-1.00
- Review: ~$0.10
- **Total: ~$0.55-1.15 per full page**

## Project Structure

```
website-builder/
├── .cursorrules              ← Agent instructions for Cursor IDE
├── README.md                 ← This file
├── skills/
│   ├── section-taxonomy.md   ← Section archetype catalogue
│   ├── style-schema.md       ← Style dimension definitions
│   └── presets/
│       ├── _template.md      ← Empty preset template
│       ├── artisan-food.md   ← Artisan food/beverage preset
│       └── saas.md           ← SaaS/tech product preset
├── templates/
│   ├── scaffold-prompt.md    ← Stage 1 prompt template
│   ├── section-prompt.md     ← Stage 2 prompt template
│   └── assembly-checklist.md ← Stage 4 review template
├── briefs/
│   ├── _template.md          ← Empty brief template
│   └── turm-kaffee.md       ← Example brief
├── output/                   ← Generated output (gitignored)
├── scripts/
│   ├── orchestrate.py        ← Sequential pipeline
│   └── orchestrate_parallel.py ← Parallel pipeline
└── agents/
    └── roles.md              ← Agent role definitions
```

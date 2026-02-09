# Web Builder

A structured skill package and orchestration pipeline for generating high-quality, industry-aware websites using AI agents. Works with any LLM (Claude, GPT-4, Gemini, etc.) in any IDE or terminal environment.

---

## For New Agents: Start Here

**If you are an AI agent encountering this repo for the first time, read this section completely before doing anything else.**

This system generates production-quality React websites through a **multi-pass pipeline**. The key insight: generating an entire page in one pass causes context degradation and visual inconsistency. Instead, we generate one section at a time, with a compact style header restated for every section to maintain visual DNA.

```
Brief → Preset Match → Scaffold → Sections (x N) → Assembly → Review
                                       ^
                                 Style Header
                              (restated each pass)
```

### What You MUST Read Before Generating

Read these files **in this exact order** before running any build:

| Order | File | What It Contains |
|-------|------|-----------------|
| 1 | `.cursorrules` | The complete pipeline instructions — your operating manual |
| 2 | `skills/section-taxonomy.md` | All 25 section archetypes with 95+ variants |
| 3 | `skills/style-schema.md` | 7 configurable style dimensions with Tailwind mappings |
| 4 | `skills/presets/{preset}.md` | The industry preset you'll use (section sequence + style config) |
| 5 | `templates/scaffold-prompt.md` | Template for generating the page specification |
| 6 | `templates/section-prompt.md` | Template for generating individual section components |
| 7 | `templates/assembly-checklist.md` | Consistency checklist for the review pass |

**Critical rule:** Never skip the skill file reads. The section taxonomy and style schema contain the design knowledge that prevents generic output. If you generate without reading them, the output will be mediocre.

### The 6-Step Pipeline

**Step 1: Read the Brief**
- Load `briefs/{project}.md`
- Identify industry, business type, tone, and specific requirements
- Note any explicit design/content requests from the client

**Step 2: Match Preset**
- Scan `skills/presets/` for the closest industry match
- Read the matched preset fully — it contains the default section sequence AND the compact style header
- If no exact match exists, use the closest one and note what to adapt

**Step 3: Generate Scaffold**
- Use `templates/scaffold-prompt.md` as your template
- Cross-reference `skills/section-taxonomy.md` for available archetypes and variants
- Output: a numbered section list with archetype, variant, and content direction per section
- Save to `output/{project}/scaffold.md`
- **CHECKPOINT:** Pause for human review if running interactively

**Step 4: Generate Sections (one at a time)**
- Use `templates/section-prompt.md` as your template
- **CRITICAL:** Restate the compact style header at the TOP of every section generation. This is the consistency mechanism. Do not skip this.
- For each section in the scaffold:
  - Generate a complete, self-contained React + TypeScript + Tailwind component
  - Animation engine (GSAP or Framer Motion) is determined by the preset's Motion line
  - Save to `output/{project}/sections/{NN}-{section-name}.tsx`
- Each section must be independently renderable but share the style DNA from the header

**Step 5: Assemble Page**
- Combine all section components into `output/{project}/page.tsx`
- Add proper imports, layout wrapper, and global styles
- Ensure the page is renderable as a standalone Next.js/React page

**Step 6: Consistency Review**
- Use `templates/assembly-checklist.md` as your checklist
- Review ALL generated sections for consistency in: button styles, color tokens, spacing, typography, animation timing, border radius, hover states
- Save review to `output/{project}/review.md`
- If issues found, regenerate ONLY the affected sections (minimal changes)

**Step 7: Deploy to Site (optional)**
- Use the `--deploy` flag or run manually
- Creates a runnable Next.js project at `output/{project}/site/`
- Auto-detects animation engine from preset, installs correct deps
- Generates layout.tsx, globals.css, page.tsx, smooth-scroll.tsx
- Run with: `cd output/{project}/site && npm run dev`

---

## Complete File Map

```
web-builder/
├── .cursorrules                    ← Agent pipeline instructions (READ FIRST)
├── .env                            ← API keys (Anthropic, Cloudinary, etc.)
├── .gitignore
├── README.md                       ← This file — universal agent onboarding
│
├── skills/                         ← Design knowledge (READ ONLY during generation)
│   ├── section-taxonomy.md         ← 25 section archetypes, 95+ variants
│   ├── style-schema.md             ← 7 style dimensions with Tailwind mappings
│   ├── animation-patterns.md       ← Named GSAP animation patterns
│   ├── presets/                    ← Industry-specific configurations
│   │   ├── _template.md            ← Empty preset template
│   │   ├── artisan-food.md         ← Coffee, bakery, artisan food & beverage
│   │   └── ... (20 presets)        ← See skills/presets/ for full list
│   └── components/                 ← Reusable component documentation
│       └── cursor-trail.md         ← Mouse-following trail effect
│
├── templates/                      ← Prompt templates for each pipeline stage
│   ├── scaffold-prompt.md          ← Stage 3: page specification generation
│   ├── section-prompt.md           ← Stage 4: individual section generation
│   └── assembly-checklist.md       ← Stage 6: consistency review checklist
│
├── briefs/                         ← Client briefs (human-written input)
│   ├── _template.md                ← Empty brief template
│   └── {project}.md                ← One brief per project
│
├── output/                         ← ALL build output (gitignored)
│   └── {project}/                  ← One folder per project
│       ├── scaffold.md             ← Page specification
│       ├── sections/               ← Raw generated section components
│       ├── page.tsx                ← Assembled page
│       ├── review.md               ← Consistency review
│       └── site/                   ← Rendered Next.js project (--deploy)
│           ├── package.json
│           ├── src/app/            ← layout.tsx, globals.css, page.tsx
│           └── src/components/     ← sections/ + smooth-scroll.tsx
│
├── scripts/                        ← Orchestration and utility scripts
│   ├── orchestrate.py              ← Sequential pipeline (requires ANTHROPIC_API_KEY)
│   ├── orchestrate_parallel.py     ← Parallel pipeline (requires ANTHROPIC_API_KEY)
│   └── quality/                    ← URL-to-brief and enrichment utilities
│       ├── url-to-brief.js         ← Generate brief from existing website URL
│       ├── url-to-preset.js        ← Generate preset from existing website URL
│       ├── enrich-preset.js        ← Enrich preset with design token extraction
│       └── validate-build.js       ← Validate build output quality
│
├── agents/                         ← Agent role definitions for multi-agent mode
│   └── roles.md                    ← Architect, Builder, Reviewer, Fixer roles
│
└── retrospectives/                 ← Session documentation and learnings
    ├── 2026-02-08-web-builder-first-build-success.md
    ├── 2026-02-08-turm-kaffee-v2-build-deploy.md
    └── 2026-02-08-farm-minerals-rebuild.md
```

**Architecture:** Site builds live inside `output/{project}/site/`, never at the repo root.
Each has its own package.json, node_modules, and dev server. Builds are fully isolated —
100 agents can build in parallel from different briefs with zero coupling.

---

## Quick Start

### Option A: Agent Mode (Recommended — highest quality)

Open this repo in Cursor, Claude Code, Windsurf, or any AI IDE. The `.cursorrules` file provides the pipeline instructions. Tell the agent:

```
Build a website from the brief at briefs/{project}.md
Use the {industry} preset at skills/presets/{preset}.md
Follow the pipeline defined in .cursorrules exactly.
```

Or more specifically:

```
Build the turm-kaffee-v2 site using the web-builder pipeline.
The brief is at briefs/tuem-kaffee-v2.md
Use the artisan-food preset at skills/presets/artisan-food.md
Follow the pipeline defined in .cursorrules exactly:
1. Read the brief
2. Match preset (artisan-food)
3. Generate scaffold → save to output/{project}/scaffold.md
4. Generate each section one at a time → save to output/{project}/sections/
5. Assemble into page.tsx → save to output/{project}/page.tsx
6. Run consistency review → save to output/{project}/review.md

Read ALL skill files before generating:
- skills/section-taxonomy.md
- skills/style-schema.md
- skills/presets/artisan-food.md
- templates/scaffold-prompt.md
- templates/section-prompt.md
- templates/assembly-checklist.md

Do not skip any step. Generate one section at a time with the compact
style header restated in every section prompt.
```

### Option B: Python SDK Scripts (Automated — requires API key)

```bash
# Prerequisites
pip install anthropic --break-system-packages
export ANTHROPIC_API_KEY=your-key-here  # Or set in .env file

# Sequential (with review checkpoint)
python scripts/orchestrate.py my-project --preset artisan-food

# Sequential + deploy to runnable Next.js site
python scripts/orchestrate.py my-project --preset artisan-food --deploy

# Parallel (faster, uses existing scaffold)
python scripts/orchestrate_parallel.py my-project --preset artisan-food --deploy
```

### Option C: Manual (Any LLM, No IDE)

If you're using ChatGPT, Gemini, or any other LLM without file system access:

1. Copy the contents of `.cursorrules` into your system prompt
2. Paste the contents of the brief, preset, section taxonomy, and style schema
3. Ask the LLM to generate the scaffold first
4. Then generate each section one at a time, pasting the style header each time
5. Assemble manually

This works but produces lower quality than Options A/B because you lose the automated file reads and consistency checking.

---

## Writing a New Brief

```bash
cp briefs/_template.md briefs/my-project.md
```

Fill in these fields:

| Field | Purpose | Example |
|-------|---------|---------|
| Business | What they do, where, what's unique | "Swiss artisan coffee roaster, St. Gallen, since 1936" |
| What They Need | Primary website purpose | "E-commerce storefront with academy promotion" |
| Key Requirements | Must-have features | "Product categories, weekly offers, contact form" |
| Target Audience | Who visits the site | "Coffee enthusiasts, home baristas, local customers" |
| Brand Personality | Tone and feel | "Warm, precise, heritage-proud, inviting" |
| Specific Requests | Explicit design/content asks | "Dark moody hero, amber accents, countdown timer" |
| Technical Notes | Platform/integration needs | "Shopify integration planned, Swiss franc pricing" |

**Brief quality directly determines output quality.** Specific details (real prices, real addresses, named products) produce dramatically better results than generic placeholders.

---

## Creating a New Preset

```bash
cp skills/presets/_template.md skills/presets/my-industry.md
```

A preset contains:
1. **Default section sequence** — the typical section order for this industry (6-14 sections)
2. **Style configuration** — color palette, typography, spacing, radius, animation, density, imagery
3. **Compact style header** — the 6-line summary restated in every section generation
4. **Content direction** — tone, hero copy patterns, CTA language
5. **Photography direction** — image style, mood, subjects
6. **Known pitfalls** — what to watch out for in this industry

See `skills/presets/artisan-food.md` for a fully populated example.

### Available Presets (20)

| Preset | Industries Covered |
|--------|--------------------|
| `artisan-food` | Coffee roasters, bakeries, artisan food & beverage |
| `beauty-cosmetics` | Beauty, skincare, cosmetics brands |
| `construction-trades` | Construction companies, trades, contractors |
| `creative-studios` | Design agencies, creative studios, portfolios |
| `education` | Schools, courses, e-learning platforms |
| `events-venues` | Events, venues, conferences, weddings |
| `fashion-apparel` | Fashion brands, clothing, apparel |
| `health-wellness` | Health, wellness, yoga, therapy practices |
| `home-lifestyle` | Home goods, interior design, lifestyle brands |
| `hotels-hospitality` | Hotels, B&Bs, resorts, hospitality |
| `jewelry-watches` | Jewelry, watches, luxury accessories |
| `medical-dental` | Medical practices, dental offices, clinics |
| `nonprofits-social` | Nonprofits, charities, social causes |
| `outdoor-adventure` | Outdoor sports, adventure, camping |
| `pet-products` | Pet supplies, veterinary, pet services |
| `professional-services` | Law firms, accounting, consulting |
| `real-estate` | Real estate agencies, property listings |
| `restaurants-cafes` | Restaurants, cafes, food service |
| `saas` | SaaS products, tech platforms, startups |
| `sports-fitness` | Gyms, fitness studios, sports equipment |

---

## Deploying Generated Output

### Automated (Recommended)

Use the `--deploy` flag to automatically create a runnable Next.js project:

```bash
# Full pipeline + deploy
python scripts/orchestrate.py my-project --preset artisan-food --deploy

# Or deploy from existing output
python scripts/orchestrate.py my-project --preset artisan-food --skip-to deploy
```

This creates `output/my-project/site/` with everything wired up:

```bash
cd output/my-project/site
npm run dev
```

### Manual

```bash
# Create new Next.js project
npx create-next-app@latest my-site --typescript --tailwind --eslint --app --src-dir --use-npm

# Install animation dependencies (pick one)
cd my-site
npm install gsap lenis          # For GSAP engine
# OR
npm install framer-motion       # For Framer Motion engine

# Copy generated sections
cp ../output/{project}/sections/*.tsx src/components/sections/

# Update src/app/page.tsx, layout.tsx, globals.css manually

npm run dev
```

### Font Setup

The generated components reference fonts via inline `style={{ fontFamily }}`. Add the fonts in `layout.tsx`:

```tsx
import { DM_Serif_Display, DM_Sans } from "next/font/google";

const dmSerif = DM_Serif_Display({ subsets: ["latin"], weight: "400" });
const dmSans = DM_Sans({ subsets: ["latin"], weight: ["400", "500", "700"] });
```

The `next/font` system loads the font files — inline style references work because the font IS loaded by Next.js at the framework level.

### Image Integration

Generated sections use placeholder image paths. Replace with real images:

**Option 1: Unsplash CDN** (free, good for placeholders)
```
https://images.unsplash.com/photo-{TIMESTAMP}-{HASH}?auto=format&fit=crop&w={WIDTH}&q={QUALITY}
```
Note: You must find real CDN URLs from Unsplash photo pages. Do NOT fabricate the TIMESTAMP-HASH values.

**Option 2: Shopify CDN** (for existing Shopify stores)
```
https://cdn.shopify.com/s/files/{STORE_ID}/files/{FILENAME}
```

**Option 3: Cloudinary** (for managed media)
```
https://res.cloudinary.com/{CLOUD_NAME}/image/upload/v{VERSION}/{FILENAME}
```

---

## Tech Stack

All generated output uses:
- **React 18+** with TypeScript
- **Tailwind CSS v4** for styling
- **Next.js App Router** conventions (App directory, `"use client"` directives)
- **Animation engine** (determined by preset):
  - **Framer Motion** — lightweight, `whileInView` scroll triggers
  - **GSAP + ScrollTrigger** — advanced scroll-aware animations, character reveals, count-ups, timeline sequences
  - **Lenis** — smooth scrolling (paired with GSAP engine)
- See `skills/animation-patterns.md` for the full GSAP pattern library

---

## The Three Knowledge Layers

### 1. Section Taxonomy (`skills/section-taxonomy.md`)

Defines 25 section archetypes with 95+ variants:

| Archetype | Example Variants |
|-----------|-----------------|
| HERO | full-bleed-overlay, split-screen, video-background |
| NAV | sticky-transparent, mega-menu, hamburger-only |
| ABOUT | editorial-split, timeline, team-grid |
| FEATURES | alternating-rows, icon-grid, bento |
| PRODUCT-SHOWCASE | category-grid, hover-cards, carousel |
| PRICING | two-tier, three-tier, comparison-table |
| TESTIMONIALS | single-featured, carousel, wall-of-love |
| CTA | split-with-image, centered-gradient, banner |
| FOOTER | minimal, mega, stacked |
| ... | (15 more archetypes) |

### 2. Style Schema (`skills/style-schema.md`)

7 configurable dimensions:

| Dimension | Options | What It Controls |
|-----------|---------|-----------------|
| Color Temperature | warm, cool, neutral | Palette mood and Tailwind color tokens |
| Typography Pairing | serif-sans, mono-sans, etc. | Font families and hierarchy |
| Whitespace | tight, balanced, generous | Section padding and internal gaps |
| Border Radius | none, subtle, medium, full | Buttons, cards, inputs rounding |
| Animation Intensity | minimal, moderate, expressive | Entrance patterns, hover effects, timing |
| Visual Density | high, medium, low | Content packing and visual weight |
| Image Treatment | full-bleed, contained, masked | How photography is used |

### 3. Industry Presets (`skills/presets/`)

Pre-configured combinations of section sequences and style settings. Each preset includes a **compact style header** — the 6-line consistency mechanism:

```
═══ STYLE CONTEXT ═══
Palette: warm-earth — bg:stone-50/white text:stone-900 accent:amber-700 border:stone-200
Type: serif-sans — heading:DM Serif Display,700 body:DM Sans,400 scale:1.333
Space: generous — sections:py-24 internal:gap-8
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: moderate — entrance:fade-up-stagger hover:lift-shadow timing:0.6s ease-out
Density: low | Images: full-bleed
═══════════════════════
```

This header is restated at the top of EVERY section generation prompt. This is the mechanism that prevents visual inconsistency across sections.

---

## Multi-Agent Mode

For systems that support parallel agents (Claude Code, Cursor multi-agent, etc.), the `agents/roles.md` file defines 4 specialized roles:

| Role | Responsibility | Pipeline Stage |
|------|---------------|----------------|
| **Architect** | Brief analysis, preset matching, scaffold generation | Steps 1-3 |
| **Builder** | Individual section component generation | Step 4 |
| **Reviewer** | Cross-section consistency evaluation | Step 6 |
| **Fixer** | Targeted fixes for flagged inconsistencies | Step 6 (if needed) |

The Architect runs first. Then multiple Builder agents can run in parallel (one per section). The Reviewer runs after all sections are complete. The Fixer runs only if the Reviewer flags issues.

---

## Completed Builds

| # | Project | Preset | Sections | Engine | Notes |
|---|---------|--------|----------|--------|-------|
| 1 | turm-kaffee v1 | artisan-food | 9 | framer-motion | First-ever build |
| 2 | farm-minerals-promo | — | 11 | gsap | Full GSAP rebuild with Lenis |
| 3 | turm-kaffee v2 | artisan-food | 11 | gsap | Full e-commerce, GSAP + Lenis |

All builds now live at `output/{project}/site/`.

---

## Known Issues & Troubleshooting

### Image URLs returning 404
Unsplash CDN URLs use the format `photo-{TIMESTAMP}-{HASH}`. You CANNOT fabricate these values — they must be discovered from actual Unsplash photo pages. See the retrospective at `retrospectives/2026-02-08-turm-kaffee-v2-build-deploy.md` for the verified URL discovery process.

### React infinite re-render loop
If a section uses a countdown timer or any `useEffect` with a `Date` object dependency, the Date must be wrapped in `useMemo`. See the `05-product-showcase-offers.tsx` fix in the v2 build.

### Dev server port locked
If `npm run dev` fails with "port in use" or lock file errors:
```bash
rm -f output/{project}/site/.next/dev/lock
lsof -ti:3000 | xargs kill -9
npm run dev
```

### `create-next-app` interactive prompt
Next.js 16+ prompts for React Compiler. Pipe "no" to skip:
```bash
echo "no" | npx create-next-app@latest my-site --typescript --tailwind --eslint --app --src-dir --use-npm
```

### Section taxonomy descriptions empty
Most taxonomy entries say "[populate on first use]". After generating a section type for the first time, update `skills/section-taxonomy.md` with the structural patterns you learned.

---

## Cost Per Site (SDK Mode)

Approximate API costs using Claude Sonnet:
- Scaffold: ~$0.05
- Sections (8-12): ~$0.40-1.00
- Review: ~$0.10
- **Total: ~$0.55-1.15 per full page**

Agent mode (Cursor/Claude Code) costs depend on your subscription.

---

## Retrospectives

Session documentation lives in `retrospectives/`. Read the most recent one for current system state, learnings, and known issues:

- `2026-02-08-web-builder-first-build-success.md` — First build, pipeline validation, GitHub push
- `2026-02-08-turm-kaffee-v2-build-deploy.md` — V2 build, deployment, image integration

---

## Contributing: Growing the System

### After completing a build:
1. Update `skills/section-taxonomy.md` with structural patterns learned from new section types
2. If the industry was new, create a preset in `skills/presets/`
3. Write a retrospective in `retrospectives/`
4. Note any new patterns, pitfalls, or reusable code

### Priority improvements:
- Populate section taxonomy structural descriptions (currently mostly empty)
- Build a pre-verified image library by category
- Test and validate the SDK scripts (`orchestrate.py`)
- Add Vercel deployment pipeline
- Build guided walkthrough UI for non-technical users

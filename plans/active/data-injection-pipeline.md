# Data Injection Pipeline: Closing the Loop from Extraction to Build Output

**Status:** Draft — Pending Approval
**Created:** 2026-02-09
**Depends on:** Animation Extraction Integration Plan (completed)
**Scope:** Two systemic gaps — animation engine injection + image/media asset injection

---

## Problem Statement

The extraction pipeline successfully captures rich data from reference websites:
- Animation libraries, intensity, Lottie file URLs, section overrides
- Image URLs with alt text, dimensions, and page position
- Per-section DOM structure, layout patterns, text content

**None of this data reaches the built output.** The section generation prompt in `orchestrate.py:400-436` hardcodes:
1. `import { motion } from "framer-motion"` — ignoring detected engine
2. `Use Framer Motion motion components` — ignoring animation patterns library
3. `Placeholder images should use a neutral gradient div` — ignoring extracted images

The preset correctly contains `animation_engine: gsap`, `animation_intensity: expressive`, and `section_overrides`, but the section prompt's explicit instructions override the Style Header metadata. Every section gets identical framer-motion fade-up-stagger regardless of what was detected.

---

## Architecture: Dedicated Injection Skills

Rather than making `orchestrate.py` more complex, this plan introduces **three dedicated injection modules** that transform extracted data into prompt-ready context blocks. The orchestrator calls each module at the right pipeline stage and passes the result into the section prompt.

```
Extraction Data (JSON)
       │
       ├──→ [animation-injector]  → per-section animation prompt block
       ├──→ [asset-injector]      → per-section image/media prompt block
       └──→ [section-context.js]  → per-section structural context (existing)
                │
                ▼
        Section Generation Prompt
        ┌─────────────────────────────────────┐
        │ Style Header (from preset)          │
        │ Section Spec (archetype/variant)    │
        │ Structural Reference (taxonomy)     │
        │ Reference Context (section-context) │ ← existing
        │ Animation Context (NEW)             │ ← from animation-injector
        │ Asset Context (NEW)                 │ ← from asset-injector
        │ Instructions (engine-aware) (NEW)   │ ← engine-branched
        └─────────────────────────────────────┘
```

---

## Phase 1: Animation Injector Module

**File:** `scripts/quality/lib/animation-injector.js`
**Purpose:** Transform animation analysis data + preset config into per-section prompt blocks
**Inputs:** `animation-analysis.json`, preset content, section archetype, animation-patterns.md
**Output:** A text block injected into each section's Claude prompt

### 1A. Engine-Specific Prompt Templates

The core problem is that one generic prompt can't produce both framer-motion and GSAP components. These are fundamentally different architectures:

| Aspect | Framer Motion | GSAP |
|--------|--------------|------|
| Import | `import { motion } from "framer-motion"` | `import { gsap } from "gsap"; import { ScrollTrigger } from "gsap/ScrollTrigger"` |
| Component pattern | `<motion.div>` wrappers with prop-based animation | `useEffect` + `useRef` + `gsap.context()` |
| Scroll trigger | `whileInView={{ opacity: 1 }}` | `ScrollTrigger.create({ trigger, start, ... })` |
| Cleanup | Automatic (unmount removes motion components) | Manual (`ctx.revert()` in useEffect cleanup) |
| Token cost | ~150-200 tokens per animated element | ~250-350 tokens per animated element |

**Solution:** Create two prompt template files:

- `templates/section-prompt-framer.md` — Current behavior, refined
- `templates/section-prompt-gsap.md` — GSAP boilerplate + ScrollTrigger patterns

The injector selects the correct template based on `animation_engine` from the preset. Both templates share the same structure (Style Header, Section Spec, Structural Reference, etc.) but differ in their Instructions section.

### 1B. Per-Section Animation Pattern Selection

The animation-patterns.md library already maps patterns to archetypes:

```
HERO     → character-reveal + staggered-timeline + bounce-loop
STATS    → count-up per metric
FEATURES → fade-up-stagger + icon-glow on hover
ABOUT    → word-reveal on heading
CTA      → staggered-timeline (heading → button)
```

The injector does:
1. Read the preset's `section_overrides` (e.g., `hero:lottie-hero features:scroll-reveal`)
2. Fall back to the Pattern-to-Archetype Map from `animation-patterns.md`
3. Look up the actual code snippet from `animation-patterns.md`
4. Inject the snippet as a "Reference Animation Pattern" block in the prompt

This gives Claude the exact GSAP code to use — not a description, but the actual pattern with configuration values from the preset's timing/easing settings.

### 1C. Lottie Integration

When `sectionOverrides` includes `lottie-hero` or the analysis detected Lottie files:

1. The injector identifies which Lottie files map to which sections (by name matching or order)
2. Injects a Lottie-specific instruction block:
   ```
   ## Lottie Animation
   This section uses a Lottie animation player.
   URL: https://cdn.example.com/hero-animation.json

   Use @lottiefiles/dotlottie-react:
   import { DotLottieReact } from '@lottiefiles/dotlottie-react';
   <DotLottieReact src="/lottie/hero-animation.json" loop autoplay />
   ```
3. The deployment stage downloads the Lottie JSON to `public/lottie/`

### 1D. Token Budget Adjustment

Current: `max_tokens: 4096` for all sections.

GSAP sections with complex animations need more tokens. The injector returns a `tokenBudget` recommendation:

| Pattern Complexity | Token Budget |
|-------------------|-------------|
| `fade-up-single` (framer-motion) | 4096 (current) |
| `fade-up-stagger` (framer-motion) | 4096 (current) |
| `character-reveal` + `staggered-timeline` (GSAP) | 6144 |
| `count-up` with multiple metrics (GSAP) | 6144 |
| Lottie integration + GSAP entrance | 6144 |
| Complex multi-pattern section | 8192 |

The orchestrator passes the recommended budget to `call_claude()` per section.

### 1E. Dependency Resolution

Current bug: `stage_deploy` installs GSAP **or** framer-motion (either/or). Fix:

- Always install framer-motion (lightweight, used for simple hover/tap effects even on GSAP sites)
- Install GSAP when `animation_engine == "gsap"`
- Install `@lottiefiles/dotlottie-react` when Lottie files are detected
- The injector returns a `dependencies` list that `stage_deploy` merges into `package.json`

---

## Phase 2: Asset Injector Module

**File:** `scripts/quality/lib/asset-injector.js`
**Purpose:** Transform extracted images + Lottie URLs into per-section asset context blocks
**Inputs:** `extraction-data.json` (assets.images, assets.backgroundImages, animations.networkResults), section archetype
**Output:** A text block injected into each section's Claude prompt + a download manifest

### 2A. Image Categorization During Extraction

The `extract-reference.js` already captures images with:
```js
{ src, alt, width, height, visible, rect }
```

Add a categorization step (new function in `extract-reference.js` or a separate module):

1. **URL-path signals** — `/hero/`, `/products/`, `/team/` in the src path
2. **Alt-text signals** — Keywords mapped to categories (existing table in `image-extraction.md`)
3. **Position signals** — Y-position relative to section boundaries → assign to section
4. **Dimension signals** — Large landscape → hero/background, square → product/team, small → icon/logo

Output: Each image gets a `category` field and a `sectionIndex` assignment.

The `image-extraction.md` skill already defines the 10 categories and the Section-to-Category mapping table. This is the spec — Phase 2A implements it as code.

### 2B. Asset Accessibility Verification

Not all extracted URLs are usable. Before injection:

1. **HEAD request** each URL (parallel, with timeout)
   - Check HTTP status (skip 403/404/500)
   - Check Content-Type (keep image/*, application/json for Lottie)
   - Check Content-Length (skip < 1KB unless SVG/icon)
2. **Dimension filter** — Skip images < 50×50px (tracking pixels, spacers)
3. **Deduplication** — Same URL appearing multiple times → keep one
4. **Lottie verification** — For network-intercepted Lottie files, verify the JSON has `v`, `fr`, `layers` keys

Output: `accessible-assets.json` with only verified, downloadable assets.

### 2C. Asset Download During Deployment

New function in `stage_deploy` (or called from it):

1. Read `accessible-assets.json`
2. Download images to `output/{project}/site/public/images/`
3. Download Lottie files to `output/{project}/site/public/lottie/`
4. Generate `asset-manifest.json` mapping original URLs to local paths:
   ```json
   {
     "images": {
       "https://cdn.example.com/hero.jpg": "/images/hero.jpg",
       "https://cdn.example.com/product-1.jpg": "/images/product-1.jpg"
     },
     "lottie": {
       "https://cdn.example.com/animation.json": "/lottie/animation.json"
     }
   }
   ```

### 2D. Per-Section Asset Injection

The asset injector builds a context block per section:

```
## Available Assets for This Section (HERO)

### Images
1. /images/hero-banner.jpg (1920×1080)
   Alt: "Aerial view of agricultural field with CropTab application"

2. /images/product-macro.jpg (800×600)
   Alt: "CropTab tablet dissolving in soil at nano scale"

### Lottie Animations
1. /lottie/hero-animation.json
   Name: "farm logo" — Use with DotLottieReact component

### Instructions
- Use these local asset paths in your component (they will exist at build time)
- For images: use Next.js <Image> component or CSS backgroundImage with the paths above
- For Lottie: use DotLottieReact component (already in dependencies)
- If no assets are listed above, use a gradient placeholder with descriptive aria-label
```

This **replaces** the current line 428 instruction. Instead of "always use gradient placeholder," the prompt says "use these assets, fall back to gradient only if none listed."

### 2E. Fallback Strategy

When no images are available for a section (extraction failed, URLs inaccessible, or no URL mode):

1. **Primary fallback** — Industry-appropriate gradient with descriptive aria-label (current behavior, kept as default)
2. **No external API calls** — We do not query Unsplash/Pexels (adds API key dependency, licensing complexity)
3. **SVG illustration** — For icon-heavy sections (FEATURES, HOW-IT-WORKS), the section generator already produces inline SVGs — this continues unchanged

---

## Phase 3: Orchestrator Integration

**File:** `scripts/orchestrate.py` — modifications to `stage_sections()` and `stage_deploy()`
**Purpose:** Wire the injectors into the pipeline

### 3A. Load Injection Data

After `stage_url_extract` completes, load the analysis artifacts:

```python
# In main() after stage_url_extract returns
animation_analysis_path = extraction_dir / "animation-analysis.json"
extraction_data_path = extraction_dir / "extraction-data.json"

animation_analysis = json.loads(animation_analysis_path.read_text()) if animation_analysis_path.exists() else None
extraction_data = json.loads(extraction_data_path.read_text()) if extraction_data_path.exists() else None
```

Pass these to `stage_sections()` and `stage_deploy()`.

### 3B. Engine-Branched Section Prompt

Replace the current monolithic prompt (lines 400-436) with:

```python
def build_section_prompt(section, i, total, style_header, structure_ref,
                         ref_context_block, animation_context, asset_context,
                         engine):
    """Build the section generation prompt with engine-specific instructions."""

    # Load engine-specific instruction template
    if engine == "gsap":
        instructions = read_file(TEMPLATES_DIR / "section-instructions-gsap.md")
    else:
        instructions = read_file(TEMPLATES_DIR / "section-instructions-framer.md")

    prompt = f"""You are a senior frontend developer generating a single website section
as a React + Tailwind CSS component.

{style_header}

## Section Specification
Number: {i + 1} of {total}
Archetype: {section['archetype']}
Variant: {section['variant']}
Content Direction: {section['content']}

## Structural Reference
{structure_ref}
{ref_context_block}
{animation_context}
{asset_context}
{instructions}

Output ONLY the component code. No explanation, no markdown code fences.
Export the component as default.
Component name: Section{num}{section['archetype'].replace('-', '')}"""

    return prompt
```

### 3C. Dynamic Token Budget

```python
# In stage_sections, per section:
token_budget = animation_injector_result.get("tokenBudget", 4096)

# Override MAX_TOKENS for this specific call
code = call_claude_with_budget(prompt, token_budget)
```

Add a `call_claude_with_budget()` function or parameterize the existing `call_claude()`.

### 3D. Asset Download in stage_deploy

After scaffolding the Next.js project and before `npm install`:

```python
# Download assets if available
if extraction_data and extraction_data.get("assets"):
    download_assets(extraction_data, site_dir)
```

The `download_assets()` function:
1. Reads the accessible-assets manifest
2. Downloads images to `site_dir / "public" / "images"`
3. Downloads Lottie files to `site_dir / "public" / "lottie"`
4. Writes the local asset manifest for prompt injection reference

### 3E. Dependency Resolution in stage_deploy

Replace the either/or logic:

```python
# Current (broken):
if engine == "gsap":
    deps["gsap"] = "^3.14.2"
else:
    deps["framer-motion"] = "^12.33.0"

# New:
deps["framer-motion"] = "^12.33.0"  # Always included (hover/tap effects)
if engine == "gsap":
    deps["gsap"] = "^3.14.2"
if has_lottie_assets:
    deps["@lottiefiles/dotlottie-react"] = "^0.13.0"
```

---

## Phase 4: Engine-Specific Instruction Templates

**Files:**
- `templates/section-instructions-framer.md`
- `templates/section-instructions-gsap.md`

### 4A. Framer Motion Instructions

```markdown
## Instructions

Generate a complete, self-contained React component for this section.

Requirements:
1. Use TypeScript with React.FC typing
2. Use ONLY the colors, fonts, spacing, radius, and animation values from
   the STYLE CONTEXT header above
3. The component must be self-contained — no external dependencies beyond:
   - React
   - Framer Motion (`import { motion } from "framer-motion"`)
   - Tailwind CSS classes
4. Use semantic HTML elements (section, nav, article, etc.)
5. Include responsive design: mobile-first, with sm/md/lg breakpoints
6. Animation approach:
   - Use `motion.div` / `motion.section` wrappers
   - Use `whileInView` for scroll-triggered entrances
   - Use `whileHover` for interactive hover states
   - Apply stagger via parent `transition.staggerChildren`
   - Match the intensity and timing from the style header
7. All text content should be realistic for the client — not lorem ipsum
```

### 4B. GSAP Instructions

```markdown
## Instructions

Generate a complete, self-contained React component for this section.

Requirements:
1. Use TypeScript with React.FC typing
2. Use ONLY the colors, fonts, spacing, radius, and animation values from
   the STYLE CONTEXT header above
3. The component must be self-contained — no external dependencies beyond:
   - React (including useEffect, useRef)
   - GSAP (`import { gsap } from "gsap"`)
   - GSAP ScrollTrigger (`import { ScrollTrigger } from "gsap/ScrollTrigger"`)
   - Tailwind CSS classes
4. Use semantic HTML elements (section, nav, article, etc.)
5. Include responsive design: mobile-first, with sm/md/lg breakpoints
6. GSAP setup pattern (MUST follow exactly):
   ```tsx
   const sectionRef = useRef<HTMLElement>(null);
   useEffect(() => {
     gsap.registerPlugin(ScrollTrigger);
     const ctx = gsap.context(() => {
       // All animations here, scoped to sectionRef
     }, sectionRef);
     return () => ctx.revert();
   }, []);
   ```
7. ScrollTrigger pattern:
   - Use `scrollTrigger: { trigger: ref, start: "top 80%", once: true }`
   - Use `gsap.from()` for entrance animations (animate FROM hidden state)
   - Use `stagger` for multi-element reveals
8. If a Reference Animation Pattern is provided above, use that exact pattern
   with the timing values from the style header
9. All text content should be realistic for the client — not lorem ipsum
```

---

## Phase 5: Idempotency & Safety

### 5A. Idempotent Asset Downloads

- Use content-addressed filenames: `{sha256-first8}-{original-name}.{ext}`
- Skip download if file already exists with matching hash
- Asset manifest is deterministic given the same extraction data

### 5B. Idempotent Injection

- Injection modules are pure functions: same inputs → same outputs
- No side effects — they return text blocks, they don't modify files
- The orchestrator is the only writer

### 5C. Graceful Degradation

At every injection point, missing data falls back to current behavior:

| Missing Data | Fallback |
|-------------|----------|
| No animation analysis | Use framer-motion with moderate intensity (current default) |
| No section overrides | Use Pattern-to-Archetype Map defaults from animation-patterns.md |
| No extracted images | Use gradient placeholder with aria-label (current behavior) |
| No Lottie files | Skip Lottie integration, use CSS/JS animations only |
| No extraction data (manual brief mode) | Entire injection system skipped, current pipeline unchanged |
| Asset download fails | Log warning, section uses gradient fallback |
| Token budget exceeds 8192 | Cap at 8192, log warning |

### 5D. Build Isolation

All injection artifacts are stored under the extraction directory:
```
output/extractions/{project}-{uuid}/
├── extraction-data.json      (existing)
├── mapped-sections.json      (existing)
├── animation-analysis.json   (existing)
├── accessible-assets.json    (NEW — Phase 2B)
├── asset-manifest.json       (NEW — Phase 2C)
└── screenshots/              (existing)
```

No global state. Parallel builds with different extraction UUIDs cannot collide.

---

## Implementation Order

```
Phase 1 (Animation Injector)     — Highest impact, closes the primary gap
  1A. Engine-specific templates   — 2 new template files
  1B. Pattern selection logic     — animation-injector.js core function
  1C. Lottie integration          — Lottie-specific prompt block
  1D. Token budget calculation    — Simple lookup table
  1E. Dependency resolution       — Fix either/or bug in stage_deploy

Phase 2 (Asset Injector)         — Closes the visual gap
  2A. Image categorization        — New function in extract-reference.js or separate module
  2B. Asset accessibility check   — HEAD requests + filtering
  2C. Asset download              — New function called from stage_deploy
  2D. Per-section asset injection — asset-injector.js core function
  2E. Fallback strategy           — Graceful degradation (mostly already exists)

Phase 3 (Orchestrator Wiring)    — Connects everything
  3A. Load injection data         — Read JSON artifacts in main()
  3B. Engine-branched prompt      — Replace hardcoded prompt with template selection
  3C. Dynamic token budget        — Parameterize call_claude()
  3D. Asset download hook         — Call download_assets() in stage_deploy
  3E. Dependency resolution       — Always include framer-motion + conditional GSAP/Lottie

Phase 4 (Templates)              — The actual prompt content
  4A. Framer Motion instructions  — Refined version of current instructions
  4B. GSAP instructions           — New template with boilerplate + ScrollTrigger

Phase 5 (Safety)                 — Idempotency + graceful degradation
  5A-D. Applied throughout implementation, not a separate coding phase
```

### Dependency Graph

```
Phase 4 (Templates)          — No dependencies, can start first
Phase 1A (Engine templates)  — Depends on Phase 4
Phase 1B (Pattern selection) — Depends on animation-patterns.md (exists)
Phase 1C (Lottie)           — Depends on 1B
Phase 1D (Token budget)     — Independent
Phase 1E (Dependencies)     — Independent

Phase 2A (Categorization)   — Depends on image-extraction.md (exists)
Phase 2B (Accessibility)    — Depends on 2A
Phase 2C (Download)         — Depends on 2B
Phase 2D (Injection)        — Depends on 2A + 2C

Phase 3 (Orchestrator)      — Depends on Phase 1 + Phase 2
```

### Parallelization

These can be built in parallel:
- **Track A:** Phase 4 → Phase 1 (animation injector + templates)
- **Track B:** Phase 2A → 2B → 2C → 2D (asset pipeline)
- **Track C:** Phase 3 (orchestrator wiring — after A and B complete)

---

## Files Created/Modified

### New Files
| File | Purpose |
|------|---------|
| `scripts/quality/lib/animation-injector.js` | Per-section animation prompt builder |
| `scripts/quality/lib/asset-injector.js` | Per-section asset prompt builder |
| `scripts/quality/lib/asset-downloader.js` | Download + verify extracted assets |
| `templates/section-instructions-framer.md` | Framer Motion section instructions |
| `templates/section-instructions-gsap.md` | GSAP section instructions |

### Modified Files
| File | Changes |
|------|---------|
| `scripts/orchestrate.py` | Wire injectors into stage_sections + stage_deploy, dynamic token budget, dependency fix |
| `scripts/quality/lib/extract-reference.js` | Add image categorization step |
| `scripts/quality/lib/section-context.js` | Add animation + asset context fields (or keep separate) |

### Unchanged Files
| File | Why Unchanged |
|------|---------------|
| `scripts/quality/lib/animation-detector.js` | Detection is complete and working |
| `scripts/quality/url-to-preset.js` | Preset generation is complete |
| `skills/animation-patterns.md` | Reference library, read-only by injector |
| `skills/image-extraction.md` | Spec document, implemented by asset-injector |
| All existing presets | Format unchanged, already contain animation fields |

---

## Success Criteria

After implementation, running the pipeline against `farmminerals.com/promo` should produce:

1. **HERO section** uses GSAP `character-reveal` on the headline + Lottie player for the logo animation — NOT framer-motion `motion.div`
2. **FEATURES sections** use GSAP `fade-up-stagger` with ScrollTrigger — NOT framer-motion `whileInView`
3. **STATS section** (if present) uses GSAP `count-up` pattern — animated numbers, not static text
4. **Product images** from the reference site appear in PRODUCT-SHOWCASE section — NOT gradient placeholders
5. **Lottie files** are downloaded to `public/lottie/` and rendered via `DotLottieReact`
6. **Build succeeds** with `npm run build` — no missing imports, no type errors
7. **Manual brief mode** (no --from-url) still works identically to current behavior
8. **Token budget** varies per section complexity — visible in pipeline output

---

## Maintenance Log

| Date | Change |
|------|--------|
| 2026-02-09 | Plan drafted based on Farm Minerals build retrospective |

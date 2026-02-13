# Deterministic Pipeline v2.0.0: Eliminate the Lossy Telephone Game

**Created:** 2026-02-11
**Status:** Implemented (pending validation builds)
**Target Version:** v2.0.0
**Depends On:** v1.2.0 (Universal Asset Intelligence Pipeline)
**Scope:** Architectural rewrite of the extraction-to-generation data flow

---

## Problem Statement

The pipeline has a **data fidelity gap** at its core. Between the source website and the generated output, data passes through three layers of LLM interpretation:

```
Source Site (ground truth)
    ↓ Playwright extracts DOM nodes (loses semantic meaning)
    ↓ Claude interprets extraction → markdown preset (lossy prose)
    ↓ Claude re-reads preset → scaffold (re-interprets its own prose)
    ↓ Claude generates each section from scaffold (third interpretation)
    = 3 layers of LLM interpretation between source and output
```

Each layer introduces drift. By section generation time, the system is working from Claude's interpretation of Claude's interpretation of a DOM scrape that didn't even dismiss the cookie banner.

### Quantified Evidence (Sofi Health build, 2026-02-11)

| Metric | Value | Impact |
|--------|-------|--------|
| Sections extracted | 11 raw DOM nodes | Only `<div>` and `<section>` tags, no semantic meaning |
| Section mapping confidence | 4/11 at 30% ("fallback") | Pipeline proceeded on guesses |
| Images extracted | 19, **zero** with section assignment | Asset injector guesses placement |
| Animation libraries detected | **0** | Site uses GSAP timeline.from but detector missed it |
| Text content starts with | "we collect cookies" | Cookie modal not dismissed |
| Icon library detected | **null** | Site uses custom SVGs, not a known library |
| Preset animation_engine | `css` | But pipeline injected Framer Motion + visual fallbacks anyway |
| Archetype diversity | 9/11 are STATS or FEATURES | Source has NAV, HERO, product carousels, botanical sections |
| Component export mismatch | `GradientShift` vs `GradientBackground` | Legacy registry has no export_name field |

### The Six Root Causes

1. **Extraction is structurally insufficient.** Raw DOM nodes with hashed class names. No headings, no content summaries, no semantic purpose. Images have no section assignment. Animations nearly undetected. Cookie banner not dismissed.

2. **Preset format forces lossy translation.** Rich extraction JSON gets compressed into markdown prose, then re-parsed by fragile regex. YAML says `animation_engine: css` but injection system overrides with GSAP/Framer Motion. The format actively creates contradictions.

3. **No confidence threshold enforcement.** 4/9 sections at 30% confidence via "fallback" proceed as confirmed. The gap report flags them but the pipeline ignores the flags.

4. **Component registries are fragmented.** Three registries that disagree. Legacy `registry.json` (36 entries, no export names) is read by the pipeline. Full `animation_registry.json` (1,034 entries, has export names) is not wired in.

5. **Claude used for deterministic tasks.** Assembly, consistency review, import generation, brace-balancing -- all code tasks done by AI, adding cost, latency, and non-determinism.

6. **No resilience patterns.** 50-minute hangs with no timeout. `--force` nukes output directories. No working checkpoint/resume.

---

## Target Architecture

```
Current (v1.2.0):                          Target (v2.0.0):
                                           
EXTRACT (Playwright)                       EXTRACT (Playwright, improved)
    ↓ extraction-data.json                     ↓ raw-extraction.json
CLAUDE → preset.md (lossy prose)           ANALYZE (1 Claude Vision call)
CLAUDE → brief.md (lossy prose)                ↓ site-spec.json (structured)
IDENTIFY (code) → identification.json      MAP (deterministic code, zero AI)
CLAUDE → scaffold.md (re-interprets)           ↓ build-plan.json (exact refs)
CLAUDE × N → sections/*.tsx                GENERATE (Claude × N, JSON input)
CLAUDE → page.tsx (assembly)                   ↓ sections/*.tsx
CLAUDE → review.md (consistency)           ASSEMBLE (deterministic code)
CODE → deploy                                  ↓ page.tsx + validated imports
                                           DEPLOY (deterministic code)
                                           
Claude calls: 20-30+                       Claude calls: 1 + N sections (11-16)
Artifacts: 6+ intermediate files           Artifacts: 3 JSON files (each is SoT)
Data format: mixed markdown/YAML/JSON      Data format: JSON throughout
```

### Single Source of Truth: `site-spec.json`

One structured JSON file replaces preset.md, brief.md, scaffold.md, and identification.json:

```json
{
  "version": "2.0.0",
  "project": "sofi-health",
  "source_url": "https://www.sofihealth.com/",
  "extracted_at": "2026-02-11T09:59:11.869Z",

  "style": {
    "palette": {
      "bg_primary": "#0a0a0a",
      "bg_secondary": "#18181b",
      "text_primary": "#ffffff",
      "text_muted": "#a1a1aa",
      "accent": "#ffffff",
      "border": "#27272a"
    },
    "fonts": {
      "heading": { "extracted": "HelveticaNowDisplayMedium", "google_fallback": "Inter", "weight": 500 },
      "body": { "extracted": "HelveticaNowDisplayMedium", "google_fallback": "Inter", "weight": 400 }
    },
    "spacing": { "section_padding": "6rem", "internal_gap": "3rem", "scale": "generous" },
    "border_radius": { "buttons": "9999px", "cards": "1.5rem", "inputs": "9999px" },
    "animation": { "engine": "gsap", "intensity": "subtle", "timing": "0.3s" },
    "density": "spacious",
    "color_temperature": "dark-neutral"
  },

  "sections": [
    {
      "index": 0,
      "archetype": "NAV",
      "variant": "sticky-transparent",
      "confidence": 0.92,
      "source_rect": { "x": 0, "y": 0, "width": 1440, "height": 80 },
      "content": {
        "headings": ["Sofi Health"],
        "body_text": [],
        "ctas": ["Shop", "Learn", "Science"]
      },
      "images": [
        { "src": "https://...logo.svg", "alt": "Sofi Health logo", "role": "logo" }
      ],
      "icons": { "library": null, "extracted_svgs": ["menu-hamburger"] },
      "animations": { "detected": [], "recommended": "css-only" },
      "components": { "matched": [], "fallbacks": [] }
    }
  ],

  "component_map": {
    "gradient-shift": {
      "source_file": "continuous/gradient-shift.tsx",
      "export_name": "GradientBackground",
      "export_type": "named",
      "import_statement": "import { GradientBackground } from '@/components/animations/gradient-shift'",
      "dependencies": ["framer-motion"],
      "engine": "framer-motion"
    }
  },

  "global": {
    "industry": "health-wellness-tech",
    "tone": "calm, scientific, aspirational",
    "photography_direction": "high-contrast product on dark, minimal lifestyle",
    "icon_strategy": "lucide-react",
    "detected_plugins": [],
    "detected_ui_patterns": []
  }
}
```

### Derived Artifact: `build-plan.json`

Deterministic code reads `site-spec.json` and produces exact build instructions with no interpretation needed:

```json
{
  "sections": [
    {
      "index": 0,
      "output_file": "00-nav.tsx",
      "archetype": "NAV",
      "variant": "sticky-transparent",
      "style_tokens": { "bg": "bg-black/80 backdrop-blur-md", "text": "text-white" },
      "content": { "headings": ["Sofi Health"], "ctas": ["Shop", "Learn"] },
      "images": [{ "src": "...", "import_as": "logo", "render_as": "inline-svg" }],
      "icons": [{ "name": "Menu", "package": "lucide-react" }],
      "animation": {
        "entrance": null,
        "pattern": "css-transition-only",
        "components_to_import": []
      },
      "token_budget": 4096
    }
  ],
  "dependencies": ["react", "next", "lucide-react", "framer-motion", "clsx", "tailwind-merge"],
  "components_to_copy": [
    { "from": "skills/animation-components/entrance/blur-fade.tsx", "to": "src/components/animations/blur-fade.tsx" }
  ],
  "assets_to_download": [
    { "url": "https://...", "dest": "public/images/hero-product.webp" }
  ]
}
```

---

## Implementation Phases

### Phase 0: Fix Extraction Quality (everything else is downstream)

**Priority:** Critical -- if extraction is garbage, nothing downstream can save it.
**Files:** `scripts/quality/lib/extract-reference.js` (706 lines)
**Estimated effort:** 1-2 hours

#### 0a: Dismiss cookie modals before extraction

Add a pre-extraction step that detects and dismisses common cookie consent patterns. Playwright can click buttons matching known selectors.

**Implementation:**

```javascript
// Add after page.goto(), before any extraction
async function dismissCookieModals(page) {
  const selectors = [
    'button[id*="cookie" i][id*="accept" i]',
    'button[class*="cookie" i][class*="accept" i]',
    'button:has-text("Accept All")',
    'button:has-text("Accept all")',
    'button:has-text("Accept Cookies")',
    'button:has-text("Got it")',
    'button:has-text("I agree")',
    '[data-testid*="cookie" i] button',
    '.cookie-banner button:first-of-type',
    '#onetrust-accept-btn-handler',
    '.cc-accept',
  ];
  for (const sel of selectors) {
    try {
      const btn = await page.$(sel);
      if (btn && await btn.isVisible()) {
        await btn.click();
        await page.waitForTimeout(500);
        break;
      }
    } catch {}
  }
}
```

**Where:** Insert at `extract-reference.js` after `await page.goto(url, ...)` and initial wait, before DOM extraction begins.

**Test:** Run extraction on sofihealth.com -- first text entry should NOT be "we collect cookies."

#### 0b: Full-page scroll capture before extraction

The current extraction captures only the initial viewport (900px height). Sites with lazy-loaded content, pinned scroll sections, or 15+ content blocks lose the majority of their content.

**Implementation:**

```javascript
// After page load, before extraction
async function scrollToBottom(page) {
  let previousHeight = 0;
  let currentHeight = await page.evaluate(() => document.body.scrollHeight);
  while (currentHeight > previousHeight) {
    previousHeight = currentHeight;
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(1000); // wait for lazy-load
    currentHeight = await page.evaluate(() => document.body.scrollHeight);
  }
  // Scroll back to top for consistent extraction
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
}
```

**Where:** Insert after cookie dismissal, before DOM extraction. Update `pageHeight` in output to use `document.body.scrollHeight` post-scroll.

**Test:** Run on sofihealth.com -- `pageHeight` should be ~24000, not 900. Section count should increase.

#### 0c: Assign images and text to sections by sectionIndex

During extraction, `renderedDOM` elements already have `sectionIndex`. Images and text content currently don't carry this field forward. One loop in the extraction connects them.

**Implementation:**

In the existing `page.evaluate()` that collects images:
```javascript
// For each image, find its closest section ancestor and record sectionIndex
images = images.map(img => {
  const rect = img.getBoundingClientRect();
  const sectionIdx = sections.findIndex(s => {
    const sr = s.rect;
    return rect.top >= sr.y && rect.top < (sr.y + sr.height);
  });
  return { ...img, sectionIndex: sectionIdx >= 0 ? sectionIdx : null };
});
```

Apply same logic to `textContent` entries.

**Where:** Modify the existing image and text collection blocks in `extract-reference.js`.

**Test:** Every image in `assets.images` should have a `sectionIndex` integer. Every text entry should have a `sectionIndex`.

**Success criteria for Phase 0:**
- [ ] Cookie banner dismissed on sofihealth.com, gsap.com, and 3 other test URLs
- [ ] `pageHeight` reflects full scrolled page, not just viewport
- [ ] All `assets.images` entries have `sectionIndex`
- [ ] All `textContent` entries have `sectionIndex`
- [ ] Extraction time stays under 60 seconds per URL

---

### Phase 1: Unified Component Registry

**Priority:** High -- prevents an entire category of import/export bugs.
**Files:** New `scripts/quality/build-unified-registry.js`, delete `skills/animation-components/registry.json` (legacy)
**Estimated effort:** 2-3 hours

#### 1a: Build auto-generated registry from source files

Create a script that scans all `.tsx` files in `skills/animation-components/` and produces a single `component-registry.json` with accurate export information.

**New file:** `scripts/quality/build-unified-registry.js`

```javascript
// For each .tsx file:
// 1. Read file content
// 2. Extract: default export name, named exports, dependencies (import statements)
// 3. Determine engine (framer-motion, gsap, css)
// 4. Record file path relative to skills/animation-components/
// 5. Generate correct import statement
// 6. Validate: file must have at least one export, must compile (tsc --noEmit)
```

**Output:** `skills/animation-components/component-registry.json`

```json
{
  "version": "2.0.0",
  "generated_at": "...",
  "components": {
    "gradient-shift": {
      "source_file": "continuous/gradient-shift.tsx",
      "export_name": "GradientBackground",
      "export_type": "named",
      "import_statement": "import { GradientBackground } from '@/components/animations/gradient-shift'",
      "dependencies": ["framer-motion"],
      "engine": "framer-motion",
      "category": "continuous",
      "archetypes": ["HERO", "CTA", "NEWSLETTER", "ABOUT"],
      "intensity": "expressive",
      "line_count": 74
    }
  }
}
```

#### 1b: Wire all pipeline code to read from unified registry

**Files to modify:**
- `scripts/quality/lib/animation-injector.js` (1330 lines) -- replace reads from legacy `registry.json`
- `scripts/quality/lib/asset-injector.js` (527 lines) -- replace visual fallback component refs
- `scripts/quality/lib/pattern-identifier.js` (900 lines) -- replace UI component library map
- `scripts/orchestrate.py` (2067 lines) -- `stage_deploy` component copying reads unified registry

Every import statement generated anywhere in the pipeline must come from `component-registry.json`'s `import_statement` field. No more constructing imports from file paths + guessed export names.

#### 1c: Delete legacy registry.json

Remove `skills/animation-components/registry.json` (the 36-entry legacy file with no export names).

**Note:** The full `animation_registry.json` (1,034 entries in `registry/`) stays -- it has detailed classification data. But the unified registry becomes the single source for import/export correctness.

**Success criteria for Phase 1:**
- [ ] `build-unified-registry.js` produces registry with export names for all 36 curated components
- [ ] Zero component import/export mismatches when running existing test harness
- [ ] `animation-injector.js`, `asset-injector.js`, `pattern-identifier.js` all read from unified registry
- [ ] `stage_deploy` component copy uses unified registry paths
- [ ] Legacy `registry.json` deleted
- [ ] Existing test harness (66 assertions) still passes

---

### Phase 2: JSON Spec Format (Replace Markdown Preset)

**Priority:** High -- eliminates the lossy prose translation layer.
**Files:** New `scripts/quality/build-site-spec.js`, modify `scripts/quality/url-to-preset.js` (275 lines), modify `scripts/orchestrate.py`
**Estimated effort:** 4-6 hours

#### 2a: Create `build-site-spec.js` module

This replaces the current two-step flow (`url-to-preset.js` → Claude → markdown, `url-to-brief.js` → Claude → markdown) with a single structured output.

**Inputs:**
- `extraction-data.json` (from Playwright)
- `mapped-sections.json` (from archetype-mapper.js)
- `animation-analysis.json` (from animation-detector.js)
- `identification.json` (from pattern-identifier.js)
- `component-registry.json` (from Phase 1)

**Process:**
1. **Style tokens** -- deterministic extraction from `design-tokens.js` output. Colors as hex + Tailwind mapping. Fonts with Google Fonts fallback. Spacing, radii, density from DOM analysis. Zero Claude interpretation needed.
2. **Section mapping** -- read `mapped-sections.json` + `identification.json`. Apply confidence thresholds (Phase 3). Enrich with images, text, icons from extraction data using `sectionIndex` (Phase 0c).
3. **Component matching** -- for each section, query unified registry for animation components, visual fallbacks, UI components. Record exact import statements.
4. **One Claude call** -- the ONLY AI interpretation step. Input: full-page screenshot + extraction summary JSON. Output: structured JSON with `industry`, `tone`, `content_direction`, and refined archetype/variant assignments for low-confidence sections. Use structured output / JSON mode.

**Output:** `output/{project}/site-spec.json`

#### 2b: Modify `stage_url_extract` to produce `site-spec.json`

Replace the current flow in `orchestrate.py:134-234`:

```
Current:
  stage_url_extract → calls url-to-preset.js (Claude) → preset.md
                    → calls url-to-brief.js (Claude) → brief.md
                    → calls section-context.js → per-section data
  stage_identify    → calls pattern-identifier.js → identification.json

Target:
  stage_extract     → calls extract-reference.js → raw-extraction.json
                    → calls archetype-mapper.js → mapped-sections.json
                    → calls animation-detector.js → animation-analysis.json
                    → calls pattern-identifier.js → identification.json
                    → calls build-site-spec.js → site-spec.json (1 Claude call inside)
```

The key difference: `build-site-spec.js` does one focused Claude Vision call with structured JSON output instead of two free-form Claude calls that produce prose markdown.

#### 2c: Modify `stage_scaffold` to read `site-spec.json` directly

Replace the current scaffold generation (Claude call that re-interprets the preset's section sequence) with deterministic code that reads `site-spec.json.sections[]` and produces the section list.

The "scaffold" becomes a JSON array, not a numbered markdown list. `parse_scaffold()` regex parsing is eliminated.

```python
def stage_scaffold(site_spec: dict, project_name: str) -> list[dict]:
    """Stage 1: Produce section list from site-spec. No Claude call needed."""
    sections = []
    for s in site_spec["sections"]:
        sections.append({
            "index": s["index"],
            "archetype": s["archetype"],
            "variant": s["variant"],
            "confidence": s["confidence"],
            "content": s["content"],
            "images": s["images"],
            # ... all structured data flows through
        })
    return sections
```

This eliminates: the scaffold Claude call, the `parse_scaffold()` regex, the bold-markdown parsing bug, and the scaffold-to-section data loss.

#### 2d: Modify `stage_sections` to accept JSON tokens instead of prose

Replace the compact style header (markdown text block) with JSON style tokens injected directly into the section prompt.

```python
# Current: style header is a markdown string restated in every prompt
style_header = """═══ STYLE CONTEXT ═══
Palette: dark-neutral | black/zinc-950 bg, white text
Type: HelveticaNowDisplayMedium · 500/400 · 1.25 ratio
..."""

# Target: style tokens are JSON, formatted into the prompt
style_json = json.dumps(site_spec["style"], indent=2)
section_json = json.dumps(section_spec, indent=2)
```

The section prompt changes from:
```
Here is the style context:
{markdown_style_header}

Generate section 3: FEATURES | alternating-rows
Content direction: ...
```

To:
```
Generate a React/TypeScript/Tailwind section component.

STYLE TOKENS (use these exact values):
{style_json}

SECTION SPEC:
{section_json}

The section spec contains the archetype, variant, content, images with section assignments,
icon mappings, animation components with exact import statements, and token budget.
Use the provided import_statement values exactly -- do not construct your own.
```

**Success criteria for Phase 2:**
- [ ] `build-site-spec.js` produces valid `site-spec.json` from sofi-health extraction data
- [ ] `site-spec.json` contains hex colors (not Tailwind names that need mapping)
- [ ] `site-spec.json` sections have images with `sectionIndex` assignments
- [ ] `site-spec.json` component_map has exact `import_statement` for every component
- [ ] `stage_scaffold` is now deterministic code (zero Claude calls)
- [ ] `stage_sections` reads JSON tokens, not markdown prose
- [ ] `parse_scaffold()` and `parse_fonts()` regex functions are removed
- [ ] Sofi Health build produces equivalent or better output than v1.2.0

---

### Phase 3: Confidence Thresholds and Fallback Strategy

**Priority:** High -- stops the pipeline from acting on low-confidence guesses.
**Files:** `scripts/quality/lib/archetype-mapper.js` (398 lines), new `scripts/quality/lib/confidence-gate.js`, modify `scripts/quality/build-site-spec.js`
**Estimated effort:** 2-3 hours

#### 3a: Define confidence tiers

```javascript
const CONFIDENCE_TIERS = {
  HIGH:   { min: 0.7, action: 'proceed' },
  MEDIUM: { min: 0.5, action: 'proceed_with_warning' },
  LOW:    { min: 0.3, action: 'screenshot_reanalysis' },
  NONE:   { min: 0.0, action: 'generic_container' }
};
```

#### 3b: Implement screenshot re-analysis for low-confidence sections

For any section mapped at confidence < 0.5:
1. Crop the full-page screenshot to that section's `rect`
2. Make a focused Claude Vision call: "What type of website section is this? Classify as one of: [archetype list]. Return JSON."
3. If confidence improves to >= 0.5, use the new classification
4. If still low, default to a generic content section (not FEATURES as fallback)

**Implementation:** Add to `build-site-spec.js`:

```javascript
async function reanalyzeLowConfidenceSections(sections, screenshotPath, archetypeList) {
  const lowConf = sections.filter(s => s.confidence < 0.5);
  if (lowConf.length === 0) return sections;
  
  // Batch: send all low-confidence crops in one Claude call
  // "Classify these N section screenshots. For each, return {archetype, variant, confidence}."
  // This is 1 additional Claude call, not N calls.
}
```

#### 3c: Add confidence metadata to build output

Every section in `site-spec.json` carries its confidence score. The section generation prompt can use this:
- High confidence: "Generate this section matching the archetype specification exactly"
- Medium confidence: "This section was classified with moderate confidence. Prioritize the content signals over the archetype template."
- Low confidence (post-reanalysis): "This section classification is uncertain. Use the provided content and images to determine the best layout."

**Success criteria for Phase 3:**
- [ ] No section below 0.5 confidence proceeds without re-analysis
- [ ] Re-analysis uses cropped screenshot + focused Claude Vision call
- [ ] Sections that can't be classified above 0.3 become generic containers
- [ ] Sofi Health extraction: 0 sections at 30% "fallback" in final output

---

### Phase 4: Remove Claude from Deterministic Tasks

**Priority:** Medium -- reduces cost, latency, and non-determinism.
**Files:** `scripts/orchestrate.py` (multiple functions)
**Estimated effort:** 3-4 hours

#### 4a: Replace `stage_assemble` with deterministic code

Current `stage_assemble` (`orchestrate.py:1074`) uses string templates already -- no Claude call. **Verify** this is still the case and ensure it generates correct imports from `component-registry.json`.

#### 4b: Replace `stage_review` with AST/token validation

Current `stage_review` (`orchestrate.py:1721`) calls Claude to review consistency. Replace with:

```python
def stage_review(sections: list[Path], site_spec: dict) -> dict:
    """Deterministic consistency review. No Claude call."""
    issues = []
    style = site_spec["style"]
    
    for section_file in sections:
        code = section_file.read_text()
        
        # Check: color tokens match palette
        for color_hex in style["palette"].values():
            # Verify no off-palette colors used
            
        # Check: font references match spec
        # Check: border-radius values match spec  
        # Check: animation timing matches spec
        # Check: imports are valid (component exists in registry)
        # Check: no emoji characters
        # Check: no placeholder image URLs
        # Check: "use client" directive present
        # Check: export default present
        # Check: braces balanced (AST parse, not regex)
    
    return {"issues": issues, "pass": len(issues) == 0}
```

This is faster, cheaper, deterministic, and catches real issues instead of hallucinating false positives.

#### 4c: Replace import generation with registry lookup

Everywhere the pipeline constructs an import statement (in `animation-injector.js`, `asset-injector.js`, `pattern-identifier.js`, or Claude prompts), replace with:

```javascript
function getImportStatement(componentId, registry) {
  const comp = registry.components[componentId];
  if (!comp) throw new Error(`Component ${componentId} not in registry`);
  return comp.import_statement; // Pre-validated, exact string
}
```

#### 4d: Replace `_detect_and_repair_truncation` with proper AST validation

The current truncation detector in `post-process.js` uses brace counting and has known false positives. Replace with:

```javascript
// Use TypeScript compiler API for validation
const ts = require('typescript');
function validateJSX(code) {
  const sourceFile = ts.createSourceFile('section.tsx', code, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const diagnostics = ts.getPreEmitDiagnostics(
    ts.createProgram(['section.tsx'], { jsx: ts.JsxEmit.ReactJSX, noEmit: true })
  );
  return { valid: diagnostics.length === 0, errors: diagnostics };
}
```

**Success criteria for Phase 4:**
- [ ] `stage_review` makes zero Claude API calls
- [ ] `stage_review` catches real issues (off-palette colors, missing exports) deterministically
- [ ] All import statements in generated sections come from registry lookup
- [ ] Truncation validation uses TypeScript AST, zero false positives
- [ ] Total Claude calls per build reduced from 20-30+ to 1 analysis + N sections

---

### Phase 5: Pipeline Resilience

**Priority:** Medium -- prevents the operational failures seen in every build.
**Files:** `scripts/orchestrate.py` (main loop and CLI)
**Estimated effort:** 3-4 hours

#### 5a: API call timeouts and retries

```python
import time

MAX_RETRIES = 3
TIMEOUT_SECONDS = 90

def call_claude_with_retry(messages, max_tokens, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                messages=messages,
                max_tokens=max_tokens,
                timeout=TIMEOUT_SECONDS,
                **kwargs
            )
            return response
        except (TimeoutError, RateLimitError) as e:
            wait = 2 ** attempt * 5  # 5s, 10s, 20s
            print(f"  Retry {attempt+1}/{MAX_RETRIES} after {wait}s: {e}")
            time.sleep(wait)
    raise RuntimeError(f"Claude API failed after {MAX_RETRIES} retries")
```

**Where:** Wrap every `client.messages.create()` call in `orchestrate.py`.

#### 5b: Checkpoint state file after every stage

```python
CHECKPOINT_FILE = output_dir / "checkpoint.json"

def save_checkpoint(stage: str, data: dict):
    checkpoint = {
        "project": project_name,
        "stage": stage,
        "timestamp": datetime.now().isoformat(),
        "data": data  # stage-specific state
    }
    # Atomic write
    tmp = CHECKPOINT_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(checkpoint, indent=2))
    tmp.rename(CHECKPOINT_FILE)

def load_checkpoint(project_name: str) -> dict | None:
    path = Path(f"output/{project_name}/checkpoint.json")
    if path.exists():
        return json.loads(path.read_text())
    return None
```

Write checkpoint after: extraction, site-spec generation, each section generation, assembly, deploy.

#### 5c: Fix `--skip-to` to read checkpoint, not scan output directory

```python
# Current: --skip-to guesses state by checking if files exist
# Target: --skip-to reads checkpoint.json for exact state

if args.skip_to:
    checkpoint = load_checkpoint(project_name)
    if not checkpoint:
        print(f"Error: No checkpoint found for {project_name}. Cannot skip.")
        sys.exit(1)
    if STAGE_ORDER.index(args.skip_to) > STAGE_ORDER.index(checkpoint["stage"]):
        print(f"Error: Cannot skip to '{args.skip_to}' -- last completed stage was '{checkpoint['stage']}'")
        sys.exit(1)
```

#### 5d: Separate `--force` and `--clean` flags

```python
# --force: ignore warnings (low confidence, validation issues), proceed anyway
# --clean: delete existing output and start fresh

parser.add_argument('--force', action='store_true', help='Ignore warnings and proceed')
parser.add_argument('--clean', action='store_true', help='Delete existing output and start fresh')

# NEVER delete output directory unless --clean is explicitly passed
if args.clean:
    shutil.rmtree(output_dir, ignore_errors=True)
```

**Success criteria for Phase 5:**
- [ ] 90-second timeout on all API calls, 3 retries with exponential backoff
- [ ] `checkpoint.json` written after every stage
- [ ] `--skip-to sections` resumes from checkpoint data, not file system guessing
- [ ] `--force` does NOT delete output (only `--clean` does)
- [ ] Pipeline survives a rate-limited API and resumes correctly

---

## Execution Order and Dependencies

```
Phase 0 (Extraction) ──────→ Phase 2 (JSON Spec) ──→ Phase 3 (Confidence)
                               ↑                          ↓
Phase 1 (Registry) ───────────┘                     Phase 4 (Deterministic)
                                                          ↓
Phase 5 (Resilience) ← can be done in parallel with any phase
```

**Recommended execution sequence:**
1. **Phase 0** first -- all other phases benefit from better extraction data
2. **Phase 1** next -- unified registry is needed by Phase 2's component_map
3. **Phase 2** is the largest change -- core architectural shift
4. **Phase 3** builds on Phase 2's site-spec format
5. **Phase 4** + **Phase 5** can be done in parallel after Phase 2

---

## Validation Build

After all phases complete, run two validation builds:

1. **Sofi Health rebuild** (`--from-url https://www.sofihealth.com/`) -- direct comparison with v1.2.0 output
2. **GSAP.com rebuild** (`--from-url https://gsap.com/`) -- tests animation detection, plugin mapping, complex sections

### Success metrics:

| Metric | v1.2.0 Baseline | v2.0.0 Target |
|--------|-----------------|---------------|
| Claude API calls per build | 20-30+ | 1 + N sections (11-16) |
| Section archetype accuracy | 64% (7/11 high confidence) | >85% (all above 0.5) |
| Component import errors | 1+ per build (export name mismatch) | 0 |
| Images with section assignment | 0% | 100% |
| Cookie banner in extraction | Present | Dismissed |
| Pipeline hangs (>5 min no output) | Common | Impossible (90s timeout) |
| Checkpoint/resume works | No (--force deletes output) | Yes (reads checkpoint.json) |
| Total build time | 20-40 min | 10-20 min |
| Approximate API cost per build | ~$1.50-2.50 | ~$0.50-1.00 |

---

## Files Changed Summary

| File | Action | Phase |
|------|--------|-------|
| `scripts/quality/lib/extract-reference.js` | Modify (cookie dismiss, scroll, sectionIndex) | 0 |
| `scripts/quality/build-unified-registry.js` | New | 1 |
| `skills/animation-components/registry.json` | Delete (legacy) | 1 |
| `skills/animation-components/component-registry.json` | New (auto-generated) | 1 |
| `scripts/quality/lib/animation-injector.js` | Modify (read unified registry) | 1 |
| `scripts/quality/lib/asset-injector.js` | Modify (read unified registry) | 1 |
| `scripts/quality/lib/pattern-identifier.js` | Modify (read unified registry) | 1 |
| `scripts/quality/build-site-spec.js` | New (core module) | 2 |
| `scripts/quality/url-to-preset.js` | Deprecate (replaced by build-site-spec) | 2 |
| `scripts/quality/url-to-brief.js` | Deprecate (replaced by build-site-spec) | 2 |
| `scripts/orchestrate.py` | Major modify (new stage flow, checkpoints, resilience) | 2, 4, 5 |
| `scripts/quality/lib/confidence-gate.js` | New | 3 |
| `templates/section-prompt.md` | Modify (JSON tokens instead of prose header) | 2 |
| `skills/presets/*.md` | Kept for manual-brief mode (not deleted) | — |
| `briefs/*.md` | Kept for manual-brief mode (not deleted) | — |

**Note:** Preset markdown files and briefs are kept for the `--preset` manual mode. The `--from-url` mode bypasses them entirely via `site-spec.json`.

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Claude structured JSON output may still hallucinate | Medium | Validate against extraction data; reject if colors/fonts don't match |
| Cookie dismiss may miss custom implementations | Low | Graceful fallback -- extraction proceeds with banner; add per-site overrides |
| TypeScript AST validation adds Node.js dependency to Python pipeline | Low | Already a hybrid pipeline; use subprocess like existing pattern |
| Full-page scroll may trigger rate limiting on target sites | Low | Add configurable scroll delay; respect robots.txt |
| Removing scaffold Claude call may reduce creative section sequencing | Medium | The analysis Claude call still recommends section order; manual override via `--preset` mode preserved |
| Phase 2 is a large change that may introduce regressions | High | Run validation builds against both test URLs; keep v1.2.0 as fallback via git tag |

---

## Maintenance Log

| Date | Change |
|------|--------|
| 2026-02-11 | Plan created from diagnostic analysis of sofi-health build |
| 2026-02-11 | All 6 phases implemented. Phase 0: extract-reference.js (706->824 lines). Phase 1: component-registry.json (48 components), legacy registry deleted. Phase 2: build-site-spec.js (587 lines), stage_scaffold_v2, JSON tokens in stage_sections. Phase 3: confidence-gate.js (180 lines) wired into build-site-spec. Phase 4: stage_review_v2 deterministic review. Phase 5: retry wrapper, checkpoints, --clean flag. orchestrate.py (1404->2417 lines). 66 test assertions pass. |

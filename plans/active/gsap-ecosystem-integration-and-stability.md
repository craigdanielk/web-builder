# GSAP Ecosystem Integration & System Stability

**Status:** Planning
**Created:** 2026-02-11
**Depends on:** Pattern Identification Pipeline (v0.9.0), Animation Registry (v0.8.0), Data Injection Pipeline (v0.5.0)
**Scope:** Full GSAP plugin coverage, 8 unresolved bugs, detection/extraction upgrades, component library expansion, build reliability
**Target version:** v1.0.0
**Evidence:** 15 retrospectives, GSAP plugin docs (https://gsap.com/docs/v3/Plugins/), gsap-v9-test live validation

---

## Problem Statement

The system covers **only 38% of GSAP's ecosystem** (15 of 40 features). 19 features are completely missing, 6 are partial. This creates a cascade of failures:

1. **Detection blind spots**: `animation-detector.js` only detects `window.gsap` and `window.ScrollTrigger`. It cannot detect SplitText, Flip, MorphSVG, DrawSVG, Observer, CustomEase, or any other plugin. When we extract gsap.com, we capture 186 GSAP calls but can't distinguish SplitText character animations from manual text splitting.

2. **Extraction doesn't categorize plugin usage**: `gsap-extractor.js` captures raw calls (`gsap.to`, `timeline.from`) but doesn't identify which plugin they belong to. A `SplitText` operation followed by staggered reveals looks identical to manual DOM manipulation.

3. **Generation can't use what it doesn't know**: `section-instructions-gsap.md` only teaches about core tweens + ScrollTrigger. Zero instructions for SplitText, Flip, DrawSVG, MorphSVG, MotionPath, Observer, or any premium plugin. Claude hand-codes inferior alternatives.

4. **8 unresolved bugs** degrade build reliability: GSAP `from()` SSR invisibility, `parse_scaffold()` bold markdown failure, zero-section asset injection bypass, nav token truncation, color temperature misclassification, font parsing corruption, and more.

### GSAP Coverage Matrix (Current State)

| Category | Features | Covered | Partial | Missing |
|----------|----------|---------|---------|---------|
| Core API | 11 | 10 | 0 | 1 (`matchMedia`) |
| Easing | 12 | 4 | 4 | 4 (Custom*) |
| Scroll | 3 | 1 | 0 | 2 |
| Text | 3 | 0 | 1 | 2 |
| SVG | 4 | 0 | 0 | 4 |
| UI | 4 | 0 | 2 | 2 |
| Physics | 2 | 0 | 0 | 2 |
| React | 1 | 1 | 0 | 0 |
| DevTools | 1 | 0 | 0 | 1 |
| **Total** | **40** | **15 (38%)** | **6 (15%)** | **19 (48%)** |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│  PHASE 1: BUG FIXES (Reliability)                            │
│  parse_scaffold, from() SSR, token truncation, font parsing  │
│  zero-section fallback, color misclassification, JSX repair  │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────┐
│  PHASE 2: GSAP DETECTION (Know what's there)                 │
│  animation-detector.js   → detect all 20 GSAP plugins       │
│  gsap-extractor.js       → classify calls by plugin          │
│  pattern-identifier.js   → map plugins to capabilities       │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────┐
│  PHASE 3: GSAP KNOWLEDGE (Know how to use them)              │
│  animation-patterns.md   → document all plugin patterns      │
│  section-instructions-gsap.md → teach Claude all plugins     │
│  animation-components/   → pre-built plugin components       │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────┐
│  PHASE 4: GSAP INJECTION (Wire it into generation)           │
│  animation-injector.js   → plugin-aware injection blocks     │
│  orchestrate.py          → plugin deps in stage_deploy       │
│  url-to-preset.js        → plugin-aware preset generation    │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────┐
│  PHASE 5: BUILD RELIABILITY (Never ship broken output)       │
│  post-process.js         → JSX truncation detection + repair │
│  orchestrate.py          → pre-flight build validation       │
│  validate-build.js       → post-deploy visual check          │
└──────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Bug Fixes (Reliability Foundation)

**Goal:** Fix all 8 active bugs. Nothing else matters if builds break.
**Effort:** 3-4 hours
**Files:** `orchestrate.py`, `post-process.js`, `animation-injector.js`, `asset-injector.js`, `url-to-preset.js`, `templates/section-instructions-gsap.md`, `templates/section-instructions-framer.md`

### 1A. Fix `parse_scaffold()` bold markdown failure [HIGH]

**File:** `orchestrate.py` (parse_scaffold function)
**Bug:** Regex `\d+\.\s+(\w[\w-]*)` fails when Claude outputs `**NAV**` with bold markers.
**Fix:** Change to `\d+\.\s+\*{0,2}(\w[\w-]*)\*{0,2}` to strip optional bold markers.
**Test:** Parse scaffold with `1. **NAV** | mega-menu | ...` — should extract `NAV`.

### 1B. Fix GSAP `from()` SSR invisibility [HIGH]

**Files:** `templates/section-instructions-gsap.md`, `skills/animation-patterns.md`
**Bug:** `gsap.from({ opacity: 0 })` immediately sets elements invisible during SSR/hydration. ScrollTrigger `once: true` never fires in static context.
**Fix — two-part:**
1. Update `section-instructions-gsap.md` to add explicit rule: "NEVER use `gsap.from()` or `gsap.fromTo()` with `opacity: 0` for entrance animations. Use Framer Motion `whileInView` for all scroll-triggered entrance reveals. Reserve GSAP for: interactive effects (hover, tilt), scroll-linked parallax (`scrub: true`), continuous animations (floating, pulsing), and text effects (SplitText character reveals with initial visibility)."
2. Update `skills/animation-patterns.md` entrance patterns to show the Framer Motion + GSAP hybrid approach: Framer for entrance, GSAP for everything else.

**Success criteria:** Sections visible on deployed sites without user interaction.

### 1C. Increase nav section token budget [HIGH]

**File:** `orchestrate.py` (stage_sections, token budget logic)
**Bug:** Nav sections (371+ lines) consistently exceed 4096 tokens and get truncated mid-JSX.
**Fix:** Add archetype-based token budget override: NAV and FOOTER sections get 6144 tokens. Add to the existing dynamic budget logic in `animation-injector.js` or directly in `orchestrate.py`.
**Test:** Generate a mega-menu nav section — should complete without truncation.

### 1D. Fix zero-section extraction asset injection bypass [HIGH]

**File:** `scripts/quality/lib/asset-injector.js`
**Bug:** When Playwright finds 0 visual `<section>` elements (JS-heavy sites), the entire asset injection pipeline is silently skipped.
**Fix:** Add fallback in `getAssetContexts()`: when section count is 0 but `assets.images` has entries, distribute images heuristically across scaffold sections by category (hero images → section 0, product → mid-sections, team → late sections, logo → LOGO-BAR archetype).
**Test:** Run with extraction data containing 0 sections but 8+ images — all images should appear in asset contexts.

### 1E. Fix preset color temperature misclassification [MEDIUM]

**File:** `scripts/quality/url-to-preset.js` (Claude prompt in generatePreset)
**Bug:** Dark overlays/modals cause Claude to classify a light site as "dark-neutral".
**Fix:** Add explicit instruction to the Claude prompt: "Determine background color from the FIRST `renderedDOM` element's `styles.backgroundColor`, NOT from overlays, modals, or tooltips. Cross-check: if >60% of text colors are dark (black, gray-900, gray-800), the site is likely light-themed regardless of any dark overlay elements."
**Test:** Process a site with dark nav overlay but white body — should classify as light.

### 1F. Fix `parse_fonts()` corruption [MEDIUM]

**File:** `orchestrate.py` (parse_fonts function)
**Bug:** Regex fails on certain preset YAML formatting, causing preset content to leak into `layout.tsx`.
**Fix:** Add validation after parse: if extracted font string contains YAML markers (`---`, `:`, `palette`), discard and fall back to `Inter`. Log a warning.
**Test:** Feed a preset with unusual line breaks in the Type line — should extract clean font or fall back.

### 1G. Add JSX truncation detection [MEDIUM]

**File:** `scripts/quality/lib/post-process.js`
**Bug:** Truncated sections ship with unclosed JSX, breaking the build.
**Fix:** Add `detectTruncation(code)` function that checks:
1. Has `export default` statement
2. JSX tag balance (count `<TagName` vs `</TagName` and `/>`)
3. No unclosed string literals (odd number of backticks/quotes)
4. No unclosed template literals
If truncation detected, attempt repair: close open tags, add missing `export default`, add missing closing braces. If unrepairable, log error and flag for regeneration.
**Test:** Feed JSX cut at line 370 mid-tag — should detect and repair or flag.

### 1H. Add `--clean` / `--force` flag for project directory conflicts [LOW]

**File:** `orchestrate.py` (main function, directory creation)
**Bug:** Re-running a project fails because output directory already exists.
**Fix:** Add `--force` CLI flag that removes existing `output/{project}/` before starting. Without flag, prompt user or fail with clear error.
**Test:** Run pipeline twice for same project with `--force` — second run should succeed.

**Phase 1 success criteria:**
- [ ] `parse_scaffold` handles `**BOLD**` archetypes
- [ ] Deployed GSAP sites have visible sections (no `from()` invisibility)
- [ ] Nav sections generate complete (no truncation)
- [ ] Zero-section sites still get asset injection
- [ ] Light sites with dark overlays classified correctly
- [ ] Truncated JSX detected and flagged before assembly

---

## Phase 2: GSAP Plugin Detection

**Goal:** Detect every GSAP plugin a reference site uses.
**Effort:** 4-6 hours
**Files:** `animation-detector.js`, `gsap-extractor.js`, `pattern-identifier.js`
**Depends on:** Phase 1 (stable builds to test against)

### 2A. Extend `animation-detector.js` plugin detection

**File:** `scripts/quality/lib/animation-detector.js` (library detection section)
**Current:** Only detects `window.gsap` and `window.ScrollTrigger`
**Add detection for all 20 GSAP plugins:**

```javascript
const GSAP_PLUGINS = [
  { name: 'GSAP',            test: () => !!window.gsap,              via: 'window.gsap' },
  { name: 'ScrollTrigger',   test: () => !!window.ScrollTrigger,     via: 'window.ScrollTrigger' },
  { name: 'ScrollSmoother',  test: () => !!window.ScrollSmoother,    via: 'window.ScrollSmoother' },
  { name: 'ScrollTo',        test: () => !!window.gsap?.plugins?.scrollTo, via: 'gsap.plugins.scrollTo' },
  { name: 'SplitText',       test: () => !!window.SplitText,         via: 'window.SplitText' },
  { name: 'ScrambleText',    test: () => !!window.ScrambleTextPlugin, via: 'window.ScrambleTextPlugin' },
  { name: 'TextReplace',     test: () => !!window.TextPlugin,        via: 'window.TextPlugin' },
  { name: 'DrawSVG',         test: () => !!window.DrawSVGPlugin,     via: 'window.DrawSVGPlugin' },
  { name: 'MorphSVG',        test: () => !!window.MorphSVGPlugin,    via: 'window.MorphSVGPlugin' },
  { name: 'MotionPath',      test: () => !!window.MotionPathPlugin,  via: 'window.MotionPathPlugin' },
  { name: 'Flip',            test: () => !!window.Flip,              via: 'window.Flip' },
  { name: 'Draggable',       test: () => !!window.Draggable,         via: 'window.Draggable' },
  { name: 'Inertia',         test: () => !!window.InertiaPlugin,     via: 'window.InertiaPlugin' },
  { name: 'Observer',        test: () => !!window.Observer,          via: 'window.Observer' },
  { name: 'Physics2D',       test: () => !!window.Physics2DPlugin,   via: 'window.Physics2DPlugin' },
  { name: 'PhysicsProps',    test: () => !!window.PhysicsPropsPlugin, via: 'window.PhysicsPropsPlugin' },
  { name: 'CustomEase',      test: () => !!window.CustomEase,        via: 'window.CustomEase' },
  { name: 'CustomWiggle',    test: () => !!window.CustomWiggle,      via: 'window.CustomWiggle' },
  { name: 'CustomBounce',    test: () => !!window.CustomBounce,      via: 'window.CustomBounce' },
  { name: 'GSDevTools',      test: () => !!window.GSDevTools,        via: 'window.GSDevTools' },
];
```

Also add script tag pattern matching:
```javascript
const scriptPatterns = [
  { library: 'GSAP',          pattern: /gsap|GreenSock/i },
  { library: 'ScrollTrigger', pattern: /ScrollTrigger/i },
  { library: 'SplitText',     pattern: /SplitText/i },
  { library: 'MorphSVG',      pattern: /MorphSVG/i },
  { library: 'DrawSVG',       pattern: /DrawSVG/i },
  { library: 'Flip',          pattern: /Flip\./i },
  { library: 'Draggable',     pattern: /Draggable/i },
  { library: 'MotionPath',    pattern: /MotionPath/i },
  { library: 'CustomEase',    pattern: /CustomEase/i },
  // ... etc
];
```

**Output:** `evidence.libraries` now includes all detected plugins (e.g., `['GSAP', 'ScrollTrigger', 'SplitText', 'Flip', 'CustomEase']`)

### 2B. Extend `gsap-extractor.js` with plugin call classification

**File:** `scripts/quality/lib/gsap-extractor.js`
**Current:** Extracts raw `gsap.to/from/fromTo/set` and `timeline` calls.
**Add:**

1. **SplitText detection**: Look for `new SplitText(` or `SplitText.create(` patterns in JS bundles. Extract: target element, split type (`chars`, `words`, `lines`), wrapper class.
2. **Flip detection**: Look for `Flip.getState(`, `Flip.from(`, `Flip.to(` patterns. Extract: target, animation type.
3. **DrawSVG detection**: Look for `drawSVG:` property in `gsap.to/from/fromTo` vars. Extract: target, start/end values.
4. **MorphSVG detection**: Look for `morphSVG:` property. Extract: target, shape.
5. **MotionPath detection**: Look for `motionPath:` property. Extract: path, alignment.
6. **Draggable detection**: Look for `Draggable.create(` pattern. Extract: target, bounds, type.
7. **CustomEase detection**: Look for `CustomEase.create(` pattern. Extract: name, curve.
8. **ScrollSmoother detection**: Look for `ScrollSmoother.create(` pattern.
9. **Observer detection**: Look for `Observer.create(` pattern.

**Output format extension:**
```javascript
{
  gsapCalls: [...],  // existing
  pluginUsage: {
    SplitText: [{ target: '.hero-title', type: 'chars', count: 3 }],
    Flip: [{ method: 'from', target: '.card-grid' }],
    DrawSVG: [{ target: '.logo-stroke', from: '0%', to: '100%' }],
    CustomEase: [{ name: 'smoothStep', curve: 'M0,0 C0.4,0 0.2,1 1,1' }],
    // ...
  }
}
```

### 2C. Extend `pattern-identifier.js` with plugin pattern matching

**File:** `scripts/quality/lib/pattern-identifier.js`
**Current:** Matches animation intents against registry. Doesn't know about specific plugins.
**Add:** `matchPluginPatterns(animationAnalysis)` function that:
1. Reads `pluginUsage` from the enhanced extraction
2. Maps each plugin to semantic capabilities:
   - `SplitText` → intent: `character-reveal`, `word-reveal`, `line-reveal`
   - `Flip` → intent: `layout-transition`, `state-change`
   - `DrawSVG` → intent: `svg-draw`, `stroke-reveal`
   - `MorphSVG` → intent: `shape-morph`
   - `MotionPath` → intent: `path-follow`, `orbit`
   - `Draggable` → intent: `drag-interaction`
   - `CustomEase` → extracts actual curves for preset
   - `ScrollSmoother` → flags for smooth-scroll setup
3. Generates gap entries when plugins are detected but we lack matching components

**Output:** Identification result now includes `detectedPlugins` array and `pluginCapabilities` map.

### 2D. Add GSAP plugin detection test fixtures

**File:** `scripts/quality/fixtures/gsap-plugin-extraction.json` (new)
**Content:** Synthetic extraction data with SplitText, Flip, DrawSVG, MorphSVG, CustomEase calls.
**Add tests to:** `test-pattern-pipeline.js` — verify plugin detection and classification.

**Phase 2 success criteria:**
- [ ] `animation-detector.js` detects all 20 GSAP plugins on window globals
- [ ] `gsap-extractor.js` classifies calls by plugin (SplitText, Flip, DrawSVG, etc.)
- [ ] `pattern-identifier.js` maps plugins to semantic capabilities
- [ ] Test harness validates plugin detection with fixtures
- [ ] Running against gsap.com detects: GSAP, ScrollTrigger, SplitText (at minimum)

---

## Phase 3: GSAP Knowledge Base

**Goal:** Teach the system how to use every GSAP plugin.
**Effort:** 6-8 hours
**Files:** `animation-patterns.md`, `section-instructions-gsap.md`, `animation-components/` (new components)
**Depends on:** Phase 2 (detection tells us what's needed)

### 3A. Expand `animation-patterns.md` with all GSAP plugins

**File:** `skills/animation-patterns.md`
**Add sections for each plugin with:**
- Pattern name, description
- Import / registration code
- Usage examples (2-3 per plugin)
- Section archetype recommendations
- Performance notes

**Plugins to document:**

| Plugin | Patterns to Add |
|--------|----------------|
| SplitText | `splittext-chars-stagger`, `splittext-words-wave`, `splittext-lines-reveal` |
| ScrambleText | `scramble-reveal`, `scramble-hover` |
| Flip | `flip-layout-transition`, `flip-filter-grid`, `flip-expand-card` |
| DrawSVG | `drawsvg-logo-reveal`, `drawsvg-icon-animate`, `drawsvg-path-progress` |
| MorphSVG | `morphsvg-shape-shift`, `morphsvg-icon-morph` |
| MotionPath | `motionpath-orbit`, `motionpath-flow`, `motionpath-follow-scroll` |
| Draggable | `draggable-carousel`, `draggable-slider`, `draggable-sort` |
| Observer | `observer-swipe-nav`, `observer-scroll-velocity` |
| ScrollSmoother | `scrollsmoother-setup`, `scrollsmoother-parallax` |
| ScrollTo | `scrollto-anchor`, `scrollto-section` |
| CustomEase | `custom-ease-brand`, `custom-ease-elastic-brand` |
| EasePack | `ease-rough`, `ease-slow-mo`, `ease-expo-scale` |
| matchMedia | `matchmedia-responsive-animation`, `matchmedia-mobile-reduce` |

### 3B. Expand `section-instructions-gsap.md` with plugin instructions

**File:** `templates/section-instructions-gsap.md`
**Current:** Only covers `gsap.to/from/fromTo`, `timeline`, `ScrollTrigger`, basic eases.
**Add:**

1. **SplitText section**: How to split text, animate chars/words/lines, revert for cleanup
2. **Flip section**: How to capture state, animate layout changes, use with filters/tabs
3. **DrawSVG section**: How to animate stroke drawing with ScrollTrigger
4. **MorphSVG section**: How to morph between shapes
5. **MotionPath section**: How to animate elements along paths
6. **matchMedia section**: How to make animations responsive (reduce on mobile, disable on prefers-reduced-motion)
7. **CustomEase section**: How to create and register custom easing curves
8. **Plugin registration pattern**: `gsap.registerPlugin(ScrollTrigger, SplitText, Flip)`
9. **Import pattern for Next.js**: Dynamic imports, client-only registration
10. **SSR safety rules**: Which plugins are safe in SSR, which need `"use client"` + useEffect

### 3C. Create GSAP plugin animation components

**Directory:** `skills/animation-components/` (new files in appropriate subdirectories)

| Component | Category | Plugin | Description |
|-----------|----------|--------|-------------|
| `splittext-chars.tsx` | text/ | SplitText | Character-by-character reveal with stagger |
| `splittext-words.tsx` | text/ | SplitText | Word-by-word reveal with wave effect |
| `splittext-lines.tsx` | text/ | SplitText | Line-by-line reveal with mask |
| `scramble-text.tsx` | text/ | ScrambleText | Random character scramble to final text |
| `flip-grid-filter.tsx` | interactive/ | Flip | Animated grid filtering (tabs → layout change) |
| `flip-expand-card.tsx` | interactive/ | Flip | Card expand to full detail view |
| `drawsvg-reveal.tsx` | entrance/ | DrawSVG | SVG stroke drawing on scroll |
| `morphsvg-icon.tsx` | interactive/ | MorphSVG | Icon shape morphing on hover/state |
| `motionpath-orbit.tsx` | continuous/ | MotionPath | Element orbiting along SVG path |
| `draggable-carousel.tsx` | interactive/ | Draggable | Touch-friendly draggable carousel |
| `observer-swipe.tsx` | interactive/ | Observer | Swipe gesture detection for mobile nav |

Each component must:
- Import and register the correct GSAP plugin
- Be `"use client"` with useEffect + context cleanup
- Include `prefers-reduced-motion` handling
- Follow the existing component template (props interface, default export)
- Work standalone — no external dependencies beyond GSAP

### 3D. Update animation registry

**After creating new components, run:**
```bash
node scripts/quality/build-animation-registry.js
```
This regenerates `animation_registry.json`, `animation_search_index.json`, `animation_taxonomy.json` to include the new plugin components.

**Phase 3 success criteria:**
- [ ] `animation-patterns.md` documents 30+ patterns (up from ~20) covering all major plugins
- [ ] `section-instructions-gsap.md` teaches Claude about SplitText, Flip, DrawSVG, MorphSVG, MotionPath, matchMedia, CustomEase
- [ ] 11 new animation components created and working
- [ ] Animation registry regenerated with new components
- [ ] Test: ask Claude to generate a hero with SplitText — should produce correct plugin usage

---

## Phase 4: GSAP Plugin Injection

**Goal:** Wire detected plugins into the generation pipeline so Claude uses them.
**Effort:** 4-6 hours
**Files:** `animation-injector.js`, `orchestrate.py`, `url-to-preset.js`
**Depends on:** Phase 2 (detection) + Phase 3 (knowledge)

### 4A. Extend `animation-injector.js` with plugin-aware blocks

**File:** `scripts/quality/lib/animation-injector.js`
**Current:** Generates animation context blocks based on engine + intensity + library components.
**Add:**

1. **Plugin context block**: When `identification.detectedPlugins` includes a plugin, generate a prompt block:
   ```
   ═══ GSAP PLUGIN CONTEXT ═══
   Detected plugins: SplitText, Flip, CustomEase
   
   SplitText: Used for character-level text animations.
   Import: import { SplitText } from "gsap/SplitText"
   Register: gsap.registerPlugin(SplitText)
   Usage: const split = new SplitText(el, { type: "chars" });
          gsap.from(split.chars, { opacity: 0, y: 20, stagger: 0.03 });
   Cleanup: split.revert() in useEffect return
   
   Flip: Used for layout transition animations.
   Import: import { Flip } from "gsap/Flip"
   ...
   ═══════════════════════════
   ```

2. **Per-section plugin recommendations**: Map detected plugins to section archetypes:
   - SplitText → HERO (character-reveal headline), TESTIMONIALS (quote reveals)
   - Flip → PRODUCT-SHOWCASE (filter tabs), GALLERY (layout transitions)
   - DrawSVG → HERO (logo reveal), HOW-IT-WORKS (step indicators)
   - MotionPath → HERO (background elements), FEATURES (icon animations)

### 4B. Update `orchestrate.py` stage_deploy with plugin dependencies

**File:** `scripts/orchestrate.py` (stage_deploy, deps section)
**Current:** Adds `gsap` and `@gsap/react` when engine is gsap.
**Add:** Read `identification.detectedPlugins` and add per-plugin npm packages.

GSAP plugins are now included in the main `gsap` package (since GSAP went free), so no additional npm packages are needed. However, we need to:
1. Generate correct imports in section files (not just `gsap` but `gsap/SplitText`, `gsap/Flip`, etc.)
2. Add plugin registration to `layout.tsx` or a `gsap-setup.ts` utility file
3. Ensure `next.config.ts` has `transpilePackages: ['gsap']` if needed

### 4C. Update `url-to-preset.js` with plugin-aware preset generation

**File:** `scripts/quality/url-to-preset.js`
**Current:** Claude prompt mentions animation engine and intensity.
**Add:** Include detected plugins in the Claude prompt so presets can specify:
```yaml
gsap_plugins:
  - SplitText    # character/word/line text animations
  - Flip         # layout transitions
  - CustomEase   # brand-specific easing curves
section_overrides:
  hero: character-reveal(SplitText)
  showcase: flip-filter-grid(Flip)
  features: drawsvg-icons(DrawSVG)
```

### 4D. Update token budgets for plugin-heavy sections

**File:** `scripts/quality/lib/animation-injector.js` (dynamic budget calculation)
**Current:** Increases budget for component injection and complex GSAP.
**Add:** +2048 tokens when a section uses SplitText or Flip (these require setup code). NAV/FOOTER always 6144 minimum.

**Phase 4 success criteria:**
- [ ] Plugin context blocks injected into section prompts when plugins detected
- [ ] Section generation produces correct `import { SplitText } from "gsap/SplitText"` imports
- [ ] Presets include `gsap_plugins` field listing detected plugins
- [ ] Token budgets increase for plugin-heavy sections
- [ ] Test: Full pipeline with gsap.com → hero uses SplitText, not manual text splitting

---

## Phase 5: Build Reliability

**Goal:** Eliminate build failures through validation at every stage.
**Effort:** 4-6 hours
**Files:** `post-process.js`, `orchestrate.py`, `validate-build.js`
**Depends on:** Phase 1 (basic fixes), can run in parallel with Phases 3-4

### 5A. JSX truncation detection + repair in `post-process.js`

**File:** `scripts/quality/lib/post-process.js`
**Add:** `validateAndRepairJSX(code, sectionName)` function:

1. **Detection**: Check for `export default`, balanced JSX tags, balanced braces/brackets
2. **Auto-repair**:
   - Missing `export default` → add at end
   - Unclosed tags → close from innermost out
   - Missing closing braces → add matching count
   - Unclosed string → close with `"`
3. **Flag**: If repair changes >20 characters, flag section for manual review or regeneration
4. Wire into `orchestrate.py` after each section generation (before saving to disk)

### 5B. Pre-flight build validation in `orchestrate.py`

**File:** `scripts/orchestrate.py` (new function `stage_validate`)
**Add Stage 5.5** between assembly and deploy:

```python
def stage_validate(project_dir: Path) -> dict:
    """Validate all sections before deployment."""
    issues = []
    
    # 1. Check all section files exist and have content
    # 2. Check all sections have "use client" directive
    # 3. Check all sections have export default
    # 4. Check layout.tsx has valid font imports (not YAML)
    # 5. Check globals.css has valid CSS (no YAML)
    # 6. Run JSX balance check on each section
    # 7. Check page.tsx imports match actual section files
    
    return { 'passed': len(issues) == 0, 'issues': issues }
```

If validation fails, print issues and ask whether to continue or abort.

### 5C. Post-deploy visual verification

**File:** `scripts/quality/validate-build.js` (extend existing)
**Add:** After `vercel --yes`, automatically:
1. Fetch the preview URL
2. Check HTTP 200 response
3. Check page has >0 visible text nodes (basic check against blank page)
4. Report any console errors from the deployed page
5. Optional: take a screenshot for manual review

### 5D. Component copy validation

**File:** `scripts/orchestrate.py` (stage_deploy, after component copy)
**Add:** After copying animation components to `src/components/animations/`:
1. Check each file has valid exports
2. Check imports reference only installed packages
3. Flag files that import from `motion/react` instead of `framer-motion`
4. Flag files that import from `@/lib/utils` (ensure `utils.ts` exists)

**Phase 5 success criteria:**
- [ ] Truncated sections detected before assembly (not at Vercel build time)
- [ ] Invalid layout.tsx / globals.css caught before deployment
- [ ] Component copy validates exports and imports
- [ ] Post-deploy check confirms site is accessible and renders
- [ ] Zero "Expected '</', got '<eof>'" errors on Vercel

---

## Implementation Order

```
Week 1: Phase 1 (bug fixes) + Phase 5A-5B (JSX repair, pre-flight validation)
         ↓ builds are now reliable
Week 1: Phase 2 (detection) — can start in parallel with Phase 1 fixes
         ↓ system knows what GSAP plugins sites use
Week 2: Phase 3 (knowledge base) — can start once detection shape is clear
         ↓ system knows how to use all plugins
Week 2: Phase 4 (injection wiring) — needs Phase 2 + 3
         ↓ generated sections use detected plugins
Week 2: Phase 5C-5D (post-deploy validation) — can run any time
         ↓ builds verified end-to-end
```

Phases 1 + 5A-5B are **independent** and should be done first — they make everything else testable.
Phases 2 + 3 are **partially independent** — detection (2) and documentation (3) can overlap.
Phase 4 is the **integration phase** — it needs 2 + 3 to be mostly complete.

---

## Test Strategy

### Unit tests (add to `test-pattern-pipeline.js`)
- Plugin detection: feed fixture with SplitText/Flip globals → assert detection
- Plugin call classification: feed JS with `new SplitText(` → assert `pluginUsage.SplitText`
- Plugin pattern matching: detected SplitText → assert `character-reveal` intent
- JSX truncation detection: feed truncated JSX → assert detection
- JSX repair: feed common truncation patterns → assert valid output

### Integration tests (live validation)
- Run full pipeline against gsap.com with all phases → verify:
  - SplitText detected
  - Hero section uses SplitText import
  - No truncated sections
  - Vercel build succeeds
  - Sections visible on deployed site

### Stress tests (new sites)
- Portfolio site heavy on Flip transitions
- SVG-heavy site with DrawSVG/MorphSVG
- SaaS with matchMedia responsive animations

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GSAP plugins not on window globals (bundled/tree-shaken) | High | Plugin detection fails | Script tag pattern matching + JS bundle scanning as fallback |
| SplitText requires paid GSAP (pre-2024) | Low | Won't install | GSAP is now free for everyone (Webflow sponsorship). All plugins included in `gsap` npm package. |
| Claude generates incorrect plugin usage | Medium | Build errors | Provide explicit import/register/usage examples in prompt context block |
| New components have TypeScript errors | Medium | Build failures | Add `tsc --noEmit` validation step after component creation |
| Token budget overflows with plugin context | Low | Truncation | Cap plugin context block at 500 tokens, prioritize most-used plugins |

---

## Success Criteria (v1.0.0)

- [ ] All 8 active bugs fixed
- [ ] GSAP coverage: 38% → 85%+ (34+ of 40 features)
- [ ] gsap.com build uses SplitText for hero text, not manual splitting
- [ ] gsap.com build has visible sections on deploy (no from() invisibility)
- [ ] gsap.com build includes per-section accent colors (multi-accent system)
- [ ] Zero Vercel build failures from truncated JSX
- [ ] Pre-flight validation catches invalid sections before deployment
- [ ] 11+ new animation components in the library (GSAP plugin-based)
- [ ] Animation registry regenerated with plugin components
- [ ] Test harness: 80+ assertions (up from 57) covering all new functionality

---

## Maintenance Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-11 | Plan created from retro analysis + GSAP audit | system |

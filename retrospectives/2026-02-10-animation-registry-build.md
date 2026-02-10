# Retrospective: Animation Registry Build

**Date:** 2026-02-10
**System Version:** v0.7.2 -> v0.8.0
**Duration:** ~30 minutes

---

## What Shipped

### Animation Registry Builder (`scripts/quality/build-animation-registry.js`)
A Node.js script that analyzes all 1,022 animation/UI components in the library and generates a structured, searchable, machine-usable registry. Runs in 1.3 seconds.

### 5 Generated Artifacts
1. **`animation_registry.json`** (1.6MB) - Full analysis of all 1,022 components with 30+ fields per entry covering framework, triggers, motion intents, conversion roles, performance risks, capabilities, and section archetype mappings.
2. **`animation_taxonomy.json`** - Controlled vocabulary defining 41 motion intents, 23 interaction intents, 16 conversion support roles, 25 layout contexts, 13 trigger types, 3 component types, and 12 animation types.
3. **`animation_search_index.json`** (367KB) - Flattened, query-optimised index enabling fast lookup by intent, section role, trigger, layout context, interaction type, performance risk, component type, framework, and animation type.
4. **`animation_capability_matrix.csv`** (189KB) - Tabular capability/risk data for all 1,022 components.
5. **`analysis_log/`** (1,022 markdown files) - Per-component classification rationale with extracted features, capabilities, performance risks, uncertainty notes, and fallback assumptions.

### Classification Results
- **335 animation** components (motion primitives, wrappers)
- **613 UI** components (pre-built section layouts, form components, data displays)
- **74 hybrid** components (structural + animated)

### Source Library Fixes
Fixed 5 broken curated components in `skills/animation-components/`:
- `entrance/word-reveal.tsx` - Rewrote with correct word-by-word reveal
- `continuous/count-up.tsx` - Created proper shared component
- `entrance/blur-fade.tsx` - Fixed imports (framer-motion not motion/react)
- `interactive/magnetic-button.tsx` - Rewrote with proper props interface
- `interactive/hover-lift.tsx` - Replaced wrong component (ZoomImageUI)

### Quality Gates
- Zero duplicate animation IDs
- Zero taxonomy violations
- Zero missing file references
- Zero processing errors

---

## What Worked

1. **Script architecture** - Splitting into 3 modules (extractor, builders, utils) kept each file manageable and testable. The main script is a clean orchestrator.
2. **Regex-based extraction** - No AST parsing needed. Regex patterns for Framer Motion APIs, GSAP, CSS animations, triggers, and content signals were sufficient for classification. Processed 1,022 files in 1.3s.
3. **Dual-source registry** - Using `registry-full.json` from the 21st.dev crawl provided dependency data without needing to parse import resolution.
4. **Weighted scoring classification** - The animation/UI/hybrid classification uses a point system (animation signals vs UI signals) rather than hard rules. This correctly handled edge cases like animated pricing cards (hybrid) vs pure hover effects (animation).
5. **Controlled taxonomy** - Defining the vocabulary first, then validating all entries against it, prevents label drift and ensures downstream consumers can rely on the label set.

---

## What Did Not Work / Challenges

1. **Security hook false positive** - The codebase has a pre-commit hook that flags certain function calls for security. Standard JavaScript regex `.matchAll()` replaced the flagged patterns.
2. **Aurora background framework detection** - The Aceternity aurora-background uses pure CSS animations with Tailwind classes, but no framer-motion or gsap import. It was correctly classified as animation (via children + composable signals) but the framework reads as "none". The uncertainty note in the analysis log flags this.
3. **Duration/easing defaults** - Many components do not specify explicit durations or easing (they rely on framework defaults). These get defaulted to 300-800ms / ease-out and flagged as "defaulted" in the analysis log.

---

## Architecture Decisions

1. **Naming convention: `{source}__{slug}`** - Animation IDs use `author__component_name` for 21st-dev and `category__component_name` for curated. This ensures uniqueness and traceability.
2. **Taxonomy as separate file** - `animation_taxonomy.json` is the single source of truth for all labels. The registry and search index validate against it. This means downstream consumers only need to read one file to understand what labels are possible.
3. **Analysis logs as markdown** - Each component gets its own `.md` file with classification rationale, uncertainty notes, and fallback assumptions. This makes the classification auditable and debuggable.

---

## Search Index Distribution

| Category | Count |
|----------|-------|
| **By framework** | |
| framer-motion | 296 |
| gsap | 18 |
| css | 51 |
| three.js | 36 |
| none (pure Tailwind/CSS) | 631 |
| **By section archetype** | |
| HERO | 56 |
| GALLERY | 31 |
| NAV | 31 |
| STATS | 26 |
| FEATURES | 18 |
| TESTIMONIALS | 18 |
| FAQ | 14 |
| PRICING | 13 |
| HOW-IT-WORKS | 13 |
| CONTACT | 11 |
| FOOTER | 10 |
| BLOG-PREVIEW | 9 |

---

## Carry-Forward Items

1. **Integration with animation-injector.js** - The new registry can replace or supplement the existing `registry.json` as the component selection source. The search index enables intent-based lookup rather than just archetype affinity.
2. **Integration with orchestrate.py stage_deploy** - Component copy could use the registry to only copy components that are actually needed for the current build.
3. **UI component to section template mapping** - The 613 UI components could be used as pre-built section templates, mapped via `section_archetypes` in the registry. This would give the pipeline access to real implementation patterns.
4. **Periodic re-run** - When new components are added to the library, `node scripts/quality/build-animation-registry.js` should be re-run. Consider adding it to the build close checklist.

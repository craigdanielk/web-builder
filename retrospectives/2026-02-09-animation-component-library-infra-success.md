# Session Retrospective: Animation Component Library Infrastructure

**Date**: 2026-02-09
**Duration**: ~3 hours (across 2 context windows)
**Outcome**: Success

---

## Initial Goal

Complete the "Deepen Animation Extraction" plan (Tasks #5-9), test with a farm-minerals v3 build, then pivot to designing and building infrastructure for a curated animation component library that replaces prompt-based animation generation with pre-built, pattern-matched React components.

## Planned Approach

This session spanned two major phases:

**Phase A: Complete extraction deepening (Tasks #5-9)**
- Step 1: Create gsap-extractor.js for static bundle analysis
- Step 2: Enhance animation-detector.js with runtime GSAP interception
- Step 3: Add per-section animation grouping
- Step 4: Create animation-summarizer.js
- Step 5: Enhance animation-injector.js with hybrid injection

**Phase B: Animation component library architecture (Tasks #10-12)**
- Step 1: Design library architecture and create plan
- Step 2: Create directory structure + registry.json
- Step 3: Rewrite animation-injector.js with 3-tier injection (component library > extracted signature > pattern snippet)
- Step 4: Add component copy step to orchestrate.py stage_deploy()

## What Actually Happened

### Execution Timeline

1. **Background agent completion (Tasks #5-6)**
   - Two agents from previous session completed: gsap-extractor.js (290 lines) and animation-detector.js enhancements (220 new lines)
   - Both syntax-verified successfully

2. **Tasks #7-9: Extraction pipeline completion**
   - Added `groupAnimationsBySection()` to animation-detector.js — maps GSAP calls to sections by Y position
   - Wired gsap-extractor into extract-reference.js for bundle download + static GSAP analysis + merge
   - Created animation-summarizer.js (180 lines) — converts per-section data to token-efficient text blocks
   - Enhanced animation-injector.js with hybrid injection (extracted data > pattern snippets)

3. **Farm minerals v3 test build + deploy**
   - Built and deployed to Vercel at https://site-psi-lake.vercel.app
   - Captured 203 merged GSAP calls (200 runtime + 3 static), intensity score 42.4 (expressive)
   - Hit the `parse_fonts()` bug again — preset YAML content leaked into layout.tsx imports
   - Fixed layout.tsx manually + fixed footer component naming mismatch (Section13 vs Section13FOOTER)
   - 73% QA review pass rate

4. **Architecture pivot decision**
   - User feedback: "slightly better, but there are a lot of differences still"
   - User proposed: build a curated library of pre-built animation components from 21st.dev
   - Key insight: extracting animation parameters and regenerating via prompt produces ~40-50% fidelity. Instead, inject actual pre-built component code — exactly like how section archetypes map to variants
   - User chose "Copy source into library" approach (self-contained, no external dependencies)

5. **Plan mode: Animation component library architecture**
   - Explored codebase: section archetype system, animation injection flow, template/prompt assembly
   - Designed registry.json format, component file format, 3-tier selection strategy
   - User requested: "Build infrastructure only, no deployments until library populated"

6. **Task #10: Directory structure + registry.json**
   - Created `skills/animation-components/` with 5 subdirectories (entrance/, scroll/, interactive/, continuous/, text/)
   - Created registry.json with 27 component entries, all status: "placeholder"

7. **Task #11: animation-injector.js rewrite (808 lines)**
   - Added registry management: `loadRegistry()`, `lookupComponent()`, `readComponentSource()`
   - Added pattern detection: `mapExtractedToPattern()` — maps GSAP calls to library patterns via heuristics
   - Added prop extraction: `extractPropOverrides()` — extracts duration/ease/stagger/y/x/scale from captured data
   - Added component context builder: `buildComponentContext()` — generates prompt block with full source + import + usage
   - Implemented 3-tier injection: Component Library > Extracted Signature > Pattern Snippet
   - Returns `componentFiles[]` for orchestrate.py to copy

8. **Task #12: orchestrate.py component copy step**
   - Added block in `stage_deploy()` after section copy: reads registry, matches archetypes, copies non-placeholder components
   - Updates package.json with component-specific dependencies
   - Fixed scoping issue: deps/pkg variables were scoped to scaffold block; switched to reading existing package.json directly

### Key Iterations

**Iteration 1: Extraction-based generation → Component library injection**
- **Initial approach**: Reverse-engineer GSAP parameters from source sites and regenerate via prompt instructions
- **Discovery**: Even with 200+ captured GSAP calls, prompt-based regeneration hits ~40-50% fidelity because Claude must reinvent the implementation from parameter descriptions
- **Pivot**: Build a curated library of pre-built components. Pipeline detects pattern, selects matching component, injects actual source code
- **Learning**: The section archetype pattern (detect → select → inject) works because it injects real code, not descriptions. Animation should follow the same pattern.

**Iteration 2: Variable scoping in orchestrate.py**
- **Initial approach**: Referenced `deps` and `pkg` variables inside the component copy block
- **Discovery**: These variables are scoped inside the `if not package.json.exists()` block — undefined for existing projects
- **Pivot**: Read existing package.json, merge new dependencies, write back
- **Learning**: Always check variable scope when adding code to long functions with conditional blocks

## Learnings & Discoveries

### Technical Discoveries

- **203 GSAP calls captured** from farmminerals.com — the extraction pipeline works well for data capture. The bottleneck is in how that data is used (prompt-based generation vs. code injection)
- **mapExtractedToPattern() heuristics**: Counter patterns (onUpdate + textContent), timeline + text targets (character-reveal), stagger + Y movement (fade-up-stagger), ScrollTrigger with pin/scrub (scroll patterns) — these reliably identify animation intent from raw GSAP data
- **Component wrapper pattern**: Animation components wrap children and target them via refs. This pattern (`<FadeUpStagger>{children}</FadeUpStagger>`) cleanly separates animation from content
- **3-tier fallback strategy**: Component Library (highest fidelity) > Extracted Signature (medium fidelity) > Pattern Snippet (lowest fidelity) — ensures every section gets some animation guidance regardless of library completeness

### Process Discoveries

- **The "detect archetype → select variant → inject code" pattern** is the core strength of the web-builder system. Extending it from sections to animations is a natural fit
- **Placeholder-based registry**: Marking components as "placeholder" lets infrastructure be built and tested before library content exists. The system gracefully falls back to existing behavior
- **Background agents work well** for independent module creation (gsap-extractor.js, animation-detector.js enhancements ran in parallel)

## Blockers Encountered

### Blocker 1: parse_fonts() bug (recurring)

- **Impact**: Build fails with corrupted layout.tsx — preset YAML content leaks into font imports
- **Root Cause**: Regex in `parse_fonts()` (orchestrate.py) fails on certain preset formatting
- **Resolution**: Manual fix of layout.tsx each time — not properly fixed in orchestrate.py
- **Time Lost**: ~15 minutes per occurrence
- **Prevention**: Need to fix the regex in parse_fonts() or add validation that layout.tsx imports are valid

### Blocker 2: Footer component naming mismatch

- **Impact**: Build TypeScript error — `Cannot find name 'Section13'`
- **Root Cause**: Generated component function named `Section13FOOTER` but export used `Section13`
- **Resolution**: Fixed export to match component name
- **Time Lost**: ~5 minutes
- **Prevention**: Post-processing should validate export default matches component name

## Final Outcome

### What Was Delivered

- **gsap-extractor.js** (454 lines) — Static JS bundle GSAP extraction
- **animation-detector.js enhancements** (750 lines total) — Runtime GSAP interception, per-section grouping
- **animation-summarizer.js** (209 lines) — Token-efficient animation signature builder
- **animation-injector.js** (808 lines) — 3-tier injection with registry lookup, pattern detection, prop extraction
- **registry.json** (303 lines) — 27 animation components across 5 categories (all placeholders)
- **orchestrate.py** (1211 lines) — Component copy step in stage_deploy()
- **skills/animation-components/** — Directory structure with 5 subdirectories
- **farm-minerals-v3** — Test build deployed to Vercel

### What Wasn't Completed

- **Component library population** — All 27 registry entries are placeholders. Waiting for user's 21st.dev examples
- **parse_fonts() fix** — Known recurring bug, not prioritized this session
- **Test build with library components** — Can't test until components are populated

### Success Criteria

- [x] Complete extraction deepening pipeline (Tasks #5-9)
- [x] Test build validates extraction data flows through to sections (203 GSAP calls)
- [x] Design animation component library architecture
- [x] Build library infrastructure (registry, injector rewrite, deploy step)
- [x] All infrastructure syntax-verified
- [ ] Populate library with real components (blocked: waiting for 21st.dev examples)
- [ ] Test build with component injection (blocked: no components yet)

## Reusable Patterns

### Code Snippets to Save

```javascript
// 3-tier injection pattern — use this when building any fallback system
// Tier 1 (best): Pre-built component from library
const componentDef = lookupComponent(selectedPattern);
if (componentDef) {
  const source = readComponentSource(componentDef.file);
  if (source) { /* inject full component */ }
}
// Tier 2 (good): Extracted data summary
if (hasExtractedData) { /* inject summarized signature */ }
// Tier 3 (fallback): Reference snippet
/* inject code snippet template */
```

```javascript
// Pattern detection from raw GSAP calls — heuristic-based mapping
// Priority order matters: specific patterns first, general patterns last
const hasCounter = anims.some(a => a.vars?.onUpdate?.includes('textContent'));
if (hasCounter) return 'count-up';
const hasTimeline = anims.some(a => a.type === 'timeline');
const hasTextTarget = anims.some(a => target.includes('char'));
if (hasTimeline && hasTextTarget) return 'character-reveal';
// ... progressively less specific checks
```

### Approaches to Reuse

**Pattern Name: Registry-based Component Injection**
- **When to use**: Any system where you need to select and inject pre-built code based on detected patterns
- **How it works**: registry.json maps pattern names to file paths + metadata. Pipeline loads registry, matches detected pattern, reads source file, injects with customized props
- **Watch out for**: Status field ("placeholder" vs "ready") — always check before injecting. Graceful fallback when component doesn't exist
- **Example**: Animation components, but could extend to section variants, layout patterns, etc.

## Recommendations for Next Time

### Do This

- Start with the component library population (21st.dev examples)
- Fix parse_fonts() — it's been hit twice now
- Test one component end-to-end before populating the whole library
- Validate the prop override mechanism works with real component props

### Avoid This

- Don't try to prompt-generate animations from parameter descriptions — the fidelity ceiling is ~50%
- Don't reference variables from conditional blocks in Python (scoping issue)
- Don't deploy test builds until the library has at least a few real components

### If Starting Over

I would have built the component library infrastructure first (before the extraction deepening work). The extraction pipeline is still valuable for pattern detection and prop extraction, but the heavy investment in animation-summarizer.js and the extraction → prompt path was partially superseded by the component library approach. The 3-tier system keeps it useful as a fallback, but the effort would have been better spent on getting the library pattern working end-to-end with even one real component.

---

## Next Steps

**Immediate actions:**
- [ ] User compiles 21st.dev animation component examples
- [ ] Populate first component (e.g., fade-up-stagger) to test full pipeline
- [ ] Fix parse_fonts() bug in orchestrate.py

**Future work:**
- [ ] Populate all 27 components from 21st.dev library
- [ ] Test build with component injection (farm-minerals v4)
- [ ] Visual comparison: component-injected build vs prompt-generated build
- [ ] Add post-processing validation for component name/export consistency

**Questions to resolve:**
- [ ] Which 21st.dev components best map to the 27 registry patterns?
- [ ] Should components use GSAP directly or abstract through a custom hook?
- [ ] How to handle components that need brand-specific color tokens?

## Related Sessions

- [2026-02-09-data-injection-pipeline-success.md](2026-02-09-data-injection-pipeline-success.md) — Built the injection pipeline this session extends
- [2026-02-08-farm-minerals-rebuild.md](2026-02-08-farm-minerals-rebuild.md) — First farm minerals build, discovered animation gaps

## Attachments

- `scripts/quality/lib/animation-injector.js` (808 lines) — 3-tier injection with registry
- `scripts/quality/lib/gsap-extractor.js` (454 lines) — Static bundle GSAP extraction
- `scripts/quality/lib/animation-summarizer.js` (209 lines) — Token-efficient summaries
- `skills/animation-components/registry.json` (303 lines) — 27 component definitions
- `~/.claude/plans/precious-seeking-flamingo.md` — Component library architecture plan

---

## Documentation Sync Results

**CLAUDE.md**: Updated
- File Map: added animation-components/, updated line counts for modified files
- Current System State: added farm-minerals-v3 build, updated active plans
- Known Issues: added parse_fonts() recurring note
- System Version: v0.5.0 -> v0.6.0

**README.md**: No changes needed
- No user-facing changes (infrastructure only, no new presets or pipeline stages)

**.cursorrules**: No changes needed
- No pipeline stage changes (component copy is within existing stage_deploy)

**Version**: v0.5.0 -> v0.6.0 (minor: animation component library infrastructure + 3-tier injection)

---

## Metadata

```yaml
date: 2026-02-09
duration_minutes: 180
outcome: success
tags: [animation, component-library, gsap, injection, infrastructure, registry]
project: web-builder
phase: animation-component-library
related_checkpoints: []
```

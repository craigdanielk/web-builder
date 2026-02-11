# Session Retrospective: GSAP Homepage Stress Test & Pipeline Diagnosis

**Date**: 2026-02-10
**Duration**: ~90 minutes
**Outcome**: Partial — Build deployed successfully, but exposed systemic pipeline gaps that led to comprehensive plan

---

## Initial Goal

Build a clone of the GSAP homepage (https://gsap.com/) to stress test the pipeline's ability to correctly identify and integrate features from a complex, animation-heavy site. The GSAP site is uniquely challenging because it's an animation library's own marketing page — the entire site IS a demonstration of advanced GSAP capabilities.

## Planned Approach

1. Run URL extraction pipeline (`url-to-preset.js` + `url-to-brief.js`)
2. Review and correct the extracted preset/brief
3. Run the full orchestrated pipeline (`orchestrate.py --deploy --no-pause`)
4. Deploy to Vercel
5. Evaluate output against the source site

## What Actually Happened

### Execution Timeline

1. **URL Extraction** (~2 min)
   - `url-to-preset.js` extracted 428 DOM elements, 94 GSAP calls from 5 JS bundles, 6 visual sections
   - `url-to-brief.js` generated a comprehensive brief with correct technical context
   - Extraction correctly identified GSAP + ScrollTrigger as libraries, `expressive` animation intensity
   - Font mapped as "Mori" (proprietary — needed manual correction to Inter)

2. **Preset/Brief Review** (~5 min)
   - Section sequence was only 6 entries with 4 repeated `FEATURES | icon-grid` — too sparse
   - Manually expanded to 10 sections with correct archetypes (NAV, HERO, FEATURES, PRODUCT-SHOWCASE, TRUST-BADGES, GALLERY, HOW-IT-WORKS, CTA, FOOTER)
   - Fixed font mapping from Mori → Inter
   - Left color palette as-is (mistake — should have caught the single-accent problem here)

3. **Pipeline Execution** (~9 min)
   - Hit `python` not found error (macOS), switched to `python3`
   - Hit "project already exists" error (extraction had created output directory), cleaned up
   - Scaffold generated 12 sections (pipeline expanded our 10 to 12)
   - All 12 sections generated successfully
   - 31 animation components automatically copied from library
   - npm install succeeded

4. **Build Fixes** (~5 min)
   - Two sections truncated by token limit: `07-gallery.tsx` (line 247 — unterminated string) and `12-footer.tsx` (line 289 — unterminated SVG)
   - Both fixed by closing the truncated JSX elements
   - Footer had "FRONTIER" branding instead of "GSAP" — fixed
   - Globals.css had light background (`#fafaf9`) instead of dark (`#000000`) — fixed
   - Inter font only loaded weight 700, needed 400/500/600/700 — fixed

5. **Deploy & Evaluation** (~10 min)
   - Built successfully on first try after fixes
   - Deployed to Vercel at `https://site-psi-lake.vercel.app`
   - User evaluated and identified critical issues:
     - Gallery cards only show brown SVG images with zoom, no actual animation demos
     - Only orange used — missing green/blue/purple/pink from actual site
     - Blank content areas under "GSAP Tools" and "What Can You Animate?" headings
     - Animations are generic scroll fades, not GSAP-specific demonstrations

6. **Diagnostic Deep Dive** (~30 min)
   - Analyzed extraction data: only 6 sections mapped, all middle ones as `FEATURES | icon-grid` at 30% confidence
   - Discovered `design-tokens.js` ignores gradient colors from `backgroundImages`
   - Discovered `archetype-mapper.js` completely ignores class names (`brands`, `showcase`, `home-tools`)
   - Discovered `hexToTailwindApprox()` maps all colors to gray shades (brightness-only, no hue detection)
   - Discovered `perSection` animation data was nearly empty despite 94 GSAP calls being extracted
   - Identified the gradient `linear-gradient(114.41deg, rgb(10, 228, 72)...)` was captured but never parsed

7. **Philosophical Reframe** (~15 min)
   - User corrected the framing: the goal isn't better extraction, it's **identification and mapping**
   - Raw CSS/DOM data is step 1 (valuable, keep it). What's missing is the interpretation layer
   - When a pattern can't be mapped to our library, that's a gap to be filled — not just a failed build
   - Every build should make the system better for the next one through gap detection and library extension
   - The system should **identify** what a site does → **map** to our capabilities → **detect gaps** → **extend** the library

8. **Plan Creation** (~15 min)
   - Wrote 678-line implementation plan: `plans/active/pattern-identification-mapping-pipeline.md`
   - 6 phases, 13 implementation steps, validation via GSAP rebuild

### Key Iteration

**Iteration 1: From "fix extraction" to "build identification layer"**
- **Initial approach**: The extraction data was thin, so the first instinct was to enhance extraction (capture more CSS, scan more elements, trigger scroll events)
- **Discovery**: The extraction actually captured the right data (gradient strings, class names, GSAP calls). The problem was that nothing INTERPRETED that data
- **Pivot**: Reframed the entire fix from "enhance extraction" to "add identification + mapping + gap detection layers between extraction and generation"
- **Learning**: The pipeline's fundamental architecture was missing a layer. Raw tokens → Claude prompt is too big a leap. Need: Raw tokens → Pattern identification → Library mapping → Gap report → Enriched prompt

---

## Learnings & Discoveries

### Technical Discoveries

- **`hexToTailwindApprox()` is fundamentally broken**: It uses brightness alone to map hex to Tailwind names. A bright green (`#0ae448`) maps to `gray-200` because it has high brightness. This means ANY non-gray color from ANY site gets its hue completely lost. This affects every URL-mode build
- **Archetype mapper ignores the strongest signal**: Class names (`home-hero`, `brands`, `showcase`, `home-tools`) are often the most reliable semantic indicators, yet the mapper doesn't read them at all. It falls through tag → role → heading keywords → fallback
- **Gradient data is captured but orphaned**: `extract-reference.js` dutifully captures background image gradients. `design-tokens.js` never reads them. `url-to-preset.js` never includes them in the Claude prompt. The green gradient that defines GSAP's Scroll section was sitting in the extraction data the whole time
- **Token truncation is still a real issue**: 2 of 12 sections were truncated mid-string. The post-processing in the pipeline should detect and repair these automatically
- **GSAP's own site is a worst-case for our pipeline**: Most visual richness is rendered via JavaScript, not static DOM. Canvas/WebGL elements, runtime-calculated animations, and dynamically loaded media mean the Playwright snapshot captures the skeleton but misses the flesh

### Process Discoveries

- **Stress testing with a known site is the best diagnostic tool**: By choosing a site we can visually compare against, every gap becomes immediately visible
- **The user's reframe was the breakthrough**: Moving from "fix extraction" to "build identification and mapping" changed the plan from a patch to a system upgrade
- **Raw extraction data is more valuable than initially apparent**: The data we need IS being captured in most cases. The failure is in interpretation, not collection
- **Manual preset review is still essential**: The expanded section sequence (from 6 to 10) was done manually. The pipeline should suggest this expansion when sections map at low confidence

---

## Blockers Encountered

### Blocker 1: `python` command not found on macOS

- **Impact**: 1 minute — quick fix
- **Root Cause**: macOS doesn't alias `python` to `python3` by default
- **Resolution**: Used `python3` directly
- **Prevention**: Update CLAUDE.md running instructions to use `python3`

### Blocker 2: "Project already exists" error

- **Impact**: 1 minute — quick fix
- **Root Cause**: `url-to-preset.js` creates `output/gsap-homepage/` for extraction data. Then `orchestrate.py` refuses to create the same directory
- **Resolution**: Deleted existing directory and re-ran
- **Prevention**: Pipeline should handle this gracefully (merge or use separate extraction dir)

### Blocker 3: Token truncation in 2 sections

- **Impact**: 5 minutes to diagnose and fix
- **Root Cause**: Gallery and Footer sections exceeded the 4096 token budget, causing Claude to truncate mid-JSX
- **Resolution**: Manually closed the truncated elements
- **Prevention**: Post-processing should detect unclosed JSX (missing export default, unbalanced tags) and either repair or regenerate

### Blocker 4: Browser screenshot timeouts

- **Impact**: Minor — couldn't take visual screenshots of the deployed site
- **Root Cause**: Heavy GSAP animations cause the browser renderer to time out during screenshot capture
- **Resolution**: Used DOM snapshot inspection instead
- **Prevention**: Known issue with animation-heavy pages; not critical

---

## Final Outcome

### What Was Delivered

1. **GSAP homepage clone** — 12-section site deployed to `https://site-psi-lake.vercel.app`
   - Functional but visually incomplete (monochrome orange, generic animations, placeholder gallery)
   - Dark theme, Inter font, GSAP engine, scroll-triggered animations
   - All sections render without errors

2. **Comprehensive pipeline diagnosis** — Complete trace of where and why the pipeline fails on complex sites
   - 6 specific failure points identified across 4 pipeline components
   - Each traced to exact file, function, and line number

3. **Implementation plan** — `plans/active/pattern-identification-mapping-pipeline.md` (678 lines)
   - 6 phases: token identification, archetype identification, animation/UI pattern matching, gap reports, preset format extensions, pipeline integration
   - 13 ordered implementation steps with dependencies
   - Success criteria for each phase
   - Validation via GSAP rebuild
   - Risk assessment

### What Wasn't Completed

- The GSAP build is visually poor — it's a functional site but doesn't represent the GSAP homepage well
- No library extensions were made this session (intentional — plan first, execute next)
- No gap report was generated (the infrastructure doesn't exist yet)

### Success Criteria

- [✓] Build completed and deployed — site is live
- [✗] Site accurately represents GSAP homepage — monochrome, missing animations, blank sections
- [✓] Pipeline gaps identified and documented — 6 systemic failures traced to code
- [✓] Implementation plan written and filed — 678-line plan in `plans/active/`
- [✓] System philosophy clarified — identification + mapping + gap detection, not better extraction

---

## Reusable Patterns

### Approaches to Reuse

**Pattern: Stress Test Diagnosis Loop**
- **When to use**: Before optimizing any pipeline, first run it against a challenging input and trace every failure
- **How it works**: Build → evaluate output → trace each deficiency back through the pipeline to the specific component that failed → document the gap chain
- **Watch out for**: The instinct to fix symptoms (manual section editing) rather than root causes (pipeline components)
- **Example**: GSAP build showed orange-only colors → traced to `hexToTailwindApprox()` losing hue → traced to `design-tokens.js` not parsing gradients → traced to `url-to-preset.js` not including gradient data in prompt

**Pattern: Philosophical Reframe Before Implementation**
- **When to use**: When a complex fix keeps growing in scope, step back and ask if the framing is wrong
- **How it works**: Instead of "make X extract more data", ask "what interpretation layer is missing between X and Y?"
- **Example**: "Fix extraction" → "Build identification layer" changed a 3-file patch into a principled system upgrade

---

## Recommendations for Next Time

### Do This

- ✅ Stress test with a known, visually inspectable site before claiming a pipeline component works
- ✅ Trace failures backward through the pipeline (output → generation → injection → identification → extraction)
- ✅ Check the extraction data directly before assuming it's incomplete — the raw data may already contain what you need
- ✅ Question the framing ("is this an extraction problem or an interpretation problem?")
- ✅ Build the plan before coding — the GSAP session produced more value from the diagnosis and plan than it would have from ad-hoc fixes

### Avoid This

- ❌ Assuming the preset is correct after extraction without verifying color accuracy, section count, and font mapping
- ❌ Trying to fix one build's output instead of fixing the system that produced it
- ❌ Ignoring low-confidence mappings (30%) in the archetype mapper output — these are screaming "I don't know what this is"
- ❌ Running `python` on macOS — always use `python3`

### If Starting Over

Would have spent less time on the actual GSAP build and more time on the diagnosis from the start. The build was necessary to produce the evidence, but only 2-3 sections needed to be inspected to identify the systemic issues. Would also have immediately checked the extraction data (mapped-sections.json, extraction-data.json) rather than waiting for the deployed site to reveal problems visually.

---

## Next Steps

**Immediate actions:**
- [ ] Execute the pattern identification and mapping pipeline plan (Phase 1-6)
- [ ] Start with Phase 1C (hue-aware Tailwind mapping) — smallest fix, biggest immediate impact
- [ ] Then Phase 2A (class name heuristics) — second biggest impact

**Future work:**
- [ ] Re-run GSAP build after pipeline upgrade to validate improvements
- [ ] Apply gap report extensions discovered from GSAP build (multi-accent, new keywords, new components)
- [ ] Stress test with 2-3 more complex sites (portfolio site, SaaS landing page, e-commerce) to find additional gaps

**Questions to resolve:**
- [ ] Should gap reports be cumulative across builds or per-build only?
- [ ] Should library extension tasks from gap reports be auto-added to `plans/backlog/`?
- [ ] What confidence threshold should trigger gap flagging (currently proposed: 0.5)?

---

## Related Sessions

- `2026-02-09-data-injection-pipeline-success.md` — Built the injection layer that this plan extends
- `2026-02-09-animation-component-library-infra-success.md` — Built the component registry that Phase 3 maps against
- `2026-02-10-animation-registry-build.md` — Built the comprehensive registry that enables pattern identification

---

## Attachments

- `plans/active/pattern-identification-mapping-pipeline.md` — The 678-line implementation plan (6 phases, 13 steps)
- `output/gsap-homepage/site/` — The deployed GSAP build (functional but visually incomplete)
- `output/extractions/gsap-homepage/` — Raw extraction data (evidence for diagnosis)
- `skills/presets/gsap-homepage.md` — Generated preset (with manual corrections)
- `briefs/gsap-homepage.md` — Generated brief

---

## Documentation Sync Results

**CLAUDE.md**: Updated
- Added gsap-homepage to Completed Builds table
- Added pattern-identification-mapping-pipeline to Active Plans
- Added `python` vs `python3` to Known Issues
- Version remains v0.6.0 (no code changes to pipeline, plan only)

**README.md**: No changes needed
- No user-facing pipeline changes

**.cursorrules**: No changes needed
- No pipeline stage changes

**Version**: v0.6.0 (no bump — planning session only, no code changes to pipeline)

---

## Metadata

```yaml
date: 2026-02-10
duration_minutes: 90
outcome: partial
tags: [gsap, stress-test, pipeline-diagnosis, identification, mapping, gap-detection, planning]
project: gsap-homepage
phase: stress-test + planning
related_checkpoints: []
```

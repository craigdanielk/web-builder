# Session Retrospective: Nike Golf Light-Theme Rebuild

**Date**: 2026-02-09
**Duration**: ~45 minutes (continuation session)
**Outcome**: Success

---

## Initial Goal

Continue the Nike Golf landing page build from where the previous agent stalled. The previous agent had extracted visual DNA from nike.com, corrected the preset from dark to light theme, regenerated the scaffold, and spawned 10 parallel section generation agents -- but then ran out of context before assembling the site or deploying.

## Planned Approach

8-step continuation plan (Steps A-H):

- Step A: Copy 10 light-theme staging sections into the site directory (overwrite old dark-theme versions)
- Step B: Fix page.tsx wrapper (`bg-gray-950` to `bg-white`)
- Step C: Fix layout.tsx fonts (remove Space Grotesk, add Inter 700)
- Step D: Audit all 10 sections for light-theme style compliance
- Step E: Build and verify locally
- Step F: Run fresh consistency review
- Step G: Deploy via Vercel
- Step H: Update .cursorrules to mandate extraction tools

## What Actually Happened

### Execution Timeline

1. **State Assessment** (5 min)
   - Discovered a critical two-layer mismatch: staging sections (light theme) vs site sections (old dark theme)
   - The previous agent had regenerated all 10 sections in `output/nike-golf/sections/` but never copied them to `output/nike-golf/site/src/components/sections/`
   - page.tsx still had `bg-gray-950 text-gray-100`
   - layout.tsx still imported Space Grotesk and had Inter at weights 400/500 only
   - globals.css still had dark-theme CSS variables
   - The existing review.md was a thorough review of the OLD dark-theme build -- now completely stale
   - Used parallel Glob/Grep calls to map the full state quickly

2. **Steps A, B, C in Parallel** (2 min)
   - Copied all 10 `.tsx` files from staging to site in one `cp` command
   - Fixed page.tsx wrapper and layout.tsx fonts simultaneously
   - Discovered globals.css still had dark-theme CSS variables -- fixed those too

3. **Step E: First Build Attempt -- FAILED** (5 min)
   - `next build` failed with: `Error occurred prerendering page "/_global-error"` + `TypeError: Cannot read properties of null (reading 'useContext')`
   - Created a custom `global-error.tsx` -- still failed
   - Searched GitHub issues and found this is a known Next.js 16 bug (#87719, #85668)
   - **Root cause**: `NODE_ENV=development` was set in the shell environment, conflicting with `next build`'s expectation to set `NODE_ENV=production`
   - **Fix**: `NODE_ENV=production npm run build` -- build passed immediately

4. **Step D: Parallel Style Audit** (10 min)
   - Launched two audit agents in parallel (sections 01-05 and sections 06-10)
   - Found 11 deviations across 8 files
   - Applied 7 critical fixes: container widths (3 files), animation durations (2 files), button borders (1 file), grid gaps (1 file)
   - Accepted 4 deviations as intentional: marquee py-6, count-up duration:2, footer no GSAP, logo-bar CSS animation

5. **Step E: Rebuild After Fixes** (1 min)
   - `NODE_ENV=production npm run build` -- passed clean
   - Verified no `max-w-6xl` or `max-w-5xl` remained anywhere

6. **Steps F & G in Parallel** (5 min)
   - Launched consistency review agent in background
   - Deployed to Vercel while review ran: `vercel --prod --yes`
   - Build passed on Vercel (no NODE_ENV issue there -- Vercel handles it correctly)
   - Live at: https://site-psi-lake.vercel.app

7. **Step H: .cursorrules Update** (2 min)
   - Added "URL Extraction Mandate" section with required flow, rationale, and post-extraction review checklist
   - Codifies the lesson from this project: don't guess colors/fonts, use the extraction scripts

8. **Consistency Review Results** (completed in background)
   - 30/37 checks passed (81%) -- up from 23/37 on old dark-theme build
   - Remaining items are low-priority cosmetic: button font weight standardization, hover shadow alignment, stagger timing harmonization

### Key Iterations

**Iteration 1: NODE_ENV Build Failure**
- **Initial approach**: Assumed `next build` would just work (it worked for the previous agent's dark-theme build)
- **Discovery**: The shell had `NODE_ENV=development` set, which conflicts with Next.js 16's internal `NODE_ENV=production` during build. This triggers a known bug where the internal `/_global-error` page fails to prerender.
- **Pivot**: Set `NODE_ENV=production` explicitly when running build
- **Learning**: Always check for non-standard NODE_ENV warnings in Next.js builds. Vercel doesn't have this issue because it controls the environment.

**Iteration 2: Two-Layer Theme Mismatch**
- **Initial approach**: Expected to only fix page.tsx and layout.tsx, with sections already in place
- **Discovery**: The staging directory (`sections/`) and the site directory (`site/src/components/sections/`) were completely different codebases -- staging had the new light theme, site still had old dark theme
- **Pivot**: Added Step A (copy staging sections over) as the very first action
- **Learning**: When an agent crashes mid-pipeline, always map the full state before executing. Staging vs deployed files can be out of sync.

**Iteration 3: globals.css Dark Theme Variables**
- **Initial approach**: Only planned to fix page.tsx and layout.tsx
- **Discovery**: `globals.css` still had `--bg-dark: #030712`, `body { background: var(--bg-dark) }`, dark scrollbar colors, and orange selection color
- **Pivot**: Rewrote globals.css variables to match light theme
- **Learning**: CSS variable files are easy to miss when switching themes. Always check globals.css alongside layout.tsx and page.tsx.

## Learnings & Discoveries

### Technical Discoveries

- **Next.js 16 + NODE_ENV bug**: `NODE_ENV=development` in the environment causes `/_global-error` prerender failure. This is documented in [vercel/next.js#87719](https://github.com/vercel/next.js/issues/87719) and [#85668](https://github.com/vercel/next.js/issues/85668). The fix is to either unset NODE_ENV or explicitly set it to `production` during build.
- **Vercel deploys don't have the NODE_ENV issue**: Vercel controls its own build environment, so the same codebase that fails locally can build fine on Vercel.
- **GSAP registerPlugin placement**: 6 out of 7 GSAP-using sections register the plugin at module scope (top of file), while 1 (02-hero) registers inside useEffect. Both work, but inconsistency is a code smell. Module scope is the standard pattern.
- **Tailwind v4 `@import "tailwindcss"`**: The new Tailwind v4 import syntax replaces the old `@tailwind base/components/utilities` directives.

### Process Discoveries

- **Parallel audit agents are highly effective**: Splitting 10 sections into two 5-section audit batches cut review time in half. Each agent read all files, applied the spec rules, and returned a structured deviation table.
- **State assessment before execution is critical**: The 5 minutes spent mapping the full state (staging vs site, theme mismatches, stale review.md) prevented cascading errors. Without it, we would have deployed the dark-theme site.
- **Background task + foreground work pattern**: Running the consistency review in the background while deploying to Vercel saved ~5 minutes of serial wait time.
- **The extraction-then-review workflow works**: The previous agent's extraction caught real Nike data (athlete names, product names, technologies), but the review step correctly identified that the bg_primary was wrong (captured cookie overlay, not actual page). This two-pass approach should be codified (and now is, in .cursorrules).

## Blockers Encountered

### Blocker 1: Next.js 16 `/_global-error` Prerender Failure

- **Impact**: Build completely blocked -- `next build` exits with code 1
- **Root Cause**: `NODE_ENV=development` in shell environment conflicts with Next.js 16's internal `NODE_ENV=production` setting during build. The discrepancy corrupts React's internal state, causing `useContext` to return null during `/_global-error` page prerendering.
- **Resolution**: Set `NODE_ENV=production` explicitly: `NODE_ENV=production npm run build`
- **Time Lost**: ~8 minutes (diagnosis, failed custom global-error.tsx attempt, web search, finding GitHub issue, applying fix)
- **Prevention**: Add `NODE_ENV=production` to the build command in `.cursorrules` Step 7, or add a pre-build check script. Alternatively, use `vercel build` locally which manages NODE_ENV correctly.

### Blocker 2: Staging vs Site Directory Desync

- **Impact**: Would have deployed the wrong (dark) theme if not caught during state assessment
- **Root Cause**: Previous agent ran out of context after generating sections in the staging directory but before copying them to the site directory. The 10-agent parallel generation succeeded, but the assembly step never ran.
- **Resolution**: Simple `cp` command to copy staging sections over
- **Time Lost**: ~2 minutes (mapping the state, confirming the mismatch)
- **Prevention**: The generation pipeline should copy sections to the site directory immediately after each section completes, not as a batch operation after all 10 finish. Or: the staging directory should BE the site directory.

## Final Outcome

### What Was Delivered

- 10-section Nike Golf landing page with correct light theme (white/gray-50 backgrounds, black accent, Inter font, rounded-full buttons)
- Deployed to Vercel: https://site-psi-lake.vercel.app
- Fresh QA consistency review: 30/37 checks passed (81%)
- Updated .cursorrules with URL extraction mandate
- Updated review.md with comprehensive light-theme audit

### What Wasn't Completed

- **Low-priority cosmetic fixes** from the review (button font weight standardization, hover shadow alignment, responsive padding on hero/CTA, stagger timing harmonization) -- documented in review.md Priority 1-9 list
- **Visual verification via screenshot** -- deployed but not visually inspected in browser during this session

### Success Criteria

- [x] All 10 sections use light-neutral palette (white/gray-50 bg, neutral-900 text, black accent)
- [x] All containers use max-w-7xl consistently
- [x] All GSAP animations use duration 0.4 and ease power2.out (with documented exceptions)
- [x] All buttons use rounded-full
- [x] All cards use rounded-3xl
- [x] Font stack is Inter-only (no Space Grotesk)
- [x] Build passes (`next build` clean)
- [x] Deployed to Vercel production
- [x] .cursorrules updated with extraction mandate
- [ ] All button styles perfectly standardized (font weight 500/600/700 inconsistency remains)

## Reusable Patterns

### Code Snippets to Save

```bash
# Fix for Next.js 16 build failure when NODE_ENV is set in environment
NODE_ENV=production npm run build

# Verify no off-spec container widths remain
grep -r "max-w-6xl\|max-w-5xl" output/*/site/src/components/sections/
```

```bash
# Quick theme audit: count light vs dark theme tokens in sections
# Light theme tokens:
grep -c "bg-white\|bg-gray-50\|text-neutral-900\|rounded-full\|rounded-3xl" sections/*.tsx

# Dark theme tokens (should be zero after migration):
grep -c "gray-950\|gray-900\|orange-500" sections/*.tsx
```

### Approaches to Reuse

**Pattern: Parallel Style Audit**
- **When to use**: After generating or migrating 5+ section components
- **How it works**: Split sections into two groups, launch two audit agents in parallel, each with the full style spec as context. Agents read all files and return structured deviation tables.
- **Watch out for**: Agents may flag the same file differently if the spec is ambiguous. Cross-reference both reports.
- **Example**: This session split 01-05 and 06-10, got results in ~3 minutes vs ~6 minutes serial.

**Pattern: State Assessment Before Execution**
- **When to use**: When continuing work from a crashed/interrupted agent
- **How it works**: Before executing any plan, use parallel Glob/Grep/Read calls to map: (1) what files exist in staging vs deployed, (2) what theme/style each layer uses, (3) what's stale.
- **Watch out for**: Don't assume the plan from the previous agent is still valid. The state may have diverged.

**Pattern: Background Deploy + Foreground Review**
- **When to use**: When both deployment and review are ready but independent
- **How it works**: Launch the review agent in background, deploy to Vercel in foreground. Both complete roughly together.
- **Watch out for**: If the review finds critical issues, you may need to redeploy. Accept this tradeoff for the time savings.

### Documentation to Reference

- [Next.js #87719](https://github.com/vercel/next.js/issues/87719) - `/_global-error` prerender bug with non-standard NODE_ENV
- [Next.js #85668](https://github.com/vercel/next.js/issues/85668) - Build fails with `useContext` null during static generation
- `output/nike-golf/review.md` - Comprehensive QA review with prioritized fix list

## Recommendations for Next Time

### Do This

- Run state assessment (Glob + Grep + Read in parallel) before executing any continuation plan
- Use `NODE_ENV=production` for all `next build` commands
- Check globals.css when switching themes (it's easy to miss)
- Launch parallel audit agents for style compliance (split sections into groups)
- Run review agent in background while deploying
- After extraction, ALWAYS verify bg_primary color against the actual page (not nav/overlay)

### Avoid This

- Don't assume staging sections == deployed sections after an interrupted build
- Don't skip globals.css when migrating themes (CSS variables override Tailwind)
- Don't create custom `global-error.tsx` as a fix for the NODE_ENV bug -- it doesn't help
- Don't use `max-w-5xl` or `max-w-6xl` for content sections -- standardize on `max-w-7xl`
- Don't run `next build` without checking `NODE_ENV` first

### If Starting Over

The pipeline should be: (1) extract from URL, (2) review extraction output manually, (3) generate scaffold, (4) generate sections directly into the site directory (not a staging directory), (5) build and audit in parallel, (6) fix deviations, (7) deploy. The staging directory introduces unnecessary complexity and creates the exact desync problem we hit. Sections should be generated directly into `site/src/components/sections/` and the site infrastructure (layout.tsx, globals.css, page.tsx) should be generated FIRST from the scaffold spec, not after sections.

Also: the extraction tools should automatically verify the bg_primary against common false positives (cookie overlays, nav backgrounds, footer backgrounds). A simple heuristic: if the detected bg is black/very dark but the majority of the page content area is light, flag it for review.

---

## Next Steps

**Immediate actions:**
- [ ] Visually inspect https://site-psi-lake.vercel.app in browser and verify light theme renders correctly
- [ ] Apply Priority 1-3 fixes from review.md if visual inspection reveals issues (button font weights, hover shadows, responsive padding)

**Future work:**
- [ ] Add `NODE_ENV=production` to the build command in .cursorrules Step 7
- [ ] Consider eliminating the staging directory pattern -- generate sections directly into site/src/components/sections/
- [ ] Add automated bg_primary verification to the url-to-preset.js extraction script
- [ ] Build a reusable "theme migration" checklist: page.tsx wrapper, layout.tsx fonts, globals.css variables, section components, review.md

**Questions to resolve:**
- [ ] Should button font weight be standardized at 600 (semibold) or 700 (bold) across all contexts?
- [ ] Should the marquee strip (03-logo-bar) use py-20 like other sections, or is py-6 the correct intentional exception?
- [ ] Is `hover:-translate-y-2` on featured product cards (07) intentionally heavier than `-translate-y-1` on category cards (04, 05)?

## Related Sessions

- `2026-02-08-web-builder-first-build-success.md` - Initial web-builder pipeline build (Turm Kaffee)
- `2026-02-08-farm-minerals-rebuild.md` - Farm Minerals build with similar pipeline

## Attachments

- `output/nike-golf/review.md` - Full QA consistency review (30/37 passed)
- `output/nike-golf/scaffold.md` - Light-theme scaffold spec
- `briefs/nike-golf.md` - Updated brief for Nike Golf
- `skills/presets/nike-golf.md` - URL-extracted preset with corrected light theme
- `.cursorrules` - Updated with URL Extraction Mandate section

---

## Metadata

```yaml
date: 2026-02-09
duration_minutes: 45
outcome: success
tags: [nike-golf, theme-migration, light-theme, next-js-16, node-env-bug, parallel-audit, vercel-deploy, url-extraction]
project: web-builder
phase: nike-golf-build-continuation
related_checkpoints: []
```

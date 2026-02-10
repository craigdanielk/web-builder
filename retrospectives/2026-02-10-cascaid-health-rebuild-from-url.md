# Session Retrospective: Cascaid Health Rebuild from URL

**Date**: 2026-02-10
**Duration**: ~30 minutes
**Outcome**: Success

---

## Initial Goal

Rebuild cascaid-health from scratch using the web-builder pipeline in URL clone mode, targeting `https://cascaidhealth.com/how-it-works/`, with previous animation fix learnings baked into the system.

## Planned Approach

1. Fix recurring `python` → `python3` command issue permanently
2. Run full pipeline: URL extraction → preset → brief → scaffold → sections → assembly → review → deploy
3. Fix any build errors
4. Deploy to Vercel

## What Actually Happened

### Execution Timeline

1. **Python command fix**
   - `which python3` confirmed `/opt/homebrew/bin/python3` (Python 3.14.0)
   - Updated `python` → `python3` in web-builder skill (`skill.md`) and all 3 occurrences in `CLAUDE.md`
   - Also fixed `pip` → `pip3` in skill error handling docs
   - This is a permanent fix — should never recur

2. **Pipeline execution**
   - First attempt failed: `Exit code 1` — previous `output/cascaid-health/` directory existed
   - Cleaned old output with `rm -rf` and re-ran
   - Pipeline completed successfully: 10 sections generated from URL extraction
   - Extraction detected: GSAP + ScrollTrigger + Lottie, expressive intensity (score 230.7), Figtree + Baskervville fonts
   - Only 1 visual section detected by Playwright (JS-heavy site with dynamic content)
   - QA review flagged 14 consistency issues (accent colors, button padding, border-radius, easing functions)

3. **Build fix: truncated section**
   - `07-trust_badges.tsx` was truncated at line 257 mid-string (Claude max_tokens hit)
   - The third integration card ("Fitness Trackers") was cut off after `text-2`
   - Completed the card following the pattern of the two preceding cards (CGM Devices, Guardian)
   - Added closing tags for all open containers

4. **Deploy**
   - Build succeeded after fix
   - Deployed to Vercel preview: https://site-eoqf4gbd9-craigs-projects-a8e1637a.vercel.app

### Key Iterations

**Iteration 1: Python command resolution**
- **Initial approach**: Skill file and CLAUDE.md both had `python` hardcoded
- **Discovery**: macOS (Homebrew) only has `python3`, no `python` symlink
- **Pivot**: Global find-and-replace across skill.md and CLAUDE.md
- **Learning**: Always use `python3` on macOS. This was the user's top frustration — it happened "every single time."

**Iteration 2: Existing project directory**
- **Initial approach**: Ran pipeline without cleaning previous output
- **Discovery**: Pipeline has safety check preventing overwrite of existing projects
- **Pivot**: `rm -rf output/cascaid-health` before re-running
- **Learning**: Pipeline's safety check is good, but the skill should handle this automatically (either clean or use `--force` flag)

**Iteration 3: Truncated section repair**
- **Initial approach**: Pipeline generated 07-trust_badges.tsx but it was truncated at 4096 tokens
- **Discovery**: Line 257 cut off mid-className string: `text-2` (should be `text-2xl`)
- **Pivot**: Read the preceding cards' pattern, completed the third card with matching structure
- **Learning**: This is the known max_tokens truncation issue. The section had 3 integration cards; only 2 fit in 4096 tokens. Token budget should have been raised for this section.

## Learnings & Discoveries

### Technical Discoveries

- **cascaidhealth.com/how-it-works/ extraction results**: Only 1 visual `<section>` detected (JS-heavy rendering), but 295 text items, 6 images, 5 fonts, 4 background images, 200 GSAP calls (from runtime interception, 0 from static bundle analysis), 415 CSS keyframes
- **Extraction quality**: Despite only 1 section detected, the pipeline still generated a good 10-section scaffold from the brief content. The archetype mapper worked with limited structural data.
- **QA review caught 14 issues**: Accent color mixing (emerald-800 vs 900), button inconsistencies, unauthorized gradients in hero, font weight deviations from spec. The review system works well as a punch list.
- **Animation engine detection accurate**: Correctly identified GSAP + ScrollTrigger + Lottie with expressive intensity

### Process Discoveries

- **The `python` → `python3` issue was a recurring user frustration**: Should have been caught and fixed on first occurrence, not after "every single time." Environment-specific commands must be documented in skills.
- **Project directory cleanup should be part of skill flow**: The skill should either prompt for cleanup or auto-handle existing directories
- **Truncation is still the #1 build quality issue**: Section 07 was truncated. This is a known issue (documented in CLAUDE.md) but still not automatically handled.

## Blockers Encountered

### Blocker 1: python command not found (recurring)

- **Impact**: Pipeline fails immediately, user frustration ("comes up every single time")
- **Root Cause**: macOS Homebrew installs `python3`, no `python` alias. Skill and docs hardcoded `python`.
- **Resolution**: Updated skill.md and CLAUDE.md globally (`python` → `python3`, `pip` → `pip3`)
- **Time Lost**: ~2 minutes this time, but cumulative across many sessions
- **Prevention**: Fixed permanently. Also a reminder to test skills on the actual target environment.

### Blocker 2: Section truncation (07-trust_badges)

- **Impact**: Build fails with "Unterminated string constant" parse error
- **Root Cause**: Claude's 4096 max_tokens limit for section generation; complex section with 3 detailed cards + SVG icons exceeded budget
- **Resolution**: Manual completion of the truncated card following established pattern
- **Time Lost**: ~5 minutes
- **Prevention**: Token budget should be raised for sections with many sub-items. Could also add post-generation truncation detection in orchestrate.py.

## Final Outcome

### What Was Delivered

- Fresh cascaid-health build from URL extraction of how-it-works page
- 10 sections: NAV, HERO, HOW-IT-WORKS, FEATURES (x2), PRODUCT-SHOWCASE, TRUST-BADGES, TESTIMONIALS, CTA, FOOTER
- Auto-generated preset: `skills/presets/cascaid-health.md`
- Auto-generated brief: `briefs/cascaid-health.md`
- Extraction data: `output/extractions/cascaid-health-e112b616/`
- Vercel preview: https://site-eoqf4gbd9-craigs-projects-a8e1637a.vercel.app
- Permanent fix: `python` → `python3` in skill + docs

### What Wasn't Completed

- User said "stop the deployment" — no production deploy, preview only
- QA review's 14 consistency issues not addressed (would need manual iteration)
- Previous session's animation enhancements (BorderBeam, CharacterFlip, scroll-reveal, dot trail) not re-applied to this fresh build

### Success Criteria

- [✓] Pipeline ran end-to-end from URL extraction
- [✓] Site builds and deploys successfully
- [✓] python3 fix applied permanently
- [✓] Truncated section repaired
- [⚠] QA review flagged 14 consistency issues (not addressed)
- [✗] Animation enhancements from previous session not carried forward

## Reusable Patterns

### Approaches to Reuse

**Pattern: Truncated Section Repair**
- **When to use**: Build fails with "Unterminated string constant" or similar parse error in a section file
- **How it works**: Read the truncated file, identify the pattern from preceding similar elements, complete the truncated element and close all open tags
- **Watch out for**: Must match the exact same className patterns, tag nesting, and data structure as sibling elements

**Pattern: Existing Project Cleanup**
- **When to use**: Re-running pipeline for a project that was previously built
- **How it works**: `rm -rf output/{project}` before running pipeline
- **Watch out for**: Don't delete extraction data if you want to reuse it (`output/extractions/` is separate)

## Recommendations for Next Time

### Do This

- ✅ Always use `python3` (now fixed in skill)
- ✅ Clean previous output before re-running a project
- ✅ Check build output for truncation errors before deploying
- ✅ Read QA review output to identify quick-win fixes

### Avoid This

- ❌ Assuming `python` exists on macOS
- ❌ Running pipeline without checking for existing project directory
- ❌ Deploying without verifying build succeeds locally first

### If Starting Over

Would add a `--clean` or `--force` flag to `orchestrate.py` that automatically removes existing project output before starting fresh. Would also add truncation detection to the post-processing step.

---

## Next Steps

**Immediate:**
- [ ] User to review preview and provide feedback on the fresh build
- [ ] Consider re-applying animation enhancements from previous session on top of this clean build

**System improvements:**
- [ ] Add `--clean` flag to orchestrate.py for project rebuilds
- [ ] Add truncation detection in post-processing (check for unclosed tags/strings)
- [ ] Consider raising token budget for sections with >3 sub-items

---

## Documentation Sync Results

**CLAUDE.md**: Updated earlier this session
- `python` → `python3` in all 3 Running the Pipeline examples
- cascaid-health added to Completed Builds
- GSAP SSR warning added to Known Issues

**README.md**: No changes needed
- No user-facing pipeline changes

**.cursorrules**: No changes needed
- No pipeline stage changes

**Version**: v0.7.1 (no bump — build session, not system change)

---

## Metadata

```yaml
date: 2026-02-10
duration_minutes: 30
outcome: success
tags: [cascaid-health, url-clone, python3-fix, truncation, rebuild]
project: web-builder
phase: cascaid-health-rebuild
related_checkpoints: []
```

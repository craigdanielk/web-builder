# Plan: VISION.md Sync Mechanism & PINNED-SCROLL Reclassification

**Created:** 2026-02-11
**Target Version:** v1.1.2
**Status:** Active

---

## Problem Statement

Two structural issues identified during system oversight review:

1. **VISION.md is not in any update flow.** The doc-sync-checklist, close-checklist, and CLAUDE.md update protocol all cascade to README.md and .cursorrules but completely skip VISION.md. This has caused significant drift — VISION.md still says 23 presets (actual: 35), doesn't reflect the animation library (1,034 components), and claims Phase 0 page templates are "In Progress" when they haven't started.

2. **PINNED-SCROLL was incorrectly elevated to a section archetype.** Pinned horizontal scrolling is a presentation technique (animation component), not a content type. It should be applicable to PRODUCT-SHOWCASE, FEATURES, GALLERY, HERO, etc. — not be a standalone archetype alongside them.

---

## Success Criteria

- [ ] VISION.md reflects v1.1.2 system reality (presets, archetypes, builds, animation library, phase status)
- [ ] VISION.md is included in the doc-sync-checklist with cascade triggers
- [ ] VISION.md is included in the close-checklist
- [ ] CLAUDE.md update protocol references VISION.md
- [ ] PINNED-SCROLL removed from section-taxonomy.md as an archetype
- [ ] Archetype count reverted to 25 (from 26)
- [ ] `gsap-pinned-horizontal.tsx` remains as animation component (unchanged)
- [ ] `pinned-horizontal-scene` remains as named animation pattern (unchanged)
- [ ] Detection pipeline (animation-detector, gsap-extractor, pattern-identifier) unchanged
- [ ] orchestrate.py pinned_scroll_block triggers on animation assignment, not archetype name
- [ ] section-instructions-gsap.md reframes pinned scroll as technique, not archetype
- [ ] animation-patterns.md archetype map updated (PINNED-SCROLL row removed, technique noted on applicable archetypes)
- [ ] CLAUDE.md version bumped to v1.1.2 with changelog entry
- [ ] Retrospective written

---

## Implementation

### Track A: PINNED-SCROLL Reclassification

**A1. section-taxonomy.md**
- Remove the PINNED-SCROLL archetype entry (lines ~312-328)
- Remove "Scroll & Immersive" category header if empty after removal
- Update archetype count from 26 to 25
- Update maintenance log

**A2. orchestrate.py**
- Change `pinned_scroll_block` trigger from `section["archetype"] == "PINNED-SCROLL"` to checking whether the animation injector assigned `gsap-pinned-horizontal` pattern
- Change 8192 min token override from archetype check to animation assignment check
- Remove scaffold instruction #5 that recommends PINNED-SCROLL as an archetype
- Keep all the actual pinned scroll rules content (it's correct, just needs a different trigger)

**A3. animation-patterns.md**
- Remove the PINNED-SCROLL row from the archetype→pattern map table
- Add notes on applicable archetypes to the `pinned-horizontal-scene` pattern entry (PRODUCT-SHOWCASE, FEATURES, GALLERY, HERO, HOW-IT-WORKS)

**A4. section-instructions-gsap.md**
- Reframe "Pinned Horizontal Scroll Sections (PINNED-SCROLL archetype)" as "Pinned Horizontal Scroll Technique"
- Change "When generating a PINNED-SCROLL section" to "When a section uses the pinned horizontal scroll technique"
- Change "Rules for PINNED-SCROLL" to "Rules for Pinned Horizontal Scroll"

**A5. Keep unchanged:**
- `skills/animation-components/scroll/gsap-pinned-horizontal.tsx` — correctly a component
- `animation-detector.js` — correctly detects pin+scrub technique
- `gsap-extractor.js` — correctly extracts pinned scroll calls
- `pattern-identifier.js` — correctly flags `pinnedScrollDetected`

### Track B: VISION.md Sync Mechanism

**B1. doc-sync-checklist.md** (retro skill asset)
- Add "VISION.md Updates" section between README.md and .cursorrules sections
- Define cascade triggers: module capability changes, phase status, build count, plan completions

**B2. plans/_close-checklist.md**
- Add VISION.md to Step 4 ("Update Dependent Docs")

**B3. CLAUDE.md Update Protocol** (embedded in CLAUDE.md lines 566-579)
- Add step for VISION.md updates

### Track C: VISION.md One-Time Refresh

**C1. Module 2 current state** — update stats:
- 35 presets (was 23)
- 25 archetypes, 99+ variants (was 25 archetypes, 95+ variants — note: back to 25 after reclassification)
- 1,034-component animation library
- 20 GSAP plugins detectable
- Pattern identification pipeline (Stage 0d)
- JSX truncation auto-repair
- 13 completed builds
- v1.1.2 system version

**C2. Phase 0 status correction**
- Commerce contract: DONE
- Page template structures: NOT STARTED (deferred — pipeline maturation prioritized)
- Section generation prompt for commerce: NOT STARTED

**C3. Add pipeline maturation summary**
- Document v0.1.0 → v1.1.2 trajectory
- 8 completed engineering plans
- Key capabilities added

**C4. "Where You Fit" section update**
- Remove stale "working on Phase 0 page templates" claim
- Accurately describe: Module 2 visual pipeline is production-ready, Phase 0 page template work is next

### Track D: CLAUDE.md Updates

**D1. Version bump** to v1.1.2
**D2. Changelog entry** documenting both changes
**D3. Archetype count** 26 → 25 in file map and references
**D4. Completed plans** — add this plan once done
**D5. Known issues** — no new issues expected

---

## Estimated Scope

| Track | Files Changed | Complexity |
|-------|---------------|------------|
| A (PINNED-SCROLL) | 4 files | Medium — careful surgery, keep detection pipeline intact |
| B (Sync mechanism) | 3 files | Low — adding sections to existing checklists |
| C (VISION.md refresh) | 1 file | Medium — significant content rewrite |
| D (CLAUDE.md) | 1 file | Low — version bump + changelog |
| **Total** | **~8 files** | **Medium** |

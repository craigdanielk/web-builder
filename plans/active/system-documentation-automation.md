# System Documentation & Versioning Automation Plan

**Status:** Implemented (2026-02-09)
**Created:** 2026-02-09
**Priority:** High — blocks efficient execution of all future plans

---

## Problem Statement

Every new Claude Code session on this project burns 5,000-15,000 tokens re-exploring the codebase before doing any work. The Explore agent reads orchestrate.py (700+ lines), every skill file, every quality script, the README, .cursorrules, and retrospectives just to understand the system state. This happens because:

1. **No CLAUDE.md exists** — Claude Code's native project context file is missing. This is the single file Claude reads automatically at session start. Without it, every session starts blind.

2. **README.md is stale** — Still references Lenis (removed in farm-minerals rebuild), says React 18 (now React 19), lists 20 presets (now 23+), doesn't mention `animation-detector.js`, doesn't cover the `--from-url` pipeline properly, lists `smooth-scroll.tsx` in the file map (no longer generated).

3. **.cursorrules is stale** — References `skills/components/image-patterns.md` which may not exist, doesn't mention the extraction pipeline or animation detection, doesn't reflect the current orchestrate.py stages.

4. **Retrospectives are write-only** — Session learnings go into `retrospectives/` but never flow back to update CLAUDE.md, README.md, or .cursorrules. Each retro captures valuable information (NODE_ENV bug, Lenis removal, Next.js 16 CVE workaround, framer-motion type errors requiring @ts-nocheck) that the next session has to rediscover.

5. **Plans lack system context** — The data-injection-pipeline plan required a full codebase exploration agent just to understand the file structure and data flow. If CLAUDE.md contained the current architecture, that exploration would be unnecessary.

**Cost:** At ~$0.02 per 1K tokens, re-exploration costs $0.10-0.30 per session. Over 50 sessions, that's $5-15 wasted — and more importantly, each exploration takes 2-5 minutes of wall time before productive work begins.

---

## Solution: Three Living Documents + Automated Sync

### Document Hierarchy

```
CLAUDE.md              ← Claude Code reads this FIRST, automatically
                         Contains: architecture, data flow, current state,
                         known issues, file map, working conventions
                         Updated: after every build or plan integration

README.md              ← Human/external audience
                         Contains: onboarding, quick start, tech stack,
                         deployment guide, contributing
                         Updated: synced from CLAUDE.md changes

.cursorrules           ← Agent pipeline instructions (for non-Claude agents)
                         Contains: generation rules, step-by-step pipeline,
                         critical constraints
                         Updated: when pipeline stages change
```

### Update Flow

```
Build/Integration Session
         │
         ├── Work happens (code changes, bug fixes, new features)
         │
         ▼
   Retrospective Skill
         │
         ├── Captures: what changed, what broke, what was learned
         │
         ▼
   CLAUDE.md Update (automated)
         │
         ├── Architecture section: new files, changed data flow
         ├── Known Issues section: add/resolve issues
         ├── System State section: version bumps, dependency changes
         ├── File Map section: new/moved/deleted files
         │
         ├──→ README.md sync (derive from CLAUDE.md)
         └──→ .cursorrules sync (if pipeline changed)
```

---

## Phase 1: Create CLAUDE.md (Single Source of Truth)

**File:** `/Users/craigkunte/Developer/GitHub/Personal/web-builder/CLAUDE.md`

This is the file that eliminates re-exploration. It must contain everything a new session needs to be productive immediately.

### Section Structure

```markdown
# Web Builder — System Context

## Quick Reference
- Tech stack: Next.js 16.1.6 / React 19 / Tailwind 4 / TypeScript 5
- Animation engines: GSAP 3.14 + Framer Motion 12
- Pipeline: orchestrate.py (6 stages, Python + Node.js hybrid)
- Deployment: Vercel CLI
- API: Anthropic Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

## Architecture
[Current pipeline diagram with stage numbers, inputs, outputs]
[Data flow from extraction → preset → scaffold → sections → deploy]

## File Map
[Complete tree with purpose annotations, line counts for key files]
[Marked as STABLE / ACTIVE / PLANNED for modification status]

## Pipeline Stages
[Each stage: function name, file:line, inputs, outputs, known issues]

## Current System State
- Active plans: [list with links]
- Recent changes: [last 3 sessions summarized]
- Known bugs: [with workarounds]
- Dependency versions: [pinned versions that matter]

## Working Conventions
- Build isolation rules
- Atomic file writes pattern
- Token budgets per stage
- Test commands

## Known Issues & Workarounds
[Accumulated from retrospectives, with resolution status]

## Modification Guide
[Which files to change for common tasks]
```

### What Makes This Different From README

| Aspect | CLAUDE.md | README.md |
|--------|-----------|-----------|
| Audience | Claude Code sessions | Humans, GitHub visitors |
| Auto-loaded | Yes (Claude Code reads it at session start) | No |
| Detail level | File paths, line numbers, function signatures | Conceptual, how-to |
| System state | Current versions, known bugs, active plans | Stable description |
| Update frequency | After every session | When CLAUDE.md changes propagate |

---

## Phase 2: Retrospective → CLAUDE.md Integration

The retrospective skill (`retro-session-analysis`) already generates structured session documentation. The missing link is flowing those learnings back into CLAUDE.md.

### 2A. Retrospective Output Contract

Each retrospective already captures:
- What changed (files created/modified/deleted)
- Bugs encountered and fixes applied
- Workarounds discovered
- Dependency version changes
- Pipeline behavior changes

### 2B. CLAUDE.md Update Checklist

After every retrospective, apply these updates to CLAUDE.md:

**Architecture section:**
- [ ] New files → add to File Map with purpose
- [ ] Deleted files → remove from File Map
- [ ] Changed data flow → update Architecture diagram
- [ ] New pipeline stage → add to Pipeline Stages

**System State section:**
- [ ] Dependency version changes → update Quick Reference
- [ ] New presets created → update preset count
- [ ] Plans completed → move from Active to Completed
- [ ] Plans created → add to Active

**Known Issues section:**
- [ ] Bugs discovered → add with workaround
- [ ] Bugs fixed → mark as resolved with date
- [ ] Workarounds discovered → add to relevant section

**Working Conventions section:**
- [ ] New patterns established → document
- [ ] Old patterns deprecated → mark and explain why

### 2C. Automation Approach

Rather than building a script, this is a **skill instruction** added to the retrospective skill:

```
After generating the retrospective document, update CLAUDE.md:
1. Read the current CLAUDE.md
2. Apply the changes from the retrospective using the checklist above
3. Increment the "Last Updated" timestamp
4. If pipeline stages changed, also update .cursorrules
```

This keeps the automation within Claude Code's existing skill system — no external scripts, no cron jobs, no CI integration needed.

---

## Phase 3: README.md Refresh

The current README.md is 499 lines and ~30% stale. Rather than maintaining it independently, derive it from CLAUDE.md.

### 3A. Sections to Fix Now

| Section | Issue | Fix |
|---------|-------|-----|
| Tech Stack (L352-363) | Says React 18+, mentions Lenis | Update to React 19, remove Lenis reference |
| File Map (L84-140) | Missing quality/lib/ scripts, missing plans/, missing animation-detector.js | Add all current files |
| Available Presets (L255-279) | Lists 20, now 23+ | Add farm-minerals-anim, farm-minerals-promo-v2, nike-golf |
| Deploy section (L361) | Mentions Lenis | Remove |
| Pipeline steps (L38-81) | Doesn't mention URL extraction as Stage 0 | Add --from-url mode |
| Quick Start (L148-213) | orchestrate.py examples outdated | Add --from-url examples |
| Known Issues (L440-463) | Missing NODE_ENV bug, Next.js 16 CVE, framer-motion type errors | Add from retrospectives |

### 3B. Ongoing Sync Rule

README.md is the public-facing version of CLAUDE.md. When CLAUDE.md changes:
- Architecture changes → update README's File Map and Pipeline sections
- New presets → update README's preset table
- New known issues → update README's troubleshooting section
- Version changes → update README's tech stack section

This sync is manual but guided by CLAUDE.md's change log.

---

## Phase 4: .cursorrules Refresh

The .cursorrules file (214 lines) is the agent instruction manual for non-Claude-Code agents (Cursor, Windsurf, etc.).

### 4A. Sections to Fix Now

| Section | Issue | Fix |
|---------|-------|-----|
| Repo Structure (L8-32) | Missing scripts/quality/lib/ tree | Add extraction and analysis scripts |
| Step 7: Deploy (L94-109) | Missing animation engine detection details | Add engine-specific behavior |
| Tech Stack (L157-167) | References Lenis, says React 18 | Update to React 19, remove Lenis |
| Image rendering (L141-144) | References `skills/components/image-patterns.md` | Verify exists or remove reference |
| Rule 8 (L141-144) | IMAGE RENDERING STANDARD references non-existent file | Fix or remove |

### 4B. Ongoing Sync Rule

.cursorrules changes only when the pipeline itself changes (new stages, new constraints, new file paths). It does NOT change for:
- New presets (those are discovered by scanning the directory)
- Bug fixes (those go in CLAUDE.md Known Issues)
- Dependency bumps (those go in CLAUDE.md System State)

---

## Phase 5: Version Tracking

### 5A. System Version in CLAUDE.md

Add a version section to CLAUDE.md:

```markdown
## System Version

**Current:** v0.4.0 (2026-02-09)

### Changelog
- v0.4.0 — Animation extraction integration (detector, analyzer, preset injection)
- v0.3.0 — URL clone mode (--from-url), auto-generated presets and briefs
- v0.2.0 — Multi-agent builds, build isolation, Vercel deployment
- v0.1.0 — Initial pipeline: brief → scaffold → sections → assembly → review
```

### 5B. Versioning Rules

| Change Type | Version Bump | Example |
|-------------|-------------|---------|
| New pipeline stage | Minor (0.X.0) | Adding asset injection stage |
| New skill file | Patch (0.0.X) | Adding a new preset |
| Bug fix | Patch (0.0.X) | Fixing dependency resolution |
| Breaking pipeline change | Minor (0.X.0) | Changing prompt template format |
| New extraction capability | Minor (0.X.0) | Adding animation detection |

### 5C. Plan Status Tracking

CLAUDE.md maintains the authoritative list of plans:

```markdown
## Plans

### Active
- [Data Injection Pipeline](plans/active/data-injection-pipeline.md) — Animation + asset injection into build output
- [System Documentation Automation](plans/active/system-documentation-automation.md) — This plan

### Completed
- [Animation Extraction Integration](plans/active/animation-extraction-integration.md) — v0.4.0
- [Template Library Upgrade](plans/completed/template-library-upgrade-plan.md) — v0.2.0
- [URL Site Structure Calculator](plans/completed/url-site-structure-calculator.md) — v0.3.0
```

---

## Implementation Order

```
Phase 1: Create CLAUDE.md                    — Immediate, highest impact
  - Write the full document from current system state
  - Include everything a new session needs
  - This is the deliverable that eliminates re-exploration

Phase 3: README.md Refresh                   — Parallel with Phase 1
  - Fix stale sections
  - Align with CLAUDE.md content

Phase 4: .cursorrules Refresh                — Parallel with Phase 1
  - Fix stale references
  - Remove Lenis, update versions

Phase 2: Retrospective Integration           — After Phase 1
  - Update the retro skill instructions
  - Add CLAUDE.md update checklist to retro output

Phase 5: Version Tracking                    — After Phase 1
  - Add version section to CLAUDE.md
  - Backfill changelog from retrospectives
```

### Parallelization

- **Track A:** CLAUDE.md creation (Phase 1)
- **Track B:** README.md + .cursorrules refresh (Phase 3 + 4) — can run in parallel with Track A since they're independent files
- **Track C:** Retrospective integration (Phase 2) — depends on Phase 1 being complete

---

## Files Created/Modified

### New Files
| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project-level single source of truth for Claude Code sessions |

### Modified Files
| File | Changes |
|------|---------|
| `README.md` | Fix stale sections (React version, Lenis, preset count, file map, known issues) |
| `.cursorrules` | Fix stale references (Lenis, image-patterns.md, React version, file map) |

### Unchanged Files
| File | Why |
|------|-----|
| All retrospective files | Read-only reference, never modified after creation |
| All plan files | Independent documents |
| All code files | This plan is documentation-only |

---

## Success Criteria

After implementation:

1. **A new Claude Code session** can read CLAUDE.md and immediately know: the pipeline architecture, current file map, active plans, known issues, and working conventions — without running an Explore agent
2. **README.md** accurately reflects the current system (React 19, no Lenis, 23+ presets, --from-url mode, NODE_ENV workaround)
3. **.cursorrules** has no references to non-existent files and correctly describes the current pipeline
4. **The retrospective skill** includes a CLAUDE.md update step in its output
5. **Token cost of session startup** drops from 5,000-15,000 tokens (exploration) to ~2,000 tokens (reading CLAUDE.md)

---

## Maintenance Log

| Date | Change |
|------|--------|
| 2026-02-09 | Plan drafted after observing repeated exploration costs across 4+ sessions |

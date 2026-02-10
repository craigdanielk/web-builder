# Build Close Checklist

Use this when a plan is complete and ready to move from `active/` to `completed/`.

---

## Pre-Close Verification

- [ ] All success criteria from the plan are met
- [ ] Code is committed and pushed
- [ ] No open blockers remain (or they're documented as carry-forward)

## Close Steps

### 1. Write Retrospective
Create `retrospectives/YYYY-MM-DD-{plan-name}.md` covering:
- **What shipped** — deliverables with file paths and line counts
- **What worked** — patterns/approaches to reuse
- **What didn't work** — problems and root causes
- **Carry forward** — tech debt, ideas, or unresolved issues for future plans

### 2. Move Plan to Completed
```bash
mv plans/active/{plan-name}.md plans/completed/
```

### 3. Update CLAUDE.md
- [ ] **Active Plans** section: remove the closed plan
- [ ] **Completed Builds** table: add entry if a site was deployed
- [ ] **Known Issues**: mark resolved issues, add new ones discovered
- [ ] **File Map**: update line counts, add/remove files
- [ ] **System Version**: bump version + add changelog entry

### 4. Update Dependent Docs (if needed)
- [ ] `README.md` — only if user-facing info changed (presets, tech stack, CLI flags)
- [ ] `.cursorrules` — only if pipeline stages changed

---

## Carry-Forward Template

When closing a plan, capture anything that should inform the next plan:

```markdown
### Carry Forward from {plan-name}

**Tech debt:**
- {issue}: {impact and suggested fix}

**Unfinished scope (deferred):**
- {feature}: {why deferred, what it needs}

**Patterns to reuse:**
- {pattern name}: {where it lives, when to use it}
```

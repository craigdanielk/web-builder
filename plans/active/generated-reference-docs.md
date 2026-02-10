# Generated Reference Documentation

**Status:** Planned
**Created:** 2026-02-10
**Priority:** Medium — reduces agent token waste by 10-20x per session
**Depends on:** None (independent of animation classification plan)
**Scope:** One Node.js script that generates three reference docs from source code

---

## Problem Statement

Every agent session that touches pipeline internals burns 50-200k tokens reading source files to understand function behavior, dependencies, and data flow. This exploration is identical across sessions — the same functions, the same parameters, the same return types. The current documentation (CLAUDE.md, .cursorrules, retrospectives) covers architecture and decisions but not function-level reference.

Manual reference docs go stale within 2-3 sessions. The solution is generated docs derived from source code — always correct because they're computed, not maintained.

---

## Solution: `scripts/generate-docs.js`

One script, three outputs. Reads source files, extracts signatures/deps/data-flow, writes markdown.

### Output 1: `docs/api-reference.md`

**Source:** All `.js` files in `scripts/quality/lib/` + `scripts/quality/*.js`

**Extraction method:**
- Regex or AST parse for `function` declarations and `module.exports`
- Extract function name, parameters, JSDoc comment (if present)
- Detect which other scripts `require()` each module (caller graph)

**Output format:**
```markdown
## animation-injector.js (808 lines)

### Exported Functions

#### `buildAllAnimationContexts(animationAnalysis, presetContent, sections)`
- **Params:** animationAnalysis (object|null), presetContent (string), sections (array)
- **Returns:** { contexts: object, allComponentFiles: string[], allDependencies: string[] }
- **Purpose:** Build per-section animation context blocks for prompt injection
- **Called by:** orchestrate.py via subprocess

#### `selectAnimation(archetype, presetIntensity, engine, usedPatterns)`
...
```

### Output 2: `docs/dependencies.md`

**Source:** `package.json` (root if exists) + `scripts/orchestrate.py` + all `require()` calls

**Extraction method:**
- Parse package.json for dependency list with versions
- Grep all `.js` files for `require('package-name')` to map package → scripts
- Regex `orchestrate.py` for `import` statements and Python deps
- Regex all files for `const UPPER_CASE = value` to extract configuration constants

**Output format:**
```markdown
## NPM Dependencies

| Package | Version | Used By | Purpose |
|---------|---------|---------|---------|
| gsap | ^3.14.2 | animation-injector.js, staggered-grid.tsx | Animation engine |
| framer-motion | ^12.33.0 | 19 component files | Animation engine |

## Configuration Constants

| Constant | Value | File | Line |
|----------|-------|------|------|
| MAX_TOKENS.section | 4096 | orchestrate.py | 75 |
| MAX_TOKENS.scaffold | 2048 | orchestrate.py | 76 |
```

### Output 3: `docs/data-flow.md`

**Source:** All `.js` files in `scripts/quality/lib/`

**Extraction method:**
- Grep for `fs.writeFileSync` / `JSON.stringify` → what each module produces
- Grep for `require()` / `JSON.parse` / `fs.readFileSync` → what each module consumes
- Map producer → file → consumer relationships

**Output format:**
```markdown
## Data Flow

### extract-reference.js
- **Produces:** extraction-data.json
- **Consumed by:** design-tokens.js, archetype-mapper.js, animation-detector.js, asset-injector.js

### animation-detector.js
- **Consumes:** extraction-data.json (from extract-reference.js)
- **Produces:** animation-analysis.json
- **Consumed by:** animation-injector.js (via orchestrate.py)
```

---

## Triggers: When Docs Regenerate

1. **Close checklist step** — Add to `plans/_close-checklist.md`: `node scripts/generate-docs.js`
2. **Retrospective doc-sync** — After session retro, run generation as part of doc-sync step
3. **Manual** — Any time via `node scripts/generate-docs.js`

NOT a pre-commit hook (too slow for every commit). NOT part of the build pipeline (unrelated to site generation).

---

## Integration Points

### CLAUDE.md addition
```markdown
## Generated Reference Docs
Run `node scripts/generate-docs.js` to regenerate. Always current.
- `docs/api-reference.md` — Function signatures, params, return types
- `docs/dependencies.md` — Packages, versions, constants
- `docs/data-flow.md` — Module input/output contracts
```

### Close checklist addition (`plans/_close-checklist.md`)
```markdown
### 2.5 Regenerate Reference Docs
node scripts/generate-docs.js
```

---

## Implementation Estimate

- **Script:** ~200-300 lines of Node.js
- **Dependencies:** None (use Node built-in `fs` + regex). Optional: `acorn` for proper AST parsing
- **Runtime:** <5 seconds
- **Session scope:** Single session build

---

## Success Criteria

1. `node scripts/generate-docs.js` runs without errors and produces three files in `docs/`
2. `docs/api-reference.md` lists every exported function across all 21 scripts with signature and one-line purpose
3. `docs/dependencies.md` lists every npm package with version and which scripts use it
4. `docs/data-flow.md` maps every JSON artifact to its producer and consumer scripts
5. Running the script twice produces identical output (deterministic)
6. An agent session reading the three docs files instead of source can answer "what does buildAnimationContext return?" without reading animation-injector.js

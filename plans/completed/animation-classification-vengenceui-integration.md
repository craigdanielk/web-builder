# Animation Classification System + VengenceUI Integration

## Context

Free-design builds (no `--from-url`) produce identical animations per archetype — every HERO gets `character-reveal`, every FEATURES gets `fade-up-stagger`. The static `ARCHETYPE_PATTERN_MAP` in `animation-injector.js:234-253` has no concept of intensity matching, industry context, or deduplication. Meanwhile, the component library has gaps that VengenceUI can fill (border effects, 3D text, background animations, cursor trails).

This plan upgrades the registry schema with intensity + affinity scoring, extracts ~11 VengenceUI components, and implements `selectAnimation()` for intelligent free-design selection.

**Goal:** A fashion site's HERO should get different animations than a construction site's HERO, and adjacent sections should never repeat the same pattern.

---

## Phase 0: Registry Schema Upgrade (existing 27 components)

**File:** `skills/animation-components/registry.json`

Add two fields to every existing component entry:

### `intensity` field
Maps to preset's `animation_intensity`. Values: `subtle`, `moderate`, `expressive`, `dramatic`.

| Component | Intensity |
|-----------|-----------|
| fade-up-single, fade-up-stagger, slide-in-left/right, scale-up, blur-fade | subtle |
| word-reveal, staggered-timeline, hover-lift, accordion-expand, marquee, count-up, parallax-section | moderate |
| character-reveal, pin-and-reveal, horizontal-scroll, parallax-layers, tilt-card, magnetic-button, hover-glow, floating, gradient-shift, typewriter | expressive |
| scroll-progress, text-gradient-flow, text-scramble, split-text-stagger | expressive |

### `affinity` field
Replaces binary `archetypes` array. Object mapping archetype names to fit scores (0.0–1.0).

Example upgrades:
```json
"fade-up-stagger": {
  "intensity": "subtle",
  "affinity": {
    "FEATURES": 0.9, "TESTIMONIALS": 0.9, "GALLERY": 0.9,
    "TEAM": 0.8, "PRODUCT-SHOWCASE": 0.8, "HOW-IT-WORKS": 0.8,
    "PRICING": 0.7, "ABOUT": 0.5, "CTA": 0.3
  }
}

"character-reveal": {
  "intensity": "expressive",
  "affinity": {
    "HERO": 0.95, "CTA": 0.6, "ABOUT": 0.4
  }
}

"count-up": {
  "intensity": "moderate",
  "affinity": {
    "STATS": 1.0, "HERO": 0.3
  }
}
```

Keep `archetypes` array for backward compat in `stage_deploy` component copy logic. The `affinity` field is additive.

---

## Phase 1: VengenceUI Component Extraction (11 components)

Clone repo, extract animation logic, refactor to web-builder's wrapper/standalone pattern.

### New Components

| # | VengenceUI Source | Registry Name | Category | Engine | Intensity | Pattern |
|---|---|---|---|---|---|---|
| 1 | `flip-text.tsx` | `character-flip` | text/ | framer-motion | expressive | Standalone (takes `text` prop) |
| 2 | `animated-number.tsx` | `count-up` (REPLACE) | continuous/ | framer-motion | moderate | Standalone (takes `value` prop) |
| 3 | `border-beam.tsx` | `border-beam` | effect/ | css | moderate | Wrapper (children + beam overlay) |
| 4 | `glow-border-card.tsx` | `glow-border` | effect/ | css | expressive | Wrapper (children + glow) |
| 5 | `logo-slider.tsx` | `marquee` (REPLACE) | continuous/ | css | subtle | Wrapper (children become marquee items) |
| 6 | `staggered-grid.tsx` | `staggered-grid` | entrance/ | gsap | expressive | Wrapper (children stagger-reveal on scroll) |
| 7 | `spotlight-navbar.tsx` | `spotlight-follow` | interactive/ | framer-motion | expressive | Standalone (nav-specific) |
| 8 | `pixelated-image-trail.tsx` | `cursor-trail` | interactive/ | css+react | dramatic | Standalone (attaches to document) |
| 9 | `reveal-loader.tsx` | `page-loader` | entrance/ | gsap | dramatic | Standalone (full-screen overlay) |
| 10 | `perspective-grid.tsx` | `perspective-grid` | background/ | css | moderate | Standalone (renders grid, accepts className) |
| 11 | `animated-hero.tsx` | `aurora-background` | background/ | css+framer | expressive | Wrapper (children over animated bg) |

### New category: `effect/` and `background/`
- `effect/` — Border/glow/decoration effects applied to containers
- `background/` — Full-section background animations

### Refactoring rules
- Strip VengenceUI's shadcn dependencies (Radix, cn utility)
- Replace `cn()` calls with template literal classNames or inline the utility
- Remove dark mode toggles (web-builder sections handle their own theming)
- Ensure `"use client"` directive at top
- Add `// @ts-nocheck` (existing convention for Framer Motion ease types)
- All components must work with zero config (sensible defaultProps)

### Replacements
- `count-up`: Current version is basic. VengenceUI's `animated-number` has smooth vertical slide with layout animation. Replace file, update registry entry.
- `marquee`: Current version is CSS-only. VengenceUI's `logo-slider` adds progressive blur masks. Replace file, update registry entry.

---

## Phase 1b: Fix `cn()` Utility Gap

**Discovered issue:** Several existing components import `cn()` from `@/lib/utils` but `stage_deploy` never generates this file.

**File:** `scripts/orchestrate.py` (in `stage_deploy`, after scaffold creation)

**Fix:** Generate `src/lib/utils.ts` during site scaffold:
```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
```

Add `clsx` and `tailwind-merge` to package.json dependencies (always — they're tiny).

**Alternative:** Strip `cn()` from all components during extraction and use plain template literals. Simpler but less composable.

**Recommendation:** Add the utility — it's 3 lines, 2 small deps, and future components will want it.

---

## Phase 2: Selection Algorithm

**File:** `scripts/quality/lib/animation-injector.js`

### New function: `selectAnimation()`

```javascript
function selectAnimation(archetype, presetIntensity, engine, usedPatterns) {
  const registry = loadRegistry();
  const intensityRank = { subtle: 1, moderate: 2, expressive: 3, dramatic: 4 };
  const presetRank = intensityRank[presetIntensity] || 2;

  const candidates = [];

  for (const [name, comp] of Object.entries(registry.components)) {
    // Filter: engine match (or css which works with both)
    if (comp.engine !== 'css' && comp.engine !== engine) continue;

    // Filter: intensity <= preset intensity (don't use dramatic on subtle preset)
    const compRank = intensityRank[comp.intensity] || 2;
    if (compRank > presetRank) continue;

    // Filter: must have affinity data for this archetype
    const score = (comp.affinity || {})[archetype] || 0;
    if (score === 0) continue;

    // Filter: not already used in adjacent sections
    if (usedPatterns.includes(name)) continue;

    // Filter: must be "ready" status
    if (comp.status !== 'ready') continue;

    candidates.push({ name, score, intensity: comp.intensity });
  }

  if (candidates.length === 0) return null;

  // Sort: highest affinity first, break ties by preferring higher intensity
  candidates.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return (intensityRank[b.intensity] || 0) - (intensityRank[a.intensity] || 0);
  });

  return candidates[0].name;
}
```

### Modifications to `buildAnimationContext()`

In the **Tier 3 fallback path** (lines 733-771), replace `resolvePatterns()` call with:

```javascript
// NEW: Use selectAnimation for free-design builds
let selectedPattern = selectAnimation(
  sectionArchetype,
  getIntensity(animationAnalysis) || parsePresetIntensity(presetContent),
  engine,
  usedPatterns  // tracked across sections in buildAllAnimationContexts
);

// Fallback to ARCHETYPE_PATTERN_MAP if selectAnimation returns null
if (!selectedPattern) {
  const fallback = resolvePatterns(sectionArchetype, overrides);
  selectedPattern = fallback ? fallback[0] : 'fade-up-single';
}
```

### Modifications to `buildAllAnimationContexts()`

Track `usedPatterns` across sections for deduplication:

```javascript
function buildAllAnimationContexts(animationAnalysis, presetContent, sections) {
  const usedPatterns = [];  // NEW: track for dedup

  for (let i = 0; i < sections.length; i++) {
    const result = buildAnimationContext(
      animationAnalysis, presetContent, archetype, i, usedPatterns  // pass usedPatterns
    );

    // Track which pattern was selected (NEW)
    if (result.selectedPattern) {
      usedPatterns.push(result.selectedPattern);
    }
    // ...
  }
}
```

### New helper: `parsePresetIntensity()`

```javascript
function parsePresetIntensity(presetContent) {
  const match = presetContent.match(/animation_intensity:\s*(subtle|moderate|expressive|dramatic)/i);
  return match ? match[1].toLowerCase() : 'moderate';
}
```

### Backward compatibility
- Tier 1 (component library lookup) — **unchanged**
- Tier 2 (extracted signature) — **unchanged**
- Tier 3 (pattern selection) — **upgraded** with `selectAnimation()`, falls back to `resolvePatterns()` if no affinity data

---

## Phase 3: Documentation Update

**File:** `skills/animation-patterns.md`

- Add pattern descriptions + code snippets for 11 new patterns
- Update the Pattern-to-Archetype Mapping table to reflect affinity scores
- Add note: "For algorithmic selection details, see registry.json affinity field"

**File:** `CLAUDE.md`

- Update File Map: add `effect/`, `background/` categories, new component count
- Update Active Plans or create new completed plan entry
- Bump version

---

## Dependency Graph

```
Phase 0 (registry schema) ──┐
                             ├──→ Phase 2 (selection algorithm) ──┐
Phase 1 (VengenceUI extract) ┤                                    ├──→ Phase 3 (docs)
                             ├──→ Phase 1b (cn() utility fix)     │
                             └──→ Registry additions ─────────────┘
```

**Parallelizable:**
- Phase 0 + Phase 1 (independent — schema upgrade vs component extraction)
- Phase 1b can run with Phase 1

**Sequential:**
- Phase 2 depends on Phase 0 (needs intensity/affinity fields to exist)
- Phase 3 depends on all phases

---

## Files Changed Summary

| File | Action |
|------|--------|
| `skills/animation-components/registry.json` | Add `intensity` + `affinity` to 27 entries, add 11 new entries |
| `scripts/quality/lib/animation-injector.js` | Add `selectAnimation()`, `parsePresetIntensity()`, modify Tier 3 path, add `usedPatterns` tracking |
| `scripts/orchestrate.py` | Add `cn()` utility generation in `stage_deploy`, add `clsx`+`tailwind-merge` deps |
| `skills/animation-patterns.md` | Add 11 new pattern descriptions |
| `skills/animation-components/text/character-flip.tsx` | NEW — from VengenceUI flip-text |
| `skills/animation-components/continuous/count-up.tsx` | REPLACE — from VengenceUI animated-number |
| `skills/animation-components/effect/border-beam.tsx` | NEW — from VengenceUI border-beam |
| `skills/animation-components/effect/glow-border.tsx` | NEW — from VengenceUI glow-border-card |
| `skills/animation-components/continuous/marquee.tsx` | REPLACE — from VengenceUI logo-slider |
| `skills/animation-components/entrance/staggered-grid.tsx` | NEW — from VengenceUI staggered-grid |
| `skills/animation-components/interactive/spotlight-follow.tsx` | NEW — from VengenceUI spotlight-navbar |
| `skills/animation-components/interactive/cursor-trail.tsx` | NEW — from VengenceUI pixelated-image-trail |
| `skills/animation-components/entrance/page-loader.tsx` | NEW — from VengenceUI reveal-loader |
| `skills/animation-components/background/perspective-grid.tsx` | NEW — from VengenceUI perspective-grid |
| `skills/animation-components/background/aurora-background.tsx` | NEW — from VengenceUI animated-hero |
| `CLAUDE.md` | File map, version bump, plan status |

---

## Verification

1. **Backward compat:** Run `python scripts/orchestrate.py test-project --from-url https://farmminerals.com/promo --no-pause` — verify URL clone mode still produces GSAP animations with extraction data (Tier 1/2 unchanged)
2. **Free-design variety:** Run two free-design builds with different presets (e.g., `--preset artisan-food` vs `--preset fashion-apparel`) — verify HERO sections get different animations
3. **Deduplication:** In any build, verify no two adjacent sections use the same animation pattern (check pipeline output logs)
4. **Intensity filtering:** Run with `fashion-apparel` (subtle intensity) — verify no `expressive` or `dramatic` components are selected
5. **Component compilation:** `cd output/{project}/site && npm run build` — verify no missing imports for animation components or `cn()` utility
6. **Registry integrity:** `node -e "const r = require('./skills/animation-components/registry.json'); const c = Object.values(r.components); console.log('Total:', c.length, 'With affinity:', c.filter(x=>x.affinity).length)"` — should show 38 total, 38 with affinity

# Pattern Identification & Mapping Pipeline

**Status:** Planning
**Created:** 2026-02-10
**Revised:** 2026-02-11
**Depends on:** Data Injection Pipeline (v0.5.0), Animation Component Library (v0.6.0), Animation Registry (v0.8.0)
**Scope:** New identification layer between extraction and generation; gap detection; library extension protocol
**Target version:** v0.9.0
**Stress test source:** GSAP homepage build — exposed systemic failures in identification, mapping, and gap handling

---

## Problem Statement

The current pipeline treats extraction as the final data source: raw CSS properties, hex colors, and DOM structure are passed directly to Claude for preset generation and section generation. This works for simple sites but fails catastrophically on visually rich sites because:

1. **No pattern recognition**: Raw tokens (hex colors, px values, gradient strings) are never interpreted into semantic patterns ("multi-accent color system", "logo marquee", "interactive demo"). The system sees `linear-gradient(114.41deg, rgb(10, 228, 72)...)` but never identifies "this is a per-section accent color for the Scroll tool card."

2. **No library mapping**: Identified site elements are never matched against our existing capabilities (1022 animation components in the registry, 25 section archetypes, 95+ variants, 24 presets). A logo marquee goes unrecognized even though we have `LOGO-BAR | scrolling-marquee` in the taxonomy.

3. **Silent fallback**: When identification fails, the archetype mapper defaults to `FEATURES | icon-grid` at 30% confidence with no feedback. There's no mechanism to flag "I couldn't identify this section — here's what I see, this needs to be added."

4. **No learning loop**: Failed identifications don't produce actionable library extension tasks. Each build starts from scratch rather than benefiting from gaps discovered in previous builds.

### Evidence from GSAP Build

| What the site has | What extraction captured | What identification produced | What was built |
|---|---|---|---|
| Green gradient Scroll card | `linear-gradient(114.41deg, rgb(10, 228, 72)...)` in `backgroundImages` | Nothing — gradient data never parsed | Orange-only monochrome cards |
| Logo marquee ("Brands using GSAP") | Class name `brands`, label "Brands using GSAP®" | `FEATURES \| icon-grid` at 30% confidence (fallback) | Static trust badge grid |
| Showcase video carousel | Class name `showcase`, label "Showcase" | `FOOTER \| mega` at 50% (position-last) | Gallery card grid with SVG placeholders |
| Interactive easing curve editor | DOM structure with bezier handles | Not identified at all | Static easing preset buttons |
| Per-section color theming (green/blue/purple/pink) | 4 distinct gradient colors in background images | Single `orange-500` accent in preset | Monochrome orange site |
| 94 GSAP calls across 5 JS bundles | All 94 calls extracted by `gsap-extractor.js` | Only section 0 mapped; `sectionOverrides: {}` | Generic scroll-triggered fades |

---

## Architecture: Identification Layer

A new layer between extraction and generation that transforms raw tokens into semantic patterns, maps them to library capabilities, and reports gaps.

```
┌─────────────────────────────────────────────────────────┐
│                  EXTRACTION (exists)                     │
│  extract-reference.js → DOM, CSS, images, fonts         │
│  gsap-extractor.js    → GSAP calls from JS bundles      │
│  design-tokens.js     → colors, fonts, radii, spacing   │
│  animation-detector.js → libraries, intensity, patterns  │
└──────────────────────┬──────────────────────────────────┘
                       │ raw tokens
                       ▼
┌─────────────────────────────────────────────────────────┐
│              IDENTIFICATION (NEW)                        │
│                                                          │
│  design-tokens.js (enhanced — Track A)                   │
│  ├── collectGradientColors()    → gradient stop parsing  │
│  ├── identifyColorSystem()      → single/multi/gradient  │
│  ├── hexToTailwindHue()         → hue-aware mapping      │
│  └── profileSectionColors()     → per-section accents    │
│                                                          │
│  archetype-mapper.js (enhanced — Track B)                │
│  ├── + CLASS_NAME_SIGNALS map                            │
│  ├── + expanded HEADING_KEYWORDS                         │
│  ├── + content-aware variant selection                   │
│  ├── + confidence-based gap flagging                     │
│  └── returns { mappedSections, gaps }                    │
│                                                          │
│  pattern-identifier.js (new — Track C)                   │
│  ├── matchAnimationPatterns()   → registry lookup        │
│  ├── matchUIComponents()        → structural detection   │
│  ├── mapComponentsToSections()  → per-section mapping    │
│  └── aggregateGapReport()       → merge all gap sources  │
│                                                          │
└──────────────────────┬──────────────────────────────────┘
                       │ semantic patterns + gap report
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  MAPPING (enhanced — Track D)             │
│                                                          │
│  url-to-preset.js (enhanced)                             │
│  ├── receives patterns, not just raw tokens              │
│  ├── multi-accent support in preset format               │
│  ├── section-level color overrides                       │
│  └── identified components in prompt context             │
│                                                          │
│  orchestrate.py (enhanced)                               │
│  ├── reads gap report for build warnings                 │
│  ├── passes pattern data to section generation           │
│  └── outputs gap summary post-build                      │
│                                                          │
└──────────────────────┬──────────────────────────────────┘
                       │ enriched preset + section specs
                       ▼
┌─────────────────────────────────────────────────────────┐
│               GENERATION (exists, improved)              │
│  orchestrate.py → scaffold → sections → assembly         │
└──────────────────────┬──────────────────────────────────┘
                       │ gap report
                       ▼
┌─────────────────────────────────────────────────────────┐
│             GAP REPORT + EXTENSION (NEW)                 │
│                                                          │
│  output/{project}/gap-report.json                        │
│  ├── missing_archetypes: []                              │
│  ├── missing_components: []                              │
│  ├── missing_color_system_features: []                   │
│  ├── missing_animation_patterns: []                      │
│  ├── low_confidence_mappings: []                         │
│  └── extension_tasks: []                                 │
│                                                          │
│  Library extension protocol (manual, informed by report) │
│  ├── section-taxonomy.md additions                       │
│  ├── animation-components/ new entries                   │
│  ├── style-schema.md + preset template updates           │
│  └── archetype-mapper.js keyword/class expansions        │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Tracks

Work is organized into 4 parallel tracks. **Tracks A and B are independent** and can be implemented concurrently. Track C depends on both A and B. Track D depends on all prior tracks.

```
Time →
 ┌──────── Track A: Color Intelligence ──────────┐
 │  A1 → A2 → A3 → A4                            │
 └────────────────────────────────────────────────┘
                                                     ↘
 ┌──────── Track B: Archetype Intelligence ──────┐    → Track C → Track D → Validate
 │  B1 → B2 → B3                                 │    ↗
 └────────────────────────────────────────────────┘
```

---

## Track A: Color Intelligence

**File:** `scripts/quality/lib/design-tokens.js` (265 lines currently)
**Goal:** Transform raw color data into identified color system patterns

### A1. Hue-Aware Tailwind Mapping

The current `hexToTailwindApprox()` in `url-to-preset.js` (lines 64–81) maps ALL colors to gray shades based on brightness alone. A bright green `#0ae448` becomes `gray-200`.

**Create** `hexToTailwindHue(hex)` in `design-tokens.js`:
1. Convert hex to HSL
2. Map hue (0–360) to Tailwind color family:
   - 0–15 → red, 15–35 → orange, 35–50 → amber, 50–65 → yellow
   - 65–80 → lime, 80–150 → green, 150–170 → emerald, 170–185 → teal
   - 185–200 → cyan, 200–215 → sky, 215–250 → blue, 250–265 → indigo
   - 265–280 → violet, 280–300 → purple, 300–330 → fuchsia, 330–345 → pink
   - 345–360 → rose
3. Map lightness to shade number (50–950)
4. Handle achromatic (saturation < 10%) → gray-{shade} (existing behavior)
5. Return e.g. `green-500` for `#0ae448`

**Update** `url-to-preset.js` to import and use `hexToTailwindHue()` instead of the inline `hexToTailwindApprox()`. Keep the old function as `hexToTailwindBrightness()` for backward compatibility.

**Export** from `design-tokens.js`: `hexToTailwindHue`, `hexToHSL` (utility).

### A2. Gradient Color Parsing

Currently `collectTokens()` only reads `s.color` and `s.backgroundColor` from DOM elements. The `backgroundImages` array in extraction data contains gradient strings that are never parsed.

**Add** `collectGradientColors(extractionData)`:
- Parse `extractionData.assets.backgroundImages` for `linear-gradient(...)` and `radial-gradient(...)` strings
- Extract RGB color stops from each gradient using regex
- Convert stops to hex via existing `rgbToHex()`
- Return: `{ gradients: [{ source, stops: [hex, hex, ...], angle }], accentColors: [hex, ...] }`
- `accentColors` = unique non-white, non-black gradient stops

### A3. Color System Identification

**Add** `identifyColorSystem(tokens, gradientData)`:
- Inputs: standard tokens from `collectTokens()` + gradient data from A2
- Combine all color sources: bg, text, accent, gradient stops
- Filter out near-white (L > 95%) and near-black (L < 5%)
- Cluster remaining colors by hue with minimum angular distance of 30°
- Classify:
  - 0–1 distinct accent hues → `single-accent`
  - 2 distinct accent hues → `dual-accent`
  - 3+ distinct accent hues → `multi-accent`
  - All accents from gradients only → `gradient-based`
- Output: `{ system, accents: [{ hue, hex, tailwind, source }] }`

### A4. Per-Section Color Profiling

**Add** `profileSectionColors(extractionData, gradientData)`:
- For each section in `extractionData.sections`, collect DOM elements whose `rect.y` falls within section vertical bounds
- Extract their unique background colors, text colors, and gradient stops
- Identify the section's dominant accent (most-frequent non-bg, non-text color)
- Map to Tailwind using `hexToTailwindHue()`
- Output: `{ sectionColors: { 0: { accent: "green-500", gradient: true }, 1: { accent: "blue-500" }, ... } }`

### Track A Success Criteria
- `hexToTailwindHue("#0ae448")` → `green-500` (not `gray-200`)
- `hexToTailwindHue("#8B5CF6")` → `violet-500` (not `gray-500`)
- Given GSAP extraction data, `identifyColorSystem()` returns `multi-accent` with at least green/orange identified
- Given any gradient string, `collectGradientColors()` extracts the RGB stops
- Per-section profiling assigns distinct accents to tool card sections

---

## Track B: Archetype Intelligence

**File:** `scripts/quality/lib/archetype-mapper.js` (268 lines currently)
**Goal:** Correctly identify section archetypes using all available signals, flag gaps

### B1. Class Name Signals + Expanded Keywords

The mapper completely ignores `section.classNames` and `section.id`. These are often the strongest identification signals.

**Add** `CLASS_NAME_SIGNALS` map:

```javascript
const CLASS_NAME_SIGNALS = {
  // Direct matches
  'hero': 'HERO', 'banner': 'HERO',
  'nav': 'NAV', 'header': 'NAV',
  'footer': 'FOOTER',
  'about': 'ABOUT',
  'features': 'FEATURES',
  'pricing': 'PRICING',
  'testimonial': 'TESTIMONIALS', 'review': 'TESTIMONIALS',
  'faq': 'FAQ',
  'team': 'TEAM',
  'contact': 'CONTACT',
  'cta': 'CTA',
  'newsletter': 'NEWSLETTER',
  'blog': 'BLOG-PREVIEW',
  'stats': 'STATS', 'counter': 'STATS',

  // Product/showcase
  'product': 'PRODUCT-SHOWCASE', 'shop': 'PRODUCT-SHOWCASE',
  'catalog': 'PRODUCT-SHOWCASE', 'tools': 'PRODUCT-SHOWCASE',
  'collection': 'PRODUCT-SHOWCASE',

  // Logo/trust
  'brand': 'LOGO-BAR', 'logo': 'LOGO-BAR',
  'partner': 'LOGO-BAR', 'client': 'LOGO-BAR', 'trust': 'TRUST-BADGES',

  // Gallery/showcase
  'showcase': 'GALLERY', 'gallery': 'GALLERY',
  'portfolio': 'PORTFOLIO', 'work': 'PORTFOLIO', 'case-stud': 'PORTFOLIO',

  // Interactive/demo
  'demo': 'FEATURES', 'playground': 'FEATURES', 'interactive': 'FEATURES',

  // Process
  'process': 'HOW-IT-WORKS', 'steps': 'HOW-IT-WORKS', 'how': 'HOW-IT-WORKS',

  // Video
  'video': 'VIDEO', 'showreel': 'VIDEO',
};
```

**Matching logic:** Split `classNames` and `id` on spaces, `-`, `_`. Check each fragment against map. Confidence: **0.8** (after tag 0.9 and role 0.85, before heading keywords 0.75).

**Expand** `HEADING_KEYWORDS`:

| Archetype | Add Keywords |
|-----------|-------------|
| `LOGO-BAR` | `brands`, `trusted`, `companies`, `used by`, `powered by`, `built with` |
| `GALLERY` | `showcase`, `examples`, `built with`, `community`, `inspiration`, `showreel` |
| `PRODUCT-SHOWCASE` | `tools`, `solutions`, `platform`, `explore`, `discover`, `our stack` |
| `CTA` | `free`, `start`, `create account`, `begin`, `launch` |
| `FEATURES` | `why`, `what you get`, `benefits`, `advantages`, `animate`, `build` |
| `HOW-IT-WORKS` | `get started`, `quick start`, `installation`, `setup`, `minutes` |
| `STATS` | `metrics`, `performance`, `speed`, `data` |

### B2. Variant Selection Enhancement

Currently `selectVariant()` returns hardcoded defaults. Improve with content-aware selection:

- `FEATURES` with class containing `demo`/`interactive`/`playground` → `interactive-demo` variant
- `FEATURES` with class containing `alternate`/`zigzag` → `alternating-rows` variant
- `FEATURES` with height > 1500px → `alternating-rows` (tall section = multiple blocks)
- `LOGO-BAR` with height < 200px → `inline`; height > 300px → `scrolling-marquee`
- `GALLERY` with class containing `reel`/`video`/`showreel` → `showcase-reel` variant

### B3. Confidence-Based Gap Flagging

**Change** `mapSectionsToArchetypes()` return signature from `mappedSections` to `{ mappedSections, gaps }`.

When a section maps at confidence < 0.5:

```javascript
if (confidence < 0.5) {
  gaps.push({
    type: 'low_confidence_mapping',
    sectionIndex: i,
    label: sec.label,
    classNames: sec.classNames,
    assignedArchetype: archetype,
    confidence,
    method,
    rawSignals: {
      tag: sec.tag,
      id: sec.id,
      classNames: sec.classNames,
      label: sec.label,
      height: sec.rect?.height,
    },
    suggestion: `Section "${sec.label}" (class: ${sec.classNames}) mapped to ${archetype} via ${method} at ${(confidence * 100).toFixed(0)}% confidence. Review and add keywords or class signals if a better archetype exists.`
  });
}
```

**Update callers** of `mapSectionsToArchetypes()` to accept the new return shape:
- `url-to-preset.js` (line ~130) — destructure `{ mappedSections, gaps }`
- `orchestrate.py` `stage_url_extract()` — the inline Node script that calls archetype-mapper

### Track B Success Criteria
- GSAP section `brands` (classNames: `"brands"`) → `LOGO-BAR` (not `FEATURES`)
- GSAP section `showcase` (classNames: `"showcase"`) → `GALLERY` (not `FOOTER`)
- GSAP section `home-tools` (classNames: `"home-tools"`) → `PRODUCT-SHOWCASE` (not `FEATURES`)
- Any section mapped below 50% confidence generates a gap record
- Variant for `brands` section → `scrolling-marquee` (not default)

---

## Track C: Pattern Identification + Gap Aggregation

**File:** `scripts/quality/lib/pattern-identifier.js` (NEW)
**Goal:** Match site patterns to the animation registry; detect UI component patterns; aggregate all gaps

This module is deliberately **lean** — it doesn't own color or archetype logic (those live in their respective files). It handles:
1. Animation pattern matching against the v0.8.0 registry (1022 components)
2. UI component structural detection
3. Gap aggregation from all sources

### C1. Animation Pattern Matching

**Input:** `animation-analysis.json` (GSAP calls, per-section data, intensity)
**Registry source:** `skills/animation-components/registry/animation_search_index.json`

**Process:**
1. Load `animation_search_index.json` — use `by_intent`, `by_trigger`, `by_section_role`, `by_framework` indexes
2. For each GSAP call in the extraction data, classify by method:
   - `timeline.from` with `opacity: 0, y: N` → intent `entrance` + `reveal`
   - `stagger` param → intent `stagger`
   - `ScrollTrigger` with `scrub: true` → trigger `scroll_linked`
   - `SplitText` or character-level manipulation → intent `typewrite` or `reveal`
   - `scale`/`rotation` continuous → intent `attention`
3. For each CSS keyframe: map name to intent (e.g. `marquee` → intent `reveal` + trigger `mount`)
4. Look up each identified intent in `by_intent` index → get candidate component IDs
5. Cross-reference with `by_section_role` (from archetype mapping) for section fit
6. Cross-reference with `by_framework` (match `gsap` vs `framer-motion` from preset)
7. Flag any identified pattern that has zero matches in the registry as a gap

**Output:**
```json
{
  "identifiedPatterns": [
    {
      "pattern": "character-reveal",
      "intent": "reveal",
      "source": "gsap-call",
      "sectionIndex": 0,
      "registryMatches": ["text__character_reveal", "21st-dev__word_reveal"],
      "bestMatch": "text__character_reveal",
      "status": "available"
    },
    {
      "pattern": "scroll-scrub-parallax",
      "intent": "parallax",
      "source": "gsap-call",
      "sectionIndex": 3,
      "registryMatches": [],
      "bestMatch": null,
      "status": "gap"
    }
  ]
}
```

### C2. UI Component Detection

Scan `extractionData.renderedDOM` for structural signatures per section:

| Pattern | Detection Signal | Maps To |
|---------|-----------------|---------|
| Logo marquee | Multiple `<img>` with small dimensions + horizontal scroll container | `LOGO-BAR \| scrolling-marquee` |
| Card grid | 3+ repeated siblings with similar structure (image + heading + text) | Card components |
| Code block | `<pre>` or `<code>` with syntax highlighting classes | Developer-focused section |
| Video embed | `<video>`, `<iframe>` with video src, `video`/`player` class | `VIDEO` archetype |
| Tab interface | `role="tablist"` or tab-like class names | Interactive component |
| Accordion/FAQ | Repeated disclosure/details elements | `FAQ` archetype |
| Form | `<form>` with `<input>` elements | Contact/newsletter/CTA |
| Carousel | `swiper`/`carousel`/`slider` class, `overflow-x` scroll | Carousel component |

### C3. Gap Report Aggregation

`aggregateGapReport(colorGaps, archetypeGaps, patternGaps, project, url)` merges all gap sources into a single structured report:

```json
{
  "project": "gsap-homepage",
  "url": "https://gsap.com/",
  "timestamp": "2026-02-11T00:00:00Z",
  "summary": {
    "total_sections": 6,
    "high_confidence_mappings": 2,
    "low_confidence_mappings": 4,
    "total_gaps": 8
  },
  "gaps": [
    {
      "id": "gap-001",
      "type": "missing_color_system_feature",
      "severity": "high",
      "description": "Site uses per-section accent colors. Preset format only supports single accent.",
      "evidence": { "gradient_stops": ["#0ae448", "#..."], "section_associations": {} },
      "extension_task": "Add section_accents map to style-schema.md and preset _template.md. Update url-to-preset.js prompt to output per-section accents."
    },
    {
      "id": "gap-002",
      "type": "missing_archetype_keyword",
      "severity": "medium",
      "description": "Section with classNames 'brands' mapped to FEATURES at 30% confidence.",
      "evidence": { "classNames": "brands", "label": "Brands using GSAP®" },
      "extension_task": "Add 'brands' to LOGO-BAR keywords in archetype-mapper.js"
    }
  ],
  "gap_types": {
    "missing_archetype_keyword": 2,
    "missing_color_system_feature": 1,
    "missing_component": 3,
    "low_confidence_mapping": 4,
    "missing_animation_pattern": 1
  }
}
```

Each gap includes:
- **type** — categorical (keyword, component, color, pattern, confidence)
- **severity** — high (blocks accurate output), medium (degrades quality), low (cosmetic)
- **evidence** — raw data that led to the gap
- **extension_task** — specific, actionable, references exact files

### Track C Success Criteria
- Given GSAP extraction data, identifies `character-reveal` from hero GSAP calls
- Registry lookup finds matching component IDs for identified intents
- Brands section with small images → `logo-marquee` UI pattern detected
- All gaps from A, B, C are merged into a single JSON report
- Gap report has correct severity assignments

---

## Track D: Integration

**Files:** `skills/style-schema.md`, `skills/presets/_template.md`, `scripts/quality/url-to-preset.js`, `scripts/orchestrate.py`
**Goal:** Wire identification into the pipeline; extend preset format for multi-accent

### D1. Preset Template + Style Schema Extensions

**Add to `_template.md`** palette section:
```yaml
palette:
  # ... existing fields ...
  accent_secondary:      # optional — second brand color
  accent_tertiary:       # optional — third brand color

section_accents:           # optional — per-section color overrides
  # section_class: tailwind-color
```

**Add to `style-schema.md`** under Color Temperature:
```
### Multi-Accent Systems
When a site uses distinct accent colors per section or product category,
the preset defines secondary/tertiary accents and optional section_accents.

Tokens:
  --color-accent-secondary
  --color-accent-tertiary

Section override format: section_class → tailwind-color
Applied via section generation prompt, not globals.css.
```

**Update** compact style header format:
```
Palette: dark-neutral (black/stone-950/amber-50/orange-500)
  Accents: scroll:green-500 svg:purple-500 text:pink-500 ui:blue-500
```

### D2. Preset Generation Enhancement

**Update** `url-to-preset.js`:
1. Import `hexToTailwindHue` from `design-tokens.js` (replace inline brightness-only function)
2. Accept identification output as additional input (color system type, gradient accents, section color profiles)
3. Update Claude prompt to:
   - Receive identified color system type alongside raw hex values
   - Use `accent_secondary`/`accent_tertiary` when multi-accent detected
   - Populate `section_accents` when per-section theming is found
   - Include gradient-derived accent colors with their Tailwind names

### D3. Section Generation Enhancement

**Update** `orchestrate.py` `stage_sections()` (~line 411):
When `section_accents` exists in the preset and the current section has an override, inject:
```
This section's accent color is green-500 (not the default orange-500).
Use green-500 for highlights, buttons, icons, and accent elements in this section.
```

When pattern identification found specific animation patterns for this section, inject:
```
Identified animation pattern: character-reveal (from reference site GSAP analysis).
Library component available: text/character-reveal.tsx
Use this pattern for the primary text entrance animation in this section.
```

### D4. Pipeline Wiring — Stage 0b

**Add** `stage_identify()` to `orchestrate.py`:

```python
def stage_identify(extraction_dir: Path, project_name: str) -> dict:
    """Stage 0b: Run pattern identification on extraction data."""
    print("\n🔍 Stage 0b: Identifying patterns...")

    result = subprocess.run(
        ["node", str(SCRIPTS_DIR / "quality" / "lib" / "pattern-identifier.js"),
         str(extraction_dir), project_name],
        capture_output=True, text=True
    )

    identification = json.loads(result.stdout)

    # Save gap report
    gap_path = OUTPUT_DIR / project_name / "gap-report.json"
    gap_path.parent.mkdir(parents=True, exist_ok=True)
    gap_path.write_text(json.dumps(identification["gapReport"], indent=2))

    # Print summary
    gaps = identification["gapReport"]["gaps"]
    high = sum(1 for g in gaps if g["severity"] == "high")
    medium = sum(1 for g in gaps if g["severity"] == "medium")
    print(f"  Color system: {identification['colorSystem']['system']}")
    print(f"  Sections identified: {identification['sectionCount']} ({identification['highConfidence']} high confidence)")
    print(f"  Animation patterns: {len(identification['animationPatterns'])} identified")
    print(f"  ⚠ Gaps: {len(gaps)} ({high} high, {medium} medium)")

    return identification
```

**Insert** between `stage_url_extract()` and `stage_scaffold()`. Pass identification output to:
- `url-to-preset.js` (color system + section colors)
- `stage_sections()` (per-section animation patterns + accent overrides)

### D5. Post-Build Gap Summary

After Stage 5 (deploy), print and save:
```
═══ GAP REPORT SUMMARY ═══
8 gaps identified for gsap-homepage build
  HIGH: 2 (multi-accent color, showcase carousel)
  MEDIUM: 3 (keyword expansions needed)
  LOW: 3 (animation patterns without components)

Extension tasks saved to: output/gsap-homepage/gap-report.json
These should be addressed before the next build of a similar site.
═══════════════════════════
```

Append gap summary to `output/{project}/review.md`.

### Track D Success Criteria
- Preset for GSAP site includes `section_accents` with at least green and orange
- Section generation prompt for "Scroll" tool card includes green-500 directive
- Style header includes `Accents:` line when multi-accent is detected
- Pipeline runs Stage 0b between extraction and scaffold
- Gap report saved for every URL-mode build
- Console shows gap summary at end of build

---

## Track T: Test Harness

**File:** `scripts/quality/test-pattern-pipeline.js` (NEW)
**Goal:** Snapshot tests against GSAP extraction data to prevent regressions

### T1. Test Fixtures

Save the GSAP homepage extraction data as a test fixture:
- `scripts/quality/fixtures/gsap-extraction-data.json` — the raw extraction
- `scripts/quality/fixtures/gsap-animation-analysis.json` — the animation analysis
- `scripts/quality/fixtures/gsap-expected-results.json` — expected outputs

### T2. Unit Tests

Test each module independently:

```javascript
// design-tokens tests
assert hexToTailwindHue("#0ae448") === "green-500"
assert hexToTailwindHue("#8B5CF6") === "violet-500"
assert hexToTailwindHue("#F97316") === "orange-500"
assert hexToTailwindHue("#333333") === "gray-800"       // achromatic fallback
assert hexToTailwindHue("#FAFAFA") === "gray-50"         // near-white

// gradient parsing
assert collectGradientColors(fixtureData).accentColors.length >= 4
assert collectGradientColors(fixtureData).gradients[0].stops.length >= 2

// color system
assert identifyColorSystem(tokens, gradients).system === "multi-accent"
assert identifyColorSystem(tokens, gradients).accents.length >= 3

// archetype mapper
const { mappedSections, gaps } = mapSectionsToArchetypes(fixtureData)
assert mappedSections.find(s => s.classNames?.includes("brands")).archetype === "LOGO-BAR"
assert mappedSections.find(s => s.classNames?.includes("showcase")).archetype === "GALLERY"
assert gaps.length > 0  // some low-confidence sections should generate gaps

// pattern identifier
assert matchAnimationPatterns(animationAnalysis).some(p => p.pattern === "character-reveal")
assert aggregateGapReport(...).gaps.every(g => g.extension_task)
```

### T3. Integration Test

Run the full identification pipeline on GSAP fixture data and verify:
1. Color system = multi-accent
2. At least 4 of 6 sections mapped at > 50% confidence (up from 2 of 6)
3. Gap report generated with valid schema
4. All gaps have type + severity + evidence + extension_task

### Test Harness Success Criteria
- `node scripts/quality/test-pattern-pipeline.js` exits 0 with all assertions passing
- Tests run in < 5 seconds (no network calls — fixture data only)
- Any regression in identification quality breaks the test

---

## Implementation Order

Tracks A and B run in **parallel**. Track C starts when both complete. Track D starts when C completes. Track T runs alongside all tracks (fixtures first, then unit tests as each module is built).

| Step | Track | Phase | Files | Effort | Depends On |
|------|-------|-------|-------|--------|------------|
| 1 | T | T1 | `fixtures/gsap-*.json` | Small | None — save existing data |
| 2 | A | A1 | `design-tokens.js` | Small | None |
| 3 | B | B1 | `archetype-mapper.js` | Medium | None |
| — | — | — | *Steps 2–3 run in parallel* | — | — |
| 4 | A | A2 | `design-tokens.js` | Small | Step 2 |
| 5 | B | B2 | `archetype-mapper.js` | Small | Step 3 |
| 6 | A | A3+A4 | `design-tokens.js` | Medium | Step 4 |
| 7 | B | B3 | `archetype-mapper.js` | Small | Step 3 |
| — | — | — | *Steps 4–7 can overlap across tracks* | — | — |
| 8 | T | T2 | `test-pattern-pipeline.js` | Small | Steps 6, 7 |
| 9 | C | C1 | `pattern-identifier.js` (new) | Medium | Steps 6, 7 |
| 10 | C | C2+C3 | `pattern-identifier.js` | Medium | Step 9 |
| 11 | D | D1 | `style-schema.md`, `_template.md` | Small | Step 6 |
| 12 | D | D2 | `url-to-preset.js` | Medium | Steps 9, 11 |
| 13 | D | D3+D4+D5 | `orchestrate.py` | Medium | Steps 10, 12 |
| 14 | T | T3 | `test-pattern-pipeline.js` | Small | Step 13 |
| 15 | — | Validate | Re-run GSAP build | — | All steps |

**Critical path:** 8 steps (A1→A2→A3/A4→C1→C2/C3→D2→D3/D4/D5→Validate)
**Parallelism:** Tracks A+B save ~3 steps vs. the original 13-step waterfall

---

## Validation: Re-run GSAP Build

After implementation, re-run the GSAP homepage build. Expected improvements:

| Section | Before | After |
|---------|--------|-------|
| "Brands using GSAP" | `FEATURES \| icon-grid` 30% | `LOGO-BAR \| scrolling-marquee` 80%+ |
| "Showcase" | `FOOTER \| mega` 50% | `GALLERY \| showcase-reel` 80%+ |
| "GSAP Tools" | `FEATURES \| icon-grid` 30% | `PRODUCT-SHOWCASE \| card-grid` 80%+ |
| Color system | Single `orange-500` accent | Multi-accent with green/purple/pink per tool section |
| Gap report | Did not exist | 5–8 actionable gaps for library extension |
| Fallback sections | 4 of 6 at 30% confidence, unreported | 0 unreported; all flagged with extension tasks |

---

## Carry-Forward: Library Extensions from GSAP Build

These specific extensions should be queued after the pipeline upgrade, informed by the gap report:

1. **Add to `HEADING_KEYWORDS`**: `brands` → LOGO-BAR, `showcase` → GALLERY, `tools` → PRODUCT-SHOWCASE
2. **Add to `CLASS_NAME_SIGNALS`**: All patterns listed in Track B
3. **New section variant**: `FEATURES | interactive-demo` — for sections with live, manipulable demos
4. **New component**: `interactive/easing-visualizer.tsx` — bezier curve editor with animation preview
5. **New component**: `ui/video-showcase-carousel.tsx` — filterable showcase grid with video previews
6. **Style schema update**: `section_accents` map for per-section color theming
7. **Preset template update**: `accent_secondary`, `accent_tertiary`, `section_accents` fields

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Class name signals are site-specific, may cause false positives | Use as signal with 0.8 confidence (not 0.95), combine with other signals. Require at least 2 matching signals for high confidence |
| Gradient parsing regex may miss complex gradients | Start with `linear-gradient` and `radial-gradient`. Log unparseable gradients as gaps |
| Multi-accent detection may over-segment | Use hue clustering with minimum 30° angular distance. Ignore near-white and near-black |
| `animation_search_index.json` is 1.6MB — loading overhead | Cache in memory after first load. Index queries are O(1) hash lookups. Expected < 100ms |
| Gap reports may be noisy on complex sites | Severity filtering — only HIGH in console. Full report in JSON |
| `mapSectionsToArchetypes()` return shape change breaks callers | Update both callers (`url-to-preset.js`, `orchestrate.py` inline script) in the same step (B3) |
| Pattern identifier adds latency to Stage 0 | All identification is local computation — no network calls. Expected < 2s overhead |

---

## Maintenance

| Date | Change | Trigger |
|------|--------|---------|
| 2026-02-10 | Plan created | GSAP homepage stress test exposed systemic pipeline gaps |
| 2026-02-11 | Plan revised (v2) | Retargeted to v0.9.0, updated for v0.8.0 registry, restructured into parallel tracks, added test harness, split responsibilities across modules |

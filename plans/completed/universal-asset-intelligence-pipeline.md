# Universal Asset Intelligence Pipeline (v1.2.0)

**Created:** 2026-02-11
**Status:** Active
**Target Version:** v1.2.0
**Depends On:** v1.1.1 (truncation auto-repair), v1.1.0 (pinned scroll + demo cards), v1.0.0 (GSAP ecosystem)

---

## Problem Statement

The "detect, match, insert, fallback" chain that works for animation patterns doesn't extend to icons, logos, visual content, or UI components. Even for animations -- where the pipeline exists -- injection is incomplete: GSAP.com has all plugins detectable and our library has matching components for every one, yet the generated site used emoji icons, identical CSS gradient placeholders, broken logo rectangles, and no embedded animation demos.

The pipeline detects but doesn't consistently deliver. The system should NEVER produce blank/placeholder output when it has 1,034 components in its library and full extraction data available.

## Design Principle

Every visual element follows the same chain:

```
Extract signal from source site
  → Map to library asset (component, icon, image, SVG)
    → Insert matched asset into section prompt + copy to site
      → If no match: download/integrate from source into library
        → If can't access: find best semantic match from library
          → NEVER leave blank, use emoji, or produce identical placeholders
```

This chain must work identically for: animation components, icons, logos/SVGs, visual content (card thumbnails, backgrounds), and UI components.

---

## Current State Audit

| Signal Type | Extract | Map | Insert | Fallback | Grade |
|-------------|---------|-----|--------|----------|-------|
| Colors | Yes | Yes (hue-aware) | Yes (per-section) | Preset defaults | A |
| Fonts | Yes | Yes (Google Fonts) | Yes (layout.tsx) | Inter | A |
| Text content | Yes | Yes (brief + context) | Yes (prompts) | Claude generates | A |
| Animation patterns | Yes | Yes (registry search) | Yes (component copy) | fade-up-stagger | B+ |
| Animation components | Partial | Yes (selectAnimation) | Section-level only | Snippet | B- |
| Images | Partial (URLs) | Yes (categories) | Yes (download) | **CSS gradient** | C |
| SVG/Icons | **None** | **None** | **None** | **Emoji** | F |
| Logos | **None** (inline SVGs missed) | Category exists | Would work if URLs existed | **Text-in-div** | F |
| UI components | Partial (detection only) | **No library match** | **No insertion** | **Claude guesses** | D |
| Card-level content | **None** | **None** | **None** | **Identical gradients** | F |

---

## Phase 1: Prompt Hardening (rules only, no pipeline code)

### 1a: Ban emoji globally

**Files:** `templates/section-prompt.md`, `templates/section-instructions-gsap.md`, `templates/section-instructions-framer.md`

Add to section-prompt.md rules:

```
NEVER use emoji characters (unicode symbols like arrows/checkmarks are acceptable).
For icons, import from lucide-react: `import { Zap, Globe, Shield } from 'lucide-react'`.
Render icons as: `<Zap className="w-6 h-6" />`.
```

Add same rule to both instruction templates.

**Test:** Generate any section with icon needs -- zero emoji in output.

### 1b: Add Lucide React as standard dependency

**Files:** `scripts/orchestrate.py` (stage_deploy deps dict)

Add `lucide-react` to the always-included dependencies (alongside `clsx`, `tailwind-merge`).

Add semantic icon mapping reference to section-prompt.md:

```
Icon mapping by section type:
- FEATURES: Zap (performance), Shield (security), Globe (global), Users (community),
  Code (developer), Gauge (speed), Lock (privacy), Layers (architecture)
- PRICING: Check, X, Star, Crown, Infinity
- HOW-IT-WORKS: ArrowRight, ChevronDown, Play, Lightbulb
- TRUST: Award, BadgeCheck, ShieldCheck, Trophy
- CONTACT: Mail, Phone, MapPin, Clock, MessageCircle
- STATS: TrendingUp, BarChart3, Activity, Target
```

**Test:** Generated sections use `<Zap className="w-6 h-6" />` not emoji.

### 1c: Logo rendering fallback rule

**Files:** `templates/section-prompt.md`

Add rule:

```
For LOGO-BAR and SOCIAL-PROOF sections without actual logo image URLs:
- Render company names as styled text pills: rounded border, brand font,
  subtle bg (e.g., bg-white/5 border border-white/10 px-6 py-3 rounded-full)
- Size all pills consistently (min-w-[120px] h-12 flex items-center justify-center)
- For scrolling marquee: use CSS @keyframes animation, duplicate the row for seamless loop
- NEVER render logos as <img> tags with missing/broken src attributes
```

**Test:** LOGO-BAR sections render clean text pills, not broken images.

---

## Phase 2: Extraction Upgrades

### 2a: Inline SVG extraction in Playwright

**Files:** `scripts/quality/lib/extract-reference.js`

Add to the DOM extraction pass:

```javascript
// Extract inline SVGs from logo containers and icon elements
const svgElements = await page.evaluate(() => {
  const svgs = [];
  // Logo SVGs
  document.querySelectorAll('[class*="logo"] svg, [class*="brand"] svg, [class*="partner"] svg').forEach(svg => {
    svgs.push({
      category: 'logo',
      viewBox: svg.getAttribute('viewBox'),
      innerHTML: svg.innerHTML.substring(0, 2000), // cap size
      parentClasses: svg.parentElement?.className || '',
      width: svg.getAttribute('width'),
      height: svg.getAttribute('height'),
    });
  });
  // Icon SVGs (smaller, in feature/card containers)
  document.querySelectorAll('[class*="icon"] svg, [class*="feature"] svg').forEach(svg => {
    const box = svg.getBoundingClientRect();
    if (box.width < 80 && box.height < 80) { // icon-sized
      svgs.push({
        category: 'icon',
        viewBox: svg.getAttribute('viewBox'),
        innerHTML: svg.innerHTML.substring(0, 1000),
        parentClasses: svg.parentElement?.className || '',
      });
    }
  });
  return svgs;
});
```

Output: `extraction-data.json` gains `assets.svgs[]` array.

**Test:** Extract gsap.com, check `assets.svgs` contains logo and icon SVGs.

### 2b: Icon library detection

**Files:** `scripts/quality/lib/extract-reference.js`

Detect icon library from DOM class names and script sources:

```javascript
// Detect icon library usage
const iconLibrary = await page.evaluate(() => {
  const signals = { library: null, icons: [] };
  // Lucide
  if (document.querySelector('[class*="lucide-"]')) {
    signals.library = 'lucide';
    document.querySelectorAll('[class*="lucide-"]').forEach(el => {
      const cls = [...el.classList].find(c => c.startsWith('lucide-'));
      if (cls) signals.icons.push(cls.replace('lucide-', ''));
    });
  }
  // Heroicons
  if (document.querySelector('[class*="hero-"]') || document.querySelector('svg[data-slot="icon"]')) {
    signals.library = 'heroicons';
  }
  // Font Awesome
  if (document.querySelector('[class*="fa-"]')) {
    signals.library = 'font-awesome';
    document.querySelectorAll('[class*="fa-"]').forEach(el => {
      const cls = [...el.classList].find(c => c.startsWith('fa-') && c !== 'fa-solid' && c !== 'fa-regular');
      if (cls) signals.icons.push(cls.replace('fa-', ''));
    });
  }
  return signals;
});
```

Output: `extraction-data.json` gains `assets.iconLibrary` object.

**Test:** Extract a site using Lucide/FA icons, verify detection.

### 2c: Enhanced logo extraction

**Files:** `scripts/quality/lib/extract-reference.js`, `scripts/quality/lib/asset-injector.js`

Target `<img>` tags in logo containers + inline SVGs:

```javascript
// Logo images
document.querySelectorAll('[class*="logo"] img, [class*="brand"] img, [class*="partner"] img, [class*="client"] img').forEach(img => {
  if (img.src && !img.src.includes('data:image/gif')) {
    logos.push({ url: img.src, alt: img.alt, type: 'raster' });
  }
});
```

In asset-injector: add logo-specific download to `public/images/logos/`, mapped to LOGO-BAR and SOCIAL-PROOF sections.

**Test:** Extract a site with raster logos, verify download + section mapping.

---

## Phase 3: Library Matching & Fallback Chain

### 3a: Icon mapping pipeline

**New file:** `scripts/quality/lib/icon-mapper.js`

Core: maintain a semantic map of ~200 common icon concepts to Lucide React names.

```javascript
const SEMANTIC_ICON_MAP = {
  // Performance / Speed
  'performance': 'Zap', 'speed': 'Gauge', 'fast': 'Zap', 'lightning': 'Zap',
  // Security
  'security': 'Shield', 'lock': 'Lock', 'safe': 'ShieldCheck', 'protect': 'Shield',
  // Global / World
  'global': 'Globe', 'world': 'Globe', 'international': 'Globe',
  // Community / Users
  'community': 'Users', 'team': 'Users', 'people': 'Users', 'developer': 'Code',
  // Documents / Content
  'docs': 'BookOpen', 'documentation': 'BookOpen', 'guide': 'BookOpen',
  // ... ~200 mappings
};

// Archetype-based fallback when no extraction data
const ARCHETYPE_ICON_DEFAULTS = {
  'FEATURES': ['Zap', 'Shield', 'Globe', 'Users', 'Code', 'Gauge', 'Lock', 'Layers'],
  'PRICING': ['Check', 'X', 'Star', 'Crown', 'Infinity', 'BadgeCheck'],
  'HOW-IT-WORKS': ['ArrowRight', 'ChevronDown', 'Play', 'Lightbulb'],
  'TRUST': ['Award', 'BadgeCheck', 'ShieldCheck', 'Trophy'],
  'STATS': ['TrendingUp', 'BarChart3', 'Activity', 'Target'],
};
```

**Interface:**
- Input: extracted icon names (from 2b) + section archetype
- Output: per-section icon assignments (specific Lucide component names)
- Injected into section prompt as `icon_context_block`

**Test:** FEATURES section gets 8 unique Lucide icon names, zero emoji.

### 3b: Visual content fallback chain

**Files:** `scripts/quality/lib/asset-injector.js` (enhance existing)

When `categorizedAssets` returns zero images for a section, activate the fallback chain:

```javascript
const SECTION_VISUAL_FALLBACK_MAP = {
  'HERO':              ['aurora-background', 'perspective-grid'],
  'FEATURES':          ['gradient-shift', 'floating'],
  'PRODUCT-SHOWCASE':  ['staggered-grid', 'perspective-grid'],
  'GALLERY':           ['parallax-layers', 'aurora-background'],
  'ABOUT':             ['blur-fade', 'floating'],
  'STATS':             ['count-up', 'gradient-shift'],
  'CTA':               ['aurora-background', 'glow-border'],
  'TESTIMONIALS':      ['floating', 'blur-fade'],
};

// For card grids: each card index maps to a different component
const CARD_VISUAL_COMPONENTS = [
  'aurora-background',
  'perspective-grid',
  'gradient-shift',
  'floating',
  'staggered-grid',
  'glow-border',
  'border-beam',
  'parallax-layers',
];
```

When fallback activates:
1. Look up archetype in `SECTION_VISUAL_FALLBACK_MAP`
2. Select component (rotating through options, no duplicates within a page)
3. Inject component import + usage example into section prompt
4. Copy component to site during stage_deploy

For card grids specifically: each card at index `i` gets `CARD_VISUAL_COMPONENTS[i % length]`.

**Test:** Gallery section without images uses `aurora-background` instead of identical CSS gradients. 6 cards use 6 different decorative components.

### 3c: Card-level animation embedding

**Files:** `scripts/quality/lib/animation-injector.js` (enhance CARD_ANIMATION_MAP)

Upgrade from describing hover effects to injecting actual library component code per card:

```javascript
const CARD_EMBEDDED_DEMOS = {
  'ScrollTrigger': { component: 'scroll-progress',    file: 'scroll/scroll-progress.tsx' },
  'SplitText':     { component: 'splittext-chars',     file: 'text/splittext-chars.tsx' },
  'DrawSVG':       { component: 'drawsvg-reveal',      file: 'entrance/drawsvg-reveal.tsx' },
  'MorphSVG':      { component: 'morphsvg-icon',       file: 'interactive/morphsvg-icon.tsx' },
  'Flip':          { component: 'flip-expand-card',     file: 'interactive/flip-expand-card.tsx' },
  'MotionPath':    { component: 'motionpath-orbit',     file: 'continuous/motionpath-orbit.tsx' },
  'Draggable':     { component: 'draggable-carousel',   file: 'interactive/draggable-carousel.tsx' },
  'ScrambleText':  { component: 'scramble-text',        file: 'text/scramble-text.tsx' },
  'Observer':      { component: 'observer-swipe',       file: 'interactive/observer-swipe.tsx' },
};
```

For PRODUCT-SHOWCASE demo-cards:
- Each card gets its plugin's actual component rendered inside it as a mini-demo
- The component source is read from the library and included in the prompt context
- The prompt instruction says: "Import this component and render it inside the card as a live animation preview"

**Test:** GSAP plugin cards each show a DIFFERENT running animation, not static icons.

### 3d: UI component injection

**Files:** `scripts/quality/lib/pattern-identifier.js` (enhance), new insertion in `animation-injector.js`

When pattern-identifier detects a UI component:

```javascript
const UI_COMPONENT_LIBRARY_MAP = {
  'logo-marquee':   { search: 'marquee infinite scroll', category: 'continuous' },
  'card-grid':      { search: 'card grid staggered', category: 'entrance' },
  'accordion':      { search: 'accordion expand', category: 'interactive' },
  'tabs':           { search: 'tab switch transition', category: 'interactive' },
  'video-embed':    { search: 'video player modal', category: null },
  'image-lightbox': { search: 'image lightbox modal', category: 'interactive' },
  'pricing-toggle': { search: 'toggle switch pricing', category: 'interactive' },
};
```

For each detected UI component:
1. Search animation_search_index.json with the search query
2. If match found in curated library: inject component
3. If match in 21st.dev library: inject component
4. If no match: log gap, proceed with Claude generation (current behavior, but now documented as last resort)

**Test:** Logo marquee detection results in marquee.tsx being injected, not Claude's inline guess.

---

## Phase 4: Pipeline Integration

### 4a: Wire icon context into section prompts

**Files:** `scripts/orchestrate.py` (stage_sections)

```python
# Build icon context block (v1.2.0)
icon_block = ""
if identification:
    icon_data = identification.get("iconMapping", {})
    section_icons = icon_data.get(str(i), [])
    if section_icons:
        icon_block = f"\n═══ ICON CONTEXT ═══\nUse these Lucide React icons for this section:\n"
        icon_block += "\n".join(f"  import {{ {ic} }} from 'lucide-react'" for ic in section_icons)
        icon_block += "\n═══════════════════\n"
```

### 4b: Wire visual fallback into asset-injector.js

Call fallback chain when `categorizedAssets` returns zero images:

```javascript
function getVisualFallback(archetype, sectionIndex, totalSections) {
  const map = SECTION_VISUAL_FALLBACK_MAP[archetype] || ['gradient-shift'];
  const component = map[sectionIndex % map.length];
  // Return component info: name, file path, import statement, usage example
  return { component, file: `.../${component}.tsx`, ... };
}
```

### 4c: Wire UI component injection into stage_deploy

In stage_deploy, alongside animation component copy:

```python
# Copy matched UI components (v1.2.0)
if ui_components:
    for comp in ui_components:
        src = SKILLS_DIR / "animation-components" / comp["file"]
        dst = site_dir / "src" / "components" / "ui" / src.name
        # copy + validate
```

---

## Phase 5: Validation

### 5a: Rebuild gsap.com as gsap-v12

Expected improvements over gsap-v11:
- [ ] Zero emoji -- all icons are Lucide React components
- [ ] Plugin demo cards show live animation previews (6 different components)
- [ ] Logo bar renders styled text pills (not broken image rectangles)
- [ ] Community showcase cards each show a different decorative component
- [ ] Features grid uses Lucide icons with descriptive names
- [ ] Every detected GSAP plugin maps to a library component that renders

### 5b: Rebuild a non-GSAP site (turm-kaffee or cascaid-health)

Validate global applicability:
- [ ] Icons use Lucide React, not emoji
- [ ] Sections without extracted images use library components as visual content
- [ ] Logo bars render cleanly regardless of extraction quality
- [ ] Card grids show differentiated visual content

---

## Parallel Track Strategy

Phases can be parallelized:

```
Phase 1 (prompt rules)  ──→  Independent, do first
Phase 2a-2c (extraction) ──→  Can run in parallel
Phase 3a (icon mapper)   ──→  Independent of extraction (has archetype fallback)
Phase 3b (visual fallback) → Independent of extraction (library-based)
Phase 3c (card embedding) ──→ Depends on 3b
Phase 3d (UI injection)  ──→  Depends on pattern-identifier output
Phase 4 (wiring)         ──→  Depends on Phase 3
Phase 5 (validation)     ──→  Depends on all above
```

**Recommended execution order:**
1. Phase 1 (all 3 items) -- immediate quality improvement, zero risk
2. Phase 3a + 3b in parallel -- library-based, no extraction dependency
3. Phase 2a-2c in parallel -- extraction upgrades
4. Phase 3c + 3d -- depends on earlier phases
5. Phase 4 -- wiring
6. Phase 5 -- validation builds

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Lucide React adds bundle size | Tree-shakeable, only used icons are bundled |
| SVG extraction captures decoration, not logos | Filter by container class (logo, brand, partner) |
| 21st.dev components may have incompatible deps | Validate imports during stage_deploy copy |
| Card-level animation embedding increases token budget | Already at 8192 for demo-cards, may need 10240 |
| Icon semantic mapping has gaps | Archetype-based fallback always provides reasonable defaults |

---

## Success Criteria

1. **Zero emoji** in any generated section across any site type
2. **Zero identical placeholders** -- every card in a grid has visually distinct content
3. **Logo bars render cleanly** -- styled text pills minimum, actual logos when extractable
4. **Every detected animation plugin** maps to a concrete library component that renders
5. **Icon usage is intentional** -- Lucide React icons semantically matched to content
6. **UI component detection produces insertion** -- not just logging
7. **Fallback chain never reaches "do nothing"** -- every branch produces visible output

---

## Files Modified (Estimated)

| File | Changes |
|------|---------|
| `templates/section-prompt.md` | +emoji ban, +icon mapping ref, +logo fallback rule |
| `templates/section-instructions-gsap.md` | +emoji ban |
| `templates/section-instructions-framer.md` | +emoji ban |
| `scripts/orchestrate.py` | +lucide-react dep, +icon_block, +visual fallback wiring |
| `scripts/quality/lib/extract-reference.js` | +SVG extraction, +icon library detection, +logo extraction |
| `scripts/quality/lib/asset-injector.js` | +visual fallback chain, +SECTION_VISUAL_FALLBACK_MAP |
| `scripts/quality/lib/animation-injector.js` | +CARD_EMBEDDED_DEMOS, enhanced buildCardAnimationBlock |
| `scripts/quality/lib/pattern-identifier.js` | +UI_COMPONENT_LIBRARY_MAP, +icon mapping output |
| `scripts/quality/lib/icon-mapper.js` | **NEW** -- semantic icon mapping + archetype defaults |
| `CLAUDE.md` | Version bump, file map, changelog |

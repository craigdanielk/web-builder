# Session Retrospective: Turm Kaffee v3 — Depth Effect & Pixel Trail Polish

**Date**: 2026-02-11
**Duration**: ~25 minutes
**Outcome**: Success

---

## Initial Goal

Deploy turm-kaffee-v3 to Vercel, then add a depth visual effect with a fixed background and a pixel trail animation scoped to the hero section.

## Planned Approach

- Step 1: Deploy existing turm-kaffee-v3 build to Vercel
- Step 2: Add fixed background depth effect with floating content panels
- Step 3: Add pixel trail animation to hero section only
- Step 4: Iterate on transparency and trail image count based on feedback

## What Actually Happened

### Execution Timeline

1. **Initial deploy** — Found `turm-kaffee-v3` in output with full site scaffold (14 sections, 36 animation components, 33 product images). Deployed to Vercel preview — clean build in 6s.

2. **Depth effect implementation** — Three-file change:
   - `globals.css` — Added fixed dark espresso background (`body::before`) with warm amber radial gradients + SVG fractal noise grain texture (`body::after`). Created `.depth-panel`, `.depth-bleed`, `.depth-gap` utility classes.
   - `layout.tsx` — Removed `bg-stone-50` from body to expose fixed background.
   - `page.tsx` — Restructured from flat section list to grouped panels: full-bleed (hero, parallax break, footer) + 4 depth panels (products, features, CTA+about, upsell+retention) with dark gaps between them.

3. **Pixel trail integration** — Modified `cursor-trail.tsx` to support `scoped` mode: when `scoped={true}`, renders inline (no `createPortal`) and only spawns trail images when cursor is within the parent element's bounds. Added `isInscopeRef` for hit-testing. Wired into hero with 5 coffee product images.

4. **User feedback iteration** — Two issues identified after first deploy:
   - White section backgrounds were fully opaque, blocking the depth effect
   - Multiple trail images were too busy; single coffee cup preferred
   
   Fix: Changed `.depth-panel` to `rgba(250, 250, 249, 0.92)` with `backdrop-filter: blur(12px)`. Added `.depth-panel > section { background-color: transparent !important; }` to override hardcoded `bg-stone-50` on 10 sections without editing each file. Reduced trail images from 5 to 1 (cappuccino aerial shot only).

5. **Production deploy** — Final version deployed to production at `site-psi-lake.vercel.app`.

### Key Iterations

**Iteration 1: Panel opacity**
- **Initial approach**: Solid `var(--background)` on depth panels
- **Discovery**: Opaque panels completely hide the fixed depth background — the "depth" effect is invisible
- **Pivot**: Switched to 92% opacity + backdrop blur, added CSS override for section backgrounds inside panels
- **Learning**: When creating depth layering, the "peek-through" effect requires both the container AND its children to be transparent. CSS cascade means child `bg-stone-50` classes override the parent's translucency.

**Iteration 2: Trail image simplification**
- **Initial approach**: 5 different coffee product images cycling through the trail
- **Discovery**: Multiple different images create visual noise, diluting the effect
- **Pivot**: Single cappuccino aerial shot — consistent, recognizable, on-brand
- **Learning**: Cursor trail effects work better with visual consistency; the motion and pixelation already provide variety — the image itself should be a single, strong visual.

## Learnings & Discoveries

### Technical Discoveries

- **`createPortal` vs inline rendering for scoped effects**: The cursor trail component portals to `document.body` by default (full-page effect). Adding a `scoped` prop that renders inline + hit-tests against the parent element's bounds is a clean way to confine interactive effects to specific sections. The parent's `overflow: hidden` naturally clips the trail.

- **CSS section background override pattern**: Rather than editing 10+ section files to remove `bg-stone-50`, a single `.depth-panel > section { background-color: transparent !important; }` rule handles it. The `!important` is justified here because Tailwind utility classes have high specificity. Inner elements (cards, inputs) with `bg-white` are unaffected since they're not direct section children.

- **Backdrop blur + semi-transparent panels**: `backdrop-filter: blur(12px)` with 92% opacity creates a frosted glass effect that lets the dark background show through while keeping text fully readable. The blur prevents the background texture from competing with content.

- **SVG fractal noise for CSS grain texture**: Inline SVG data URI with `feTurbulence` filter creates an organic grain texture without loading an external image. `baseFrequency: 0.7`, `numOctaves: 4`, opacity `0.035` gives a subtle, paper-like feel.

### Process Discoveries

- **Three-file depth pattern is reusable**: The `globals.css` (fixed bg + panel classes) + `layout.tsx` (remove body bg) + `page.tsx` (wrap sections in panels with gaps) pattern can be applied to any build as a post-build enhancement.
- **Deploy-iterate-deploy is fast**: Vercel preview deploys in ~25s. Quick feedback loops made it easy to refine opacity and trail config without over-engineering upfront.

## Blockers Encountered

None — clean execution throughout.

## Final Outcome

### What Was Delivered

- Production deployment of turm-kaffee-v3 with depth visual effects
- Fixed dark espresso background with warm gradient highlights and grain texture
- 4 floating content panels with semi-transparent frosted glass effect
- Dark gap reveals between panel groups for editorial depth feel
- Scoped pixel trail animation on hero section (single cappuccino image)
- Desktop-only trail (hidden on touch devices)

### Files Modified

| File | Change |
|------|--------|
| `globals.css` | Fixed background, grain texture, depth panel classes, pixelated trail CSS |
| `layout.tsx` | Removed `bg-stone-50` from body |
| `page.tsx` | Restructured into depth panels with gaps |
| `cursor-trail.tsx` | Added `scoped` prop for section-confined rendering |
| `03-hero.tsx` | Added CursorTrail import and component with single coffee cup image |

### Success Criteria

- [x] Turm-kaffee-v3 deployed to Vercel production
- [x] Fixed background creates depth/layering effect
- [x] Content sections float above background with visual separation
- [x] Pixel trail confined to hero section only
- [x] Trail uses single coffee cup image
- [x] Semi-transparent panels let background show through
- [x] No build errors or TypeScript failures

## Reusable Patterns

### Pattern: Scoped Cursor Trail

**When to use**: Any section-specific interactive mouse effect
**How it works**: `scoped={true}` prop switches from `createPortal(el, document.body)` to inline rendering. Parent's `overflow: hidden` clips the trail. Hit-test on `mousemove` prevents spawning outside the scope element.
**Watch out for**: Parent must have `position: relative` and `overflow: hidden`

### Pattern: Depth Panel Layering

**When to use**: Adding editorial depth to any flat single-page site
**How it works**: Three files — fixed dark background on body, section groups wrapped in semi-transparent `.depth-panel` divs with backdrop blur, dark gaps between panels
**Watch out for**: Child sections with hardcoded backgrounds need CSS override (`.depth-panel > section { background-color: transparent !important; }`)

### Pattern: CSS Grain Texture (No External Image)

```css
body::after {
  content: '';
  position: fixed;
  inset: 0;
  z-index: 0;
  opacity: 0.035;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.7' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-size: 256px 256px;
  pointer-events: none;
}
```

## Recommendations for Next Time

### Do This

- Deploy first, then iterate — Vercel preview is fast enough for rapid feedback
- Use CSS overrides for bulk section changes rather than editing each file
- Single-image cursor trails look cleaner than multi-image
- Backdrop blur + semi-transparency is the right recipe for "frosted depth"

### Avoid This

- Don't use fully opaque panel backgrounds when trying to create depth — the effect is invisible
- Don't use too many different images in cursor trails — visual noise defeats the purpose
- Don't forget that Tailwind utility classes on section elements will override parent container backgrounds

### If Starting Over

Would implement the depth panel pattern from the start by adding it to `stage_deploy` in orchestrate.py as an optional `--depth` flag. This would auto-wrap the generated `page.tsx` sections into depth panels and add the fixed background CSS during site scaffolding, eliminating the need for post-build manual restructuring.

---

## Next Steps

**Future work:**
- [ ] Consider adding `--depth` flag to orchestrate.py's `stage_deploy` for automatic depth panel generation
- [ ] The scoped cursor trail pattern could be added to the animation component library as a variant
- [ ] Test depth panel effect on dark-themed builds (may need inverted treatment — light fixed bg, dark panels)

---

## Documentation Sync Results

**CLAUDE.md**: No changes needed
- This was a per-project UI enhancement, not a system-level change. No pipeline stages, presets, or system capabilities were modified.

**README.md**: No changes needed
- No user-facing changes to the build system.

**.cursorrules**: No changes needed
- No pipeline changes.

**Version**: v1.1.0 (unchanged — no system-level changes)

---

## Metadata

```yaml
date: 2026-02-11
duration_minutes: 25
outcome: success
tags: [turm-kaffee, depth-effect, cursor-trail, ui-polish, vercel-deploy, visual-enhancement]
project: turm-kaffee-v3
phase: post-build-polish
related_checkpoints: []
```

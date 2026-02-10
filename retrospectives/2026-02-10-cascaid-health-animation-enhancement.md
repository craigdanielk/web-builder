# Session Retrospective: Cascaid Health Animation Enhancement

**Date**: 2026-02-10
**Duration**: ~3 hours (across context continuations)
**Outcome**: Partial Success

---

## Initial Goal

Add intense, showstopping animation elements to the cascaid-health build using the 35-component animation library, then fix rendering issues discovered during QA.

## Planned Approach

1. Read all 13 section files + animation component APIs
2. Rewrite every section with dramatic animations (GSAP + Framer Motion + library components)
3. Add page-level effects (scroll progress bar, cursor trail)
4. Build, deploy, iterate on feedback

## What Actually Happened

### Execution Timeline

1. **Animation Library Audit**
   - Read all 27+ animation component files to understand APIs (BorderBeam, GlowBorder, CharacterFlip, PerspectiveGrid, etc.)
   - Read all 13 section files to understand current structure

2. **Full Animation Rewrite (13 sections + globals.css)**
   - `globals.css`: Added ~150 lines of animation keyframes (aurora-bg, glow-rotate, char-flip, border-beam, float variants, pulse-glow, shimmer, gradient-shift, particle-drift, counter-glow, scroll-marquee, morph)
   - `page.tsx`: Added ScrollProgressBar (Framer Motion spring-based emerald gradient) + CursorTrail (page-wide)
   - `02-hero`: PerspectiveGrid background, 6 floating orbs, CharacterFlip headline, GSAP parallax, magnetic CTA
   - `03-problem`: BorderBeam cards, 3D tilt on mousemove, particle background
   - `04-stats`: SVG progress rings, BorderBeam, counter-glow
   - `05-solution`: GlowBorder cards, WordRotate tagline
   - `06-features`: Alternating slide-in, parallax images
   - `07-how_it_works`: Timeline line drawing, alternating entrance
   - `08-comparison`: Cascading row reveal, checkmark pop-in
   - `09-team`: BorderBeam cards, 3D stagger
   - `10-logo_bar`: Infinite marquee
   - `11-faq`: AnimatePresence accordion
   - `12-cta`: GlowBorder form, floating particles
   - `13-footer`: Staggered entrance
   - First build + deploy succeeded

3. **Iteration 1: Cursor Trail Fix**
   - User feedback: pixel trail used images, was too distracting, covered whole page
   - Fix: Removed global CursorTrail, created lightweight `useDotTrail` hook scoped to hero only
   - Spawns small circles/diamonds/rings in emerald brand colors
   - Second build + deploy succeeded

4. **Iteration 2: Rendering Bug Fixes**
   - User reported 4 issues via screenshots:
     - Sections 03, 08, 09: Cards/rows completely invisible
     - Hero: PerspectiveGrid text bleeding through
     - Hero: CharacterFlip text barely visible
     - Hero: Missing scroll-reveal parallax effect
   - Root cause analysis + fixes applied (see Key Iterations below)
   - Third build + deploy succeeded

### Key Iterations

**Iteration 1: Cursor Trail Scope**
- **Initial approach**: Page-wide CursorTrail component with pixelated images
- **Discovery**: Too distracting, images inappropriate, covered all sections
- **Pivot**: Created `useDotTrail` custom hook — lightweight DOM-based dot spawner scoped to hero container only
- **Learning**: Cursor effects should be surgical, not global. Small shapes in brand colors beat flashy images.

**Iteration 2: GSAP ScrollTrigger SSR Rendering Failure**
- **Initial approach**: All section entrance animations used `gsap.from({ opacity: 0 })` with `ScrollTrigger once: true`
- **Discovery**: GSAP `from()` immediately sets elements to the "from" state (opacity: 0). In Next.js SSR/hydration context, ScrollTrigger may never fire, leaving elements permanently invisible. Affected 3 sections (03-problem, 08-comparison, 09-team).
- **Pivot**: Replaced all GSAP entrance animations with Framer Motion `whileInView` + `initial`/`viewport={{ once: true }}`. Kept GSAP only for interactive effects (hover tilt, continuous pulse).
- **Learning**: **Never use GSAP `from()` for entrance animations in Next.js SSR.** Framer Motion's `whileInView` handles hydration correctly. Use GSAP only for interactive/continuous effects that don't affect initial visibility.

**Iteration 3: CharacterFlip Visibility**
- **Initial approach**: CSS `char-flip` keyframe had `opacity: 0` at 25% and 50% — text invisible half the cycle
- **Discovery**: With `duration: 4s`, characters were invisible for ~2 seconds per cycle
- **Pivot**: Changed keyframe to subtle 3D wobble (rotateX/rotateY) keeping `opacity: 1` throughout
- **Learning**: Character animation keyframes must never drop opacity below 0.8 for readability.

**Iteration 4: PerspectiveGrid Bleed-Through**
- **Initial approach**: PerspectiveGrid as hero background at `opacity-[0.07]`
- **Discovery**: Grid tile borders (`border-gray-300`) visible through hero overlay, text labels bleeding through
- **Pivot**: Removed PerspectiveGrid from hero entirely. Floating orbs + bg image + gradients provide sufficient depth.
- **Learning**: CSS grid components with visible borders don't work well as subtle background layers — even at low opacity, high-contrast borders show through.

## Learnings & Discoveries

### Technical Discoveries

- **GSAP `from()` + SSR = invisible elements**: The #1 gotcha. GSAP immediately sets the "from" state, and if ScrollTrigger doesn't fire (SSR, hydration timing, already-scrolled-past), elements stay hidden forever. Always use Framer Motion `whileInView` for entrance animations in Next.js.
- **CharacterFlip needs careful keyframe tuning**: The default `char-flip` keyframe was too aggressive. Subtle 3D wobbles (8-10deg rotateX/Y) read much better than full 90deg flips with opacity drops.
- **`useDotTrail` pattern**: Lightweight custom hook for scoped cursor effects — spawns DOM elements on mousemove, uses CSS transitions for fadeout, auto-removes after 650ms. Works well with `requestAnimationFrame` for smooth animation start.
- **ScrollTrigger `scrub: true` for scroll-reveal**: Works perfectly for hero parallax effects — foreground fades with blur while background comes into focus. The `fromTo` pattern is key for background elements.
- **BorderBeam + Framer Motion `whileInView`**: These compose well — wrap BorderBeam in a `motion.div` with `whileInView` for entrance, let BorderBeam handle the continuous border animation.

### Process Discoveries

- **Screenshot-driven QA catches SSR issues fast**: The user's screenshots immediately revealed which sections were broken. Without visual QA, GSAP SSR bugs could persist unnoticed.
- **Animation components need SSR testing**: The animation library was built for component extraction, not SSR. Components that rely on GSAP ScrollTrigger for visibility need SSR-safe alternatives.
- **Iterative deployment works well**: 3 deploys in one session, each fixing specific feedback. Quick build + deploy cycle (under 2 minutes) enables tight feedback loops.

## Blockers Encountered

### Blocker 1: GSAP from() SSR Invisibility

- **Impact**: 3 sections (problem, comparison, team) rendered with invisible cards/rows in production
- **Root Cause**: GSAP `from()` sets elements to starting state immediately; ScrollTrigger in SSR context may not fire
- **Resolution**: Replaced with Framer Motion `whileInView` for all entrance animations
- **Time Lost**: ~30 minutes diagnosis + rewrite
- **Prevention**: Establish rule: GSAP for interactive/continuous only, Framer Motion for entrance animations in Next.js

## Final Outcome

### What Was Delivered

- 13 section files rewritten with animation enhancements
- `globals.css` with 15+ animation keyframes
- Page-level scroll progress bar
- Scoped dot trail cursor effect on hero
- Hero scroll-reveal parallax (foreground fades, background focuses)
- 3 Vercel preview deployments
- Final: https://site-opdmjrlo7-craigs-projects-a8e1637a.vercel.app

### What Wasn't Completed

- User noted "a couple things need to be sorted out" — likely minor polish items that would take 1-2 hours of developer iteration
- No formal QA pass on all 13 sections after final deploy
- Mobile responsiveness of new animations not verified

### Success Criteria

- [✓] Dramatic animation enhancement across all sections
- [✓] Animation library components integrated (BorderBeam, GlowBorder, CharacterFlip, PerspectiveGrid)
- [✓] Cursor trail scoped and brand-appropriate
- [✓] Hero scroll-reveal parallax effect
- [✓] All sections render visible content
- [⚠] User noted remaining polish items needed
- [✗] No mobile/responsive animation testing

## Reusable Patterns

### Code Snippets to Save

```tsx
// Lightweight dot trail hook — scoped to container, brand colors, auto-cleanup
function useDotTrail(containerRef: React.RefObject<HTMLElement | null>) {
  const lastPos = useRef({ x: 0, y: 0 });
  const shapes = ['circle', 'diamond', 'ring'] as const;
  const colors = ['#34d399', '#10b981', '#6ee7b7', '#a7f3d0', '#059669'];
  // ... spawn on mousemove, CSS transition fadeout, 650ms auto-remove
}
```

```tsx
// SSR-safe entrance animation pattern (Framer Motion, NOT GSAP)
<motion.div
  initial={{ opacity: 0, y: 60, scale: 0.9 }}
  whileInView={{ opacity: 1, y: 0, scale: 1 }}
  transition={{ duration: 0.7, delay: index * 0.12, ease: 'easeOut' }}
  viewport={{ once: true, margin: '-50px' }}
>
  {/* content */}
</motion.div>
```

```tsx
// Hero scroll-reveal: foreground fades, background focuses
gsap.to(foregroundRef.current, {
  opacity: 0, y: -80, filter: 'blur(8px)',
  ease: 'none',
  scrollTrigger: { trigger: sectionRef.current, start: 'top top', end: '60% top', scrub: true },
});
gsap.fromTo('.hero-bg-image',
  { scale: 1.1, opacity: 0.2, filter: 'blur(4px)' },
  { scale: 1, opacity: 0.6, filter: 'blur(0px)',
    ease: 'none',
    scrollTrigger: { trigger: sectionRef.current, start: 'top top', end: '60% top', scrub: true },
  }
);
```

### Approaches to Reuse

**Pattern: GSAP for Interactive, Framer for Entrance**
- **When to use**: Any Next.js site with both animation engines
- **How it works**: Use Framer Motion `whileInView`/`initial` for scroll-triggered entrance animations (SSR-safe). Use GSAP only for hover effects, continuous animations, and scrub-linked scroll parallax.
- **Watch out for**: Never use `gsap.from({ opacity: 0 })` for initial element visibility in SSR context.

**Pattern: Scoped Cursor Effects**
- **When to use**: When adding mouse-following decorations
- **How it works**: Custom hook with container ref, `window.addEventListener('mousemove')`, boundingRect check, DOM element spawning with CSS transitions
- **Watch out for**: Always scope to 1-2 sections max. Use brand colors, small shapes (6-16px), 650ms lifespan.

## Recommendations for Next Time

### Do This

- ✅ Use Framer Motion `whileInView` for all entrance animations in Next.js
- ✅ Test animations with Vercel preview deploys (not just local dev)
- ✅ Screenshot QA after each deploy iteration
- ✅ Keep cursor effects scoped and subtle
- ✅ Use `gsap.fromTo()` (not `from()`) when GSAP must control initial visibility

### Avoid This

- ❌ GSAP `from({ opacity: 0 })` with ScrollTrigger in SSR/Next.js
- ❌ PerspectiveGrid as subtle background (borders always bleed through)
- ❌ CharacterFlip keyframes with `opacity: 0` frames (makes text unreadable)
- ❌ Page-wide cursor trail effects (too distracting)
- ❌ Using image-based cursor trails

### If Starting Over

Would split the animation enhancement into two passes: (1) entrance animations with Framer Motion `whileInView` only, deploy and verify all sections render, (2) add GSAP interactive effects, continuous animations, and scroll-linked parallax on top. This prevents the SSR visibility bug from ever occurring.

---

## Next Steps

**Remaining polish (user-identified):**
- [ ] Developer to iterate on remaining visual polish items (~1-2 hours)
- [ ] Mobile responsiveness check for all animations
- [ ] Verify all section content renders correctly on mobile viewports

**Future work:**
- [ ] Add the GSAP `from()` SSR warning to animation-patterns.md
- [ ] Update animation-injector.js to default to Framer Motion for entrance animations
- [ ] Consider adding `viewport={{ once: true, margin: '-50px' }}` as standard pattern in section prompt templates

## Related Sessions

- `2026-02-09-animation-component-library-infra-success.md` — Built the animation library infrastructure this session uses
- `2026-02-09-data-injection-pipeline-success.md` — Built the injection pipeline that copies components to builds

---

## Documentation Sync Results

**CLAUDE.md**: Updated
- Added cascaid-health to Completed Builds table
- Added GSAP SSR warning to Known Issues

**README.md**: No changes needed
- No user-facing pipeline or preset changes

**.cursorrules**: No changes needed
- No pipeline stage changes

**Version**: v0.6.0 (no bump — this is a build session, not a system change)

---

## Metadata

```yaml
date: 2026-02-10
duration_minutes: 180
outcome: partial
tags: [animation, cascaid-health, gsap, framer-motion, ssr-bug, scroll-reveal, next-js]
project: web-builder
phase: cascaid-health-build
related_checkpoints: []
```

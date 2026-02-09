# Session Retrospective: Farm Minerals CropTab Promo — Full Rebuild

**Date:** 2026-02-08
**Duration:** ~30 minutes
**Outcome:** Success — 17-section site compiling and serving
**Project:** web-builder / farm-minerals-site

---

## Initial Goal

Build and serve the Farm Minerals CropTab promo website from `briefs/farm-minerals-promo.md`.

## What Actually Happened

### Phase 1: Discovery — Site Already Existed (Partially)

The pipeline had already been run previously. A `farm-minerals-site/` Next.js project existed with 11 generated sections, scaffold output, and assembled page.tsx. Initial attempt was to simply start the dev server.

### Phase 2: Bug — Turbopack CSS Crash

The dev server started but **the page loaded blank**. Investigation revealed Turbopack was panicking on CSS processing:

```
FATAL: An unexpected Turbopack error occurred.
Caused by: [project]/src/app/globals.css [app-client] (css)
  - failed to receive message
  - unable to handle stderr from the Node.js process
  - stream closed unexpectedly
```

The HTML was being served (GET / 200), but CSS compilation crashed on every request, causing Turbopack to panic in a loop. The browser received HTML but no styles — appearing as a blank/hanging page.

**Root cause:** Corrupted `node_modules` causing Turbopack's PostCSS worker IPC to fail when processing `@tailwindcss/postcss`.

**Fix:** `rm -rf .next node_modules && npm install`. Fresh install resolved the IPC crash completely.

**Key learning:** When Turbopack panics on CSS, the symptom is a page that "loads nothing" — the HTML actually arrives but without styles. Always check server logs for FATAL errors, not just HTTP status codes.

### Phase 3: Quality Gap — Pipeline Output vs Actual Site

After fixing the crash, the site rendered but the user correctly identified it as **only ~10-15% of the actual website**. A detailed comparison via WebFetch of `farmminerals.com/promo` revealed massive gaps:

| Dimension | Pipeline Output | Actual Site |
|-----------|----------------|-------------|
| Colors | Pastel green (green-50) | Dark green #404F1D + cream #F4EDE6 + gold #FFBC03 |
| Copy | Generic paraphrased text | Exact brand copy with specific claims |
| Animations | Basic Framer Motion fade-ups | GSAP scroll-triggered, character-by-character reveals, canvas sprites |
| Sections | 11 generic | 17+ distinct sections with specific layouts |
| Interactivity | Static only | SVG trial map, conditional form fields, smooth scroll, mouse trail |
| Typography | Fixed sizes | Viewport-relative (0.96vw desktop, 4vw mobile) |
| Form | Basic fields, no logic | Conditional fields, multi-select, submit states |

**Key insight:** The web-builder pipeline is a pattern recognizer — it maps briefs to section archetypes and assigns style tokens. It does NOT scrape or replicate actual websites. For a site with this level of design sophistication, the pipeline output is a starting skeleton, not a finished product.

### Phase 4: Full Rebuild Decision

User chose "Full rebuild" over incremental fixes. This was the right call — patching 11 generic sections to match a 17-section professionally designed site would have been more work than starting fresh.

### Phase 5: Parallel Execution

Planned and executed the rebuild using:
- **4 parallel agents** building sections in batches (01-04, 05-08, 09-12, 13-17)
- New dependencies: `gsap` (scroll animations), `lenis` (smooth scrolling)
- Complete color system overhaul in globals.css
- New page.tsx assembly with 17 imports

All 17 sections compiled successfully on first attempt. Zero build errors.

---

## Learnings

### Technical

1. **Turbopack + @tailwindcss/postcss IPC crash** — Corrupted node_modules can cause Turbopack's PostCSS worker process to silently fail. The symptom is a page that "loads nothing" because CSS never arrives. Fix: nuke node_modules + .next and reinstall.

2. **Next.js 16 has no --no-turbopack flag** — Turbopack is the default and only bundler. `--no-turbopack` doesn't exist; there's no webpack fallback option in the CLI.

3. **GSAP + React pattern** — The correct pattern for GSAP in React 19 with Next.js:
   ```tsx
   useEffect(() => {
     gsap.registerPlugin(ScrollTrigger);
     const ctx = gsap.context(() => { /* animations */ }, sectionRef);
     return () => ctx.revert();
   }, []);
   ```
   Register plugin inside useEffect, use gsap.context() for cleanup.

4. **Lenis smooth scroll in Next.js App Router** — Must be a client component wrapper imported in layout.tsx. Cannot be in a server component.

### Process

5. **Pipeline output ≠ website replication** — The web-builder pipeline generates from archetypes + style tokens + brief content. It cannot replicate a specific website's design language, animations, or interaction patterns. For replication tasks, WebFetch the target first, then build to match.

6. **WebFetch for design extraction is powerful** — A single WebFetch call extracted the complete color palette, all copy, section structure, animation patterns, typography system, and interactive elements from the actual site. This should be Step 0 for any rebuild-from-reference task.

7. **Parallel agent builds work well for independent sections** — 4 agents writing 4-5 sections each, all completing in ~3-4 minutes. No conflicts because each writes to a unique file path.

8. **The form section is always the heaviest** — At 619 lines (25% of total code), the application form with conditional fields, multi-select checkboxes, and submit state management took the longest to build.

---

## Blockers Encountered

| Blocker | Resolution | Time Lost |
|---------|-----------|-----------|
| Turbopack CSS crash (blank page) | rm -rf node_modules .next && npm install | ~5 min |
| No --no-turbopack CLI flag | Didn't need it after fresh install fixed the crash | ~1 min |

---

## Deliverables

| Artifact | Location | Status |
|----------|----------|--------|
| 17 section components | farm-minerals-site/src/components/sections/*.tsx | Complete |
| Updated globals.css | farm-minerals-site/src/app/globals.css | Complete |
| Updated layout.tsx | farm-minerals-site/src/app/layout.tsx | Complete |
| Updated page.tsx | farm-minerals-site/src/app/page.tsx | Complete |
| Lenis smooth scroll wrapper | farm-minerals-site/src/components/smooth-scroll.tsx | Complete |
| New deps (gsap, lenis) | farm-minerals-site/package.json | Installed |

**Total lines of code:** 2,456 (sections only) + ~80 (global files) = ~2,536 lines

---

## What's Still Missing (vs actual site)

These items were NOT replicated because they require original assets or are beyond the scope of a code rebuild:

1. **150-frame AVIF sprite animation** (CropTab dissolving in water) — needs actual image sequence
2. **120-frame plant growth interactive demo** — needs actual sprite frames + click interaction
3. **Background video/AVIF** in hero — needs actual media asset
4. **Product photography** — all product cards use placeholders
5. **Mouse trail cursor effect** — decorative, deprioritized
6. **Viewport-relative typography** (0.96vw system) — used responsive Tailwind instead
7. **Character-by-character SplitText animation** — GSAP SplitText is a paid plugin; used word-level stagger instead
8. **Nav color-switching on scroll over sections** — partially implemented (transparent→solid), full section-aware color switching would need IntersectionObserver per section

---

## Reusable Patterns

### GSAP ScrollTrigger in React (reuse for any section)
```tsx
useEffect(() => {
  gsap.registerPlugin(ScrollTrigger);
  const ctx = gsap.context(() => {
    gsap.from(".animate-item", {
      y: 40, opacity: 0, stagger: 0.15, duration: 0.8,
      scrollTrigger: { trigger: sectionRef.current, start: "top 80%" }
    });
  }, sectionRef);
  return () => ctx.revert();
}, []);
```

### Conditional form fields pattern
```tsx
const [showOther, setShowOther] = useState(false);
// In checkbox: onChange={() => setShowOther(!showOther)}
// Field: <div className={`transition-all duration-300 overflow-hidden ${showOther ? 'max-h-20 opacity-100' : 'max-h-0 opacity-0'}`}>
```

### Farm Minerals color system (reuse for dark-green + cream sites)
```css
--bg-cream: #F4EDE6;
--dark-green: #404F1D;
--light-green: #8fa36c;
--bright-green: #a7bf85;
--gold: #FFBC03;
```

---

## Recommendations

1. **Update the web-builder brief template** to include a "Reference URL analysis" step — run WebFetch on the target URL BEFORE generating, and use the extracted design details to inform section content and styling.

2. **Add GSAP as an animation option** in the style schema alongside Framer Motion. GSAP's ScrollTrigger is significantly more capable for scroll-based animations.

3. **Create a "rebuild-from-reference" pipeline** separate from the "generate-from-brief" pipeline. The two tasks have fundamentally different inputs and quality bars.

4. **The 16-application-form.tsx pattern** (619 lines, conditional fields, multi-select, submit states) should be extracted as a reusable form template in the section taxonomy.

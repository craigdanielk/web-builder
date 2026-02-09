# Session Retrospective: Turm Kaffee v2 — Full Build, Deploy & Image Integration

**Date:** 2026-02-08
**Outcome:** SUCCESS
**Duration:** Extended session (multi-context, context handoff mid-session)
**Build:** turm-kaffee-v2 (11 sections, artisan-food preset)

---

## Initial Goal

Build the Turm Kaffee v2 website from the brief at `briefs/tuem-kaffee-v2.md` using the full web-builder pipeline. Deploy to a local dev server for preview. Integrate placeholder imagery from Unsplash for all visual sections.

---

## Planned Approach

Follow the 6-step pipeline defined in `.cursorrules`:
1. Read the brief
2. Match preset (artisan-food)
3. Generate scaffold → `output/turm-kaffee-v2/scaffold.md`
4. Generate each section one-at-a-time → `output/turm-kaffee-v2/sections/`
5. Assemble into `page.tsx`
6. Run consistency review

Then deploy to the existing `turm-kaffee-site/` Next.js project and replace placeholder image paths with real Unsplash CDN URLs.

---

## What Actually Happened

### Phase 1: Pipeline Execution (11 Sections)

**Brief:** `briefs/tuem-kaffee-v2.md` — Turm Kaffee, St. Gallen Switzerland, heritage coffee roaster since 1936. V2 is a more complete e-commerce-ready design with product categories, weekly offers, barista academy, and contact.

**Preset Match:** `artisan-food` (exact match)

**Scaffold Adaptation:** Expanded from the preset's default 8-section sequence to 11 sections:
- Added LOGO-BAR (scrolling-marquee) for brand values ticker
- Added dual PRODUCT-SHOWCASE sections (category-grid + hover-cards for weekly offers)
- Added CTA (split-with-image) for Barista Academy
- Added TRUST-BADGES (icon-strip)
- Added CONTACT (info-plus-form)
- Upgraded FOOTER to mega variant

**Section Generation:** All 11 sections generated one-at-a-time with compact style header restated each pass:
```
Palette: warm-earth — bg:stone-50/white text:stone-900 accent:amber-700 border:stone-200
Type: serif-sans — heading:DM Serif Display,700 body:DM Sans,400 scale:1.333
Space: generous — sections:py-24 internal:gap-8
Radius: medium — buttons:rounded-lg cards:rounded-xl inputs:rounded-lg
Motion: moderate — entrance:fade-up-stagger hover:lift-shadow timing:0.6s ease-out
Density: low | Images: full-bleed
```

**Consistency Review:** 30/30 PASS across all dimensions.

### Phase 2: Deployment to Dev Server

- Cleared old v1 section components from `turm-kaffee-site/src/components/sections/`
- Copied all 11 v2 section files into the project
- Updated `src/app/page.tsx` with new imports and component usage
- Updated `src/app/layout.tsx` metadata
- Ran `npm run dev` in `turm-kaffee-site/`

**Bug 1: Port 3000 locked**
- Stale `.next/dev/lock` file and zombie process from previous session
- Fix: `rm .next/dev/lock` + `kill` stale process + restart

**Bug 2: Maximum update depth exceeded (infinite re-render loop)**
- `05-product-showcase-offers.tsx` had a `useCountdown` hook with `nextSunday` as a dependency
- `nextSunday` was a `new Date()` created on every render → new reference each time → infinite loop
- Fix: Wrapped `nextSunday` in `useMemo(() => { ... }, [])` to stabilize the reference
- **Pattern worth remembering:** Any `Date` object used as a `useEffect` dependency MUST be memoized

### Phase 3: Placeholder Image Integration

**Initial approach:** Generated Unsplash URLs using `photo-TIMESTAMP-HASH` format from memory
**Problem:** Several IDs were fabricated/invalid → 404 errors on the CDN

**Resolution approach:**
1. Browsed Unsplash search pages in the browser
2. Extracted photo page hrefs (e.g., `/photos/slug-SHORTID`)
3. Fetched each photo page to find the actual CDN URL in the `<img>` tag
4. CDN URL format confirmed: `https://images.unsplash.com/photo-{TIMESTAMP}-{HASH}?auto=format&fit=crop&w={WIDTH}&q={QUALITY}`

**14 verified Unsplash CDN URLs sourced for:**

| Section | Image | CDN ID |
|---------|-------|--------|
| Hero | Dark steaming coffee cup | `photo-1753572736770-6abc29d123d8` |
| Category: Coffee | Coffee beans closeup | `photo-1561986845-fbeb7f7913d8` |
| Category: Tea | Tea cup on wooden table | `photo-1677161825339-631a230988e6` |
| Category: Machines | Espresso portafilter | `photo-1522659516672-189a712c29af` |
| Category: Accessories | Chemex pour-over | `photo-1522675397120-8cb88c83ac16` |
| Category: Gifts | Coffee bags in burlap | `photo-1565273975921-c884f2b703df` |
| Offer: Ethiopian | Coffee bag product | `photo-1559056199-641a0ac8b55e` |
| Offer: Colombia | Beans in bowl macro | `photo-1712251769743-d5a18ae2a577` |
| Offer: Guatemala | Coffee carton box | `photo-1586054070406-585cac3d08f5` |
| Offer: Swiss Blend | Two bags of beans | `photo-1565273975921-c884f2b703df` |
| Craft: Roasting | Industrial roaster | `photo-1741994043738-393513f7bf52` |
| Craft: Freshness | Beans in bowl | `photo-1712251769743-d5a18ae2a577` |
| Craft: Ritual | Pour-over brewing | `photo-1442512595331-e89e73853f31` |
| Academy CTA | Barista making latte art | `photo-1531441059801-fa3f5859e128` |

**All 14 images verified loading in browser.** All 5 section files updated.

---

## Key Learnings

### Technical

1. **Unsplash CDN URL format:** `https://images.unsplash.com/photo-{TIMESTAMP}-{HASH}` — the TIMESTAMP-HASH is NOT the short alphanumeric photo ID visible in page URLs. You must visit the photo page HTML to find the CDN URL. Never fabricate these IDs.

2. **`useMemo` for Date objects in React effects:** Any `new Date()` used as a `useEffect` dependency must be wrapped in `useMemo` with an empty dependency array. Otherwise, every render creates a new Date reference, triggering the effect again → infinite loop.

3. **Port/lock cleanup on dev server restart:** Next.js dev server leaves `.next/dev/lock` files. If the process dies uncleanly, you must manually remove the lock and kill zombie processes before restarting.

4. **11-section build maintained consistency:** The style header restatement mechanism scales well from 9 sections (v1) to 11 sections (v2) — 30/30 consistency score.

5. **`WebFetch` cannot parse binary image URLs.** When verifying images, use the browser navigation (which shows the image rendered) rather than `WebFetch` (which tries to parse as HTML and fails on binary data).

### Process

6. **Image sourcing is the slowest part of the pipeline.** Generating 11 sections and assembling took less time than finding and verifying 14 working Unsplash CDN URLs. Future builds should either (a) use the Shopify CDN for real product images, or (b) maintain a pre-verified image library by category.

7. **Dual product-showcase sections work well.** Using `category-grid` for browsing and `hover-cards` for promotional offers creates natural visual variety while serving different shopping intents.

8. **The mega footer variant is information-dense.** 11 sections of content + a mega footer pushes the total component count high. Consider if all footer content is necessary or if a simpler variant would suffice.

---

## Blockers Encountered

### Resolved: Fabricated Unsplash URLs
- **Issue:** Initially used made-up `photo-TIMESTAMP-HASH` CDN IDs that returned 404
- **Resolution:** Systematically browsed Unsplash, extracted real CDN URLs from photo page HTML
- **Prevention:** Maintain a verified image library (`skills/image-library.md`) by category

### Resolved: React infinite re-render
- **Issue:** `useCountdown` hook caused max update depth exceeded
- **Resolution:** `useMemo` wrapper on the Date object
- **Prevention:** Always memoize objects used as effect dependencies

### Resolved: Dev server port conflict
- **Issue:** Stale lock file from previous session
- **Resolution:** Manual cleanup + process kill
- **Prevention:** Clean shutdown of dev server between sessions

---

## Final Deliverables

| Deliverable | Location | Status |
|---|---|---|
| v2 Scaffold (11 sections) | `output/turm-kaffee-v2/scaffold.md` | Complete |
| v2 Sections (11 .tsx files) | `output/turm-kaffee-v2/sections/` | Complete |
| v2 Assembled page | `output/turm-kaffee-v2/page.tsx` | Complete |
| v2 Consistency review | `output/turm-kaffee-v2/review.md` | Complete (30/30) |
| Rendered Next.js site | `turm-kaffee-site/` | Complete with images |
| All placeholder images | Verified Unsplash CDN URLs in 5 section files | Complete |

---

## Reusable Patterns

### Pattern: Unsplash CDN URL Discovery
1. Search Unsplash for topic (e.g., "coffee beans dark")
2. Get photo page href from search results (e.g., `/photos/slug-SHORTID`)
3. Fetch photo page HTML with `WebFetch`
4. Extract CDN URL from `<img>` src: `https://images.unsplash.com/photo-{TIMESTAMP}-{HASH}`
5. Use with query params: `?auto=format&fit=crop&w={WIDTH}&q={QUALITY}`

### Pattern: Memoized Date for Countdown Hooks
```tsx
const targetDate = useMemo(() => {
  const d = new Date();
  d.setDate(d.getDate() + (7 - d.getDay()));
  d.setHours(23, 59, 59, 0);
  return d;
}, []);
const countdown = useCountdown(targetDate);
```

### Pattern: Dual Product Showcase
Use two PRODUCT-SHOWCASE sections with different variants:
- `category-grid` for browse-by-category (5 cards, image backgrounds, explore CTAs)
- `hover-cards` for time-limited offers (4 cards, countdown timer, pricing)

---

## Completed Builds to Date

| # | Project | Preset | Sections | Score | Status |
|---|---------|--------|----------|-------|--------|
| 1 | turm-kaffee (v1) | artisan-food | 9 | 30/34 | Complete |
| 2 | farm-minerals-promo | — | 11 | — | Complete |
| 3 | turm-kaffee-v2 | artisan-food | 11 | 30/30 | Complete + deployed |

---

## Handoff State for Next Agent

**Repo:** `/Users/craigkunte/Developer/GitHub/Personal/web-builder`
**GitHub:** https://github.com/craigdanielk/web-builder
**Dev server:** `turm-kaffee-site/` → `npm run dev` → `http://localhost:3000`

**What's done:**
- Full skill package with 20 industry presets
- 3 completed builds (turm-kaffee v1, farm-minerals, turm-kaffee v2)
- turm-kaffee-v2 deployed to Next.js dev server with all images loading
- Comprehensive retrospectives documenting learnings

**What's not done:**
- Section taxonomy structural descriptions still mostly unpopulated
- SDK scripts (`orchestrate.py`, `orchestrate_parallel.py`) untested with live API key
- No automated image library — image sourcing is manual
- Real Shopify CDN integration for product images (planned)
- No CI/CD or Vercel deployment yet

**Key files to read first:**
1. `README.md` — system overview and universal agent onboarding
2. `.cursorrules` — agent pipeline instructions
3. `skills/presets/artisan-food.md` — example of a fully populated preset
4. This retrospective — latest learnings and patterns

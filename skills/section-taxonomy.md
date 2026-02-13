# Section Taxonomy

The canonical list of website section archetypes. Each archetype represents a
distinct functional unit that appears across websites regardless of industry.

Structural descriptions are populated through real project use. Empty entries
are intentional — they get filled the first time you generate that section type.

---

## Navigation & Chrome

### NAV
**Purpose:** Primary site navigation
**Variants:**
- `sticky-transparent` — Transparent on hero, solid on scroll
- `sticky-solid` — Always visible with background
- `mega-menu` — Expanded dropdown with columns
- `sidebar` — Vertical navigation (app-style)
- `hamburger-only` — Mobile-first, icon toggle on all screens
- `centered-logo` — Logo centered, links split left/right

**Animation:** CSS transitions only (bg opacity, text color on scroll). No GSAP needed.
**Structure:** [populate on first use]
**Notes:** []

### ANNOUNCEMENT-BAR
**Purpose:** Top-of-page banner for promotions, shipping info, or alerts
**Variants:**
- `static` — Simple text bar
- `dismissible` — With close button
- `countdown` — With timer element
- `scrolling` — Marquee-style rotating messages

**Animation:** CSS only. Slide-down entrance on page load, marquee via CSS `@keyframes` for `scrolling` variant. No GSAP needed.
**Structure:** [populate on first use]
**Notes:** []

### FOOTER
**Purpose:** Site-wide footer with links, legal, contact
**Variants:**
- `mega` — Multi-column with newsletter, social, sitemap
- `minimal` — Logo, copyright, essential links only
- `newsletter-focused` — Newsletter CTA as primary element
- `split` — Two-column with CTA on one side

**Animation:** `fade-up-single` — lightweight, single entrance on scroll.
**Structure:** [populate on first use]
**Notes:** []

---

## Hero & Opening

### HERO
**Purpose:** First impression, primary value proposition, main CTA
**Variants:**
- `centered` — Text centered, CTA below, optional background image
- `split-image` — Text left, image/mockup right (or reversed)
- `video-background` — Full-bleed video with overlay text
- `full-bleed-overlay` — Full-width image with dark/gradient overlay + text
- `minimal-text` — Large typography only, no image, maximum whitespace
- `animated-gradient` — Animated gradient or mesh background with text
- `editorial` — Magazine-style with asymmetric layout, mixed media
- `product-hero` — Product image dominant with supporting text

**Animation:** `character-reveal` or `word-reveal` on headline + `staggered-timeline` for subtitle → body → CTA. Add `bounce-loop` on scroll indicator chevron.
**Structure:** [populate on first use]
**Notes:** []

---

## Social Proof & Trust

### LOGO-BAR
**Purpose:** Client/partner/press logos for credibility
**Variants:**
- `static-grid` — Logos in a row, grayscale
- `scrolling-marquee` — Infinite horizontal scroll
- `with-stats` — Logos plus key metrics (users, revenue, etc.)

**Animation:** `fade-up-stagger` on logo grid. CSS `@keyframes` for `scrolling-marquee` variant. Add `count-up` if `with-stats` variant.
**Structure:** [populate on first use]
**Notes:** []

### TESTIMONIALS
**Purpose:** Customer quotes and endorsements
**Variants:**
- `carousel` — Rotating cards with photo, name, role, quote
- `grid` — 3-6 testimonials visible at once
- `single-featured` — One large quote, prominent styling
- `video` — Video testimonials with play buttons
- `wall` — Many short quotes in masonry layout

**Animation:** `fade-up-stagger` on cards/quotes. `word-reveal` on featured quote text for `single-featured` variant.
**Structure:** [populate on first use]
**Notes:** []

### STATS
**Purpose:** Key metrics and social proof numbers
**Variants:**
- `counter-animation` — Numbers animate up on scroll
- `icon-grid` — Icon + number + label in grid
- `inline-bar` — Horizontal strip of stats
- `infographic` — Visual/illustrated data presentation

**Animation:** `count-up` per metric (proxy object + onUpdate). `fade-up-stagger` on container elements. Supports prefix/suffix/decimals.
**Structure:** [populate on first use]
**Notes:** []

### TRUST-BADGES
**Purpose:** Security, certification, and guarantee signals
**Variants:**
- `icon-strip` — Row of badge icons
- `certification-logos` — Formal cert logos with labels
- `guarantee-block` — Money-back or satisfaction guarantee

**Animation:** `fade-up-stagger` on badges. Optional `icon-glow` on hover for interactive variants.
**Structure:** [populate on first use]
**Notes:** []

---

## Features & Value Proposition

### FEATURES
**Purpose:** Explain what the product/service does
**Variants:**
- `bento-grid` — Mixed-size cards in bento layout
- `icon-grid` — Icon + title + description in uniform grid
- `alternating-rows` — Image left/right alternating with text
- `tabbed` — Tab navigation switching between feature details
- `accordion` — Expandable feature descriptions
- `cards-with-hover` — Cards that reveal detail on hover

**Animation:** `fade-up-stagger` on cards/rows. Add `icon-glow` on hover for icon-based variants. CSS `hover:scale-105 hover:shadow` for cards.
**Structure:** [populate on first use]
**Notes:** []

### HOW-IT-WORKS
**Purpose:** Process explanation, typically 3-5 steps
**Variants:**
- `numbered-steps` — Vertical numbered list with descriptions
- `horizontal-timeline` — Left-to-right step progression
- `animated-sequence` — Steps reveal sequentially on scroll
- `icon-steps` — Icon + title + description per step

**Animation:** `staggered-timeline` for sequential step reveals. `path-draw` on connecting lines between steps for `horizontal-timeline` variant.
**Structure:** [populate on first use]
**Notes:** []

### COMPARISON
**Purpose:** Us vs them, before/after, or feature comparison
**Variants:**
- `vs-table` — Two-column comparison table
- `before-after-slider` — Draggable slider between two images
- `checkmark-grid` — Feature list with check/cross per competitor

**Animation:** `fade-up-stagger` on table rows or grid items. `line-reveal` on comparison headings.
**Structure:** [populate on first use]
**Notes:** []

---

## Pricing & Conversion

### PRICING
**Purpose:** Plan options and pricing
**Variants:**
- `two-tier` — Simple two-option layout
- `three-tier` — Standard three columns with highlighted recommended
- `toggle` — Monthly/annual toggle switching prices
- `comparison-table` — Feature comparison across all tiers
- `single-product` — One product with quantity/options

**Animation:** `fade-up-stagger` on pricing cards. CSS `hover:scale-105 hover:shadow-xl` on cards. `count-up` on price values for toggle transitions.
**Structure:** [populate on first use]
**Notes:** []

### CTA
**Purpose:** Conversion-focused call to action
**Variants:**
- `centered` — Headline + subtext + button, centered
- `split-with-image` — CTA text on one side, image on other
- `floating-bar` — Sticky bottom bar with CTA
- `gradient-block` — Full-width gradient background with CTA

**Animation:** `staggered-timeline` for heading → subtitle → button sequence. `bounce-loop` on scroll indicator if present.
**Structure:** [populate on first use]
**Notes:** []

### NEWSLETTER
**Purpose:** Email capture / lead generation
**Variants:**
- `inline` — Embedded in page flow with input + button
- `split` — Two-column with value prop + form
- `minimal` — Just an input field and submit

**Animation:** `fade-up-single` on the form block. CSS transitions on input focus states.
**Structure:** [populate on first use]
**Notes:** []

---

## Content & Story

### ABOUT
**Purpose:** Brand story, mission, founding narrative
**Variants:**
- `editorial-split` — Image on one side, narrative text on other
- `timeline` — Chronological milestones
- `team-story` — Narrative with team photos woven in
- `values-grid` — Mission/vision/values in card layout

**Animation:** `word-reveal` on heading. `fade-up-single` on body text. `fade-up-stagger` on `values-grid` cards. `path-draw` on `timeline` connecting lines.
**Structure:** [populate on first use]
**Notes:** []

### TEAM
**Purpose:** Team member showcase
**Variants:**
- `grid-with-hover` — Photo grid, details on hover
- `carousel` — Scrollable team cards
- `minimal-list` — Name + role + photo, compact
- `featured-leadership` — Large cards for leads, small for team

**Animation:** `fade-up-stagger` on team cards. CSS `hover:scale-105` + overlay reveal for `grid-with-hover` variant.
**Structure:** [populate on first use]
**Notes:** []

### FAQ
**Purpose:** Frequently asked questions
**Variants:**
- `accordion` — Expandable question/answer pairs
- `two-column` — Questions split across two columns
- `categorized` — Grouped by topic with tabs or headers
- `searchable` — With search/filter input

**Animation:** `fade-up-stagger` on question items. CSS transitions on accordion expand/collapse (height + opacity). No GSAP needed for accordion motion.
**Structure:** [populate on first use]
**Notes:** []

---

## Product & Portfolio

### PRODUCT-SHOWCASE
**Purpose:** Display products or services
**Variants:**
- `single-hero` — One product large with details
- `grid` — Product card grid with image, name, price
- `hover-cards` — Cards with hover-reveal additional info
- `category-grid` — Grouped by category with headers
- `demo-cards` — Each card demonstrates a different animation technique with a unique visual indicator. Cards share grid layout but differ in: gradient direction/colors, micro-animation (SVG stroke draw, morphing blob, orbiting dot, flip transition, text scramble, 3D rotate), and hover effect. Used when showcasing animation capabilities, plugin features, or diverse product differentiators.

**Animation:** `fade-up-stagger` on product cards. CSS `hover:scale-105 hover:shadow-lg` on cards. `staggered-timeline` for `single-hero` variant (image → title → description → CTA). For `demo-cards` variant: each card gets a UNIQUE micro-animation mapped from `CARD_ANIMATION_MAP` in animation-injector.js — e.g. DrawSVG → card-stroke-draw, MorphSVG → card-morph-blob, MotionPath → card-orbit-dot. Fallback to CSS-only effects when plugins unavailable.
**Structure:** Section wrapper → heading + subheading → responsive grid (2-col md, 3-col lg) → cards. For `demo-cards`: each card = icon/visual indicator + title + description + unique hover micro-animation. No two cards share the same gradient or animation treatment.
**Notes:** The `demo-cards` variant MUST produce visually distinct cards — identical cards defeat the purpose. Card micro-animations should be small (5-8 lines each) to avoid token budget issues. When GSAP plugins are detected, map them 1:1 to card effects; when not detected, use CSS transitions + transforms.

### PORTFOLIO
**Purpose:** Work samples, case studies
**Variants:**
- `masonry` — Mixed-size image grid
- `filtered-grid` — Grid with category filter tabs
- `full-width-showcase` — Full-bleed images with overlay text
- `case-study-cards` — Cards linking to detailed case studies

**Animation:** `fade-up-stagger` on portfolio items. CSS `hover:scale-102` with overlay text reveal on hover. Filter transitions via CSS for `filtered-grid`.
**Structure:** [populate on first use]
**Notes:** []

### BLOG-PREVIEW
**Purpose:** Recent articles or content teasers
**Variants:**
- `card-grid` — 3 cards with image, title, excerpt
- `featured-plus-list` — One large featured + list of recent
- `magazine` — Mixed layout with varied card sizes

**Animation:** `fade-up-stagger` on cards. CSS `hover:shadow-lg hover:-translate-y-1` on cards.
**Structure:** [populate on first use]
**Notes:** []

---

## Media & Visual

### VIDEO
**Purpose:** Video content embed or showcase
**Variants:**
- `full-width-embed` — Full-width video player
- `lightbox-trigger` — Thumbnail that opens video modal
- `background-loop` — Muted looping video as section background

**Animation:** `fade-up-single` on video container. CSS `hover:scale-105` on `lightbox-trigger` play button. No scroll animations on `background-loop` (autoplay on mount).
**Structure:** [populate on first use]
**Notes:** []

### GALLERY
**Purpose:** Image gallery or visual showcase
**Variants:**
- `masonry` — Mixed-size image grid
- `carousel` — Horizontal scrolling images
- `lightbox-grid` — Grid thumbnails opening full-size modal
- `before-after` — Comparison slider

**Animation:** `fade-up-stagger` on gallery items. CSS `hover:scale-102` with overlay on images. Lightbox open/close via CSS transitions.
**Structure:** [populate on first use]
**Notes:** []

---

## Functional

### CONTACT
**Purpose:** Contact form and information
**Variants:**
- `split-with-map` — Form on one side, map on other
- `simple-form` — Centered form with fields
- `multi-step` — Multi-page form wizard
- `info-plus-form` — Contact details + form side by side

**Animation:** `fade-up-stagger` on form fields. `marker-pulse` on map pins for `split-with-map` variant. CSS transitions on input focus states.
**Structure:** [populate on first use]
**Notes:** []

### APP-DOWNLOAD
**Purpose:** Mobile app promotion
**Variants:**
- `device-mockup` — Phone mockup with app store buttons
- `split-features` — App features on one side, mockup on other
- `screenshot-carousel` — App screenshots in device frames

**Animation:** `staggered-timeline` for mockup → heading → buttons sequence. `float-loop` on device mockup for subtle motion. `fade-up-stagger` on feature list.
**Structure:** [populate on first use]
**Notes:** []

### INTEGRATIONS
**Purpose:** Integration partners, tech stack, or ecosystem
**Variants:**
- `logo-grid` — Partner/integration logos in grid
- `scrolling-marquee` — Infinite scroll of logos
- `categorized` — Grouped by integration type

**Animation:** `fade-up-stagger` on logo grid. CSS `@keyframes` for `scrolling-marquee` variant. CSS `hover:grayscale-0` for grayscale-to-color logo reveal.
**Structure:** [populate on first use]
**Notes:** []

---

## Section Count: 25 archetypes, 99+ variants

## Maintenance Log

| Date | Change | Project Source |
|------|--------|---------------|
| 2026-02-08 | Initial skeleton created | — |
| 2026-02-11 | Added PINNED-SCROLL archetype (4 variants) for pinned horizontal scroll | Track A v1.1.0 |
| 2026-02-11 | Removed PINNED-SCROLL archetype — reclassified as animation component (`gsap-pinned-horizontal.tsx`). Pinned horizontal scroll is a presentation technique, not a content type. Applicable to PRODUCT-SHOWCASE, FEATURES, GALLERY, HERO, HOW-IT-WORKS via animation injection. | v1.1.2 |
| 2026-02-08 | Added Animation field to all 25 archetypes with pattern recommendations | farm-minerals-promo rebuild |

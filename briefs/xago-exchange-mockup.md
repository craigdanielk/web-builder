# Brief: xago-exchange-mockup

## Business
Xago is a regulated fintech cross-border exchange for high-net-worth individuals, moving large volumes daily between regulated financial institutions and crypto rails (XRP Ledger, stablecoins, multi-fiat: ZAR, USD, GBP, EUR, USDT, USDC, and more). The product is a React (Create React App) web application at exchange.xago.io. This build is a **mobile-first, enterprise-grade redesign MOCKUP** of the app's hero screens for CEO visual confirmation — **mock/static data, NOT wired to the production backend** (Phase-1). Backend/API stays untouched; this reskins the frontend presentation only.

## What They Need
The app's mobile UI/UX is the business bottleneck. Current-state audit (2026-07-24, captured on iPhone 390×844 via the live authenticated app — this brief IS the seed; no live crawl needed):
- **P1 — CRITICAL: clients cannot transact/trade on mobile.** The wallets view is a desktop-first wide table (Currency × Available/Pending/Open-Orders/Total + Deposit/Send/Receive/Convert per row). On a phone it does not reflow — columns collapse, rows render empty, and the Deposit/Send/Receive/Convert action buttons disappear. The core money actions are unreachable.
- **P2 — KYC/onboarding fails on mobile.** Gated actions surface a "verify your account" prompt as a truncated toast pinned to the top, partly hidden behind the logo. The verification path is unclear.
- Navigation is a slide-out drawer that works but, collapsed, overlaps content with unlabeled icons.
- No mobile design system: dense desktop table crammed to phone width, no mobile type scale, touch targets far below 44×44, non-tabular numerals on a money product, dark theme functional but not enterprise-premium.

**Real audit-engine numbers (2026-07-24, cite these):** overall 50.7/100, HIGH risk, 94 FAILs. Mobile **LCP 12.1s** on the wallets screen (Google "poor" is >4s — ~3× worse), FCP 9.1s, perf 0.51 — the app is very slow to become usable on mobile. Accessibility: **no H1**, **4 form controls without labels**. The redesign must fix perf (lean bundle, fast first paint), accessibility (H1 + labelled controls), and the mobile layout.

Build a mobile-first redesign that makes the money journey work thumb-first, fast, and accessible, at Stripe/Vercel tier of polish.

## Key Requirements (hero screens — build all four, mobile-first)
- **Login** — clean enterprise login (email + 2FA), Xago CI light-accent, mobile-first.
- **Onboarding / KYC** — stepped mobile flow with always-visible progress + inline status; clear "what's needed next" (replaces the truncated toast).
- **Dashboard / Wallets** — replace the table with **mobile asset cards**: one card per currency (icon, code, balance in tabular numerals) with primary actions (Deposit / Send / Receive / Convert) as thumb-reachable buttons and/or a per-asset action sheet, plus a sticky global action bar. No horizontal-scroll table at ≤768px. Sticky header with portfolio value + market selector.
- **Transact / trade** — first-class single-column stepped flow (asset → amount → review → confirm), sticky primary CTA, tabular amounts, clear fee/rate. The core job must be completable on a phone.
- **Navigation** — bottom tab bar or a clean drawer that never overlaps content; labeled targets; 44×44.

## Target Audience
- High-net-worth individuals executing large-value cross-border transactions on mobile.
- Institutional-grade expectations: low friction, high trust, precise data.

## Brand Personality
- Institutional fintech: precise, trustworthy, calm, premium. Confidence without noise. Money-grade clarity (tabular figures, exact rates).

## Design Standard (binding)
Quiet-enterprise synthesis + **light Xago CI traces**: neutral/dark base with a single restrained Xago accent, real type scale, **tabular numerals** for all balances/amounts, 8pt spacing grid, **44×44 touch targets**, sticky thumb-reachable action bars, disciplined ~150ms motion, dark-mode-native, WCAG AA. Vercel/Stripe tier of polish. Pull palette + any brand assets from tenant context (phase0_field_values, creative_assets).

## Build
Next.js + Tailwind + the enterprise tokens; mock/static data; deploy to Vercel; capture mobile/tablet/desktop screenshots of each of the four hero screens for review. Publish the deploy record (live URL + screenshots) as documents slug `exchange-redesign-prototype::xago::2026-07-24`.

# Brief: Xago

## Business
Xago (Xago Technologies Pty Ltd) is a South African fintech, founded 2016 and
regulated by the FSCA, that moves money across borders using stablecoins on the
XRP Ledger. It provides fast, low-cost cross-border transfers and a crypto asset
gateway, with stablecoins pegged 1:1 to supported fiat, reaching into
difficult-to-access corridors. Domain: xago.io. Model: transaction-based SaaS
(no monthly fees; charges per transaction).

## What They Need
Replace two disconnected properties — a WordPress marketing site (xago.io) and a
slow client-rendered React registration/exchange SPA (exchange.xago.io) — with a
single unified Next.js app. Marketing and funnel entry become generated sections;
the exchange functional core (auth / KYC / trading) becomes protected app-routes
mounted on the same shell. This kills the marketing → separate-slow-SPA handoff
and the ~10.8s blank-paint /register.

## Key Requirements
- One unified app shell that marketing pages and protected app-routes both mount on
- Page types: homepage, pricing, signup, KYC, account, checkout, legal
- Conversion-focused signup/registration funnel entry (SIGNUP-FORM, TRUST-BADGES)
- Regulatory trust signals: FSCA regulation, licensing, required risk disclaimers
- Fast first paint — the rebuild exists to fix the SPA performance debt
- Institutional credibility for treasury/business buyers alongside individual remitters

## Target Audience
- Business treasury / cross-border payers
- Individual remitters sending into difficult-to-access corridors
- Crypto asset gateway users (on/off-ramp between fiat and stablecoins)

## Brand Personality
- Technical
- Institutional
- Restrained

## Specific Requests
- Palette: deep navy (#0d0e45 / #222b60) as the institutional base, warm orange
  (#f47643) as the accent, neutral greys (#b5b7ba / #e0e0e0 / #b0b1b3) and white
- Typography: Inter (primary)
- Logo: https://xago.io/wp-content/uploads/2024/08/xago-logo_2-1.png
- Surface the transaction-based, no-monthly-fees pricing story honestly (no rates
  published — do not invent numbers)
- Include the required crypto risk disclaimer on relevant surfaces

## Technical Notes
- Target platform: Vercel (clean Next.js app, no Shopify)
- Industry preset: fintech
- Source stacks being replaced: WordPress (marketing) + client-rendered React SPA (exchange)
- Integrations in the business domain: XRP Ledger, Ripple (not site integrations to build)
- Jurisdiction: South Africa · Regulator: FSCA · Currencies: ZAR, XRP, fiat-pegged stablecoins
- Carried-into-unified-app exchange components (auth/KYC/trading) are seamed as
  protected app-routes, not fabricated

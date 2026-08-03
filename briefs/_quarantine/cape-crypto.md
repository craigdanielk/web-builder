# Brief: Cape Crypto

## Business
Cape Crypto (Pty) Ltd — licensed South African crypto exchange (FSP No. 53746), Cape Town-based. Buy/sell Bitcoin, Ethereum, XRP, USDT. Since 2020. Diff: lowest trade fees SA, ZAR bank deposit/withdraw, Lightning Network support.

## What They Need
Marketing/conversion site → drive signups to trade app (trade.capecrypto.com). Educate + reassure (regulated FSP, SA-based) + funnel to sign-up in <1 min.

## Key Requirements
- Hero: value prop + fee claim + CTA (sign up/sign in)
- 3-step "how it buy works" flow (Sign Up → Deposit → Buy) w/ app screenshots
- Feature grid: fees, easy ZAR deposits, Lightning
- Partner/trust logos section
- FAQ / support block linking help centre
- Footer: legal (FSP disclosure, terms, privacy, travel rule), nav to Wealth Mgmt, Merchant Services, Developers, About
- App store badges (Google Play, App Store)
- Links out to separate subdomains: trade app (auth), support (Zendesk help centre)

## Target Audience
- SA retail crypto newcomers (email-only onboarding signal ease-of-use focus)
- Cost-conscious traders (fee comparison shoppers)
- Merchants/businesses (separate Merchant Services vertical)
- Devs wanting API (Developers link)

## Brand Personality
- Direct, no-fluff ("nothing else required", "no hidden fees, no hassle")
- Locally proud (SA flag imagery, "Proudly South African")
- Trust-forward (licensed FSP, "since 2020" trust marker)
- Speed-focused ("within a minute", "instantly", "lightning-fast")

## Specific Requests
- Keep 3-step visual onboarding w/ screenshots (Sign Up/Deposit/Buy screens)
- Preserve SA flag + local trust cues
- Partner logos row (Numeral, Aluma referenced)
- Separate subdomain arch: main site (marketing) / trade.* (app) / support.* (Zendesk) — keep this split, not merge into monolith

## Technical Notes
- Standard Next.js build
- Multi-subdomain integration: link out cleanly to trade.capecrypto.com (auth) and support.capecrypto.com (Zendesk HC) — no need to rebuild those
- FSP compliance disclaimer must render in footer, full legal text preserved
- App store badge links (iOS/Android)
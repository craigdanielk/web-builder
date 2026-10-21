# Brief: THURIS

## Business
THURIS is a botanical fragrance house (Aweku Laboratories (Pty) Ltd, South Africa). Its first
release, the Founding Collection, is three 10 ml botanical essences — Frankincense (Boswellia
serrata, India), Neroli (Citrus aurantium blossom, France) and Rose Geranium (Pelargonium
graveolens, South Africa). The Founding Release is limited to 90 bottles, 30 of each essence.

## What They Need
A single-page headless Shopify pre-order site (Next.js front end, Shopify Storefront API) that
presents the house and the Founding Collection and takes paid-in-full pre-orders. Checkout stays
disabled until the dispatch window, policies, shipping, tax and payments are approved.

## Key Requirements
- Page copy is operator-authored and supplied as a capture: `intake/thuris/capture-bundle/`.
  Copy source: `intake/thuris/THURIS-launch-copy.md`. Nothing is invented; `[HOLD]` items
  never render.
- Pre-order via a Shopify selling plan, pay in full at checkout; per-essence cap of 30; the complete
  collection draws one unit from each essence and is disabled when any one is fully reserved.
- Two-tone page: dark ceremonial base, light editorial sections where the source marks
  `data-tone="light"`.
- Lead market UAE (AED display); ZAR store base; USD, EUR, AUD, CAD via Shopify Markets conversion.

## Target Audience
- UAE fragrance connoisseurs — value material, provenance and restraint over wellness language
- Luxury gifting buyers in the UAE — want a compact, premium object with a clear story
- International niche-fragrance buyers — want exact naming, origin and straightforward terms

## Brand Personality
- Measured, sensory, precise
- Provenance-led
- Quietly authoritative — demonstrates rather than claims luxury

## Specific Requests
- Brand CI: `intake/thuris/assets/logos/THURIS_Brand_CI_Guide_v1.0.pdf`, with the operator's
  two-mode colour system and decisions in `intake/thuris/RESOLVED-DECISIONS.md`.
- Logo: temporary raster crops from the CI guide (`assets/logos/pdf-raster/`) until production
  vectors exist.
- No generated media — image slots stay empty and are recorded.

## Technical Notes
- Tenant `thuris`, target_platform shopify, source_platform none, industry luxury-premium.
- Store: thuris.myshopify.com.
- Prohibited terms and language are declared in phase 0 and enforced by the compliance gate.

# chowlol202__modern_pricing_table

**Source:** `21st-dev-library/chowlol202/modern-pricing-table.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 267

## Extracted Features

- **Triggers:** time_delay
- **Motion Intents:** exit, slide, stagger
- **Interaction Intents:** none
- **Supported Elements:** heading, card, button
- **Layout Contexts:** table
- **Section Archetypes:** PRICING
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: true
- Composable: false
- Looping: false
- Duration Range: 300ms - 600ms
- Easing: ease-in-out, ease-out

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: low
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **hybrid** component. Has both significant animation patterns (24 motion elements) and UI structure (0 content strings, 2 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 600ms (extracted from code)
- Default easing: ease-in-out, ease-out (extracted)

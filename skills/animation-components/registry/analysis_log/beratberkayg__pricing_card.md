# beratberkayg__pricing_card

**Source:** `21st-dev-library/beratberkayg/pricing-card.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 213

## Extracted Features

- **Triggers:** hover
- **Motion Intents:** exit
- **Interaction Intents:** hover
- **Supported Elements:** card, button
- **Layout Contexts:** card
- **Section Archetypes:** PRICING
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: ease-out

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

Classified as **hybrid** component. Has both significant animation patterns (2 motion elements) and UI structure (7 content strings, 4 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

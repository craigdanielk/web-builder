# ravikatiyar162__card_17

**Source:** `21st-dev-library/ravikatiyar162/card-17.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 109

## Extracted Features

- **Triggers:** hover
- **Motion Intents:** exit, flip
- **Interaction Intents:** hover
- **Supported Elements:** heading, card, button
- **Layout Contexts:** card
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y, z

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
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: false
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: true

## Classification Rationale

Classified as **animation** component. Provides motion primitives. Uses 2 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

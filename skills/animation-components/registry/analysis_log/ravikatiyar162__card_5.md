# ravikatiyar162__card_5

**Source:** `21st-dev-library/ravikatiyar162/card-5.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 115

## Extracted Features

- **Triggers:** click
- **Motion Intents:** stagger
- **Interaction Intents:** engage
- **Supported Elements:** heading, card, button, image
- **Layout Contexts:** card
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 400ms - 400ms
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

Classified as **animation** component. Provides motion primitives. Uses 10 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 400ms - 400ms (extracted from code)
- Default easing: ease-in-out, ease-out (extracted)

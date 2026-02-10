# kavikatiyar__tracker_card

**Source:** `21st-dev-library/kavikatiyar/tracker-card.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 137

## Extracted Features

- **Triggers:** click, mount
- **Motion Intents:** spring
- **Interaction Intents:** engage
- **Supported Elements:** heading, card, button
- **Layout Contexts:** card
- **Section Archetypes:** none
- **Directionality:** omnidirectional
- **Axis:** none

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 1500ms - 1500ms
- Easing: ease-in-out

## Performance and Risk

- GPU Accelerated: false
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **animation** component. Provides motion primitives. Uses 3 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 1500ms - 1500ms (extracted from code)
- Default easing: ease-in-out (extracted)

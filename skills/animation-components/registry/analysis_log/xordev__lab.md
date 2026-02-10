# xordev__lab

**Source:** `21st-dev-library/xordev/lab.tsx`
**Component Type:** animation
**Framework:** none
**Animation Type:** layout
**Line Count:** 186

## Extracted Features

- **Triggers:** mount, resize
- **Motion Intents:** slide
- **Interaction Intents:** none
- **Supported Elements:** any
- **Layout Contexts:** section
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: false
- Interruptible: false
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: false
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: false
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: true

## Classification Rationale

Classified as **animation** component. Provides motion primitives.  Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- No animation framework detected - classification relies on filename signals only.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

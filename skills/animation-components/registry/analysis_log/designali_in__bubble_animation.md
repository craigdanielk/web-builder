# designali_in__bubble_animation

**Source:** `21st-dev-library/designali-in/bubble-animation.tsx`
**Component Type:** animation
**Framework:** none
**Animation Type:** entrance
**Line Count:** 151

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** slide, blur
- **Interaction Intents:** none
- **Supported Elements:** any
- **Layout Contexts:** section
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: true
- Duration Range: 300ms - 800ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: false
- Layout Shift Risk: low
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: false
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **animation** component. Provides motion primitives.  Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- No animation framework detected - classification relies on filename signals only.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

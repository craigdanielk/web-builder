# dhileepkumargm__shader_animation

**Source:** `21st-dev-library/dhileepkumargm/shader-animation.tsx`
**Component Type:** animation
**Framework:** three.js
**Animation Type:** entrance
**Line Count:** 180

## Extracted Features

- **Triggers:** mount
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
- Looping: true
- Duration Range: 300ms - 800ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: false
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: false
- Accessibility Safe: false
- Reduced Motion Fallback: false
- Requires Layout Measurement: true

## Classification Rationale

Classified as **animation** component. Provides motion primitives.  Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

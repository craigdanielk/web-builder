# entrance__fade_up_single

**Source:** `entrance/fade-up-single.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 62

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** reveal, entrance, bounce
- **Interaction Intents:** none
- **Supported Elements:** any
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: spring

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **animation** component. Provides motion primitives. Uses 4 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: spring (extracted)

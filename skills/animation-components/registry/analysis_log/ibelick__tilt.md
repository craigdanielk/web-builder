# ibelick__tilt

**Source:** `21st-dev-library/ibelick/tilt.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 93

## Extracted Features

- **Triggers:** hover
- **Motion Intents:** exit, flip, tilt
- **Interaction Intents:** hover
- **Supported Elements:** any
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** omnidirectional
- **Axis:** z

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: true
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

Classified as **animation** component. Accepts children and wraps them with motion behaviour. Uses 2 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

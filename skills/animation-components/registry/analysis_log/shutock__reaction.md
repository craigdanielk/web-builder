# shutock__reaction

**Source:** `21st-dev-library/shutock/reaction.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 79

## Extracted Features

- **Triggers:** click, time_delay
- **Motion Intents:** exit, slide, rotate
- **Interaction Intents:** engage
- **Supported Elements:** button, any
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x, z

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: true
- Looping: false
- Duration Range: 1000ms - 1000ms
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

Classified as **animation** component. Accepts children and wraps them with motion behaviour. Uses 2 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 1000ms - 1000ms (extracted from code)
- Default easing: ease-in-out, ease-out (extracted)

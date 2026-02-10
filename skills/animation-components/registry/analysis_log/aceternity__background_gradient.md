# aceternity__background_gradient

**Source:** `21st-dev-library/aceternity/background-gradient.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 73

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** emphasis
- **Interaction Intents:** none
- **Supported Elements:** background, any
- **Layout Contexts:** background
- **Section Archetypes:** none
- **Directionality:** omnidirectional
- **Axis:** none

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: true
- Composable: true
- Looping: true
- Duration Range: 5000ms - 5000ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: low
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: false
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **animation** component. Accepts children and wraps them with motion behaviour. Uses 2 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 5000ms - 5000ms (extracted from code)
- Default easing: ease-out (defaulted)

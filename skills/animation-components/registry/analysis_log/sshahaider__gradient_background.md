# sshahaider__gradient_background

**Source:** `21st-dev-library/sshahaider/gradient-background.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** background
**Line Count:** 73

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** gradient
- **Interaction Intents:** none
- **Supported Elements:** background, any
- **Layout Contexts:** background
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: true
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: ease-in-out

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

Classified as **animation** component. Accepts children and wraps them with motion behaviour. Uses 1 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-in-out (extracted)

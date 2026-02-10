# ibelick__text_shimmer_wave

**Source:** `21st-dev-library/ibelick/text-shimmer-wave.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** text
**Line Count:** 90

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** shimmer, flip, slide, emphasis
- **Interaction Intents:** none
- **Supported Elements:** text, any
- **Layout Contexts:** text
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x, z

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: true
- Looping: true
- Duration Range: 300ms - 800ms
- Easing: ease-in-out

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

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-in-out (extracted)

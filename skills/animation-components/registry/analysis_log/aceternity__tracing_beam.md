# aceternity__tracing_beam

**Source:** `21st-dev-library/aceternity/tracing-beam.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** scroll
**Line Count:** 126

## Extracted Features

- **Triggers:** scroll_linked, time_delay
- **Motion Intents:** parallax, glow, spring, progress, beam
- **Interaction Intents:** scroll
- **Supported Elements:** any
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 200ms - 10000ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: false
- Layout Shift Risk: medium
- Scroll Coupling Risk: medium
- Motion Stacking Risk: low
- Mobile Safe: false
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: true

## Classification Rationale

Classified as **animation** component. Provides motion primitives. Uses 11 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 200ms - 10000ms (extracted from code)
- Default easing: ease-out (defaulted)

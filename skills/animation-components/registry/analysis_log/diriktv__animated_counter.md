# diriktv__animated_counter

**Source:** `21st-dev-library/diriktv/animated-counter.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 237

## Extracted Features

- **Triggers:** hover, click, time_delay
- **Motion Intents:** exit, flip, scale, slide, glow, bounce, spring, count, attention, emphasis
- **Interaction Intents:** hover, engage
- **Supported Elements:** any
- **Layout Contexts:** section
- **Section Archetypes:** STATS
- **Directionality:** vertical, horizontal
- **Axis:** y, x, z

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: true
- Duration Range: 300ms - 4000ms
- Easing: linear, ease-out, spring

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

Classified as **animation** component. Provides motion primitives. Uses 20 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 4000ms (extracted from code)
- Default easing: linear, ease-out, spring (extracted)

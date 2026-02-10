# scroll__scroll_progress

**Source:** `scroll/scroll-progress.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** scroll
**Line Count:** 91

## Extracted Features

- **Triggers:** scroll_linked
- **Motion Intents:** spring, progress, emphasis
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
- Composable: true
- Looping: true
- Duration Range: 1250ms - 1250ms
- Easing: ease-in-out

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: low
- Scroll Coupling Risk: medium
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: false
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **animation** component. Accepts children and wraps them with motion behaviour. Uses 3 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 1250ms - 1250ms (extracted from code)
- Default easing: ease-in-out (extracted)

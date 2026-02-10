# scroll__parallax_layers

**Source:** `scroll/parallax-layers.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** scroll
**Line Count:** 64

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** parallax
- **Interaction Intents:** none
- **Supported Elements:** any
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: true
- Looping: false
- Duration Range: 20ms - 20ms
- Easing: linear

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

Classified as **animation** component. Accepts children and wraps them with motion behaviour. Uses 1 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 20ms - 20ms (extracted from code)
- Default easing: linear (extracted)

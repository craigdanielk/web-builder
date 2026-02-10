# scroll__parallax_section

**Source:** `scroll/parallax-section.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** scroll
**Line Count:** 58

## Extracted Features

- **Triggers:** scroll_linked
- **Motion Intents:** parallax, progress
- **Interaction Intents:** scroll
- **Supported Elements:** image
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** omnidirectional
- **Axis:** none

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: low
- Scroll Coupling Risk: medium
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **animation** component. Provides motion primitives. Uses 2 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

# entrance__staggered_grid

**Source:** `entrance/staggered-grid.tsx`
**Component Type:** animation
**Framework:** gsap
**Animation Type:** entrance
**Line Count:** 176

## Extracted Features

- **Triggers:** scroll_linked, mount, time_delay
- **Motion Intents:** stagger
- **Interaction Intents:** scroll
- **Supported Elements:** any
- **Layout Contexts:** section
- **Section Archetypes:** GALLERY
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: true
- Interruptible: false
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

Classified as **animation** component. Provides motion primitives.  Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

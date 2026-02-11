# interactive__flip_grid_filter

**Source:** `interactive/flip-grid-filter.tsx`
**Component Type:** animation
**Framework:** gsap
**Animation Type:** layout
**Line Count:** 65

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** flip
- **Interaction Intents:** filter
- **Supported Elements:** any
- **Layout Contexts:** any
- **Section Archetypes:** GALLERY
- **Directionality:** omnidirectional
- **Axis:** none

## Capabilities

- Stagger: true
- Interruptible: false
- Reversible: false
- Composable: true
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: false
- Layout Shift Risk: low
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: true
- Reduced Motion Fallback: true
- Requires Layout Measurement: false

## Classification Rationale

Classified as **animation** component. Accepts children and wraps them with motion behaviour.  Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

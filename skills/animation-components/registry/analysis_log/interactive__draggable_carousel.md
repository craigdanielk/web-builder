# interactive__draggable_carousel

**Source:** `interactive/draggable-carousel.tsx`
**Component Type:** animation
**Framework:** gsap
**Animation Type:** interactive
**Line Count:** 71

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** slide, drag
- **Interaction Intents:** none
- **Supported Elements:** card, any
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** horizontal
- **Axis:** x

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: true
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: false
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: false
- Accessibility Safe: true
- Reduced Motion Fallback: true
- Requires Layout Measurement: true

## Classification Rationale

Classified as **animation** component. Accepts children and wraps them with motion behaviour.  Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

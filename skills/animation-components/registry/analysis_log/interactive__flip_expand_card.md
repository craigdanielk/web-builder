# interactive__flip_expand_card

**Source:** `interactive/flip-expand-card.tsx`
**Component Type:** animation
**Framework:** gsap
**Animation Type:** entrance
**Line Count:** 56

## Extracted Features

- **Triggers:** click
- **Motion Intents:** flip, collapse, expand
- **Interaction Intents:** engage, expand
- **Supported Elements:** card, any
- **Layout Contexts:** card
- **Section Archetypes:** none
- **Directionality:** omnidirectional
- **Axis:** none

## Capabilities

- Stagger: false
- Interruptible: false
- Reversible: true
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

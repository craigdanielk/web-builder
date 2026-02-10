# interactive__tilt_card

**Source:** `interactive/tilt-card.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 55

## Extracted Features

- **Triggers:** hover
- **Motion Intents:** exit, flip, slide, glow, tilt
- **Interaction Intents:** hover
- **Supported Elements:** card, image
- **Layout Contexts:** card
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x, z

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: ease-in-out, ease-out

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: false
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: true

## Classification Rationale

Classified as **animation** component. Provides motion primitives. Uses 5 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-in-out, ease-out (extracted)

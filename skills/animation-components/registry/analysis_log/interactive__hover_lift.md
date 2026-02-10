# interactive__hover_lift

**Source:** `interactive/hover-lift.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** hover
**Line Count:** 45

## Extracted Features

- **Triggers:** hover
- **Motion Intents:** glow, attention
- **Interaction Intents:** hover
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
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **animation** component. Accepts children and wraps them with motion behaviour. Uses 2 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

# avanishverma4__parallax_text_scroll

**Source:** `21st-dev-library/avanishverma4/parallax-text-scroll.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** scroll
**Line Count:** 96

## Extracted Features

- **Triggers:** scroll_linked
- **Motion Intents:** parallax, spring
- **Interaction Intents:** scroll
- **Supported Elements:** text, any
- **Layout Contexts:** text
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

- GPU Accelerated: true
- Layout Shift Risk: low
- Scroll Coupling Risk: medium
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

# designali_in__text_wave_animation

**Source:** `21st-dev-library/designali-in/text-wave-animation.tsx`
**Component Type:** animation
**Framework:** css
**Animation Type:** text
**Line Count:** 110

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** shimmer
- **Interaction Intents:** none
- **Supported Elements:** text, heading
- **Layout Contexts:** text
- **Section Archetypes:** none
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

- GPU Accelerated: false
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
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

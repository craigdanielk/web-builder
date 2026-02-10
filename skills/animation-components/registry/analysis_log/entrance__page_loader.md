# entrance__page_loader

**Source:** `entrance/page-loader.tsx`
**Component Type:** animation
**Framework:** gsap
**Animation Type:** loading
**Line Count:** 179

## Extracted Features

- **Triggers:** mount, time_delay
- **Motion Intents:** slide, loading
- **Interaction Intents:** none
- **Supported Elements:** any
- **Layout Contexts:** section
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: true
- Interruptible: false
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 100ms - 500ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: low
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

- Default duration: 100ms - 500ms (extracted from code)
- Default easing: ease-out (defaulted)

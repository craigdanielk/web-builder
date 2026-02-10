# shugar__collapse

**Source:** `21st-dev-library/shugar/collapse.tsx`
**Component Type:** animation
**Framework:** none
**Animation Type:** entrance
**Line Count:** 102

## Extracted Features

- **Triggers:** click, mount
- **Motion Intents:** slide, collapse, expand
- **Interaction Intents:** engage, expand
- **Supported Elements:** heading, button
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** horizontal
- **Axis:** x

## Capabilities

- Stagger: false
- Interruptible: false
- Reversible: true
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
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

- No animation framework detected - classification relies on filename signals only.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

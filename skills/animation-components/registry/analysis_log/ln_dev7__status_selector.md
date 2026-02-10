# ln_dev7__status_selector

**Source:** `21st-dev-library/ln-dev7/status-selector.tsx`
**Component Type:** ui
**Framework:** none
**Animation Type:** entrance
**Line Count:** 256

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** entrance
- **Interaction Intents:** select
- **Supported Elements:** button
- **Layout Contexts:** section
- **Section Archetypes:** STATS
- **Directionality:** omnidirectional
- **Axis:** none

## Capabilities

- Stagger: false
- Interruptible: false
- Reversible: false
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

Classified as **UI** component. Contains 6 hardcoded content strings. Imports 3 shadcn/ui components. Large component (256 lines) with structural layout.

## Uncertainty Notes

- No animation framework detected - classification relies on filename signals only.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

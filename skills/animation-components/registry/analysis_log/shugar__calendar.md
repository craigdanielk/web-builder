# shugar__calendar

**Source:** `21st-dev-library/shugar/calendar.tsx`
**Component Type:** ui
**Framework:** none
**Animation Type:** entrance
**Line Count:** 881

## Extracted Features

- **Triggers:** hover, click, focus, mount
- **Motion Intents:** entrance
- **Interaction Intents:** hover, engage, focus, submit
- **Supported Elements:** heading, button
- **Layout Contexts:** section
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y

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
- Mobile Safe: false
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **UI** component. Contains 12 hardcoded content strings. Imports 5 shadcn/ui components. Large component (881 lines) with structural layout.

## Uncertainty Notes

- No animation framework detected - classification relies on filename signals only.
- Very large file - may contain multiple sub-components. Registry entry covers the primary export only.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

# vaib215__event_manager

**Source:** `21st-dev-library/vaib215/event-manager.tsx`
**Component Type:** ui
**Framework:** none
**Animation Type:** exit
**Line Count:** 1494

## Extracted Features

- **Triggers:** hover, click
- **Motion Intents:** exit, drag
- **Interaction Intents:** hover, engage, submit
- **Supported Elements:** heading, card, button
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

Classified as **UI** component. Contains 19 hardcoded content strings. Imports 9 shadcn/ui components. Large component (1494 lines) with structural layout.

## Uncertainty Notes

- No animation framework detected - classification relies on filename signals only.
- Very large file - may contain multiple sub-components. Registry entry covers the primary export only.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

# designali_in__browser

**Source:** `21st-dev-library/designali-in/browser.tsx`
**Component Type:** ui
**Framework:** none
**Animation Type:** entrance
**Line Count:** 752

## Extracted Features

- **Triggers:** click, mount, time_delay
- **Motion Intents:** entrance
- **Interaction Intents:** engage, submit
- **Supported Elements:** heading, card, button, image
- **Layout Contexts:** section
- **Section Archetypes:** none
- **Directionality:** omnidirectional
- **Axis:** none

## Capabilities

- Stagger: false
- Interruptible: false
- Reversible: true
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: false
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: false
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **UI** component. Contains 25 hardcoded content strings. Imports 5 shadcn/ui components. Large component (752 lines) with structural layout.

## Uncertainty Notes

- No animation framework detected - classification relies on filename signals only.
- Very large file - may contain multiple sub-components. Registry entry covers the primary export only.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

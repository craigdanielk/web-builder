# scroll__pin_and_reveal

**Source:** `scroll/pin-and-reveal.tsx`
**Component Type:** ui
**Framework:** none
**Animation Type:** scroll
**Line Count:** 139

## Extracted Features

- **Triggers:** viewport
- **Motion Intents:** reveal, pin
- **Interaction Intents:** none
- **Supported Elements:** heading, card, image
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y

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
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **UI** component. Contains 9 hardcoded content strings.  

## Uncertainty Notes

- No animation framework detected - classification relies on filename signals only.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

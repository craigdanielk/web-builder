# preetsuthar17__spotlight_card

**Source:** `21st-dev-library/preetsuthar17/spotlight-card.tsx`
**Component Type:** animation
**Framework:** none
**Animation Type:** exit
**Line Count:** 64

## Extracted Features

- **Triggers:** hover, focus
- **Motion Intents:** exit, slide, spotlight
- **Interaction Intents:** hover, focus
- **Supported Elements:** card, any
- **Layout Contexts:** card
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: false
- Interruptible: false
- Reversible: false
- Composable: true
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: false
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: true

## Classification Rationale

Classified as **animation** component. Accepts children and wraps them with motion behaviour.  Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- No animation framework detected - classification relies on filename signals only.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

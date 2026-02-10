# text__character_flip

**Source:** `text/character-flip.tsx`
**Component Type:** animation
**Framework:** none
**Animation Type:** entrance
**Line Count:** 106

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** flip, slide
- **Interaction Intents:** none
- **Supported Elements:** text
- **Layout Contexts:** text
- **Section Archetypes:** none
- **Directionality:** horizontal
- **Axis:** x

## Capabilities

- Stagger: true
- Interruptible: false
- Reversible: false
- Composable: false
- Looping: true
- Duration Range: 300ms - 800ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: low
- Scroll Coupling Risk: low
- Motion Stacking Risk: medium
- Mobile Safe: true
- Accessibility Safe: false
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **animation** component. Provides motion primitives.  Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- No animation framework detected - classification relies on filename signals only.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

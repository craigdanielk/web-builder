# ruixen_ui__ruixen_ui_hero

**Source:** `21st-dev-library/ruixen.ui/ruixen-ui-hero.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 138

## Extracted Features

- **Triggers:** mount, time_delay
- **Motion Intents:** slide
- **Interaction Intents:** none
- **Supported Elements:** button, image
- **Layout Contexts:** hero
- **Section Archetypes:** HERO
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 500ms - 1500ms
- Easing: ease-in-out, ease-out

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

Classified as **animation** component. Provides motion primitives. Uses 14 motion elements. 

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 500ms - 1500ms (extracted from code)
- Default easing: ease-in-out, ease-out (extracted)

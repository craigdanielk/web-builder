# ruixen_ui__timeline_02

**Source:** `21st-dev-library/ruixen.ui/timeline-02.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 81

## Extracted Features

- **Triggers:** viewport
- **Motion Intents:** reveal
- **Interaction Intents:** none
- **Supported Elements:** heading, card
- **Layout Contexts:** any
- **Section Archetypes:** HOW-IT-WORKS
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 500ms - 500ms
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

Classified as **animation** component. Provides motion primitives. Uses 2 motion elements. 

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 500ms - 500ms (extracted from code)
- Default easing: ease-out (defaulted)

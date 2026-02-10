# ravikatiyar162__team_showcase

**Source:** `21st-dev-library/ravikatiyar162/team-showcase.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 121

## Extracted Features

- **Triggers:** hover
- **Motion Intents:** exit, scale, slide, bounce, spring, stagger, attention
- **Interaction Intents:** hover
- **Supported Elements:** heading, card, button, image
- **Layout Contexts:** any
- **Section Archetypes:** TEAM, PRODUCT-SHOWCASE
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: spring

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

Classified as **animation** component. Provides motion primitives. Uses 4 motion elements. 

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: spring (extracted)

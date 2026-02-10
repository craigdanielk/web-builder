# ravikatiyar162__guest_selector

**Source:** `21st-dev-library/ravikatiyar162/guest-selector.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 163

## Extracted Features

- **Triggers:** click
- **Motion Intents:** exit, slide
- **Interaction Intents:** engage, select
- **Supported Elements:** heading, button
- **Layout Contexts:** section
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 200ms - 300ms
- Easing: ease-in-out, ease-out, ease-in

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

Classified as **animation** component. Provides motion primitives. Uses 5 motion elements. 

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 200ms - 300ms (extracted from code)
- Default easing: ease-in-out, ease-out, ease-in (extracted)

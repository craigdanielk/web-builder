# ruixen_ui__hybrid_tabs

**Source:** `21st-dev-library/ruixen.ui/hybrid-tabs.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 81

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** exit
- **Interaction Intents:** none
- **Supported Elements:** card
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: true
- Composable: false
- Looping: false
- Duration Range: 250ms - 250ms
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

Classified as **animation** component. Provides motion primitives. Uses 2 motion elements. 

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 250ms - 250ms (extracted from code)
- Default easing: ease-out (defaulted)

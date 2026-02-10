# ruixen_ui__animated_feature_spotlight3d

**Source:** `21st-dev-library/ruixen.ui/animated-feature-spotlight3d.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 141

## Extracted Features

- **Triggers:** hover, time_delay
- **Motion Intents:** exit, flip, scale, bounce, spring, spotlight, attention
- **Interaction Intents:** hover
- **Supported Elements:** button
- **Layout Contexts:** any
- **Section Archetypes:** FEATURES
- **Directionality:** vertical
- **Axis:** y, z

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 600ms
- Easing: spring

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

Classified as **animation** component. Provides motion primitives. Uses 13 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 600ms (extracted from code)
- Default easing: spring (extracted)

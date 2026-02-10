# ravikatiyar162__onboarding_welcome_screen

**Source:** `21st-dev-library/ravikatiyar162/onboarding-welcome-screen.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 143

## Extracted Features

- **Triggers:** click
- **Motion Intents:** bounce, spring, stagger
- **Interaction Intents:** engage
- **Supported Elements:** button, image
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 800ms - 800ms
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

Classified as **animation** component. Provides motion primitives. Uses 14 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 800ms - 800ms (extracted from code)
- Default easing: spring (extracted)

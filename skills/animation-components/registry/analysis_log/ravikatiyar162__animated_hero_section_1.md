# ravikatiyar162__animated_hero_section_1

**Source:** `21st-dev-library/ravikatiyar162/animated-hero-section-1.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 148

## Extracted Features

- **Triggers:** click
- **Motion Intents:** stagger
- **Interaction Intents:** engage
- **Supported Elements:** button
- **Layout Contexts:** hero
- **Section Archetypes:** HERO
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 600ms - 800ms
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

Classified as **animation** component. Provides motion primitives. Uses 10 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 600ms - 800ms (extracted from code)
- Default easing: ease-in-out, ease-out (extracted)

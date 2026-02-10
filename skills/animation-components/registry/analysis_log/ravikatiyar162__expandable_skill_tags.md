# ravikatiyar162__expandable_skill_tags

**Source:** `21st-dev-library/ravikatiyar162/expandable-skill-tags.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 102

## Extracted Features

- **Triggers:** click
- **Motion Intents:** exit, stagger, collapse, expand
- **Interaction Intents:** engage, expand
- **Supported Elements:** heading, button
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: true
- Composable: false
- Looping: false
- Duration Range: 200ms - 200ms
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

Classified as **animation** component. Provides motion primitives. Uses 6 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 200ms - 200ms (extracted from code)
- Default easing: ease-out (defaulted)

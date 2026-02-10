# isaiahbjork__animated_card_options

**Source:** `21st-dev-library/isaiahbjork/animated-card-options.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 140

## Extracted Features

- **Triggers:** hover, click, time_delay
- **Motion Intents:** exit, slide, bounce, spring, attention
- **Interaction Intents:** hover, engage
- **Supported Elements:** heading, card
- **Layout Contexts:** card
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 200ms - 500ms
- Easing: ease-out, spring

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

Classified as **animation** component. Provides motion primitives. Uses 4 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 200ms - 500ms (extracted from code)
- Default easing: ease-out, spring (extracted)

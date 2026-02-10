# uniquesonu__modern_background_paths

**Source:** `21st-dev-library/uniquesonu/modern-background-paths.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 404

## Extracted Features

- **Triggers:** hover, mount, time_delay
- **Motion Intents:** exit, float, flip, scale, slide, rotate, bounce, spring, attention, emphasis
- **Interaction Intents:** hover
- **Supported Elements:** heading, button, background
- **Layout Contexts:** background
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x, z

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: true
- Duration Range: 300ms - 20000ms
- Easing: linear, ease-in-out, ease-out, spring

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: medium
- Mobile Safe: true
- Accessibility Safe: false
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **hybrid** component. Has both significant animation patterns (24 motion elements) and UI structure (1 content strings, 1 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 20000ms (extracted from code)
- Default easing: linear, ease-in-out, ease-out, spring (extracted)

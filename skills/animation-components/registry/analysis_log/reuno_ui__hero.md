# reuno_ui__hero

**Source:** `21st-dev-library/reuno-ui/hero.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 323

## Extracted Features

- **Triggers:** hover, click, mount, time_delay
- **Motion Intents:** exit, scale, slide, rotate, bounce, spring, attention
- **Interaction Intents:** hover, engage
- **Supported Elements:** button
- **Layout Contexts:** hero
- **Section Archetypes:** HERO
- **Directionality:** vertical, horizontal
- **Axis:** y, x, z

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: true
- Composable: false
- Looping: false
- Duration Range: 300ms - 20000ms
- Easing: linear, ease-in-out, spring

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

Classified as **hybrid** component. Has both significant animation patterns (22 motion elements) and UI structure (6 content strings, 0 UI imports).

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 20000ms (extracted from code)
- Default easing: linear, ease-in-out, spring (extracted)

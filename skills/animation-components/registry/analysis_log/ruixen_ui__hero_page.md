# ruixen_ui__hero_page

**Source:** `21st-dev-library/ruixen.ui/hero-page.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 303

## Extracted Features

- **Triggers:** mount, time_delay
- **Motion Intents:** exit, flip, slide, rotate, blur, bounce, spring, stagger
- **Interaction Intents:** none
- **Supported Elements:** heading, card, button, image
- **Layout Contexts:** hero
- **Section Archetypes:** HERO
- **Directionality:** vertical, horizontal
- **Axis:** y, x, z

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 1000ms - 1500ms
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

Classified as **hybrid** component. Has both significant animation patterns (5 motion elements) and UI structure (6 content strings, 2 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 1000ms - 1500ms (extracted from code)
- Default easing: spring (extracted)

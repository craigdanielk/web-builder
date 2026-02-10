# beratberkayg__feature_card

**Source:** `21st-dev-library/beratberkayg/feature-card.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** hover
**Line Count:** 132

## Extracted Features

- **Triggers:** hover, click
- **Motion Intents:** scale, slide, rotate, bounce, spring, attention, emphasis
- **Interaction Intents:** hover, engage
- **Supported Elements:** heading, card, button
- **Layout Contexts:** card
- **Section Archetypes:** FEATURES
- **Directionality:** vertical, horizontal
- **Axis:** y, x, z

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: true
- Duration Range: 6000ms - 12000ms
- Easing: linear, ease-in-out, spring

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: low
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: false
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **hybrid** component. Has both significant animation patterns (8 motion elements) and UI structure (0 content strings, 2 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 6000ms - 12000ms (extracted from code)
- Default easing: linear, ease-in-out, spring (extracted)

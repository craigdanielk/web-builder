# ravikatiyar162__workflow_builder_card

**Source:** `21st-dev-library/ravikatiyar162/workflow-builder-card.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 161

## Extracted Features

- **Triggers:** hover
- **Motion Intents:** exit, attention
- **Interaction Intents:** hover
- **Supported Elements:** heading, card, button, image
- **Layout Contexts:** card
- **Section Archetypes:** HOW-IT-WORKS
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 300ms
- Easing: ease-in-out, ease-out

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

Classified as **hybrid** component. Has both significant animation patterns (4 motion elements) and UI structure (4 content strings, 3 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 300ms (extracted from code)
- Default easing: ease-in-out, ease-out (extracted)

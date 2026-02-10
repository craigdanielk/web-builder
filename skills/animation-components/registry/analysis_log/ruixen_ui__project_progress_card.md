# ruixen_ui__project_progress_card

**Source:** `21st-dev-library/ruixen.ui/project-progress-card.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** scroll
**Line Count:** 113

## Extracted Features

- **Triggers:** click
- **Motion Intents:** stagger, progress
- **Interaction Intents:** engage
- **Supported Elements:** heading, card, button
- **Layout Contexts:** card
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 250ms - 250ms
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

Classified as **hybrid** component. Has both significant animation patterns (9 motion elements) and UI structure (0 content strings, 3 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 250ms - 250ms (extracted from code)
- Default easing: ease-in-out, ease-out (extracted)

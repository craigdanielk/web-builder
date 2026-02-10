# ln_dev7__issue_grid

**Source:** `21st-dev-library/ln-dev7/issue-grid.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 200

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** entrance
- **Interaction Intents:** none
- **Supported Elements:** heading, card
- **Layout Contexts:** section
- **Section Archetypes:** GALLERY
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: ease-out

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

Classified as **hybrid** component. Has both significant animation patterns (2 motion elements) and UI structure (2 content strings, 2 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

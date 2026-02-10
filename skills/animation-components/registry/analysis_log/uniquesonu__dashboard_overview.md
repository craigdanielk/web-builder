# uniquesonu__dashboard_overview

**Source:** `21st-dev-library/uniquesonu/dashboard-overview.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** hover
**Line Count:** 124

## Extracted Features

- **Triggers:** hover
- **Motion Intents:** glow, bounce, spring, attention
- **Interaction Intents:** hover
- **Supported Elements:** heading, card
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: spring

## Performance and Risk

- GPU Accelerated: false
- Layout Shift Risk: low
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **hybrid** component. Has both significant animation patterns (2 motion elements) and UI structure (7 content strings, 1 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: spring (extracted)

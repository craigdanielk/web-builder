# ravikatiyar162__order_status_tracker

**Source:** `21st-dev-library/ravikatiyar162/order-status-tracker.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 130

## Extracted Features

- **Triggers:** click
- **Motion Intents:** stagger
- **Interaction Intents:** engage
- **Supported Elements:** heading, card, button, image
- **Layout Contexts:** any
- **Section Archetypes:** STATS
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
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

Classified as **hybrid** component. Has both significant animation patterns (10 motion elements) and UI structure (2 content strings, 1 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

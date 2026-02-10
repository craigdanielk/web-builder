# isaiahbjork__dashboard_card_with_modal

**Source:** `21st-dev-library/isaiahbjork/dashboard-card-with-modal.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 431

## Extracted Features

- **Triggers:** hover, click, mount, time_delay
- **Motion Intents:** exit, scale, slide, blur, bounce, spring, stagger, attention
- **Interaction Intents:** hover, engage
- **Supported Elements:** heading, card, button, image, modal
- **Layout Contexts:** card, modal
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 200ms - 200ms
- Easing: spring

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: low
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: true
- Reduced Motion Fallback: true
- Requires Layout Measurement: false

## Classification Rationale

Classified as **hybrid** component. Has both significant animation patterns (26 motion elements) and UI structure (6 content strings, 4 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 200ms - 200ms (extracted from code)
- Default easing: spring (extracted)

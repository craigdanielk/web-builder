# uilayout_contact__pricing

**Source:** `21st-dev-library/uilayout.contact/pricing.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 307

## Extracted Features

- **Triggers:** click, time_delay
- **Motion Intents:** blur, bounce, spring
- **Interaction Intents:** engage
- **Supported Elements:** heading, card, button
- **Layout Contexts:** section
- **Section Archetypes:** PRICING
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: true
- Composable: false
- Looping: false
- Duration Range: 500ms - 500ms
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

Classified as **hybrid** component. Has both significant animation patterns (2 motion elements) and UI structure (21 content strings, 3 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 500ms - 500ms (extracted from code)
- Default easing: spring (extracted)

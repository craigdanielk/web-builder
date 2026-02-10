# ravikatiyar162__product_card_1

**Source:** `21st-dev-library/ravikatiyar162/product-card-1.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** hover
**Line Count:** 165

## Extracted Features

- **Triggers:** hover, click
- **Motion Intents:** glow, attention
- **Interaction Intents:** hover, engage
- **Supported Elements:** heading, card, button, image
- **Layout Contexts:** card
- **Section Archetypes:** PRODUCT-SHOWCASE
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: true
- Composable: false
- Looping: false
- Duration Range: 300ms - 500ms
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

Classified as **hybrid** component. Has both significant animation patterns (2 motion elements) and UI structure (2 content strings, 2 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 500ms (extracted from code)
- Default easing: ease-in-out, ease-out (extracted)

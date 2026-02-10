# ravikatiyar162__author_form_card

**Source:** `21st-dev-library/ravikatiyar162/author-form-card.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 150

## Extracted Features

- **Triggers:** click
- **Motion Intents:** reveal, bounce, stagger
- **Interaction Intents:** engage, submit
- **Supported Elements:** card, button
- **Layout Contexts:** card, form
- **Section Archetypes:** CONTACT
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
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

Classified as **hybrid** component. Has both significant animation patterns (12 motion elements) and UI structure (4 content strings, 5 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: spring (extracted)

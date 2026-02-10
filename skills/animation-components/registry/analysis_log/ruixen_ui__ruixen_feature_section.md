# ruixen_ui__ruixen_feature_section

**Source:** `21st-dev-library/ruixen.ui/ruixen-feature-section.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** layout
**Line Count:** 249

## Extracted Features

- **Triggers:** mount, time_delay
- **Motion Intents:** slide, blur
- **Interaction Intents:** none
- **Supported Elements:** heading, card, button, image
- **Layout Contexts:** section
- **Section Archetypes:** FEATURES
- **Directionality:** vertical, horizontal
- **Axis:** y, x

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

Classified as **hybrid** component. Has both significant animation patterns (2 motion elements) and UI structure (9 content strings, 1 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

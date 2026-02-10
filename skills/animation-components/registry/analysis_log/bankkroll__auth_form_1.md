# bankkroll__auth_form_1

**Source:** `21st-dev-library/bankkroll/auth-form-1.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 660

## Extracted Features

- **Triggers:** click, time_delay
- **Motion Intents:** exit
- **Interaction Intents:** engage, submit
- **Supported Elements:** heading, card, button
- **Layout Contexts:** form
- **Section Archetypes:** CONTACT
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 300ms
- Easing: ease-in-out

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: low
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: false
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **hybrid** component. Has both significant animation patterns (8 motion elements) and UI structure (14 content strings, 5 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.
- Very large file - may contain multiple sub-components. Registry entry covers the primary export only.

## Fallback Assumptions

- Default duration: 300ms - 300ms (extracted from code)
- Default easing: ease-in-out (extracted)

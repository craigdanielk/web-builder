# preetsuthar17__command_menu

**Source:** `21st-dev-library/preetsuthar17/command-menu.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 498

## Extracted Features

- **Triggers:** hover, click, mount
- **Motion Intents:** exit, slide
- **Interaction Intents:** hover, engage, submit, navigate
- **Supported Elements:** card, nav
- **Layout Contexts:** nav
- **Section Archetypes:** NAV
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 200ms - 200ms
- Easing: ease-in-out, ease-out

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

Classified as **hybrid** component. Has both significant animation patterns (2 motion elements) and UI structure (14 content strings, 2 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 200ms - 200ms (extracted from code)
- Default easing: ease-in-out, ease-out (extracted)

# ruixen_ui__tree_node_tooltip

**Source:** `21st-dev-library/ruixen.ui/tree-node-tooltip.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 109

## Extracted Features

- **Triggers:** click
- **Motion Intents:** exit
- **Interaction Intents:** engage
- **Supported Elements:** card, button
- **Layout Contexts:** popover
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: true
- Composable: false
- Looping: false
- Duration Range: 200ms - 200ms
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

Classified as **animation** component. Provides motion primitives. Uses 2 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 200ms - 200ms (extracted from code)
- Default easing: ease-out (defaulted)

# ruixen_ui__feature_highlight_pro_card

**Source:** `21st-dev-library/ruixen.ui/feature-highlight-pro-card.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 145

## Extracted Features

- **Triggers:** hover, click, time_delay
- **Motion Intents:** exit, flip, scale, bounce, spring, attention, emphasis
- **Interaction Intents:** hover, engage
- **Supported Elements:** card, button
- **Layout Contexts:** card
- **Section Archetypes:** FEATURES
- **Directionality:** vertical
- **Axis:** y, z

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: true
- Duration Range: 300ms - 2200ms
- Easing: ease-in-out, spring

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: false
- Accessibility Safe: false
- Reduced Motion Fallback: false
- Requires Layout Measurement: true

## Classification Rationale

Classified as **animation** component. Provides motion primitives. Uses 11 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 300ms - 2200ms (extracted from code)
- Default easing: ease-in-out, spring (extracted)

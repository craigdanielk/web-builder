# spaceboydavey__scroll_navigation_menu

**Source:** `21st-dev-library/spaceboydavey/scroll-navigation-menu.tsx`
**Component Type:** animation
**Framework:** framer-motion
**Animation Type:** entrance
**Line Count:** 358

## Extracted Features

- **Triggers:** viewport, scroll_linked, hover, click, time_delay
- **Motion Intents:** reveal, exit, scale, slide, rotate, bounce, spring, stagger, emphasis
- **Interaction Intents:** hover, engage, scroll, navigate
- **Supported Elements:** heading, card, nav
- **Layout Contexts:** nav
- **Section Archetypes:** NAV
- **Directionality:** vertical, horizontal
- **Axis:** y, x, z

## Capabilities

- Stagger: true
- Interruptible: true
- Reversible: true
- Composable: false
- Looping: true
- Duration Range: 300ms - 2500ms
- Easing: ease-in-out, spring

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: low
- Scroll Coupling Risk: medium
- Motion Stacking Risk: medium
- Mobile Safe: true
- Accessibility Safe: false
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **animation** component. Provides motion primitives. Uses 28 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 2500ms (extracted from code)
- Default easing: ease-in-out, spring (extracted)

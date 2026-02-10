# reuno_ui__text_scroll_animation

**Source:** `21st-dev-library/reuno-ui/text-scroll-animation.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** scroll
**Line Count:** 206

## Extracted Features

- **Triggers:** scroll_linked
- **Motion Intents:** parallax, flip, slide, progress
- **Interaction Intents:** scroll
- **Supported Elements:** text
- **Layout Contexts:** text
- **Section Archetypes:** none
- **Directionality:** horizontal
- **Axis:** x, z

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
- Layout Shift Risk: low
- Scroll Coupling Risk: medium
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **hybrid** component. Has both significant animation patterns (4 motion elements) and UI structure (7 content strings, 0 UI imports).

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

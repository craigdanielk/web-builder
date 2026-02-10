# youcefbnm__animated_video_on_scroll

**Source:** `21st-dev-library/youcefbnm/animated-video-on-scroll.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** scroll
**Line Count:** 218

## Extracted Features

- **Triggers:** viewport, scroll_linked, hover, click
- **Motion Intents:** reveal, parallax, blur, bounce, spring, progress
- **Interaction Intents:** hover, engage, scroll
- **Supported Elements:** any
- **Layout Contexts:** section
- **Section Archetypes:** VIDEO-SHOWCASE
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: true
- Duration Range: 300ms - 800ms
- Easing: spring

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: low
- Scroll Coupling Risk: medium
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: false
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **hybrid** component. Has both significant animation patterns (3 motion elements) and UI structure (6 content strings, 0 UI imports).

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: spring (extracted)

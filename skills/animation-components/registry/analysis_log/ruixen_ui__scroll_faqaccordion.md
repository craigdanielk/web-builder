# ruixen_ui__scroll_faqaccordion

**Source:** `21st-dev-library/ruixen.ui/scroll-faqaccordion.tsx`
**Component Type:** animation
**Framework:** framer-motion, gsap
**Animation Type:** scroll
**Line Count:** 193

## Extracted Features

- **Triggers:** scroll_linked, mount
- **Motion Intents:** pin, collapse, expand
- **Interaction Intents:** scroll, expand
- **Supported Elements:** heading
- **Layout Contexts:** section
- **Section Archetypes:** FAQ
- **Directionality:** vertical
- **Axis:** y

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 400ms - 400ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: medium
- Scroll Coupling Risk: medium
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **animation** component. Provides motion primitives. Uses 2 motion elements. Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

No significant classification uncertainties.

## Fallback Assumptions

- Default duration: 400ms - 400ms (extracted from code)
- Default easing: ease-out (defaulted)

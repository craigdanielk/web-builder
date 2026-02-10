# itsankitverma__profile_card

**Source:** `21st-dev-library/itsankitverma/profile-card.tsx`
**Component Type:** hybrid
**Framework:** framer-motion
**Animation Type:** exit
**Line Count:** 234

## Extracted Features

- **Triggers:** hover, click, time_delay
- **Motion Intents:** exit, scale, rotate, bounce, spring, attention, emphasis
- **Interaction Intents:** hover, engage
- **Supported Elements:** heading, card, button, image
- **Layout Contexts:** card
- **Section Archetypes:** none
- **Directionality:** vertical
- **Axis:** y, z

## Capabilities

- Stagger: false
- Interruptible: true
- Reversible: false
- Composable: false
- Looping: true
- Duration Range: 500ms - 25000ms
- Easing: linear, ease-in-out, ease-out, spring

## Performance and Risk

- GPU Accelerated: true
- Layout Shift Risk: low
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: false
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **hybrid** component. Has both significant animation patterns (16 motion elements) and UI structure (12 content strings, 2 UI imports).

## Uncertainty Notes

- Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.

## Fallback Assumptions

- Default duration: 500ms - 25000ms (extracted from code)
- Default easing: linear, ease-in-out, ease-out, spring (extracted)

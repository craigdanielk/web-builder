# reaviz__incident_report_1

**Source:** `21st-dev-library/reaviz/incident-report-1.tsx`
**Component Type:** animation
**Framework:** none
**Animation Type:** effect
**Line Count:** 131

## Extracted Features

- **Triggers:** mount
- **Motion Intents:** slide, glow
- **Interaction Intents:** none
- **Supported Elements:** heading
- **Layout Contexts:** any
- **Section Archetypes:** none
- **Directionality:** vertical, horizontal
- **Axis:** y, x

## Capabilities

- Stagger: false
- Interruptible: false
- Reversible: false
- Composable: false
- Looping: false
- Duration Range: 300ms - 800ms
- Easing: ease-out

## Performance and Risk

- GPU Accelerated: false
- Layout Shift Risk: medium
- Scroll Coupling Risk: low
- Motion Stacking Risk: low
- Mobile Safe: true
- Accessibility Safe: true
- Reduced Motion Fallback: false
- Requires Layout Measurement: false

## Classification Rationale

Classified as **animation** component. Provides motion primitives.  Minimal hardcoded content - reusable across contexts.

## Uncertainty Notes

- No animation framework detected - classification relies on filename signals only.

## Fallback Assumptions

- Default duration: 300ms - 800ms (defaulted - no explicit duration found)
- Default easing: ease-out (defaulted)

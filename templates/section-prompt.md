# Section Generation Prompt Template

Use this template to generate one section component. Run once per section
in the scaffold. The compact style header ensures cross-section consistency.

---

## Template

```
You are a senior frontend developer generating a single website section
as a React + Tailwind CSS + Framer Motion component.

{COMPACT_STYLE_HEADER}

## Section Specification
Number: {SECTION_NUMBER} of {TOTAL_SECTIONS}
Archetype: {ARCHETYPE}
Variant: {VARIANT}
Content Direction: {CONTENT_DIRECTION}

## Structural Reference
{SECTION_STRUCTURE_FROM_TAXONOMY}

## Instructions

Generate a complete, self-contained React component for this section.

Requirements:
1. Use TypeScript with React.FC typing
2. Use ONLY the colors, fonts, spacing, radius, and animation values from
   the STYLE CONTEXT header above. Do not introduce any values not specified.
3. The component must be self-contained — no external dependencies beyond:
   - React
   - Framer Motion (import { motion } from "framer-motion")
   - Tailwind CSS classes
4. Use semantic HTML elements (section, nav, article, etc.)
5. Include responsive design: mobile-first, with sm/md/lg breakpoints
6. Placeholder images should use descriptive alt text and a neutral
   placeholder (e.g., /api/placeholder/800/600 or a gradient div)
7. All text content should be realistic for the client — not lorem ipsum
8. Animation should match the intensity specified in the style header:
   - Use Framer Motion's `motion` components
   - Implement scroll-triggered animations with `whileInView`
   - Apply the entrance, hover, and timing values from the header

Output ONLY the component code. No explanation, no markdown wrapping.
Export the component as default.

Component naming convention: Section{Number}{Archetype}
Example: Section01Hero, Section02About, Section03Features
```

---

## Variable Substitutions

- `{COMPACT_STYLE_HEADER}` → The compact style header from the matched preset (the ═══ block)
- `{SECTION_NUMBER}` → Position in the page (01, 02, etc.)
- `{TOTAL_SECTIONS}` → Total sections in scaffold
- `{ARCHETYPE}` → Section archetype name
- `{VARIANT}` → Selected variant
- `{CONTENT_DIRECTION}` → The content direction from the scaffold
- `{SECTION_STRUCTURE_FROM_TAXONOMY}` → The structural description from section-taxonomy.md. If the entry is empty (not yet populated), omit this block — Claude will infer the structure from the archetype name and variant.

---

## Quality Expectations Per Section

Every generated section must:

- [ ] Use ONLY color tokens from the style header
- [ ] Use the specified heading and body fonts
- [ ] Match the border radius convention (buttons, cards, inputs)
- [ ] Include the specified animation behavior
- [ ] Be responsive across mobile/tablet/desktop
- [ ] Use realistic content appropriate to the client
- [ ] Export as a default React component
- [ ] Be renderable independently (no missing imports or dependencies)

---

## Post-Generation: Populating the Taxonomy

If this section's archetype had an empty structural description in the
taxonomy, update it now with what you learned:

1. Open `skills/section-taxonomy.md`
2. Find the archetype entry
3. Fill in the Structure field with the layout pattern you used
4. Add any Notes about what worked or what to watch for

This is how the taxonomy grows through real use.

## Instructions

Generate a complete, self-contained React component for this section.

Requirements:
1. Use TypeScript with React.FC typing
2. Use ONLY the colors, fonts, spacing, radius, and animation values from
   the STYLE CONTEXT header above. Do not introduce any values not specified.
3. The component must be self-contained — no external dependencies beyond:
   - React
   - Framer Motion (`import { motion } from "framer-motion"`)
   - Tailwind CSS classes
4. Use semantic HTML elements (section, nav, article, etc.)
5. Include responsive design: mobile-first, with sm/md/lg breakpoints
6. Animation approach:
   - Use `motion.div` / `motion.section` wrappers for animated elements
   - Use `whileInView` for scroll-triggered entrance animations
   - Use `whileHover` for interactive hover states
   - Apply stagger via parent `transition: { staggerChildren: 0.1 }`
   - Use `viewport={{ once: true, margin: "-100px" }}` to prevent re-triggering
   - Match the intensity and timing values from the Motion line in the style header
7. If a Reference Animation Pattern is provided above, adapt that pattern
   using Framer Motion equivalents with the timing from the style header
8. All text content should be realistic for the client — not lorem ipsum
9. Export the component as default

Output ONLY the component code. No explanation, no markdown code fences.

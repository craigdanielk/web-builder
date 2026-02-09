## Instructions

Generate a complete, self-contained React component for this section.

Requirements:
1. Use TypeScript with React.FC typing
2. Use ONLY the colors, fonts, spacing, radius, and animation values from
   the STYLE CONTEXT header above. Do not introduce any values not specified.
3. The component must be self-contained — no external dependencies beyond:
   - React (including useEffect, useRef)
   - GSAP (`import { gsap } from "gsap"`)
   - GSAP ScrollTrigger (`import { ScrollTrigger } from "gsap/ScrollTrigger"`)
   - Tailwind CSS classes
4. Use semantic HTML elements (section, nav, article, etc.)
5. Include responsive design: mobile-first, with sm/md/lg breakpoints
6. GSAP setup pattern (MUST follow exactly):
   ```tsx
   const sectionRef = useRef<HTMLElement>(null);
   useEffect(() => {
     gsap.registerPlugin(ScrollTrigger);
     const ctx = gsap.context(() => {
       // All animations here, scoped to sectionRef
     }, sectionRef);
     return () => ctx.revert();
   }, []);
   ```
7. ScrollTrigger pattern:
   - Use `scrollTrigger: { trigger: element, start: "top 80%", once: true }`
   - Use `gsap.from()` for entrance animations (animate FROM hidden state TO natural state)
   - Use `stagger` for multi-element reveals: `gsap.from(".item", { stagger: 0.1 })`
   - For counter/number animations use: `gsap.to(obj, { value: target, snap: { value: 1 }, ... })`
8. If a Reference Animation Pattern is provided above, use that exact GSAP pattern
   with the timing values from the style header's Motion line
9. Hover effects: Use Framer Motion `motion.div` with `whileHover` ONLY for simple
   hover states (scale, shadow). Do NOT mix GSAP scroll animations with Framer Motion
   scroll triggers — keep GSAP for scroll, Framer for hover only.
10. All text content should be realistic for the client — not lorem ipsum
11. Export the component as default

Output ONLY the component code. No explanation, no markdown code fences.

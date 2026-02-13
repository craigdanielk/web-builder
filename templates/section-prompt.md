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

## Reference Section Context (optional — from URL extraction)
{REFERENCE_SECTION_CONTEXT}

## Reference Images (optional — from image manifest)
{REFERENCE_IMAGES}

## Instructions

Generate a complete, self-contained React component for this section.

Requirements:
1. Use TypeScript with React.FC typing
2. Use ONLY the colors, fonts, spacing, radius, and animation values from
   the STYLE CONTEXT header above. Do not introduce any values not specified.
3. The component must be self-contained — no external dependencies beyond:
   - React (useState, useEffect, useRef)
   - Animation library (see rule 8 below)
   - Tailwind CSS classes
4. Use semantic HTML elements (section, nav, article, etc.)
5. Include responsive design: mobile-first, with sm/md/lg breakpoints
6. Images: If Reference Images are provided above, use those actual URLs.
   Render with CSS `backgroundImage` on divs — NOT `<img>` tags (except logos).
   Always include `role="img"` and `aria-label` for accessibility.
   Use `backgroundSize: 'cover'` and `backgroundPosition: 'center'`.
   If NO Reference Images provided, use gradient placeholders instead.
   NEVER use placeholder services like /api/placeholder.
7. All text content should be realistic for the client — not lorem ipsum
8. Animation must match the engine and intensity from the style header.
   Check the Motion line in the STYLE CONTEXT:

   **If engine is `framer-motion` (e.g., Motion: moderate/framer-motion):**
   - Import { motion } from "framer-motion"
   - Use `whileInView` for scroll-triggered animations
   - Apply entrance, hover, and timing values from the header

   **If engine is `gsap` (e.g., Motion: moderate/gsap):**
   - Import { gsap } from "gsap" and { ScrollTrigger } from "gsap/ScrollTrigger"
   - Use useEffect + useRef + gsap.context() for all animations
   - Register plugin inside useEffect: gsap.registerPlugin(ScrollTrigger)
   - Use ScrollTrigger with start: "top 80%", once: true
   - Apply section-specific animation overrides from the header pipe (|)
   - Reference pattern names from skills/animation-patterns.md:
     * HERO sections → character-reveal or word-reveal + staggered-timeline
     * STATS sections → count-up per metric
     * FEATURES → fade-up-stagger + icon-glow on hover
     * MAP/TRIALS → marker-pulse on SVG points
     * CTA → staggered-timeline for heading → button
     * All other sections → fade-up-stagger (default)
   - Always return ctx.revert() in useEffect cleanup

9. **Animation Component Library (MANDATORY when provided):**
   - If the Animation Context above includes a "### Animation Component Source" block,
     you MUST import that component from `@/components/animations/{pattern-name}`.
   - Do NOT rewrite the animation logic inline — use the provided component as-is.
   - The component is already copied to the project. Just import and use it.
   - Example: if the context provides pattern `character-reveal`, import it:
     `import CharacterReveal from "@/components/animations/character-reveal";`
   - Wrap your content with the animation component according to its Props section.
   - If the Animation Context includes a "## Section plugin recommendations" block,
     use at least one recommended plugin in this section. Import it, register it
     with `gsap.registerPlugin()`, and use it in your GSAP context.

10. **Archetype + Variant Overrides:**

   **When archetype is PRODUCT-SHOWCASE and variant is `demo-cards`:**
   - CRITICAL: Each card in this showcase MUST have a visually DISTINCT treatment
   - Each card gets a UNIQUE gradient direction and color combination from the palette
     (e.g., card 1: top-left to bottom-right green→black, card 2: radial blue→dark, etc.)
   - Each card gets a UNIQUE micro-animation that represents its label/category:
     * "3D Product Rotation" → subtle CSS perspective rotate on hover (`card-3d-rotate`)
     * "Morph Path Animation" → background SVG blob that morphs shape (`card-morph-blob`)
     * "Motion Path Sequences" → small dot orbiting the card border (`card-orbit-dot`)
     * "Flip Layout Transitions" → card flip animation on hover (`card-flip-preview`)
     * "DrawSVG Sequences" → SVG stroke drawing around the card on scroll (`card-stroke-draw`)
     * "Text Animations" → title text scrambles/reveals on hover (`card-text-scramble`)
     * "Gradient Effects" → unique gradient hue shift on hover (`card-gradient-shift`)
     * "Particle Effects" → particles burst from card on hover (`card-particle-burst`)
   - Each card's hover state must be different from other cards
   - Use the detected GSAP plugins for these effects where available
   - When no GSAP plugins are detected, use CSS-only fallbacks:
     * perspective + rotateY/rotateX for 3D
     * clip-path transitions for reveals
     * background-position shifts for gradients
     * transform: scale + box-shadow for lifts
   - DO NOT give all cards the same gradient, same hover effect, or same layout
   - The entire point of this section is showing VARIETY

11. **Icon & Emoji Rules (MANDATORY):**
   - NEVER use emoji characters as icons or decorative elements. Unicode symbols (arrows, checkmarks) are acceptable.
   - For icons, always import from `lucide-react`: `import { Zap, Globe, Shield } from 'lucide-react'`
   - Render icons as React components: `<Zap className="w-6 h-6" />`
   - Use semantic icon names that match the content purpose (see Icon Mapping below)
   - For decorative shapes/blobs, use CSS or SVG, not emoji

   **Icon Mapping by Section Type:**
   - FEATURES: Zap (performance), Shield (security), Globe (global), Users (community), Code (developer), Gauge (speed), Lock (privacy), Layers (architecture), Cpu (tech), Rocket (launch), Eye (visibility), Sparkles (quality)
   - PRICING: Check (included), X (excluded), Star (popular), Crown (premium), Infinity (unlimited), BadgeCheck (verified)
   - HOW-IT-WORKS: ArrowRight (next step), ChevronDown (expand), Play (action), Lightbulb (idea), Settings (configure), CircleDot (step marker)
   - TRUST / SOCIAL-PROOF: Award (achievement), BadgeCheck (verified), ShieldCheck (certified), Trophy (winner), ThumbsUp (endorsement)
   - CONTACT: Mail (email), Phone (call), MapPin (location), Clock (hours), MessageCircle (chat), Send (submit)
   - STATS: TrendingUp (growth), BarChart3 (data), Activity (live), Target (goal), Percent (metric), Hash (count)

12. **Logo Bar Rendering (MANDATORY for LOGO-BAR / SOCIAL-PROOF):**
   - When actual logo image URLs are provided in the asset context, use them as CSS backgroundImage on divs
   - When NO logo image URLs are available, render company names as styled text pills:
     `<div className="min-w-[120px] h-12 flex items-center justify-center px-6 py-3 rounded-full border border-white/10 bg-white/5 text-sm font-medium tracking-wide">{companyName}</div>`
   - NEVER render logos as `<img>` tags with missing, broken, or placeholder src attributes
   - For scrolling marquee variants: duplicate the row for seamless CSS @keyframes loop animation

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
- `{REFERENCE_SECTION_CONTEXT}` → (Optional) Per-section context from URL extraction. Only present when using `--from-url` mode. Contains layout details, element structure, text content, and visual characteristics from the reference site. When absent, omit the entire Reference Section Context block.
- `{REFERENCE_IMAGES}` → (Optional) Image URLs from the image manifest relevant to this section's archetype. Formatted as a numbered list with URL, alt text, and size. When absent or empty, omit the entire Reference Images block — the section will use gradient fallbacks. See `skills/image-extraction.md` for the section-to-category mapping that determines which images are assigned to which sections.

---

## Quality Expectations Per Section

Every generated section must:

- [ ] Use ONLY color tokens from the style header
- [ ] Use the specified heading and body fonts
- [ ] Match the border radius convention (buttons, cards, inputs)
- [ ] Include the specified animation behavior
- [ ] Be responsive across mobile/tablet/desktop
- [ ] Use realistic content appropriate to the client
- [ ] Use reference image URLs if provided, gradient fallbacks if not
- [ ] Include `role="img"` and `aria-label` on all image divs
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

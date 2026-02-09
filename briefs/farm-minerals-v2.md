# Brief: farm-minerals-v2

## Business
Farm Minerals manufactures and sells advanced agricultural fertilizers and feed additives using proprietary nanotechnology. Their flagship product is CropTab™, a tablet-based fertilizer system that delivers nutrients at a particle size smaller than plant cells. The company positions itself as a sustainable agriculture innovator, emphasizing dramatic reductions in carbon emissions (½ ton CO₂e saved per acre), near-zero runoff (99% uptake), and drastically lighter logistics (1000x lighter than traditional fertilizers). They're currently in field trial phase and operating with limited product access.

## What They Need
A promotional/product launch website that generates qualified leads for their field trial program and early access requests. The site needs to educate farmers and agricultural decision-makers on the revolutionary technology while building credibility through data-driven environmental and efficiency claims. Primary conversion goal is capturing contact information through "request access," "request a sample," and "check eligibility" actions.

## Key Requirements
- Hero section with provocative value proposition question ("How much could you grow — if nothing was wasted?")
- Technology explanation section covering particle size, integration, and manufacturing benefits
- Product showcase for CropTab™ with "just drop it" delivery system demonstration
- Environmental impact metrics prominently displayed (CO₂ savings, uptake percentage, logistics weight reduction)
- Field trial transparency section with progress updates and methodology explanation
- Social proof section for farmer testimonials and field test results
- Product format selector distinguishing Macronutrient Fertilizers, Micronutrient Fertilizers, and Feed Additives
- Individual product pages or sections for: CropTab™ NPK, CropTab™ K, CropTab™ N, CropTab™ P, CropTab™ NPK+, Nutripeak™ Micros, ElevateFeed™
- Multiple gated conversion points throughout the page (not just bottom-of-funnel)
- Educational content linking to deeper science pages (/science/croptab and /approach)
- Early adopter messaging ("You don't get many chances to be early")
- Food safety information section

## Target Audience
- Commercial farmers and large-scale agricultural operations looking to reduce input costs while maintaining yields
- Sustainability-focused agricultural operations under pressure to reduce carbon footprint
- Progressive early-adopter farmers willing to test new agricultural technology
- Agricultural operations managers responsible for purchasing decisions
- Secondary: Agricultural consultants, agronomists, and farm management companies

## Brand Personality
- Scientific and data-driven (specific metrics like "99% uptake," "1000x lighter," "½ ton CO₂e")
- Bold and disruptive (challenging traditional fertilizer delivery methods)
- Transparent and methodical (openly sharing field trial progress and methodology)
- Environmental without being preachy (carbon savings presented as operational efficiency, not just planet-saving)
- Accessible innovation (complex nanotech explained in farmer-friendly terms like "just drop it")
- Confident but not overpromising (emphasis on testing, trials, and proof)

## Specific Requests
- Maintain the question-led value proposition approach in hero section
- Preserve the visual comparison approach showing tablet format vs traditional bulk fertilizers
- Keep the three-metric callout design (1000x lighter logistics, ½ ton CO₂e saved, 99% uptake)
- Maintain distinct product variant imagery showing different CropTab™ formulations
- Preserve the "field trials in progress" transparency approach with update timeline
- Keep the dual CTA pattern (soft "learn more" vs hard "request access")
- Maintain the benefit trio structure: smaller particles + effortless integration + zero emissions
- Preserve "Less in, same out" messaging framework
- Keep eligibility checking as a distinct conversion path (suggests limited/qualified access strategy)

## Technical Notes
- Next.js with TypeScript
- Product selector interface needs to handle multiple product categories and variants without full page reloads
- Multiple modal or popup forms for gated content (request access, check eligibility, request sample) — consider single unified form component with different triggers
- Consider headless CMS integration for field trial updates and farmer testimonial management
- Image optimization critical for product comparison visuals and before/after field imagery
- Analytics tracking needed for multiple conversion points throughout page flow
- Email capture integration for early access list
- Mobile-first approach essential for farmers accessing in field or on equipment
- Fast load times critical for rural internet connections
- Consider progressive disclosure pattern for technical/scientific content (science-curious vs just-give-me-results users)
# Brief: gsap-v9-test

## Business
GSAP (GreenSock Animation Platform) is a professional-grade JavaScript animation library that enables developers to create high-performance animations for web applications. They provide animation tools for UI, SVG, WebGL, text effects, and scroll-based interactions. The platform is now free for everyone thanks to Webflow's sponsorship, serving both professional developers and agencies building modern web experiences.

## What They Need
A developer-focused marketing website that showcases GSAP's animation capabilities through live demonstrations while providing clear paths to documentation, learning resources, and community engagement. The site must demonstrate the product's power through its own implementation—practicing what it preaches with sophisticated animations throughout.

## Key Requirements
- Hero section with animated tagline demonstrating GSAP's capabilities in real-time
- Tool-specific landing pages or sections for: Core, Scroll, SVG, UI, and Text animation features
- Brand showcase section displaying logos of companies using GSAP
- Portfolio/Showcase section featuring community work built with GSAP
- User authentication system (sign in/account creation with benefits messaging)
- Direct links to documentation, installation guides, and React integration
- Resource hub connecting to video lessons, community forums, and learning materials
- Clear CTA highlighting the "free for everyone" pricing model
- Navigation structure that separates tools, learning resources, and community sections

## Target Audience
- Professional front-end developers and creative coders building interactive web experiences
- Agency developers creating custom websites for high-profile clients
- UI/UX developers focused on micro-interactions and polished animations
- WebGL and SVG specialists needing reliable animation tooling
- Developers migrating from other animation libraries seeking enterprise-grade solutions

## Brand Personality
- Professional and technical—focused on robustness, performance, and reliability
- Playful and creative—uses animated wordplay and visual demonstrations of capabilities
- Confident—positions as the industry standard ("wildly robust," "unmatched support")
- Developer-first—emphasizes ease of implementation ("plug-and-play," "effortless")
- Community-oriented—showcases user work and provides extensive learning resources

## Specific Requests
- Implement meta-level animations throughout that demonstrate GSAP's own capabilities (animated text, morphing elements, scroll-triggered effects)
- Create kinetic typography effects in headings that break words apart and animate individual letters/words
- Include visual demonstrations for each tool category (Scroll, SVG, Text, UI) with inline examples
- Maintain the "Animate Anything" messaging as a core brand statement
- Design animated transitions between sections that feel silky-smooth and professional
- Preserve the showcase carousel/grid featuring real projects from the community
- Ensure animations enhance rather than distract from the technical documentation access
- Include prominent "free for everyone" messaging with attribution to Webflow sponsorship

## Technical Notes
- Build with Next.js for optimal performance and SEO
- Must integrate GSAP library throughout for all animations (dogfooding the product)
- Performance is critical—animations must be 60fps on all modern devices
- Consider code-splitting for heavy animation sections to maintain fast initial load
- Implement proper scroll performance optimization for parallax/scroll-triggered animations
- May require custom animation components that can be demonstrated and documented simultaneously
- Integration with YouTube for video lessons and external community platforms
- Account system suggests backend authentication requirements (consider NextAuth or similar)
- Documentation section may pull from external API or CMS
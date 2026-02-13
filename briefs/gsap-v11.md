# Brief: gsap-v11

## Business
GSAP (GreenSock Animation Platform) is a professional-grade JavaScript animation library used by web developers and designers worldwide. They provide animation tools and plugins for modern web development, including scroll-based animations, SVG manipulation, text effects, and UI interactions. The platform is now free for everyone thanks to Webflow's sponsorship, though they likely have premium tiers. Their client base includes major brands and professional development teams creating high-end web experiences.

## What They Need
A marketing and documentation website that serves as both a showcase for GSAP's animation capabilities and a conversion funnel for developer adoption. The site needs to demonstrate the library's power through immersive, animated examples while providing clear pathways to documentation, learning resources, and account creation. The rebuild must prove GSAP's performance capabilities by being itself an exemplar of smooth, professional web animation.

## Key Requirements
- Hero section with dynamic, attention-grabbing animation showcasing "Animate Anything" concept
- Product segmentation by tool type (Core, Scroll, SVG, UI, Text)
- Dedicated landing pages or sections for each tool category with animated demonstrations
- Brand showcase section featuring logos/examples from major clients
- Community showcase gallery highlighting user-created projects
- Comprehensive navigation to documentation, video lessons, React integration guides
- Account creation system with clear value proposition ("Why create an account?")
- Prominent messaging about free tier availability
- Installation/getting started resources
- Learning resources hub (video lessons, documentation, community forums)
- Interactive demos that prove the library's capabilities through the site's own animations

## Target Audience
- Professional front-end developers and creative coders looking for production-ready animation solutions
- Web designers who code or work closely with developers on high-end digital experiences
- WebGL developers creating immersive web experiences
- React developers seeking animation libraries
- Agency teams building client work requiring sophisticated interactions
- Intermediate to advanced developers who value performance, reliability, and robust documentation

## Brand Personality
- Professional and confident - positions itself as the industry standard for serious developers
- Technically sophisticated but approachable - "wildly robust" paired with "plug-and-play"
- Performance-obsessed - emphasizes "silky-smooth" performance throughout
- Playful yet authoritative - copy uses wordplay ("Nice and easy easing", "Leave them lost for words") while maintaining credibility
- Community-focused - strong emphasis on showcase, learning resources, and community
- Modern and cutting-edge - aligned with current web development practices (React, WebGL)

## Specific Requests
- The site itself must be a demonstration of GSAP's capabilities - expect heavy use of scroll-triggered animations, text effects, morphing elements, and smooth transitions throughout
- Animated typography that breaks apart, morphs, or animates in creative ways (evident from the fragmented heading text in extraction)
- Interactive easing curve demonstrations showing "personality" in animation
- The homepage should showcase different animation types (scroll, SVG, text, UI) in dedicated sections
- Maintain the "Animate Anything" messaging as the core value proposition
- Preserve the emphasis on ease-of-use alongside power ("plug-and-play" vs "wildly robust")
- Include animated visual elements that respond to user interaction or scroll position
- Brand showcase should be prominent to establish credibility
- Clear differentiation between tool categories with visual/animated examples for each

## Technical Notes
- Build on Next.js with emphasis on performance optimization given the animation-heavy nature
- Must achieve 60fps animations site-wide to prove GSAP's performance claims
- Implement GSAP library extensively throughout the site as a working demonstration
- Consider code splitting and lazy loading given expected animation payload
- Ensure animations are accessible and respect prefers-reduced-motion settings
- Documentation integration may require API or CMS connection for version-specific docs
- Video content hosting for lessons (likely YouTube embed based on navigation links)
- Community/showcase features may require database for user submissions
- Account system integration for sign-in functionality
- Consider WebGL canvas elements for more immersive hero/feature sections
- Optimize for developer audience (fast load times, clean code, good DX if open source)
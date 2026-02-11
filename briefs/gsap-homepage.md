# Brief: gsap-homepage

## Business
GSAP (GreenSock Animation Platform) is a professional-grade JavaScript animation library company serving web developers and designers globally. They provide a wildly robust animation toolkit that enables professionals to create silky-smooth animations for UI, SVG, WebGL, and interactive experiences. The product is now free for everyone thanks to Webflow's sponsorship, transitioning from their previous licensing model. GSAP is the industry-standard animation library used by major brands and professional development teams worldwide.

## What They Need
A high-performance marketing website that demonstrates GSAP's animation capabilities through the site itself while educating developers about the library's features, tools, and use cases. The site must convert visitors into users by showcasing the library's power, ease of use, and versatility while providing clear pathways to documentation, learning resources, and implementation.

## Key Requirements
- Hero section with animated headline demonstrating GSAP's core capabilities ("Animate Anything")
- Four distinct tool category pages/sections: Scroll, SVG, Text, and UI Interactions
- Brand showcase section featuring recognizable companies using GSAP
- Community showcase gallery highlighting exceptional work built with GSAP
- Pricing/business model explanation (emphasis on "free for everyone" messaging)
- Account creation system with clear value proposition
- Documentation hub with installation guides and API references
- Learning resources section linking to video lessons, React integration guides, and tutorials
- Community forum integration
- Core library information and feature demonstrations
- Interactive animated examples throughout demonstrating ease of use, easing functions, and choreography capabilities

## Target Audience
- Professional front-end developers and creative developers working on production web applications
- Web animation specialists and motion designers transitioning to code
- UI/UX developers building interactive experiences
- WebGL and creative coding professionals
- Development teams at agencies and product companies requiring reliable animation solutions
- React developers seeking animation library integration
- Intermediate to advanced JavaScript developers who value performance and robustness

## Brand Personality
- Confident and professional without being corporate or stuffy
- Technically sophisticated yet accessible ("plug-and-play" ease)
- Playful and creative through wordplay and animated demonstrations
- Performance-obsessed and quality-focused ("silky-smooth," "wildly robust")
- Community-oriented and educational
- Industry-leading and established (professional-grade, used by major brands)
- Energetic and dynamic through animated typography and interactive elements

## Specific Requests
- The site must be a working showcase of GSAP's capabilities—practice what you preach through sophisticated scroll-triggered animations, text effects, and smooth transitions
- Animated typography in headings that demonstrates the library's text animation features
- Interactive animated word/letter effects in key messaging ("Easy Easing," "Plug-and-play")
- Scroll-based storytelling animations showcasing the ScrollTrigger plugin
- Each tool category (Scroll, SVG, Text, UI) needs its own detailed section with visual demonstrations
- Maintain the distinctive animated headline treatment that morphs/animates words
- Preserve the "effortlessly animate anything JS can touch" messaging with interactive proof
- Brand logo showcase must feel credible and impressive
- Account creation modal/overlay system with clear benefits explanation
- Visual demonstrations of easing curves and animation choreography concepts
- Mobile-responsive with maintained animation quality across devices

## Technical Notes
- Build on Next.js with TypeScript for type safety
- Integrate GSAP library (obviously) with ScrollTrigger, SplitText, and other premium plugins
- Performance is critical—animations must be 60fps smooth on all devices
- Consider SSR implications for GSAP animations (client-side initialization)
- Video background or WebGL elements in hero section if performance allows
- API integration for community forum and showcase gallery
- Authentication system for account creation and sign-in
- Analytics tracking for conversion funnel (view → docs → installation → account creation)
- CDN for video lessons and tutorial content
- Documentation should be searchable and versioned (currently v3)
- Consider headless CMS for showcase gallery and brand logos to allow easy updates
- Accessibility considerations for animated content (prefers-reduced-motion support)
- Fast page loads despite heavy animation—code splitting and lazy loading essential
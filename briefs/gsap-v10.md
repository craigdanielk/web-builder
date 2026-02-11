# Brief: gsap-v10

## Business
GSAP (GreenSock Animation Platform) is a professional-grade JavaScript animation library used by developers and designers worldwide. They provide animation tools and plugins for web development, with a focus on performance, ease of use, and cross-browser compatibility. The library is now free for everyone thanks to Webflow's sponsorship. GSAP is used by major brands and serves the professional web development community with tools for animating UI elements, SVG graphics, scroll-based interactions, text effects, and WebGL experiences.

## What They Need
A marketing and documentation website that showcases GSAP's capabilities while simultaneously demonstrating them through live animations and interactive examples. The site needs to convert developers to try the library, encourage account creation, provide clear paths to documentation and learning resources, and highlight the professional-grade nature of the product. The site itself should be a living demonstration of what GSAP can accomplish.

## Key Requirements
- Hero section with animated headline demonstrating GSAP's animation capabilities in real-time
- Product segmentation into clear tool categories (Core, Scroll, SVG, UI, Text)
- Dedicated showcase section featuring real-world implementations and brand users
- Interactive demos and examples embedded throughout the marketing pages
- User account system with sign-in functionality and benefits explanation
- Clear documentation access points and learning resource links
- Community section integration
- Prominent "free for everyone" messaging with link to pricing/licensing information
- Tool-specific landing pages (Scroll, SVG, Text, UI Interactions) with tailored examples
- Brand credibility section showcasing companies using GSAP
- Video lessons integration (YouTube channel link)
- React-specific resources and documentation
- Installation documentation easily accessible from navigation

## Target Audience
- Professional web developers and engineers building production applications
- Creative developers and digital agencies creating interactive brand experiences
- Front-end developers working with React and modern JavaScript frameworks
- WebGL and three.js developers building immersive experiences
- UI/UX designers who code and need animation tools
- Teams at established brands seeking reliable, performant animation solutions

## Brand Personality
- Professional and technically credible - positioning as the industry-standard solution
- Confident and authoritative - using language like "wildly robust" and "unmatched support"
- Playful and creative - demonstrated through animated UI and personality in copy ("Nice and easy easing," "Leave them lost for words")
- Performance-focused - emphasizing "silky-smooth performance" and reliability
- Developer-friendly - speaking directly to technical users while remaining approachable
- Premium quality despite being free - maintaining professional positioning

## Specific Requests
- The site must heavily feature real-time GSAP animations throughout every section to serve as a live demo
- Animated typography effects should be prominent, particularly in headings and hero sections
- The "Animate Anything" concept should be visually demonstrated with multiple examples showing different use cases
- Maintain the tool categorization approach (Scroll, SVG, Text, UI) as primary navigation pillars
- Interactive demos should show code snippets alongside visual results where possible
- The showcase section should feature high-quality work from real brands using the library
- Emphasize the "free for everyone" message prominently, tied to Webflow sponsorship
- Include personality-driven microcopy throughout ("Plug-and-play eases," "lost for words")
- Preserve the clean, modern aesthetic that doesn't distract from the animated demonstrations

## Technical Notes
- Build with Next.js for optimal performance and SEO
- Must integrate GSAP library extensively throughout for on-brand animated experiences
- Performance is critical - animations must be smooth and performant to demonstrate product quality
- Implement smooth scroll interactions using ScrollTrigger (GSAP's scroll plugin)
- Account authentication system required for user sign-in functionality
- YouTube API integration for video lessons section
- Documentation should be accessible via client-side navigation (likely docs subdomain or path)
- Consider React Server Components carefully given the heavy client-side animation requirements
- Mobile performance must be optimized given the animation-heavy nature
- Analytics tracking for conversion events (sign-ups, documentation visits, showcase interactions)
- Accessibility considerations for animated content (respect prefers-reduced-motion)
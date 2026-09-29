# Methodology extraction — Nate Herk reel "Claude Code + Seedance 2.5" (Instagram DdrKWKDGhy3)

- **Source:** https://www.instagram.com/reel/DdrKWKDGhy3/ · @nateherkai · 37.7 s, 1080×1920@60
- **Evidence (local, gitignored):** `docs/design/references/reel-DdrKWKDGhy3/` (reel.mp4, 1 fps frames, contact.jpg, transcript.srt)
- **Extracted:** 2026-09-29 for XT-2 S5 (decision record amendment A1)

## The method, as shown

| # | Step | Evidence (t) |
|---|---|---|
| 1 | Design the site in **Figma** first (layout, type, hero composition) | 0:04 — "Start a project" Figma frame |
| 2 | Give the design to **Claude Code**, which builds the site | 0:07 — Claude Code todos/build log |
| 3 | Give **Seedance 2.5** one image of the **finished end state** (the completed house) as the reference | 0:14–0:17 — Higgsfield UI: References = house image, model Seedance 2.5 |
| 4 | Prompt: **"Using reference pic generate the entire construction process backwards"** | 0:17 — prompt field, verbatim |
| 5 | Seedance produces finished → dismantled (house → framing → foundations → bare plot) | 0:19–0:22 |
| 6 | Claude Code: **"connect the playback to the user's scroll"**. Played in reverse, scrolling *builds* the house and ends exactly on the finished image | 0:23–0:30 |
| 7 | **Chapter labels synced to scroll progress** over the film ("Set the foundations", "Framing & Roofing", "Interior and Furnishings", "Beautiful Landscaping") with a progress bar | 0:19–0:34 overlays |
| 8 | Layout: dark hero with headline + CTA on one side, film frame dominant; the film carries the narrative, the DOM carries copy | 0:28 |

## Why it works (the principle)

1. **Generate backwards from a fixed end state.** The end state is a real input image, so the
   payoff frame is exactly right. Generative drift only affects the journey, never the destination.
   This is the same principle as our S1 logo-lock anchor.
2. **One film = one narrative arc.** Scroll maps to time, and time maps to the story (build-up).
3. **DOM does the talking.** Labels and progress are live text over the film, so copy stays
   crisp, editable and accessible.

## What the reel does NOT show (our bar must add)
- Frame-sequence engineering: it scrubs an `<video>` (`currentTime`), which stutters on
  mobile/Safari and can't be decoded backwards smoothly. We scrub **pre-extracted AVIF/WebP
  frames on canvas**.
- Mobile composition (9:16 variant), reduced-motion path, poster/LCP strategy, weight budget.
- Multi-chapter continuity (the reel is one clip). We chain clips last-frame→first-frame.
- Brand-exact colour: we grade frames to the fixed palette and overlay the vector master
  on the final frame.

## Trend translation (S5)
| Reel | Trend |
|---|---|
| Finished house image | **Exact logo-lock frame**: S1 render of the blades at the core of the navy glass globe, teal routes, on abyss `#0f1419` (vector master overlaid) |
| "construction process backwards" | "the mark **coming apart** backwards: four blades separate and travel outward along teal routes to the globe's edge, scattering into fragmented providers" |
| Reversed on scroll | Scroll = **fragmented providers → Collect / Convert / Pay / Track → one ecosystem (the logo)** |
| Chapter labels | The four blades = the four product beats (copy from `src/content/home.ts`, unchanged) |
| Single clip | 5 s, Seedance 2.0/2.5, `start_image` = lock frame, 4k 16:9 **and** a separate 9:16 mobile generation |

Seedance CLI supports this directly: `--start-image` (the lock frame), `--image-references`
(≤9, look anchors), `--resolution 4k`, `--aspect-ratio 16:9|9:16`, `--duration`.

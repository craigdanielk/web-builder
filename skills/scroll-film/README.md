---
name: scroll-film
description: Anchored generative scroll-film toolkit. Builds a pinned, scroll-scrubbed film section (hero or chapter) from AI video that resolves into the EXACT brand mark — reference-reel methodology extraction, Higgsfield plate + Seedance clip generation anchored on vector-composited frames, frame pipeline (denoise, optical-flow interpolation, deband, WebP + manifest), a smooth React/Next player (Lenis, sub-frame dissolve, exact-anchor resolve, settle-to-copy), and QA probes (fidelity, frame pacing, screenshots). Use when asked for a scroll-driven video hero, "watch it build as you scroll", logo-assembly film, Apple-style scrubbed sequence, or to turn a Seedance/Higgsfield clip into a scroll experience. Pairs with cinematic-site (whole-site pipeline) — this is its film-section engine.
---

# Scroll Film

Proven on Trend Digital's homepage hero (2026-09-29): land inside a glass globe → scroll → the
four logo blades assemble → resolve into the exact mark → globe settles aside → headline + CTA.
Evidence: `services/trend-digital-website/docs/design/spikes/XT-2-findings.md`.

**Division of labour (the core lesson):** generated film carries the *look*; code carries
*exactness* (the logo), *choreography* (scroll mapping) and *copy* (live DOM). Never let a
model draw the brand mark.

Tools in `tools/` (run with a Python that has pillow, numpy and playwright; for example the scripts venv).
Player in `templates/ScrollFilm.tsx`. Traps are in `references/edge-cases.md`: read it once per run.

## 0 · Preflight
- `tools/hf.sh preflight` checks the binary (`~/.npm-global/bin/higgsfield` ≥1.1), auth, credits and **today's spend by model**. A model you didn't run means another consumer is on the account, so stop and tell the operator.
- Run Higgsfield outside the agent sandbox. `ffmpeg`, `yt-dlp`, `whisper-cli` present.
- Quote before generating: `tools/hf.sh cost seedance_2_5 --mode omni_reference --start-image a.png --end-image b.png --resolution 1080p --duration 10`. Reference prices: 2.5 1080p 10 s = 120 credits; 2.0 4k 8 s ≈ 176.

## 1 · Method source (optional)
If the operator points at a reference reel or video: `tools/reel_extract.sh <url> <dir>` produces
the video, caption, contact sheet and local transcript. Write the method up as a table of steps
with timestamps plus a "what it doesn't show" list (see `references/methodology-reel.md`).
The canonical recipe it yields: **fix the end state as an input image, generate the journey,
scrub it on scroll, let the DOM carry the copy.**

## 2 · Anchors (exact brand frames)
1. Generate **plates** (no logo) with an image model at 4k. Nano Banana Pro follows brand
   palettes well; GPT Image 2.5 drifts saturated. Prompt for empty space where the mark goes.
   Generate a separate 16:9 **and** 9:16 composition. Mobile is designed, not cropped.
2. For hero compositions, pass the approved plate as `--image-references` so start and end
   plates share one visual world (for example "inside the object" as the start, "object right third" as the end).
3. `tools/anchor.py --plate end.png --svg brand-mark.svg --at auto --size 1920x1080 --out anchor-end.png`
   composites the **vector master** at the detected glow core. Use `--at X,Y` if auto misses.

## 3 · Film generation
- Seedance 2.5: `--mode omni_reference --start-image <start> --end-image <anchor-end>`, 1080p, 8–10 s,
  `--generate_audio false --bitrate_mode high`. Seedance 2.0 is the only 4k route (`--mode std --resolution 4k`).
- Alternative ("the reel's method"): `--start-image <anchor>` with a prompt that runs the
  process **backwards**, then reverse the clip in `frames.sh --reverse`.
- Prompt skeleton: one continuous shot, no cuts; the start state; what emerges and travels where;
  "ends exactly on the final reference frame"; camera language; lighting; "no text, no people, no
  currency symbols".
- Run through `tools/hf.sh run <out.json> <model> …` (bash; recovers dropped waits), then `hf.sh fetch`.
- Generate 2 variants per format when credits allow. Each run is a new take, and no model
  re-renders a take at a different resolution.

## 4 · Gate: anchor fidelity (hard rule)
`tools/fidelity.py --video clip.mp4 --anchor anchor-end.png`. Generated end frames measured
IoU 0.42–0.68 against the true mark. **`end_image` guides; it does not guarantee.** The player
must therefore dissolve into the exact anchor (`endAnchor` prop). After building, screenshot the
page at the resolve point and re-run `fidelity.py --a shot.png --b anchor.png`. The mark colour
delta must be under 5/255 (the IoU term also counts glow and routes, so read it with the delta).

## 5 · Frames
`tools/frames.sh clip.mp4 public/film/d --fps 48 --long 1920 --q 88` (and `--long 1920` on a 9:16
clip into `public/film/m`). This produces a denoised, optical-flow 48 fps, debanded WebP set plus
`manifest.json`. Check a few mid-motion frames for interpolation warping.
Weight is 6–12 MB per format at q88. That's fine for previews but over budget for production. See §8.

## 6 · Player
Copy `templates/ScrollFilm.tsx` (needs `lenis`). Minimal use:
```tsx
<ScrollFilm desktop={{ dir: "/film/d" }} mobile={{ dir: "/film/m" }}
  start={{ desktop: "/film/start-16x9.webp", mobile: "/film/start-9x16.webp" }}
  endAnchor={{ desktop: "/film/end-16x9.webp", mobile: "/film/end-9x16.webp" }}
  settle={{ desktopVw: 20, mobileVh: -24 }} ariaLabel="Brand">
  {/* headline, subheadline, CTAs — set text colour inline (theme h1 colours bleed) */}
</ScrollFilm>
```
Timing rule: the anchor resolves **before** the settle starts (`filmEnd` 0.74 < `settleStart` 0.78).
Reduced motion shows the settled state immediately.

## 7 · QA
- `tools/probe.py --url http://localhost:3000/ --section 'section[aria-label="Brand"]' --shots /tmp/sf`
  reports frame pacing at 1× and 4× CPU plus desktop and mobile screenshots at progress points.
  Target: ≥55 fps median at 4× and 0 frames over 50 ms on desktop (reference result: 120 fps, 0).
- Look at every screenshot before reporting. Check copy readability, visible edges and the header clash.
- Kill any dev server you start, and never leave one on a port an OAuth callback might use.

## 8 · Quality levers (in order of impact)
1. **Source resolution:** 4k-native generation (Seedance 2.0) or AI upscale. Encoding can't add detail.
2. **Delivery:** WebCodecs decode of one keyframe-dense AV1/H.264 file into in-memory frames
   (5–10× better bytes-to-quality than per-frame images), with `frames.sh` WebP as the fallback.
3. Responsive sets per DPR and viewport, chapter-lazy loading, first and last frame first.
4. A fine CSS film grain over the canvas hides residual compression as an intentional texture.
5. A CDN or edge cache (immutable headers) improves speed, **not** quality.

## Outputs to record
Findings doc (what was generated, credits spent, fidelity numbers, pacing numbers, open levers),
prompts and job JSONs committed, media gitignored unless shipping.

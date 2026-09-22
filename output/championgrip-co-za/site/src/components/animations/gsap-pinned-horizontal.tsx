"use client";
import { useRef, useEffect, ReactNode } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

interface PinnedHorizontalScrollProps {
  /** Content panels to scroll horizontally */
  children: ReactNode;
  /** Additional CSS classes for the pinned section wrapper */
  className?: string;
  /** Scrub smoothness — 0 = instant, 1 = smooth, 2+ = very smooth (default: 1) */
  scrub?: number | boolean;
  /** Easing for the horizontal translate (default: "none" for 1:1 scroll coupling) */
  ease?: string;
  /** Enable snap to panel boundaries (default: false) */
  snap?: boolean;
  /** Whether to add spacing below the pinned section (default: true) */
  pinSpacing?: boolean;
  /** Additional height multiplier for scroll distance. 1 = content width, 1.5 = 50% more scroll needed (default: 1) */
  scrollMultiplier?: number;
  /** Show a progress indicator (dot trail) below the pinned content (default: false) */
  showProgress?: boolean;
  /** Number of panels for snap calculation. If omitted, auto-detected from children count */
  panelCount?: number;
}

/**
 * GSAP Pinned Horizontal Scroll
 *
 * Pins a section in the viewport and translates vertical scroll input into
 * horizontal content movement. The signature pattern of premium marketing sites.
 *
 * Uses ScrollTrigger({ pin: true, scrub: true }) for smooth 1:1 scroll coupling.
 *
 * Mobile: Falls back to a vertical stack layout via gsap.matchMedia().
 * Accessibility: Respects prefers-reduced-motion.
 *
 * @example
 * ```tsx
 * <PinnedHorizontalScroll snap showProgress>
 *   <div className="min-w-screen h-screen flex items-center justify-center">
 *     Panel 1
 *   </div>
 *   <div className="min-w-screen h-screen flex items-center justify-center">
 *     Panel 2
 *   </div>
 * </PinnedHorizontalScroll>
 * ```
 */
export default function PinnedHorizontalScroll({
  children,
  className = "",
  scrub = 1,
  ease = "none",
  snap = false,
  pinSpacing = true,
  scrollMultiplier = 1,
  showProgress = false,
  panelCount,
}: PinnedHorizontalScrollProps) {
  const sectionRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sectionRef.current || !containerRef.current) return;

    const mm = gsap.matchMedia();

    // Desktop: pinned horizontal scroll
    mm.add(
      {
        isDesktop: "(min-width: 768px)",
        isReduced: "(prefers-reduced-motion: reduce)",
      },
      (context) => {
        const { isDesktop, isReduced } = context.conditions as Record<string, boolean>;

        // Reduced motion: no animation at all
        if (isReduced) return;

        // Mobile: skip pinning (content stacks vertically via CSS)
        if (!isDesktop) return;

        const container = containerRef.current!;
        const scrollWidth = container.scrollWidth - window.innerWidth;

        if (scrollWidth <= 0) return;

        const adjustedScrollWidth = scrollWidth * scrollMultiplier;

        const tween = gsap.to(container, {
          x: -scrollWidth,
          ease,
          scrollTrigger: {
            trigger: sectionRef.current,
            pin: true,
            pinSpacing,
            scrub,
            end: () => `+=${adjustedScrollWidth}`,
            invalidateOnRefresh: true,
            ...(snap && panelCount
              ? {
                  snap: {
                    snapTo: 1 / (panelCount - 1),
                    duration: { min: 0.2, max: 0.5 },
                    ease: "power1.inOut",
                  },
                }
              : snap
              ? {
                  snap: {
                    snapTo:
                      1 /
                      Math.max(
                        (container.children.length || 1) - 1,
                        1
                      ),
                    duration: { min: 0.2, max: 0.5 },
                    ease: "power1.inOut",
                  },
                }
              : {}),
            onUpdate: showProgress
              ? (self: { progress: number }) => {
                  if (progressRef.current) {
                    progressRef.current.style.width = `${self.progress * 100}%`;
                  }
                }
              : undefined,
          },
        });

        return () => {
          tween.scrollTrigger?.kill();
          tween.kill();
        };
      }
    );

    return () => mm.revert();
  }, [scrub, ease, snap, pinSpacing, scrollMultiplier, showProgress, panelCount]);

  return (
    <section
      ref={sectionRef}
      className={`relative ${className}`}
      data-pinned-scroll
    >
      {/* Desktop: h-screen overflow-hidden for pinning. Mobile: auto height */}
      <div className="h-screen flex items-center overflow-hidden md:overflow-visible">
        {/* Desktop: flex row. Mobile: flex col */}
        <div
          ref={containerRef}
          className="flex md:flex-row flex-col will-change-transform"
        >
          {children}
        </div>
      </div>

      {/* Progress indicator */}
      {showProgress && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 w-32 h-1 bg-white/20 rounded-full overflow-hidden hidden md:block">
          <div
            ref={progressRef}
            className="h-full bg-white/80 rounded-full transition-none"
            style={{ width: "0%" }}
          />
        </div>
      )}
    </section>
  );
}

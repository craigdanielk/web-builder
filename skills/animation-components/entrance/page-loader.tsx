"use client";
// @ts-nocheck

import React, { useEffect, useRef } from "react";
import gsap from "gsap";

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

type StaggerType = "left-to-right" | "right-to-left" | "center-out" | "edges-in";
type MovementType = "top-down" | "bottom-up" | "fade-out" | "scale-vertical";

interface PageLoaderProps {
  /** Text to display during loading */
  text?: string;
  /** Font size for the text */
  textSize?: string;
  /** Color of the text */
  textColor?: string;
  /** Background color(s) — single or gradient */
  bgColors?: string[];
  /** Gradient angle in degrees */
  angle?: number;
  /** Stagger order for bar animation */
  staggerOrder?: StaggerType;
  /** Direction bars move to reveal content */
  movementDirection?: MovementType;
  /** Delay before text starts fading relative to bars */
  textFadeDelay?: number;
  /** Additional CSS classes */
  className?: string;
  /** Callback when the animation completes */
  onComplete?: () => void;
  /** Font family for the text */
  fontFamily?: string;
}

function PageLoader({
  text = "LOADING",
  textSize = "100px",
  textColor = "white",
  bgColors = ["#000000"],
  angle = 0,
  staggerOrder = "left-to-right",
  movementDirection = "top-down",
  textFadeDelay = 0.5,
  className,
  onComplete,
  fontFamily = "inherit",
}: PageLoaderProps) {
  const preloaderRef = useRef<HTMLDivElement>(null);

  const getBackgroundStyle = () => {
    if (bgColors.length === 0) return { backgroundColor: "black" };
    if (bgColors.length === 1) return { backgroundColor: bgColors[0] };
    return {
      backgroundImage: `linear-gradient(${angle}deg, ${bgColors.join(", ")})`,
    };
  };

  const getStaggerFrom = (type: StaggerType): string | number => {
    switch (type) {
      case "right-to-left":
        return "end";
      case "center-out":
        return "center";
      case "edges-in":
        return "edges";
      case "left-to-right":
      default:
        return "start";
    }
  };

  const getAnimationProperties = (type: MovementType) => {
    switch (type) {
      case "bottom-up":
        return { y: "-100%", ease: "power2.inOut" };
      case "fade-out":
        return { autoAlpha: 0, ease: "power2.inOut" };
      case "scale-vertical":
        return { scaleY: 0, transformOrigin: "center", ease: "power2.inOut" };
      case "top-down":
      default:
        return { y: "100%", ease: "power2.inOut" };
    }
  };

  useEffect(() => {
    if (!preloaderRef.current) return;

    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        onComplete: onComplete,
      });

      const moveProps = getAnimationProperties(movementDirection);
      const staggerConfig = {
        each: 0.1,
        from: getStaggerFrom(staggerOrder) as gsap.Position,
      };

      // 1. Reveal text
      tl.to(".name-text span", {
        y: 0,
        stagger: 0.05,
        duration: 0.2,
        ease: "power2.out",
      });

      // 2. Animate bars
      tl.to(".preloader-item", {
        delay: 1,
        duration: 0.5,
        stagger: staggerConfig,
        ...moveProps,
      })
        // 3. Fade text
        .to(
          ".name-text span",
          { autoAlpha: 0, duration: 0.3 },
          `<${textFadeDelay}`
        )
        // 4. Hide container
        .to(
          preloaderRef.current,
          { autoAlpha: 0, duration: 0.1 },
          "+=0.1"
        );
    }, preloaderRef);

    return () => ctx.revert();
  }, [staggerOrder, movementDirection, textFadeDelay, onComplete]);

  return (
    <div
      className={cn(
        "absolute inset-0 z-[50] flex overflow-hidden bg-transparent",
        className
      )}
      ref={preloaderRef}
    >
      {[...Array(10)].map((_, i) => (
        <div
          key={i}
          className="preloader-item h-full w-[10%]"
          style={getBackgroundStyle()}
        />
      ))}

      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="overflow-hidden">
          <p
            className="name-text flex leading-none tracking-tighter"
            style={{
              fontSize: textSize,
              color: textColor,
              fontWeight: "400",
              fontFamily: fontFamily,
              textTransform: "uppercase",
              zIndex: 10,
              position: "relative",
            }}
          >
            {text.split("").map((char, index) => (
              <span key={index} className="inline-block translate-y-full">
                {char === " " ? "\u00A0" : char}
              </span>
            ))}
          </p>
        </div>
      </div>
    </div>
  );
}

export default PageLoader;

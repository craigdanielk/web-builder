"use client";
// @ts-nocheck

import React, { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

interface StaggeredGridProps {
  /** Child elements to render in the grid */
  children?: React.ReactNode;
  /** Center overlay text */
  centerText?: string;
  /** Additional CSS classes */
  className?: string;
  /** Number of grid columns */
  columns?: number;
  /** Number of grid rows */
  rows?: number;
  /** Whether to show the center text overlay */
  showCenterText?: boolean;
}

function StaggeredGrid({
  children,
  centerText = "Halcyon",
  className,
  columns = 7,
  rows = 5,
  showCenterText = true,
}: StaggeredGridProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const gridRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);

  const splitText = (text: string) => {
    return text.split("").map((char, i) => (
      <span
        key={i}
        className="char inline-block"
        style={{ willChange: "transform" }}
      >
        {char === " " ? "\u00A0" : char}
      </span>
    ));
  };

  // Simple load check without imagesLoaded dependency
  useEffect(() => {
    const images = gridRef.current?.querySelectorAll("img") || [];
    if (images.length === 0) {
      setIsLoaded(true);
      return;
    }

    let loaded = 0;
    const total = images.length;
    const onLoad = () => {
      loaded++;
      if (loaded >= total) setIsLoaded(true);
    };

    images.forEach((img) => {
      if (img.complete) {
        onLoad();
      } else {
        img.addEventListener("load", onLoad);
        img.addEventListener("error", onLoad);
      }
    });

    // Fallback: force loaded after 3s
    const timeout = setTimeout(() => setIsLoaded(true), 3000);
    return () => clearTimeout(timeout);
  }, []);

  useEffect(() => {
    if (!isLoaded || !gridRef.current) return;

    const ctx = gsap.context(() => {
      // Animate text characters
      if (textRef.current) {
        const chars = textRef.current.querySelectorAll(".char");
        gsap.timeline({
          scrollTrigger: {
            trigger: textRef.current,
            start: "top bottom",
            end: "center center-=25%",
            scrub: 1,
          },
        }).from(chars, {
          ease: "sine.out",
          yPercent: 300,
          autoAlpha: 0,
          stagger: {
            each: 0.05,
            from: "center",
          },
        });
      }

      // Animate grid items by column
      if (gridRef.current) {
        const gridItems = gridRef.current.querySelectorAll(".grid__item");
        const numColumns = columns;
        const middleColumnIndex = Math.floor(numColumns / 2);

        const columnGroups: Element[][] = Array.from(
          { length: numColumns },
          () => []
        );
        gridItems.forEach((item, index) => {
          const columnIndex = index % numColumns;
          columnGroups[columnIndex].push(item);
        });

        columnGroups.forEach((columnItems, columnIndex) => {
          const delayFactor =
            Math.abs(columnIndex - middleColumnIndex) * 0.2;

          gsap.timeline({
            scrollTrigger: {
              trigger: gridRef.current,
              start: "top bottom",
              end: "center center",
              scrub: 1.5,
            },
          }).from(columnItems, {
            yPercent: 450,
            autoAlpha: 0,
            delay: delayFactor,
            ease: "sine.out",
          });
        });
      }
    }, gridRef);

    return () => ctx.revert();
  }, [isLoaded, columns]);

  return (
    <div className={cn("relative overflow-hidden w-full", className)}>
      {showCenterText && (
        <section className="grid place-items-center w-full relative mt-[10vh]">
          <div
            ref={textRef}
            className="font-alt uppercase flex content-center text-[clamp(3rem,14vw,10rem)] leading-[0.7] text-neutral-900 dark:text-white"
          >
            {splitText(centerText)}
          </div>
        </section>
      )}

      <section className="grid place-items-center w-full relative">
        <div
          ref={gridRef}
          className="relative w-full my-[10vh] h-auto aspect-[1.1] max-w-none p-4 grid gap-4"
          style={{
            gridTemplateColumns: `repeat(${columns}, 1fr)`,
            gridTemplateRows: `repeat(${rows}, 1fr)`,
          }}
        >
          {children}
        </div>
      </section>
    </div>
  );
}

export default StaggeredGrid;

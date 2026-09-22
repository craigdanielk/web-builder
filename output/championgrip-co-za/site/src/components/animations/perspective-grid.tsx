"use client";
// @ts-nocheck

import React, { useEffect, useState, useMemo } from "react";

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

interface PerspectiveGridProps {
  /** Additional CSS classes for the grid container */
  className?: string;
  /** Number of tiles per row/column */
  gridSize?: number;
  /** Whether to show the gradient overlay */
  showOverlay?: boolean;
  /** Fade radius percentage for the gradient overlay */
  fadeRadius?: number;
}

function PerspectiveGrid({
  className,
  gridSize = 40,
  showOverlay = true,
  fadeRadius = 80,
}: PerspectiveGridProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const tiles = useMemo(
    () => Array.from({ length: gridSize * gridSize }),
    [gridSize]
  );

  return (
    <div
      className={cn(
        "relative w-full h-full overflow-hidden bg-white dark:bg-black",
        "[--fade-stop:#ffffff] dark:[--fade-stop:#000000]",
        className
      )}
      style={{
        perspective: "2000px",
        transformStyle: "preserve-3d",
      }}
    >
      <div
        className="absolute w-[80rem] aspect-square grid origin-center"
        style={{
          left: "50%",
          top: "50%",
          transform:
            "translate(-50%, -50%) rotateX(30deg) rotateY(-5deg) rotateZ(20deg) scale(2)",
          transformStyle: "preserve-3d",
          gridTemplateColumns: `repeat(${gridSize}, 1fr)`,
          gridTemplateRows: `repeat(${gridSize}, 1fr)`,
        }}
      >
        {mounted &&
          tiles.map((_, i) => (
            <div
              key={i}
              className="tile min-h-[1px] min-w-[1px] border border-gray-300 dark:border-gray-700 bg-transparent transition-colors duration-[1500ms] hover:duration-0"
            />
          ))}
      </div>

      {showOverlay && (
        <div
          className="absolute inset-0 pointer-events-none z-10"
          style={{
            background: `radial-gradient(circle, transparent 25%, var(--fade-stop) ${fadeRadius}%)`,
          }}
        />
      )}
    </div>
  );
}

export default PerspectiveGrid;

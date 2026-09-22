"use client";
// @ts-nocheck

import React, { useMemo } from "react";

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

interface CharacterFlipProps {
  /** The text content to animate */
  text?: string;
  /** Additional CSS classes for the wrapper */
  className?: string;
  /** Duration of the flip animation in seconds */
  duration?: number;
  /** Initial delay before animation starts in seconds */
  delay?: number;
  /** Whether the animation should loop infinitely */
  loop?: boolean;
  /** Custom separator for splitting text */
  separator?: string;
  /** Whether all characters should animate together (no stagger) */
  together?: boolean;
}

function CharacterFlip({
  text = "Hello World",
  className,
  duration = 2.2,
  delay = 0,
  loop = true,
  separator = " ",
  together = false,
}: CharacterFlipProps) {
  const words = useMemo(() => text.split(separator), [text, separator]);
  const totalChars = text.length;

  const getCharIndex = (wordIndex: number, charIndex: number) => {
    let index = 0;
    for (let i = 0; i < wordIndex; i++) {
      index += words[i].length + (separator === " " ? 1 : separator.length);
    }
    return index + charIndex;
  };

  return (
    <div
      className={cn(
        "flip-text-wrapper inline-block leading-none",
        className
      )}
      style={{ perspective: "1000px" }}
    >
      {words.map((word, wordIndex) => {
        const chars = word.split("");

        return (
          <span
            key={wordIndex}
            className="word inline-block whitespace-nowrap"
            style={{ transformStyle: "preserve-3d" }}
          >
            {chars.map((char, charIndex) => {
              const currentGlobalIndex = getCharIndex(wordIndex, charIndex);

              let calculatedDelay = delay;
              if (!together) {
                const normalizedIndex = currentGlobalIndex / totalChars;
                const sineValue = Math.sin(normalizedIndex * (Math.PI / 2));
                calculatedDelay = sineValue * (duration * 0.25) + delay;
              }

              return (
                <span
                  key={charIndex}
                  className="flip-char inline-block relative"
                  data-char={char}
                  style={
                    {
                      "--flip-duration": `${duration}s`,
                      "--flip-delay": `${calculatedDelay}s`,
                      "--flip-iteration": loop ? "infinite" : "1",
                      transformStyle: "preserve-3d",
                    } as React.CSSProperties
                  }
                >
                  {char}
                </span>
              );
            })}
            {separator === " " && wordIndex < words.length - 1 && (
              <span className="whitespace inline-block">&nbsp;</span>
            )}
            {separator !== " " && wordIndex < words.length - 1 && (
              <span className="separator inline-block">{separator}</span>
            )}
          </span>
        );
      })}
    </div>
  );
}

export default CharacterFlip;

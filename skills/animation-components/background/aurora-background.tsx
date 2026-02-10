"use client";
// @ts-nocheck

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

interface AuroraBackgroundProps {
  /** Content to render over the aurora background */
  children?: React.ReactNode;
  /** Additional CSS classes */
  className?: string;
  /** Force specific theme rendering */
  forceTheme?: "dark" | "light";
}

function AuroraBackground({
  children,
  className = "",
  forceTheme,
}: AuroraBackgroundProps) {
  const [isDark, setIsDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    const checkDarkMode = () => {
      if (forceTheme) return forceTheme === "dark";
      return document.documentElement.classList.contains("dark");
    };
    setIsDark(checkDarkMode());

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === "class") {
          setIsDark(checkDarkMode());
        }
      });
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => observer.disconnect();
  }, [forceTheme]);

  if (!mounted) {
    return null;
  }

  return (
    <section className={cn("relative w-full h-auto", className)}>
      {/* Animated Aurora Background */}
      <div
        className="relative w-full h-full min-h-[500px] flex items-center justify-center transition-all duration-500"
        style={{
          backgroundImage: `
            repeating-linear-gradient(
              100deg,
              var(--stripe-color) 0%,
              var(--stripe-color) 7%,
              transparent 10%,
              transparent 12%,
              var(--stripe-color) 16%
            ),
            repeating-linear-gradient(
              100deg,
              hsl(var(--rainbow-blue)) 10%,
              hsl(var(--rainbow-pink)) 15%,
              hsl(var(--rainbow-blue)) 20%,
              hsl(var(--rainbow-cyan)) 25%,
              hsl(var(--rainbow-blue)) 30%
            )
          `,
          backgroundSize: "300%, 200%",
          backgroundPosition: "50% 50%, 50% 50%",
          filter: isDark
            ? "blur(10px) opacity(0.5) saturate(2)"
            : "blur(10px) invert(1)",
          maskImage:
            "radial-gradient(circle at 50% 50%, black 60%, transparent 100%)",
          WebkitMaskImage:
            "radial-gradient(circle at 50% 50%, black 60%, transparent 100%)",
        }}
      >
        <div
          className="absolute inset-0 animate-aurora-bg"
          style={{
            backgroundImage: `
              repeating-linear-gradient(
                100deg,
                var(--stripe-color) 0%,
                var(--stripe-color) 7%,
                transparent 10%,
                transparent 12%,
                var(--stripe-color) 16%
              ),
              repeating-linear-gradient(
                100deg,
                hsl(var(--rainbow-blue)) 10%,
                hsl(var(--rainbow-pink)) 15%,
                hsl(var(--rainbow-blue)) 20%,
                hsl(var(--rainbow-cyan)) 25%,
                hsl(var(--rainbow-blue)) 30%
              )
            `,
            backgroundSize: "200%, 100%",
            backgroundAttachment: "fixed",
            mixBlendMode: "difference",
          }}
        />
      </div>

      {/* Content Overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-8 text-center px-4">
        {children}
      </div>
    </section>
  );
}

export default AuroraBackground;

"use client";

import React, { useRef, useEffect, useState } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";

interface MagneticButtonProps {
  /** Button content */
  children: React.ReactNode;
  /** Additional CSS classes for the button */
  className?: string;
  /** How strongly the button is attracted to the cursor (0-1) */
  strength?: number;
  /** Distance in pixels at which the magnetic effect activates */
  magneticDistance?: number;
  /** Click handler */
  onClick?: () => void;
  /** HTML button type */
  type?: "button" | "submit" | "reset";
  /** Disabled state */
  disabled?: boolean;
}

export function MagneticButton({
  children,
  className = "",
  strength = 0.45,
  magneticDistance = 120,
  onClick,
  type = "button",
  disabled = false,
}: MagneticButtonProps) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const springConfig = { stiffness: 200, damping: 20 };
  const springX = useSpring(x, springConfig);
  const springY = useSpring(y, springConfig);

  const [isHovering, setIsHovering] = useState(false);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (buttonRef.current) {
        const button = buttonRef.current.getBoundingClientRect();
        const centerX = button.left + button.width / 2;
        const centerY = button.top + button.height / 2;

        const deltaX = e.pageX - centerX;
        const deltaY = e.pageY - centerY;

        const distance = Math.sqrt(deltaX ** 2 + deltaY ** 2);

        if (distance < magneticDistance) {
          const pull = 1 - distance / magneticDistance;
          x.set(deltaX * pull * strength);
          y.set(deltaY * pull * strength);
          setIsHovering(true);
        } else {
          x.set(0);
          y.set(0);
          setIsHovering(false);
        }
      }
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [x, y, strength, magneticDistance]);

  return (
    <motion.button
      ref={buttonRef}
      className={className}
      style={{ x: springX, y: springY }}
      onClick={onClick}
      type={type}
      disabled={disabled}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      data-hovering={isHovering}
    >
      {children}
    </motion.button>
  );
}

export default MagneticButton;

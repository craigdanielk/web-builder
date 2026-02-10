"use client";
// @ts-nocheck

import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

interface CountUpProps {
  /** The numeric value to display */
  value?: number;
  /** Additional CSS classes */
  className?: string;
}

function CountUp({ value = 0, className }: CountUpProps) {
  return (
    <div className={cn("flex items-center", className)}>
      <div className="flex relative items-center">
        {value.toString().split("").map((digit, index) => (
          <SingleNumberHolder key={index} value={digit} index={index} />
        ))}
      </div>
    </div>
  );
}

function SingleNumberHolder({ value, index }: { value: string; index: number }) {
  const [height, setHeight] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  let notANumber = false;

  useEffect(() => {
    if (containerRef.current) {
      setHeight(getComputedStyle(containerRef.current).height);
    }
  }, []);

  if (index === 0) {
    notANumber = isNaN(Number.parseInt(value));
  }

  const vars = {
    init: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
  };

  return (
    <div
      className="relative"
      style={{ height: height || "auto", overflowY: "hidden", overflowX: "clip" }}
      ref={containerRef}
    >
      {notANumber && (
        <motion.span
          initial="init"
          animate="animate"
          exit="exit"
          variants={vars}
          key={value}
          layout="size"
        >
          {value}
        </motion.span>
      )}
      {!notANumber && <RenderStrip value={value} eleHeight={height} />}
    </div>
  );
}

const zeroToNine = Array.from({ length: 10 }, (_, k) => k);

function RenderStrip({ eleHeight, value }: { eleHeight: string | null; value: string }) {
  const heightInNumber = Number.parseInt(eleHeight?.replace("px", "") || "48");
  const negative = heightInNumber * -1;
  const pos = heightInNumber;
  const prev = useRef(value);

  const currentVal = parseInt(value);
  const prevVal = parseInt(prev.current);

  const diff = prevVal - currentVal;
  const dir = currentVal > prevVal ? pos * diff * -1 : negative * diff;

  useEffect(() => {
    prev.current = value;
  }, [value]);

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={value}
        initial={{ y: dir }}
        animate={{ y: 0 }}
        exit={{ y: 0, transition: { duration: 0.1 } }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="flex relative flex-col"
      >
        <motion.span
          layout
          key={`negative-${value}`}
          className="flex flex-col items-center absolute bottom-full left-0"
        >
          {zeroToNine
            .filter((val) => val < currentVal)
            .map((val, idx) => (
              <span key={`${val}_${idx}`}>{val}</span>
            ))}
        </motion.span>

        <span key={`current-${value}`}>{value}</span>

        <motion.span
          layout
          key={`positive-${value}`}
          className="flex flex-col items-center absolute top-full left-0"
        >
          {zeroToNine
            .filter((val) => val > currentVal)
            .map((val, idx) => (
              <span key={`${val}_${idx}`}>{val}</span>
            ))}
        </motion.span>
      </motion.div>
    </AnimatePresence>
  );
}

export default CountUp;

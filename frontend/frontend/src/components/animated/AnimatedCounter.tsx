"use client";

import { useEffect, useState } from "react";
import { motion, useSpring, useTransform } from "framer-motion";
import { spring } from "@/lib/animations";

interface AnimatedCounterProps {
  value: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
  className?: string;
}

export function AnimatedCounter({ 
  value, 
  duration = 1.5, 
  suffix = "", 
  prefix = "",
  className = "" 
}: AnimatedCounterProps) {
  const [hasHydrated, setHasHydrated] = useState(false);
  const motionValue = useSpring(0, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001
  });

  const rounded = useTransform(motionValue, (latest) => Math.round(latest));

  useEffect(() => {
    setHasHydrated(true);
    motionValue.set(value);
  }, [motionValue, value]);

  if (!hasHydrated) {
    return <span className={className}>{prefix}0{suffix}</span>;
  }

  return (
    <span className={`inline-flex items-center ${className}`}>
      {prefix}
      <motion.span>{rounded}</motion.span>
      {suffix}
    </span>
  );
}

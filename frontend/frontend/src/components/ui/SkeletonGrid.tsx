"use client";

import { motion } from "framer-motion";
import { staggerContainer } from "@/lib/animations";

interface SkeletonGridProps {
  count: number;
  variant: "course-card" | "insight-card";
}

export function SkeletonGrid({ count, variant }: SkeletonGridProps) {
  const items = Array.from({ length: count });

  if (variant === "course-card") {
    return (
      <motion.div 
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        {items.map((_, i) => (
          <motion.div
            key={i}
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0 }
            }}
            className="h-[280px] rounded-2xl bg-white/5 border border-white/10 overflow-hidden relative"
          >
            {/* Shimmer Effect */}
            <motion.div
              animate={{ x: ["-100%", "200%"] }}
              transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
              className="absolute inset-0 z-10 bg-gradient-to-r from-transparent via-white/5 to-transparent skew-x-12"
            />
            
            <div className="p-6 h-full flex flex-col gap-4">
              <div className="w-16 h-16 rounded-xl bg-white/10" />
              <div className="w-3/4 h-6 rounded bg-white/10 mt-2" />
              <div className="w-full h-4 rounded bg-white/10" />
              <div className="w-1/2 h-4 rounded bg-white/10" />
              
              <div className="mt-auto flex justify-between">
                <div className="w-1/3 h-8 rounded-full bg-white/10" />
                <div className="w-10 h-10 rounded-full bg-white/10" />
              </div>
            </div>
          </motion.div>
        ))}
      </motion.div>
    );
  }

  if (variant === "insight-card") {
    return (
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 md:grid-cols-2 gap-4"
      >
        {items.map((_, i) => (
          <motion.div
            key={i}
            variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
            className="h-[120px] rounded-xl bg-white/5 border border-white/10 overflow-hidden relative p-5 flex flex-col gap-3"
          >
            <motion.div
              animate={{ x: ["-100%", "200%"] }}
              transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
              className="absolute inset-0 z-10 bg-gradient-to-r from-transparent via-white/5 to-transparent skew-x-12"
            />
            <div className="w-1/2 h-4 rounded bg-white/10" />
            <div className="w-full h-3 rounded bg-white/10" />
            <div className="w-2/3 h-3 rounded bg-white/10" />
          </motion.div>
        ))}
      </motion.div>
    );
  }

  return null;
}

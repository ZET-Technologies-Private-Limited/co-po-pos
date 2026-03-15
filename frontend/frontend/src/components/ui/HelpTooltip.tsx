"use client";

import { useState } from "react";
import { HelpCircle } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

interface HelpTooltipProps {
  text: string;
  className?: string;
}

export function HelpTooltip({ text, className = "" }: HelpTooltipProps) {
  const [open, setOpen] = useState(false);

  return (
    <span className={`relative inline-flex items-center ${className}`}>
      <button
        type="button"
        aria-label={`Help: ${text}`}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="text-white/25 hover:text-white/60 transition-colors focus:outline-none focus:text-white/60"
      >
        <HelpCircle className="w-3.5 h-3.5" aria-hidden="true" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            role="tooltip"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.15 }}
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 bg-[#1E293B] border border-white/10 px-3 py-2 text-xs text-white/70 font-light leading-relaxed shadow-xl z-50 pointer-events-none"
          >
            {text}
            <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-[#1E293B]" />
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  );
}

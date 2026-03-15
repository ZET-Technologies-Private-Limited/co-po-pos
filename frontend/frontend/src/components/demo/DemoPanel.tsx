"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDemoStore } from "@/lib/demoStore";
import { Gauge, Wand2, RefreshCcw, X } from "lucide-react";

export function DemoPanel() {
  const [isVisible, setIsVisible] = useState(false);
  const { isActive, speed, toggleDemo, setSpeed, resetDemo } = useDemoStore();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.shiftKey && e.key === 'D') {
        setIsVisible(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (!isVisible) return null;

  const speeds = [
    { label: "1x", value: 1 },
    { label: "2x", value: 2 },
    { label: "5x", value: 5 },
  ];

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 50, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 50, scale: 0.95 }}
        className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] bg-black/80 backdrop-blur-xl border border-white/20 rounded-2xl p-4 shadow-2xl flex items-center gap-6"
      >
        <div className="flex items-center gap-3 border-r border-white/20 pr-6">
          <div className={`w-3 h-3 rounded-full ${isActive ? 'bg-attain animate-pulse' : 'bg-white/20'}`} />
          <span className="text-white font-mono text-sm tracking-wider uppercase">
            Hackathon Demo Panel
          </span>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={toggleDemo}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              isActive ? 'bg-brand text-white' : 'bg-white/10 text-white/50 hover:bg-white/20 hover:text-white'
            }`}
          >
            <Wand2 className="w-4 h-4" />
            {isActive ? 'Demo Active' : 'Start Auto-Pilot'}
          </button>

          <div className="flex items-center gap-2 bg-white/5 rounded-lg p-1 border border-white/10">
            <Gauge className="w-4 h-4 text-white/50 ml-2" />
            {speeds.map(s => (
              <button
                key={s.value}
                onClick={() => setSpeed(s.value)}
                className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
                  speed === s.value ? 'bg-white/20 text-white' : 'text-white/40 hover:text-white'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>

          <button
            onClick={resetDemo}
            className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/5 hover:bg-alert/20 hover:text-alert text-white/50 transition-colors"
            title="Reset Demo State"
          >
            <RefreshCcw className="w-4 h-4" />
          </button>

          <button
            onClick={() => setIsVisible(false)}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/10 text-white/50 hover:text-white transition-colors ml-4"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

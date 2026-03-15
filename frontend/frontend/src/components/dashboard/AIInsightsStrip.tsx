"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";

export function AIInsightsStrip() {
  const insights = [
    "CO3 in DBMS is 12% below target threshold.",
    "Data Structures mid-term shows high variance in PO2 attainment.",
    "3 new syllabi pending AI mapping generation.",
    "Operating Systems course has achieved 94% PO coverage.",
    "Suggested intervention for CSE-301 based on recent quiz scores."
  ];

  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % insights.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [insights.length]);

  return (
    <div className="w-full bg-insight/10 border border-insight/30 rounded-2xl p-4 flex items-center gap-4 overflow-hidden relative">
      <div className="absolute left-0 top-0 bottom-0 w-16 bg-gradient-to-r from-[#0F172A] to-transparent z-10" />
      <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-[#0F172A] to-transparent z-10" />
      
      <div className="bg-insight text-white w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(124,58,237,0.5)] z-20">
        <Sparkles className="w-4 h-4" />
      </div>
      
      <div className="flex-1 relative h-6 overflow-hidden z-0">
        <motion.div
           key={currentIndex}
           initial={{ y: 30, opacity: 0 }}
           animate={{ y: 0, opacity: 1 }}
           exit={{ y: -30, opacity: 0 }}
           transition={{ type: "spring", stiffness: 300, damping: 30 }}
           className="absolute inset-0 flex items-center text-sm font-medium text-white/90 whitespace-nowrap"
        >
           <span className="opacity-50 mr-2">AI Insight:</span> {insights[currentIndex]}
        </motion.div>
      </div>
      
      <div className="flex gap-1 z-20">
         {insights.map((_, i) => (
           <div 
             key={i} 
             className={`h-1.5 rounded-full transition-all duration-500 ${i === currentIndex ? 'w-4 bg-insight' : 'w-1.5 bg-white/20'}`} 
           />
         ))}
      </div>
    </div>
  );
}

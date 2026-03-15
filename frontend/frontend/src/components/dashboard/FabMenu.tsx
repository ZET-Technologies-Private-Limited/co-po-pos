"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Upload, BrainCircuit, FileSearch, Users } from "lucide-react";
import { spring } from "@/lib/animations";

export function FabMenu() {
  const [isOpen, setIsOpen] = useState(false);

  const actions = [
    { id: "upload", icon: Upload, label: "Upload Syllabus", rotate: -90, x: 0, y: -70 },
    { id: "ai", icon: BrainCircuit, label: "Generate Mapping", rotate: -45, x: -50, y: -50 },
    { id: "analyze", icon: FileSearch, label: "Analyze Exams", rotate: 0, x: -70, y: 0 },
    { id: "team", icon: Users, label: "Manage Faculty", rotate: -135, x: 50, y: -50 },
  ];

  return (
    <div className="fixed bottom-32 right-8 z-40 flex items-center justify-center">
      <AnimatePresence>
        {isOpen && (
           <>
             {actions.map((action, i) => (
                <motion.button
                  key={action.id}
                  initial={{ opacity: 0, scale: 0, x: 0, y: 0 }}
                  animate={{ 
                    opacity: 1, 
                    scale: 1, 
                    x: action.x, 
                    y: action.y 
                  }}
                  exit={{ opacity: 0, scale: 0, x: 0, y: 0 }}
                  transition={{ 
                    ...spring.snappy,
                    delay: i * 0.05 
                  }}
                  className="absolute w-12 h-12 rounded-full bg-white/10 border border-white/20 backdrop-blur-xl flex items-center justify-center text-white hover:bg-white/20 hover:scale-110 transition-colors group"
                >
                   <action.icon className="w-5 h-5" />
                   
                   {/* Tooltip */}
                   <div className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-cosmic border border-white/10 rounded-md text-[10px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                     {action.label}
                   </div>
                </motion.button>
             ))}
           </>
        )}
      </AnimatePresence>

      <motion.button
        animate={{ rotate: isOpen ? 45 : 0 }}
        transition={spring.snappy}
        onClick={() => setIsOpen(!isOpen)}
        className="relative w-14 h-14 rounded-full bg-gradient-to-tr from-brand to-aurora flex items-center justify-center text-white shadow-[0_0_20px_rgba(29,78,216,0.5)] z-10"
      >
        <Plus className="w-6 h-6" />
      </motion.button>
    </div>
  );
}

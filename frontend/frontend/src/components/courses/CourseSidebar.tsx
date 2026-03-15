"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Circle } from "lucide-react";
import { AnimatedCounter } from "@/components/animated/AnimatedCounter";

export function CourseSidebar({ courseId }: { courseId: string }) {
  const steps = [
    { id: 1, label: "Syllabus Upload", status: "complete" },
    { id: 2, label: "CO Generation", status: "complete" },
    { id: 3, label: "PO/PSO Mapping", status: "current" },
    { id: 4, label: "Exam Analysis", status: "pending" },
    { id: 5, label: "Attainment Report", status: "pending" },
    { id: 6, label: "Final Submission", status: "pending" },
  ];

  const completedSteps = steps.filter(s => s.status === "complete").length;
  const totalSteps = steps.length;
  const progress = Math.round((completedSteps / totalSteps) * 100);

  return (
    <div className="w-72 shrink-0 flex flex-col gap-6 sticky top-24">
      {/* Course Metadata - FLAT AI STYLE */}
      <div className="relative overflow-hidden group pb-8 border-b border-white/10">
         {/* <div className="absolute inset-0 bg-gradient-to-br from-brand/20 to-aurora/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500" /> */}
         
         <div className="relative z-10">
           <div className="px-2 py-1 bg-white/10 w-max rounded text-xs font-mono text-white/70 mb-4">CSE-301</div>
           <h2 className="text-2xl font-display text-white leading-tight mb-2">Database Management Systems</h2>
           <p className="text-sm text-white/50 mb-6">B.Tech • Semester 5 • Core</p>
           
           {/* circular progress ring */}
           <div className="flex items-center gap-4 bg-black/20 p-4 rounded-2xl border border-white/5">
              <div className="relative w-12 h-12 flex items-center justify-center shrink-0">
                 <svg className="w-full h-full -rotate-90">
                    <circle cx="24" cy="24" r="20" className="stroke-white/10 stroke-2 fill-none" />
                    <motion.circle 
                      cx="24" cy="24" r="20" 
                      className="stroke-brand stroke-2 fill-none" 
                      strokeLinecap="round"
                      strokeDasharray={2 * Math.PI * 20}
                      initial={{ strokeDashoffset: 2 * Math.PI * 20 }}
                      animate={{ strokeDashoffset: 2 * Math.PI * 20 * (1 - progress / 100) }}
                      transition={{ duration: 1.5, ease: "easeOut" }}
                    />
                 </svg>
                 <div className="absolute inset-0 flex items-center justify-center text-xs font-mono font-bold text-white">
                   <AnimatedCounter value={progress} duration={1.5} />%
                 </div>
              </div>
              <div className="text-sm">
                <div className="text-white font-medium">Overall Progress</div>
                <div className="text-white/40">{completedSteps} of {totalSteps} steps</div>
              </div>
           </div>
         </div>
      </div>

      {/* Workflow Pipeline - LINEAR STYLE */}
      <div className="pt-4">
         <h3 className="text-[10px] font-mono text-white/20 uppercase tracking-[0.3em] mb-10 pl-3">Phase Protocol</h3>
         
         <div className="flex flex-col relative">
           <div className="absolute left-[11px] top-3 bottom-4 w-0.5 bg-white/10" />
           <motion.div 
             className="absolute left-[11px] top-3 w-0.5 bg-gradient-to-b from-brand to-aurora origin-top"
             initial={{ scaleY: 0 }}
             animate={{ scaleY: (completedSteps + 0.5) / totalSteps }}
             transition={{ duration: 1.5, ease: "easeOut" }}
           />
           
           {steps.map((step, i) => (
             <div key={step.id} className="flex flex-col group relative">
                <div className="flex items-center gap-4 py-3 relative z-10">
                  <div className={`w-6 h-6 rounded-full bg-cosmic flex items-center justify-center shrink-0 border-2 transition-colors duration-500
                    ${step.status === 'complete' ? 'border-aurora text-aurora' : 
                      step.status === 'current' ? 'border-brand text-brand' : 'border-white/20 text-transparent'}
                  `}>
                     {step.status === 'complete' ? <CheckCircle2 className="w-4 h-4" /> : <Circle className="w-2 h-2 fill-current" />}
                  </div>
                  <div className={`text-sm transition-colors duration-300
                    ${step.status === 'complete' ? 'text-white/80' : 
                      step.status === 'current' ? 'text-white font-semibold' : 'text-white/40'}
                  `}>
                    {step.label}
                  </div>
                </div>
             </div>
           ))}
         </div>
      </div>
      
      {/* Keyboard Shortcuts Hint */}
      <div className="text-center">
         <p className="text-xs text-white/30 font-mono">Press <kbd className="px-1.5 py-0.5 rounded bg-white/10 border border-white/20 text-white/50 pb-1">?</kbd> for shortcuts</p>
      </div>
    </div>
  );
}

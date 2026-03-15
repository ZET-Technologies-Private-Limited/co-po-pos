"use client";

import { motion } from "framer-motion";
import { FileDown, Sparkles, BookOpen, Clock } from "lucide-react";

export function ActivityTimeline() {
  const activities = [
    { id: 1, title: "Exam uploaded", time: "10 mins ago", icon: FileDown, color: "text-brand" },
    { id: 2, title: "AI analysis complete", time: "45 mins ago", icon: Sparkles, color: "text-aurora" },
    { id: 3, title: "DBMS Syllabus updated", time: "2 hours ago", icon: BookOpen, color: "text-emerald-500" },
    { id: 4, title: "Mid-term report generated", time: "5 hours ago", icon: Clock, color: "text-purple-500" },
  ];

  return (
    <div className="w-full flex flex-col relative py-4">
      <div className="flex-1 relative pl-4">
        <div className="absolute left-[39px] top-6 bottom-6 w-[1px] bg-white/10" />
        
        <div className="flex flex-col gap-12">
          {activities.map((activity, i) => (
             <motion.div
               key={activity.id}
               initial={{ opacity: 0, x: -20 }}
               whileInView={{ opacity: 1, x: 0 }}
               viewport={{ once: true }}
               transition={{ delay: 0.2 + i * 0.1, type: "spring", stiffness: 300, damping: 24 }}
               className="flex items-start gap-8 relative z-10 group"
             >
                <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 bg-cosmic border border-white/20 group-hover:border-white/50 transition-colors`}>
                   <activity.icon className={`w-5 h-5 ${activity.color} opacity-80 group-hover:opacity-100 transition-opacity`} />
                </div>
                
                <div className="flex flex-col pt-2 pb-6 border-b border-white/5 flex-1 group-hover:border-white/20 transition-colors">
                   <span className="text-lg font-display text-white group-hover:text-white transition-colors">{activity.title}</span>
                   <span className="text-sm text-white/40 font-mono mt-1 group-hover:text-white/60 transition-colors">{activity.time}</span>
                </div>
             </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

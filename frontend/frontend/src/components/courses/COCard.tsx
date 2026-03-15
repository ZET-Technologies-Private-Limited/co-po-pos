"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, RefreshCw, PenSquare, Trash2, Check, Sparkles, Target, X } from "lucide-react";

interface COCardProps {
  id: string;
  name: string;
  description: string;
  level: string;
  confidence: number;
  streaming?: boolean;
}

const bloomColors: Record<string, string> = {
  "Remember": "text-white/20",
  "Understand": "text-brand",
  "Apply": "text-aurora",
  "Analyze": "text-insight",
  "Evaluate": "text-alert",
  "Create": "text-attain",
};

export function COCard({ id, name, description, level, confidence, streaming = false }: COCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedDesc, setEditedDesc] = useState(description);
  
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 50 : 1,
  };

  const isLowConfidence = confidence < 75;

  return (
    <motion.div
      ref={setNodeRef}
      style={style}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1, y: isDragging ? -5 : 0 }}
      className={`relative w-full py-10 border-b border-white/5 group transition-all ${isDragging ? 'bg-white/[0.03] pl-4 border-white/20' : 'hover:bg-white/[0.01]'}`}
    >
      <div className="flex gap-8 items-start">
        {/* Drag Handle */}
        <div 
           {...attributes} 
           {...listeners}
           className="mt-2 cursor-grab active:cursor-grabbing text-white/10 hover:text-white/40 transition-colors shrink-0"
        >
          <GripVertical className="w-5 h-5" />
        </div>
        
        <div className="flex-1 min-w-0">
           <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-6">
              <div className="flex flex-wrap items-center gap-8">
                 <span className="text-4xl font-mono font-light text-white/10 group-hover:text-white/30 transition-colors">{name}</span>
                 
                 <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest leading-none">Cognitive Complexity</span>
                    <span className={`text-sm font-mono uppercase tracking-widest ${bloomColors[level] || bloomColors['Remember']} flex items-center gap-2`}>
                       <span className="w-1.5 h-1.5 rounded-full bg-current opacity-40" />
                       {level}
                    </span>
                 </div>
                 
                 <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest leading-none">Diagnostic Trust</span>
                    <div className="flex items-center gap-3">
                       <span className={`text-sm font-mono uppercase tracking-widest ${isLowConfidence ? 'text-alert' : 'text-attain'}`}>{confidence}%</span>
                       <div className="w-16 h-[1px] bg-white/5 relative overflow-hidden">
                          <motion.div className={`h-full ${isLowConfidence ? 'bg-alert' : 'bg-attain'}`} 
                             initial={{ width: 0 }} animate={{ width: `${confidence}%` }} transition={{ duration: 1.5 }} />
                       </div>
                    </div>
                 </div>

                 {isLowConfidence && (
                   <span className="text-[10px] font-mono text-alert border border-alert/20 px-3 py-1 bg-alert/5 uppercase tracking-widest animate-pulse">
                     Structural Review Advised
                   </span>
                 )}
              </div>
              
              <div className="flex gap-4 md:opacity-0 group-hover:opacity-100 transition-all shrink-0">
                 {isEditing ? (
                   <button onClick={() => setIsEditing(false)} className="w-10 h-10 border border-attain text-attain flex items-center justify-center hover:bg-attain hover:text-white transition-all">
                     <Check className="w-4 h-4" />
                   </button>
                 ) : (
                   <>
                     <button className="w-10 h-10 border border-white/5 text-white/20 flex items-center justify-center hover:border-white hover:text-white transition-all">
                       <RefreshCw className="w-4 h-4" />
                     </button>
                     <button onClick={() => setIsEditing(true)} className="w-10 h-10 border border-white/5 text-white/20 flex items-center justify-center hover:border-white hover:text-white transition-all">
                       <PenSquare className="w-4 h-4" />
                     </button>
                     <button className="w-10 h-10 border border-white/5 text-white/10 flex items-center justify-center hover:border-alert hover:text-alert transition-all">
                       <Trash2 className="w-4 h-4" />
                     </button>
                   </>
                 )}
              </div>
           </div>
           
           <div className="pl-0 md:pl-0">
              {isEditing ? (
                 <textarea 
                   value={editedDesc}
                   onChange={e => setEditedDesc(e.target.value)}
                   className="w-full bg-white/[0.03] border border-white/10 p-6 text-xl font-light text-white outline-none focus:border-brand transition-all resize-none font-display leading-relaxed"
                   rows={3}
                   autoFocus
                 />
              ) : (
                 <p className="text-2xl font-light text-white/70 group-hover:text-white transition-colors leading-relaxed font-display">{editedDesc}</p>
              )}
           </div>
        </div>
      </div>
    </motion.div>
  );
}

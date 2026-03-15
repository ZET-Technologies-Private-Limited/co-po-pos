"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface MatrixGridProps {
  cos: { id: string, name: string }[];
  pos: { id: string, name: string }[];
  initialMapping: Record<string, Record<string, number>>;
  isHeatmap?: boolean;
}

export function MatrixGrid({ cos, pos, initialMapping, isHeatmap = false }: MatrixGridProps) {
  const [mapping, setMapping] = useState(initialMapping);

  const handleCellClick = (coId: string, poId: string) => {
    if (isHeatmap) return;
    
    setMapping(prev => {
      const current = prev[coId]?.[poId] || 0;
      const next = (current + 1) % 4;
      
      return {
        ...prev,
        [coId]: {
          ...(prev[coId] || {}),
          [poId]: next
        }
      };
    });
  };

  const getCellColor = (val: number, isHeatmap: boolean) => {
    if (val === 0) return isHeatmap ? "bg-alert/10 border-alert/20 text-alert/40" : "bg-white/5 border-white/5 text-white/10";
    if (val === 1) return "bg-brand/10 border-brand/20 text-brand";
    if (val === 2) return "bg-brand/40 border-brand/50 text-white";
    if (val === 3) return "bg-brand border-brand text-white shadow-[0_0_20px_rgba(37,99,235,0.3)]";
    return "";
  };

  return (
    <div className="w-full overflow-hidden relative border-t border-white/10">
       <div className="overflow-x-auto">
         <table className="w-full text-left border-collapse">
            <thead>
               <tr className="border-b border-white/10">
                 <th className="p-8 border-r border-white/10 w-32 shrink-0 sticky left-0 z-20 bg-cosmic">
                   <div className="text-[10px] font-mono text-white/20 uppercase tracking-[0.2em]">CO \ PO</div>
                 </th>
                 {pos.map(po => (
                   <th key={po.id} className="p-8 text-center min-w-[80px]">
                     <div className="text-sm font-mono text-white/40 uppercase tracking-widest">{po.name}</div>
                   </th>
                 ))}
               </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {cos.map((co, i) => (
                <motion.tr 
                   key={co.id}
                   initial={{ opacity: 0 }}
                   whileInView={{ opacity: 1 }}
                   transition={{ delay: i * 0.05 }}
                   className="group"
                >
                  <td className="p-8 border-r border-white/10 sticky left-0 z-20 bg-cosmic transition-colors">
                     <div className="font-display text-2xl text-white group-hover:text-brand transition-colors">{co.name}</div>
                  </td>
                  
                  {pos.map((po) => {
                    const val = mapping[co.id]?.[po.id] || 0;
                    return (
                      <td key={po.id} className="p-4 text-center">
                        <motion.button
                           whileTap={!isHeatmap ? { scale: 0.95 } : {}}
                           onClick={() => handleCellClick(co.id, po.id)}
                           className={`w-12 h-12 flex items-center justify-center mx-auto text-xs font-mono transition-all border ${getCellColor(val, isHeatmap)} ${!isHeatmap ? 'cursor-pointer hover:scale-105' : 'cursor-default'}`}
                        >
                           <AnimatePresence mode="wait">
                              <motion.span
                                 key={val}
                                 initial={{ opacity: 0 }}
                                 animate={{ opacity: 1 }}
                              >
                                {val > 0 ? (
                                  <span className="font-bold underline underline-offset-4 decoration-white/20">{val}</span>
                                ) : (
                                  <span className="opacity-20">{isHeatmap ? "!" : "-"}</span>
                                )}
                              </motion.span>
                           </AnimatePresence>
                        </motion.button>
                      </td>
                    );
                  })}
                </motion.tr>
              ))}
            </tbody>
         </table>
       </div>
    </div>
  );
}

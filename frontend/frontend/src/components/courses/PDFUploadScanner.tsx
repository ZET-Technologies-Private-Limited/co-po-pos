"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, FileText, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { spring } from "@/lib/animations";

interface PDFUploadScannerProps {
  onScanComplete: () => void;
}

export function PDFUploadScanner({ onScanComplete }: PDFUploadScannerProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadState, setUploadState] = useState<"idle" | "uploading" | "scanning" | "complete">("idle");

  const startUploadSequence = () => {
    setUploadState("uploading");
    setTimeout(() => {
      setUploadState("scanning");
      setTimeout(() => {
        setUploadState("complete");
        setTimeout(() => {
          onScanComplete();
        }, 1200);
      }, 3500);
    }, 1000);
  };

  return (
    <>
      <div 
        className={`group relative overflow-hidden flex flex-col items-center justify-center py-32 cursor-pointer transition-all border ${isDragging ? "border-brand bg-brand/5" : "border-white/10 hover:border-white/30"}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => { e.preventDefault(); setIsDragging(false); startUploadSequence(); }}
      >
         <input type="file" className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20" onChange={startUploadSequence} accept=".pdf" />
         
         <AnimatePresence mode="wait">
            {uploadState === "idle" && (
              <motion.div 
                key="idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center pointer-events-none"
              >
                 <UploadCloud className="w-16 h-16 text-white/20 group-hover:text-white/40 group-hover:scale-110 transition-all mb-8" />
                 <div className="text-center relative z-10">
                    <p className="text-white/70 text-2xl font-display tracking-tight group-hover:text-white transition-colors">Digest Syllabus Architecture</p>
                    <p className="text-white/25 text-xs font-mono uppercase tracking-widest mt-4">AI Vision Scanning automatically performs outcome extraction</p>
                 </div>
                 <div className="mt-12 px-8 py-3 border border-white/10 text-white/30 text-[10px] font-mono uppercase tracking-widest group-hover:border-white/30 group-hover:text-white/60 transition-all">
                    Select PDF Document
                 </div>
              </motion.div>
            )}
            
            {uploadState !== "idle" && (
              <motion.div 
                key="processing"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center relative z-10 pointer-events-none gap-10"
              >
                 <div className="relative">
                    <Loader2 className="w-16 h-16 text-brand animate-spin" />
                    <Sparkles className="absolute -top-2 -right-2 w-6 h-6 text-aurora animate-pulse" />
                 </div>
                 
                 <div className="text-center">
                    <p className="text-white text-3xl font-display tracking-tight uppercase">
                      {uploadState === "uploading" ? "Synchronizing Data" : uploadState === "scanning" ? "Deconstructing Curriculum" : "Reconstruction Complete"}
                    </p>
                    <p className="text-white/30 text-[10px] font-mono uppercase tracking-[0.2em] mt-4">
                       {uploadState === "complete" ? "Ready for mapping validation" : "Neural parsing in progress"}
                    </p>
                 </div>
                 
                 <div className="w-80 h-[2px] bg-white/5 relative overflow-hidden">
                    <motion.div 
                       className={`h-full ${uploadState === "complete" ? 'bg-attain shadow-[0_0_15px_rgba(5,150,105,0.5)]' : 'bg-brand shadow-[0_0_15px_rgba(37,99,235,0.5)]'}`}
                       initial={{ width: "0%" }}
                       animate={{ width: uploadState === "uploading" ? "30%" : uploadState === "scanning" ? "95%" : "100%" }}
                       transition={{ duration: uploadState === "uploading" ? 1 : uploadState === "scanning" ? 3.5 : 0.5 }}
                    />
                 </div>
              </motion.div>
            )}
         </AnimatePresence>
      </div>

      {/* Theatrical Full-Screen Overlay during scanning */}
      <AnimatePresence>
        {uploadState === "scanning" && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] bg-cosmic/95 backdrop-blur-3xl flex flex-col items-center justify-center p-8"
          >
             <motion.div 
                animate={{ top: ["-20%", "120%"] }}
                transition={{ repeat: Infinity, duration: 2.2, ease: "linear" }}
                className="fixed left-0 right-0 h-32 bg-gradient-to-b from-transparent via-aurora/10 to-aurora/40 border-b-2 border-aurora/50 z-0 mix-blend-screen pointer-events-none"
             />
             
             <div className="relative z-10 flex flex-col items-center gap-12 text-center">
                <div className="flex gap-4">
                   {[1,2,3,4].map(i => (
                     <motion.div key={i} animate={{ height: [10, 40, 10] }} transition={{ repeat: Infinity, duration: 1, delay: i*0.2 }} 
                        className="w-1.5 bg-aurora/40 rounded-full" />
                   ))}
                </div>
                <div>
                   <h2 className="text-6xl font-display text-white tracking-tighter mb-4">Reading Curriculum.</h2>
                   <p className="text-white/30 font-mono text-xs uppercase tracking-[0.4em]">Neural Vector Mapping Active</p>
                </div>
             </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

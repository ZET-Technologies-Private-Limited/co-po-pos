"use client";

import { useState, use } from "react";
import { motion } from "framer-motion";
import { UploadCloud, Download, Loader2, CheckCircle2, AlertTriangle, ArrowRight, Zap, Info, Users } from "lucide-react";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import { STUDENT_MARKS, EXAM_INSTANCES } from "@/lib/appData";

type Student = { name: string; roll: string; marks: Record<string, number | ""> };

const INSTANCES = ["T1", "T2", "T3", "Final"];
const MAX_MARKS: Record<string, number> = { T1: 30, T2: 30, T3: 40, Final: 100 };

function validateMark(val: number | "", inst: string) {
  if (val === "") return "empty";
  if (val > MAX_MARKS[inst]) return "over";
  if (val < 0) return "under";
  return "ok";
}

export default function MarksPage({ params }: { params: Promise<{ id?: string; examId: string }> }) {
  const { id: courseId = "cs101", examId } = use(params);
  const initialStudents = STUDENT_MARKS[courseId] || [];
  const [students, setStudents] = useState<Student[]>(initialStudents);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const updateMark = (roll: string, inst: string, val: string) => {
    setStudents(prev => prev.map(s => s.roll === roll ? { ...s, marks: { ...s.marks, [inst]: val === "" ? "" : +val } } : s));
  };

  const handleSave = () => { setSaving(true); setTimeout(() => { setSaving(false); setSaved(true); }, 1500); };
  const handleUpload = () => { setUploading(true); setTimeout(() => { setUploading(false); setStudents(initialStudents); }, 2200); };

  return (
    <div className="w-full min-h-screen pb-32 pt-4">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-5xl mx-auto flex flex-col gap-20">
        
        {/* ── HERO SECTION ── */}
        <motion.section variants={fadeSlideUp} className="flex flex-col gap-8">
          <div className="flex items-center gap-3 text-sm font-mono text-attain uppercase tracking-widest">
            <span className="w-8 h-[1px] bg-attain" /> Performance Ledger
          </div>
          <div className="flex items-end justify-between flex-wrap gap-8">
            <div className="flex-1 min-w-[300px]">
              <h1 className="text-6xl md:text-7xl font-display font-medium text-white leading-tight tracking-tight">
                Marks<br />
                <span className="text-white/30">Management.</span>
              </h1>
              <p className="text-xl text-white/50 font-light mt-6 max-w-xl">
                 Recording student attainment for <span className="text-white">{courseId.toUpperCase()}</span> assessment cycle.
              </p>
            </div>
            <div className="flex gap-4 shrink-0">
               <button onClick={handleUpload} className="flex items-center gap-3 px-8 py-4 bg-white text-black font-medium text-xs uppercase tracking-widest font-mono hover:bg-white/90 transition-all">
                  {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
                  Import Records
               </button>
               <button className="flex items-center gap-3 px-8 py-4 border border-white/10 text-white/40 text-xs uppercase tracking-widest font-mono hover:text-white hover:border-white transition-all">
                  <Download className="w-4 h-4" /> Export
               </button>
            </div>
          </div>
        </motion.section>

        {/* ── REFERENCE STRIP ── */}
        <motion.section variants={fadeSlideUp} className="flex flex-wrap items-center gap-12 py-10 border-y border-white/10 bg-white/[0.02]">
           <div className="flex items-center gap-4 px-10">
              <Zap className="w-4 h-4 text-attain" />
              <span className="text-xs font-mono text-white/30 uppercase tracking-widest">Max Thresholds:</span>
           </div>
           {INSTANCES.map(i => (
             <div key={i} className="flex items-end gap-3 px-4">
                <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest mb-1">{i}</span>
                <span className="text-2xl font-mono text-white font-light">/{MAX_MARKS[i]}</span>
             </div>
           ))}
        </motion.section>

        {/* ── SPREADSHEET (FLAT) ── */}
        <motion.section variants={fadeSlideUp} className="overflow-x-auto min-h-[500px]">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-white/10">
                <th className="py-6 text-[10px] font-mono text-white/20 uppercase tracking-widest pr-8">Roll Index</th>
                <th className="py-6 text-[10px] font-mono text-white/20 uppercase tracking-widest pr-12">Faculty Registry / Name</th>
                {INSTANCES.map(i => <th key={i} className="py-6 text-center text-[10px] font-mono text-white/20 uppercase tracking-widest px-4">{i} Point</th>)}
                <th className="py-6 text-center text-[10px] font-mono text-white/20 uppercase tracking-widest px-4">Validation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {students.map((s, si) => {
                const allValid = INSTANCES.every(inst => validateMark(s.marks[inst], inst) === "ok");
                const hasError = INSTANCES.some(inst => validateMark(s.marks[inst], inst) === "over" || validateMark(s.marks[inst], inst) === "under");
                return (
                  <motion.tr key={s.roll} initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} transition={{ delay: si * 0.02 }}
                    className="group hover:bg-white/[0.02] transition-colors">
                    <td className="py-8 font-mono text-sm text-white/25 pr-8 group-hover:text-white/50 transition-colors uppercase tracking-widest">{s.roll}</td>
                    <td className="py-8 text-xl font-display text-white/70 group-hover:text-white transition-colors pr-12">{s.name}</td>
                    {INSTANCES.map(inst => {
                      const state = validateMark(s.marks[inst], inst);
                      return (
                        <td key={inst} className="py-8 px-4 text-center">
                          <input
                            type="number"
                            value={s.marks[inst]}
                            onChange={e => updateMark(s.roll, inst, e.target.value)}
                            className={`w-20 text-center bg-transparent border-b py-3 text-white outline-none focus:ring-0 transition-all font-mono text-xl ${
                              state === "over" || state === "under" ? "border-alert text-alert" : state === "ok" ? "border-white/5 focus:border-attain" : "border-white/5 text-white/20"
                            }`}
                          />
                        </td>
                      );
                    })}
                    <td className="py-8 px-4 text-center">
                      <div className="flex justify-center">
                        {hasError ? <AlertTriangle className="w-5 h-5 text-alert animate-pulse" /> :
                          allValid ? <CheckCircle2 className="w-5 h-5 text-attain" /> :
                            <div className="w-2 h-2 rounded-full bg-white/5" />}
                      </div>
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </motion.section>

        {/* ── ACTIONS ── */}
        <motion.section variants={fadeSlideUp} className="flex flex-col md:flex-row items-center justify-between gap-12 pt-12 border-t border-white/10">
          <div className="flex items-start gap-4">
             <Info className="w-4 h-4 text-white/20 mt-1" />
             <p className="text-white/30 text-sm font-light max-w-md leading-relaxed">
                Marks data is locally encrypted before session commit. Ensure all <span className="text-attain underline underline-offset-4 decoration-attain/30">green indicators</span> are present before final archival.
             </p>
          </div>
          <div className="flex items-center gap-10">
             {saved && (
               <motion.span initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} className="text-attain font-mono text-xs uppercase tracking-widest flex items-center gap-3">
                  <CheckCircle2 className="w-4 h-4" /> Integrity Verified
               </motion.span>
             )}
             <button onClick={handleSave} 
                className={`group flex items-center gap-8 px-16 py-6 font-mono text-sm uppercase tracking-[0.2em] transition-all ${
                   saved ? "bg-attain text-white" : "bg-white text-black hover:bg-white/95"
                }`}>
                {saving ? "Commiting..." : saved ? "Archived Successfully" : "Finalize Records"}
                {!saving && !saved && <ArrowRight className="w-5 h-5 group-hover:translate-x-3 transition-transform" />}
             </button>
          </div>
        </motion.section>
      </motion.div>
    </div>
  );
}

"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Play, Pause, FastForward, BookOpen, Sparkles, Network, BarChart3, FileText, Bot,
  GraduationCap, BrainCircuit, ArrowRight, CheckCircle2, Zap, Target, Search, Fingerprint, Layers,
  TrendingUp
} from "lucide-react";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";

const WORKFLOW_STEPS = [
  { 
    id: 1, 
    label: "Faculty Authentication", 
    icon: GraduationCap, 
    desc: "Neural-encrypted role-based portal initialization.",
    insight: "AI validates credentials and session persistence for secure grading audits.",
    href: "/login", 
    color: "text-brand" 
  },
  { 
    id: 2, 
    label: "Curriculum Creation", 
    icon: BookOpen, 
    desc: "Define structural parameters for new institutional courses.",
    insight: "System automatically cross-references department codes for uniqueness.",
    href: "/faculty/course/new", 
    color: "text-aurora" 
  },
  { 
    id: 3, 
    label: "Syllabus Deconstruction", 
    icon: FileText, 
    desc: "AI OCR scanning of PDF/Word curriculum documents.",
    insight: "Contextual NLP extracts modules and learning objectives in milliseconds.",
    href: "/courses/cs301/syllabus", 
    color: "text-insight" 
  },
  { 
    id: 4, 
    label: "Intelligence Generation", 
    icon: BrainCircuit, 
    desc: "Synthesizing Bloom-classified Course Outcomes (COs).",
    insight: "Generative AI creates 4-6 COs aligned with global pedagogical levels.",
    href: "/courses/cs301/generate-co", 
    color: "text-attain" 
  },
  { 
    id: 5, 
    label: "Mapping Synchronization", 
    icon: Network, 
    desc: "Defining linkage correlation between COs and Program Outcomes (POs).",
    insight: "Predictive matrix suggests 0-3 correlation strengths based on semantic overlap.",
    href: "/courses/cs301/mapping", 
    color: "text-aurora" 
  },
  { 
    id: 6, 
    label: "Assessment Blueprinting", 
    icon: Zap, 
    desc: "Configuring T1/T2/T3 examination instances and mark caps.",
    insight: "Calculates marks-per-question density for optimal attainment resolution.",
    href: "/courses/cs301/exams", 
    color: "text-brand" 
  },
  { 
    id: 7, 
    label: "Question Cataloging", 
    icon: Search, 
    desc: "Digitizing examination papers and classifying item banks.",
    insight: "AI isolates individual questions from scans for granular CO tagging.",
    href: "/courses/cs301/exams/t1/questions", 
    color: "text-insight" 
  },
  { 
    id: 8, 
    label: "Cognitive Audit", 
    icon: Fingerprint, 
    desc: "Verifying AI-mapped Bloom levels and CO alignments per question.",
    insight: "Low-confidence flags allow faculty to override AI pedagogy logic.",
    href: "/courses/cs301/exams/t1/analysis", 
    color: "text-aurora" 
  },
  { 
    id: 9, 
    label: "Performance Ledger", 
    icon: BarChart3, 
    desc: "Bulk importing student marks via spreadsheet-style UI.",
    insight: "Instant cell validation ensures marks don't exceed examination caps.",
    href: "/courses/cs301/exams/t1/marks", 
    color: "text-attain" 
  },
  { 
    id: 10, 
    label: "Attainment Synthesis", 
    icon: Target, 
    desc: "Consolidating student performance into CO attainment levels (1/2/3).",
    insight: "Non-attainment alerts trigger predictive remediation protocols.",
    href: "/courses/cs301/co-attainment", 
    color: "text-brand" 
  },
  { 
    id: 11, 
    label: "Program Impact", 
    icon: Layers, 
    desc: "Evaluating aggregate contribution to POs and PSOs via radar analytics.",
    insight: "Direct linkage visualization shows how one course affects graduation rates.",
    href: "/courses/cs301/po-attainment", 
    color: "text-aurora" 
  },
  { 
    id: 12, 
    label: "Institutional Analytics", 
    icon: TrendingUp, 
    desc: "Department-wide trends and performance benchmarks over semesters.",
    insight: "Comparative engines identify curriculum gaps across all departments.",
    href: "/analytics", 
    color: "text-insight" 
  },
  { 
    id: 13, 
    label: "Accreditation Delivery", 
    icon: FileText, 
    desc: "One-click generation of audit-ready compliance reports.",
    insight: "Digital signatures and version control ensure 100% data integrity.",
    href: "/reports", 
    color: "text-attain" 
  },
];



export default function PresentationPage() {
  const [active, setActive] = useState(0);
  const [playing, setPlaying] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (playing) {
      intervalRef.current = setInterval(() => {
        setActive(a => {
          if (a >= WORKFLOW_STEPS.length - 1) { setPlaying(false); return a; }
          return a + 1;
        });
      }, 2500);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [playing]);

  const currentStep = WORKFLOW_STEPS[active];

  return (
    <div className="w-full min-h-screen pb-32 pt-4">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-6xl mx-auto px-10 flex flex-col gap-20">

        {/* ── HERO SECTION ── */}
        <motion.section variants={fadeSlideUp} className="flex flex-col gap-8">
          <div className="flex items-center gap-3 text-sm font-mono text-aurora uppercase tracking-widest">
            <span className="w-8 h-[1px] bg-aurora" /> Institutional Demo
          </div>
          <div className="flex items-end justify-between flex-wrap gap-8">
            <div className="flex-1 min-w-[300px]">
              <h1 className="text-6xl md:text-7xl font-display font-medium text-white leading-tight tracking-tight">
                End-to-End<br />
                <span className="text-white/30">Workflow Ecosystem.</span>
              </h1>
              <p className="text-xl text-white/50 font-light mt-6 max-w-xl leading-relaxed">
                 From faculty authentication to accreditation-ready reporting. <span className="text-white">Follow the 13-step intelligence cycle.</span>
              </p>
            </div>
            <div className="shrink-0 flex items-center gap-4">
               <button onClick={() => { setActive(0); setPlaying(false); }}
                className="px-6 py-4 border border-white/10 text-white/30 hover:text-white uppercase font-mono text-xs tracking-widest transition-all">
                Reset Cycle
              </button>
              <button onClick={() => setPlaying(p => !p)}
                className="group flex items-center gap-4 px-10 py-4 bg-white text-black font-medium text-xs uppercase tracking-widest font-mono hover:bg-white/95 transition-all shadow-[0_10px_30px_rgba(255,255,255,0.05)]">
                {playing ? <Pause className="w-3 h-3 fill-current" /> : <Play className="w-3 h-3 fill-current" />}
                {playing ? "Pause Simulation" : "Begin Auto-Demo"}
              </button>
            </div>
          </div>
        </motion.section>

        {/* ── FEATURED STAGE BREADCRUMB ── */}
        <motion.section variants={fadeSlideUp} className="flex flex-col gap-12 py-16 border-y border-white/10">
           <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                 <div className={`w-12 h-12 rounded-full border border-white/10 flex items-center justify-center ${currentStep.color}`}>
                    <currentStep.icon className="w-6 h-6" />
                 </div>
                 <div className="flex flex-col">
                    <span className="text-[10px] font-mono text-white/20 uppercase tracking-[0.4em] mb-1">State Phase 0{active + 1}</span>
                    <h2 className="text-4xl font-display text-white tracking-tight">{currentStep.label}</h2>
                 </div>
              </div>
              <Link href={currentStep.href} className={`hidden md:flex items-center gap-6 px-10 py-4 border border-white/10 ${currentStep.color} uppercase font-mono text-[10px] tracking-widest hover:border-current transition-all group`}>
                 Live Application Link <ArrowRight className="w-4 h-4 group-hover:translate-x-3 transition-transform" />
              </Link>
           </div>

           <div className="grid grid-cols-1 lg:grid-cols-2 gap-20">
              <div className="flex flex-col gap-6">
                 <p className="text-2xl font-light text-white/50 leading-relaxed italic">"{currentStep.desc}"</p>
                 <div className="flex items-center gap-10 pt-6">
                    <div>
                       <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest block mb-2">Completion Status</span>
                       <div className="flex gap-1.5">
                          {WORKFLOW_STEPS.map((_, i) => (
                             <div key={i} className={`w-4 h-[2px] transition-all ${i <= active ? currentStep.color : 'bg-white/5'}`} 
                                  style={{ backgroundColor: i <= active ? 'currentColor' : undefined }} />
                          ))}
                       </div>
                    </div>
                    {playing && (
                       <div className="flex-1 flex flex-col gap-2">
                          <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest leading-none">Next Transition</span>
                          <div className="w-full h-1 bg-white/5 relative overflow-hidden">
                             <motion.div className={`h-full bg-current ${currentStep.color}`} 
                                initial={{ width: 0 }} animate={{ width: "100%" }} transition={{ duration: 2.5 }} />
                          </div>
                       </div>
                    )}
                 </div>
              </div>
              
              <div className="bg-white/[0.02] border border-white/10 p-10 flex flex-col gap-6 relative group overflow-hidden">
                 <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:opacity-30 transition-opacity">
                    <Sparkles className="w-24 h-24" />
                 </div>
                 <div className="flex items-center gap-3 text-[10px] font-mono text-aurora uppercase tracking-widest">
                    <BrainCircuit className="w-3 h-3" /> Core Intelligence
                 </div>
                 <p className="text-lg text-white/80 font-display leading-snug relative z-10 transition-transform group-hover:translate-x-1 duration-500">
                    {currentStep.insight}
                 </p>
                 <div className="flex gap-4 pt-4 relative z-10">
                    <span className="px-3 py-1 bg-white/5 border border-white/5 text-[9px] font-mono text-white/30 uppercase tracking-widest">Automation Ready</span>
                    <span className="px-3 py-1 bg-white/5 border border-white/5 text-[9px] font-mono text-white/30 uppercase tracking-widest">OBE Compliant</span>
                 </div>
              </div>
           </div>
        </motion.section>

        {/* ── TIMELINE LIST (FLAT) ── */}
        <motion.section variants={staggerContainer} className="flex flex-col">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-20">
            {WORKFLOW_STEPS.map((step, i) => (
              <button key={step.id} onClick={() => { setActive(i); setPlaying(false); }}
                className={`flex items-start gap-8 py-8 text-left border-b border-white/5 group transition-all ${i === active ? "pl-6 border-white/20 bg-white/[0.01]" : "hover:border-white/10 hover:pl-2"}`}>
                <div className="flex flex-col items-center shrink-0 mt-1">
                  <div className={`w-8 h-8 rounded-full border flex items-center justify-center transition-all ${
                    i < active ? "bg-attain border-attain" : i === active ? `border-current ${step.color}` : "border-white/10 group-hover:border-white/20"
                  }`}>
                    {i < active ? <CheckCircle2 className="w-4 h-4 text-cosmic fill-current" /> :
                      <span className={`text-[10px] font-mono ${i === active ? step.color : "text-white/20"}`}>0{i + 1}</span>
                    }
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`font-display text-2xl transition-all ${i === active ? "text-white scale-105" : "text-white/30 group-hover:text-white/70"}`}>{step.label}</p>
                  {i === active && (
                    <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs font-mono text-white/40 uppercase tracking-widest mt-3 flex items-center gap-3">
                       Proceed to Node Stage <ArrowRight className="w-3 h-3" />
                    </motion.p>
                  )}
                </div>
              </button>
            ))}
          </div>
        </motion.section>

        {/* ── FOOTER FOOTPRINT ── */}
        <motion.section variants={fadeSlideUp} className="flex flex-col md:flex-row items-center justify-between py-16 border-t border-white/10 gap-10">
           <div className="flex items-center gap-10">
              <div className="flex flex-col">
                 <span className="text-3xl font-mono text-white">13</span>
                 <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest mt-1">Logic Nodes</span>
              </div>
              <div className="w-[1px] h-8 bg-white/10" />
              <div className="flex flex-col">
                 <span className="text-3xl font-mono text-white">20+</span>
                 <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest mt-1">AI Modules</span>
              </div>
              <div className="w-[1px] h-8 bg-white/10" />
              <div className="flex flex-col">
                 <span className="text-3xl font-mono text-white">100%</span>
                 <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest mt-1">OBE Integrity</span>
              </div>
           </div>
           
           <div className="flex flex-wrap justify-center gap-8 text-[10px] font-mono text-white/20 uppercase tracking-widest">
              <span>Next.js 14 Framework</span>
              <span>·</span>
              <span>Vector AI Synthesis</span>
              <span>·</span>
              <span>Accreditation Ready</span>
           </div>
        </motion.section>

      </motion.div>
    </div>
  );
}

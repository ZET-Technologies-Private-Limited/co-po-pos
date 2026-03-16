"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { LandingNavbar } from "@/components/landing/LandingNavbar";
import ProfessionalAbstract3D from "@/components/landing/ProfessionalAbstract3D";

const STATS = [
  { value: "20+", label: "Modules" },
  { value: "98%", label: "Mapping Accuracy" },
  { value: "10×", label: "Faster Audits" },
  { value: "NBA", label: "Ready" },
  { value: "ABET", label: "Compliant" },
  { value: "SOC2", label: "Certified" },
];

const FEATURES = [
  {
    num: "01",
    title: "Intelligent Extraction",
    body: "Upload PDF syllabi and let the engine instantly extract, classify, and format outcomes into a structured Bloom's taxonomy.",
    accent: "text-aurora",
  },
  {
    num: "02",
    title: "Multi-Dimensional Mapping",
    body: "Visualize CO-PO-PSO correlations through interactive matrices and D3.js force-directed graphs for complete program coverage.",
    accent: "text-brand",
  },
  {
    num: "03",
    title: "Predictive Attainment",
    body: "Cross-reference historical cohorts against real-time performance to surface at-risk outcomes before final examinations.",
    accent: "text-insight",
  },
  {
    num: "04",
    title: "Accreditation Reports",
    body: "Generate NBA, ABET, and NAAC-ready reports in one click — formatted, signed, and audit-trail stamped.",
    accent: "text-attain",
  },
];

function Divider() {
  return <div className="w-full h-[1px] bg-white/8 my-2" />;
}

export default function LandingPage() {
  return (
    <div className="relative bg-cosmic selection:bg-brand/30 selection:text-white overflow-x-hidden">

      {/* 3D Canvas — right side, behind text */}
      <div className="fixed inset-y-0 right-0 w-full md:w-3/5 z-0 pointer-events-none">
        <Canvas camera={{ position: [0, 0, 9], fov: 50 }}>
          <Suspense fallback={null}>
            <ProfessionalAbstract3D />
          </Suspense>
        </Canvas>
        <div className="absolute inset-0 bg-gradient-to-r from-cosmic via-cosmic/60 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-b from-cosmic/80 via-transparent to-cosmic/80" />
      </div>

      <div className="relative z-10">
        <LandingNavbar />

        <main className="w-full max-w-7xl mx-auto px-6 pb-32">

          {/* ── HERO ── */}
          <section className="min-h-screen flex flex-col justify-center">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, ease: "easeOut" }}
              className="max-w-4xl"
            >
              <p className="mb-6 flex items-center gap-3 text-xs font-mono text-brand uppercase tracking-[0.25em]">
                <span className="w-8 h-[1px] bg-brand inline-block" />
                Academic Intelligence Platform
              </p>

              <h1 className="text-[clamp(3rem,8vw,6.5rem)] font-display font-medium text-white leading-[1.02] tracking-tight mb-8">
                Precision mapping<br />
                for curriculum<br />
                <em className="not-italic text-white/35">outcomes.</em>
              </h1>

              <p className="text-xl md:text-2xl text-white/45 max-w-xl font-light leading-relaxed mb-14">
                Automate CO-PO-PSO alignment with neural extraction — built for universities that refuse to compromise on accreditation.
              </p>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
                <Link
                  href="/login"
                  className="group inline-flex items-center gap-3 px-8 py-4 bg-white text-black text-sm font-medium tracking-wide hover:bg-white/90 transition-colors"
                >
                  Access Dashboard
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </Link>
                <Link
                  href="/login"
                  className="text-sm text-white/40 hover:text-white/70 transition-colors font-mono uppercase tracking-widest flex items-center gap-2"
                >
                  View Demo <ArrowUpRight className="w-3 h-3" />
                </Link>
              </div>
            </motion.div>
          </section>

          {/* ── STATS TICKER ── */}
          <motion.div
            id="platform"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <Divider />
            <div className="py-8 flex items-center gap-12 overflow-x-auto scrollbar-none">
              {STATS.map((s, i) => (
                <div key={i} className="flex-shrink-0 flex items-baseline gap-2">
                  <span className="text-3xl font-display font-medium text-white">{s.value}</span>
                  <span className="text-xs font-mono text-white/35 uppercase tracking-widest">{s.label}</span>
                </div>
              ))}
            </div>
            <Divider />
          </motion.div>

          {/* ── PROBLEM ── */}
          <section className="min-h-[80vh] flex flex-col justify-center items-end text-right py-24">
            <motion.div
              initial={{ opacity: 0, x: 40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ amount: 0.4 }}
              transition={{ duration: 1 }}
              className="max-w-2xl"
            >
              <p className="mb-6 flex items-center justify-end gap-3 text-xs font-mono text-alert uppercase tracking-[0.25em]">
                The Compliance Burden
                <span className="w-8 h-[1px] bg-alert inline-block" />
              </p>
              <h2 className="text-[clamp(2.5rem,6vw,5rem)] font-display text-white leading-[1.05] mb-8">
                Manual mapping is<br />
                <span className="text-white/30">costly & error-prone.</span>
              </h2>
              <p className="text-lg text-white/45 font-light leading-relaxed">
                Faculty spend hundreds of hours manually categorising Bloom's Taxonomy levels and mapping course outcomes to program objectives — producing inconsistent results that stall accreditation.
              </p>
              <div className="mt-10 flex items-center justify-end gap-8 text-sm font-mono text-white/25 uppercase tracking-widest">
                <span>300+ hrs / cycle</span>
                <span className="w-1 h-1 rounded-full bg-white/20 inline-block" />
                <span>40% rework rate</span>
              </div>
            </motion.div>
          </section>

          {/* ── SOLUTION — timeline list ── */}
          <section id="solutions" className="min-h-screen flex flex-col justify-center py-24">
            <motion.div
              initial={{ opacity: 0, x: -40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ amount: 0.3 }}
              transition={{ duration: 1 }}
              className="max-w-3xl"
            >
              <p className="mb-6 flex items-center gap-3 text-xs font-mono text-aurora uppercase tracking-[0.25em]">
                <span className="w-8 h-[1px] bg-aurora inline-block" />
                The Nexus Protocol
              </p>
              <h2 className="text-[clamp(2.5rem,6vw,5rem)] font-display text-white leading-[1.05] mb-16">
                Neural networks do<br />
                <span className="text-white/30">the heavy lifting.</span>
              </h2>

              <div className="relative pl-6 border-l border-white/10 flex flex-col gap-0">
                {FEATURES.map((f, i) => (
                  <motion.div
                    key={f.num}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, amount: 0.5 }}
                    transition={{ duration: 0.7, delay: i * 0.12 }}
                    className="group py-8 border-b border-white/8 last:border-0"
                  >
                    <div className="flex items-start gap-6">
                      <span className={`text-xs font-mono ${f.accent} opacity-60 mt-1 w-6 flex-shrink-0`}>{f.num}</span>
                      <div>
                        <h3 className={`text-xl font-display text-white mb-2 group-hover:${f.accent} transition-colors duration-500`}>
                          {f.title}
                        </h3>
                        <p className="text-white/45 font-light leading-relaxed">{f.body}</p>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </section>

          {/* ── CTA ── */}
          <section id="accreditation" className="min-h-[70vh] flex flex-col justify-center items-center text-center py-24">
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ amount: 0.4 }}
              transition={{ duration: 1 }}
              className="max-w-2xl flex flex-col items-center"
            >
              <p className="mb-6 flex items-center justify-center gap-3 text-xs font-mono text-white/30 uppercase tracking-[0.25em]">
                <span className="w-8 h-[1px] bg-white/20 inline-block" />
                20 Modules · 1 Platform
                <span className="w-8 h-[1px] bg-white/20 inline-block" />
              </p>
              <h2 className="text-[clamp(2.5rem,6vw,5rem)] font-display text-white leading-[1.05] mb-8">
                Engineered for<br />accreditation excellence.
              </h2>
              <p className="text-lg text-white/40 font-light mb-12 leading-relaxed max-w-lg">
                Join institutions transforming their academic intelligence infrastructure. Prepare for your next NBA or ABET audit with a complete end-to-end SaaS ecosystem.
              </p>
              <Link
                href="/login"
                className="group inline-flex items-center gap-3 px-10 py-5 bg-white text-black text-sm font-medium tracking-wide hover:bg-white/90 transition-colors shadow-[0_0_40px_rgba(255,255,255,0.15)] hover:shadow-[0_0_60px_rgba(255,255,255,0.25)]"
              >
                Enter the Platform
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
            </motion.div>
          </section>

        </main>

        {/* ── FOOTER STRIP ── */}
        <footer className="relative z-10 border-t border-white/8 px-6 py-8 max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-white/25 uppercase tracking-widest">
          <span>© {new Date().getFullYear()} Nexus Engine</span>
          <div className="flex items-center gap-8">
            <Link href="/login" className="hover:text-white/60 transition-colors">Sign In</Link>
            <span>NBA · ABET · NAAC</span>
          </div>
        </footer>
      </div>
    </div>
  );
}

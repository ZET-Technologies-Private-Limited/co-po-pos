"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line, CartesianGrid, Legend } from "recharts";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import { useAuthStore } from "@/lib/authStore";

const DEPT_DATA = [
  { dept: "CS", attainment: 82 }, { dept: "EC", attainment: 67 },
  { dept: "ME", attainment: 74 }, { dept: "CE", attainment: 78 }, { dept: "IT", attainment: 85 },
];

const TREND_DATA = [
  { sem: "Sem 1", co: 65, po: 60 }, { sem: "Sem 2", co: 70, po: 64 },
  { sem: "Sem 3", co: 67, po: 62 }, { sem: "Sem 4", co: 74, po: 68 },
  { sem: "Sem 5", co: 79, po: 73 }, { sem: "Sem 6", co: 82, po: 76 },
];

const EXAM_PERF = [
  { exam: "T1", average: 67, highest: 28, lowest: 12 },
  { exam: "T2", average: 72, highest: 30, lowest: 16 },
  { exam: "T3", average: 70, highest: 38, lowest: 18 },
  { exam: "Final", average: 75, highest: 95, lowest: 42 },
];

const FILTERS = ["All Departments", "Computer Science", "Electronics", "Mechanical", "Civil", "IT"];

export default function AnalyticsPage() {
  const { activeRole } = useAuthStore();
  const [dept, setDept] = useState(activeRole === "department_head" ? "Computer Science" : "All Departments");
  const [period, setPeriod] = useState("2025-26");

  // Explicit Role Matrix: Faculty and Course Lead CANNOT access PO/PSO institutional analytics
  if (activeRole === "faculty" || activeRole === "subject_lead") {
    return (
      <div className="w-full min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-display text-alert mb-2">Access Restricted</h2>
          <p className="text-white/40 font-mono text-sm uppercase tracking-widest">
            Your role ({activeRole.replace('_', ' ')}) does not have clearance for institutional PO/PSO reporting.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full min-h-screen pb-24">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-5xl mx-auto px-6 pt-12">

        <motion.div variants={fadeSlideUp} className="flex items-end justify-between mb-12">
          <div>
            <div className="flex items-center gap-3 text-sm font-mono text-brand uppercase tracking-widest mb-4">
              <span className="w-8 h-[1px] bg-brand"></span>
              Analytics
            </div>
            <h1 className="text-5xl font-display text-white">Insights Dashboard</h1>
            {activeRole === "department_head" && (
              <p className="text-white/40 font-mono text-xs uppercase tracking-widest mt-4">
                LOCKED TO: COMPUTER SCIENCE DEPARTMENT
              </p>
            )}
          </div>
          <div className="flex gap-4 text-sm font-mono">
            <select value={period} onChange={e => setPeriod(e.target.value)} className="bg-cosmic border-b border-white/20 text-white/60 outline-none py-2 cursor-pointer hover:text-white transition-colors">
              {["2025-26", "2024-25", "2023-24"].map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
        </motion.div>

        {/* Department Filter - ONLY for Admins */}
        {activeRole === "admin" && (
          <motion.div variants={fadeSlideUp} className="flex gap-6 flex-wrap pb-8 border-b border-white/10 mb-12 text-sm font-mono">
            {FILTERS.map(f => (
              <button key={f} onClick={() => setDept(f)}
                className={`uppercase tracking-widest transition-colors ${dept === f ? "text-white border-b border-white pb-1" : "text-white/40 hover:text-white/70"}`}>
                {f}
              </button>
            ))}
          </motion.div>
        )}

        {/* Section 1: Outcome Attainment Trends */}
        <motion.div variants={fadeSlideUp} className="mb-24">
          <h2 className="text-2xl font-display text-white mb-2">Attainment Trends</h2>
          <p className="text-white/40 font-light mb-8">CO and PO attainment across semesters showing progressive improvement.</p>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={TREND_DATA}>
              <CartesianGrid stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="sem" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} axisLine={false} tickLine={false} domain={[50, 100]} />
              <Tooltip contentStyle={{ background: '#0F172A', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }} />
              <Legend wrapperStyle={{ color: "rgba(255,255,255,0.5)", fontSize: "12px" }} />
              <Line type="monotone" dataKey="co" name="CO Attainment" stroke="#06B6D4" strokeWidth={2} dot={{ fill: "#06B6D4", r: 4 }} />
              <Line type="monotone" dataKey="po" name="PO Attainment" stroke="#7C3AED" strokeWidth={2} dot={{ fill: "#7C3AED", r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Section 2: Department Comparison (Only relevant for Admins) */}
        {activeRole === "admin" && (
          <motion.div variants={fadeSlideUp} className="mb-24">
            <h2 className="text-2xl font-display text-white mb-2">Department Comparison</h2>
            <p className="text-white/40 font-light mb-8">Average CO attainment across all departments for the selected period.</p>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={DEPT_DATA} barCategoryGap="40%">
                <XAxis dataKey="dept" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} axisLine={false} tickLine={false} domain={[0, 100]} />
                <Tooltip contentStyle={{ background: '#0F172A', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }} />
                <Bar dataKey="attainment" name="Attainment" radius={[2, 2, 0, 0]}>
                  {DEPT_DATA.map((entry, index) => (
                    <Cell key={index} fill={entry.attainment >= 80 ? "#059669" : entry.attainment >= 70 ? "#06B6D4" : "#E11D48"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        )}

        {/* Section 3: Exam Performance in plain text list */}
        <motion.div variants={fadeSlideUp}>
          <h2 className="text-2xl font-display text-white mb-2">Exam Performance Summary</h2>
          <p className="text-white/40 font-light mb-8">Average, highest and lowest scores across all configured exam instances.</p>
          <div className="flex flex-col divide-y divide-white/10">
            {EXAM_PERF.map((e, i) => (
              <div key={e.exam} className="flex items-center gap-12 py-6">
                <span className="font-mono text-white/40 text-sm w-14">{e.exam}</span>
                <div className="flex-1 h-1 bg-white/10">
                  <motion.div className="h-full bg-aurora" style={{ width: `${e.average}%` }}
                    initial={{ width: 0 }} whileInView={{ width: `${e.average}%` }} viewport={{ once: true }} transition={{ duration: 1, delay: i * 0.1 }} />
                </div>
                <div className="flex gap-8 text-sm font-mono">
                  <span className="text-white">{e.average}<span className="text-white/30">%</span></span>
                  <span className="text-attain hidden sm:block">▲{e.highest}</span>
                  <span className="text-alert hidden sm:block">▼{e.lowest}</span>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}

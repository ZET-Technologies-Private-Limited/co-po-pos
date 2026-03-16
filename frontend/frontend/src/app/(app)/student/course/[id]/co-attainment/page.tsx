"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import { motion } from "framer-motion";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import apiClient from "@/lib/apiClient";

export default function StudentCourseCOAttainmentPage() {
  const { id } = useParams();
  const courseId = id as string;

  const [course, setCourse] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [weighted, setWeighted] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [c, s, w] = await Promise.all([
          apiClient.getCourse(courseId),
          apiClient.getCourseAttainment(courseId),
          apiClient.getWeightedCOAttainment(courseId),
        ]);
        if (cancelled) return;
        setCourse(c);
        setSummary(s);
        setWeighted(w);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load CO attainment.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [courseId]);

  const coRows: any[] = useMemo(() => {
    if (Array.isArray(summary?.attainments)) return summary.attainments;
    if (Array.isArray(summary?.co_attainments)) return summary.co_attainments;
    if (Array.isArray(summary)) return summary;
    return [];
  }, [summary]);

  const weightedRows: any[] = useMemo(() => {
    if (Array.isArray(weighted?.attainments)) return weighted.attainments;
    if (Array.isArray(weighted)) return weighted;
    return [];
  }, [weighted]);

  return (
    <AccessGate feature="dashboard" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-5xl mx-auto pb-24 space-y-6">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-4">
          <h1 className="text-3xl font-display text-white">CO Attainment</h1>
          <p className="text-white/50 mt-1 text-sm">{course?.course_name || "Course"}</p>
        </motion.header>

        {loading && <p className="text-white/60">Loading...</p>}
        {error && <p className="text-alert text-sm">{error}</p>}

        {!loading && !error && (
          <>
            <motion.section variants={fadeSlideUp} className="border border-white/10">
              <div className="px-4 py-3 border-b border-white/10">
                <h2 className="text-sm font-mono text-white uppercase tracking-widest">Course Outcome Attainment</h2>
              </div>
              {coRows.length === 0 ? (
                <p className="px-4 py-8 text-white/40 text-sm">No attainment data available yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="px-4 py-2 text-left text-[10px] font-mono text-white/40 uppercase">CO</th>
                        <th className="px-4 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Statement</th>
                        <th className="px-4 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Attainment %</th>
                        <th className="px-4 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Level</th>
                      </tr>
                    </thead>
                    <tbody>
                      {coRows.map((row: any, i: number) => {
                        const pct = Number(row.attainment_percentage ?? row.percentage ?? row.attainment ?? 0);
                        const level = row.attainment_level ?? row.level ?? (pct >= 60 ? "L3" : pct >= 40 ? "L2" : "L1");
                        const color = level === "L3" ? "text-attain" : level === "L2" ? "text-brand" : "text-alert";
                        return (
                          <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                            <td className="px-4 py-3 text-xs text-white font-mono">{row.co_code ?? row.code ?? `CO${i + 1}`}</td>
                            <td className="px-4 py-3 text-xs text-white/60 max-w-xs">{row.statement ?? row.co_statement ?? "—"}</td>
                            <td className="px-4 py-3 text-xs text-white">{pct}%</td>
                            <td className={`px-4 py-3 text-xs font-mono font-bold ${color}`}>{level}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </motion.section>

            {weightedRows.length > 0 && (
              <motion.section variants={fadeSlideUp} className="border border-white/10">
                <div className="px-4 py-3 border-b border-white/10">
                  <h2 className="text-sm font-mono text-white uppercase tracking-widest">Weighted CO Attainment</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="px-4 py-2 text-left text-[10px] font-mono text-white/40 uppercase">CO</th>
                        <th className="px-4 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Weighted %</th>
                        <th className="px-4 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Level</th>
                      </tr>
                    </thead>
                    <tbody>
                      {weightedRows.map((row: any, i: number) => {
                        const pct = Number(row.weighted_percentage ?? row.attainment_percentage ?? row.percentage ?? 0);
                        const level = row.attainment_level ?? row.level ?? (pct >= 60 ? "L3" : pct >= 40 ? "L2" : "L1");
                        const color = level === "L3" ? "text-attain" : level === "L2" ? "text-brand" : "text-alert";
                        return (
                          <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                            <td className="px-4 py-3 text-xs text-white font-mono">{row.co_code ?? row.code ?? `CO${i + 1}`}</td>
                            <td className="px-4 py-3 text-xs text-white">{pct}%</td>
                            <td className={`px-4 py-3 text-xs font-mono font-bold ${color}`}>{level}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </motion.section>
            )}
          </>
        )}
      </motion.div>
    </AccessGate>
  );
}

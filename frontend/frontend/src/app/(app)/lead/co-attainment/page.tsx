"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import { motion } from "framer-motion";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import apiClient from "@/lib/apiClient";

export default function LeadCOAttainmentPage() {
  const { user, activeAY } = useAuthStore();
  const dept = user?.department || "CSE";
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await apiClient.getLeadCOAttainment({ department: dept, academic_year: activeAY });
        if (cancelled) return;
        setData(res);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load CO attainment.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [dept, activeAY]);

  const items: any[] = useMemo(() => {
    if (Array.isArray(data?.items)) return data.items;
    if (Array.isArray(data)) return data;
    return [];
  }, [data]);

  return (
    <AccessGate feature="co_attainment" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-6xl mx-auto pb-24 space-y-6">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-4">
          <h1 className="text-3xl font-display text-white">Lead CO Attainment</h1>
          <p className="text-white/50 mt-1 text-sm">AY {activeAY}</p>
        </motion.header>

        {loading && <p className="text-white/60">Loading...</p>}
        {error && <p className="text-alert text-sm">{error}</p>}

        {!loading && !error && (
          <motion.section variants={fadeSlideUp} className="border border-white/10">
            {items.length === 0 ? (
              <p className="px-4 py-8 text-white/40 text-sm">No CO attainment data for AY {activeAY}.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="px-4 py-3 text-left text-[10px] font-mono text-white/40 uppercase">Course</th>
                      <th className="px-4 py-3 text-left text-[10px] font-mono text-white/40 uppercase">CO</th>
                      <th className="px-4 py-3 text-left text-[10px] font-mono text-white/40 uppercase">CIE %</th>
                      <th className="px-4 py-3 text-left text-[10px] font-mono text-white/40 uppercase">SEE %</th>
                      <th className="px-4 py-3 text-left text-[10px] font-mono text-white/40 uppercase">Final %</th>
                      <th className="px-4 py-3 text-left text-[10px] font-mono text-white/40 uppercase">Level</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item: any, i: number) => {
                      const pct = Number(item.attainment_percentage ?? item.percentage ?? 0);
                      const level = pct >= 60 ? "L3" : pct >= 40 ? "L2" : "L1";
                      const color = pct >= 60 ? "text-attain" : pct >= 40 ? "text-brand" : "text-alert";
                      return (
                        <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                          <td className="px-4 py-3 text-xs text-white/70">{item.course_code ?? "—"}</td>
                          <td className="px-4 py-3 text-xs text-white font-mono">{item.co_id ?? item.co ?? "—"}</td>
                          <td className="px-4 py-3 text-xs text-white/70">{item.cie_percentage ?? "—"}</td>
                          <td className="px-4 py-3 text-xs text-white/70">{item.see_percentage ?? "—"}</td>
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
        )}
      </motion.div>
    </AccessGate>
  );
}

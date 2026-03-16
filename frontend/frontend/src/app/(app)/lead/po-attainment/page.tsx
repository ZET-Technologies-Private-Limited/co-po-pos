"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import { motion } from "framer-motion";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import apiClient from "@/lib/apiClient";

export default function LeadPOAttainmentPage() {
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
        const res = await apiClient.getLeadPOAttainment({ department: dept, academic_year: activeAY });
        if (!cancelled) setData(res);
      } catch (e: any) {
        if (!cancelled) setError(typeof e?.message === "string" ? e.message : "Failed to load PO attainment.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [dept, activeAY]);

  const items: any[] = useMemo(() => {
    if (Array.isArray(data?.items)) return data.items;
    if (Array.isArray(data?.attainments)) return data.attainments;
    if (Array.isArray(data)) return data;
    return [];
  }, [data]);

  return (
    <AccessGate feature="po_attainment" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-6xl mx-auto pb-24 space-y-6">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-4">
          <h1 className="text-3xl font-display text-white">Lead PO Attainment</h1>
          <p className="text-white/50 mt-1 text-sm">Department: {dept} | AY {activeAY}</p>
        </motion.header>

        {loading && <p className="text-white/60">Loading...</p>}
        {error && <p className="text-alert text-sm">{error}</p>}

        {!loading && !error && (
          <motion.section variants={fadeSlideUp} className="border border-white/10">
            {items.length === 0 ? (
              <p className="px-4 py-8 text-white/40 text-sm">No PO attainment data for AY {activeAY}.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="px-4 py-3 text-left text-[10px] font-mono text-white/40 uppercase">PO</th>
                      <th className="px-4 py-3 text-left text-[10px] font-mono text-white/40 uppercase">Attainment %</th>
                      <th className="px-4 py-3 text-left text-[10px] font-mono text-white/40 uppercase">Target %</th>
                      <th className="px-4 py-3 text-left text-[10px] font-mono text-white/40 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item: any, i: number) => {
                      const pct = Number(item.attainment_percentage ?? item.percentage ?? item.attainment ?? 0);
                      const target = Number(item.target ?? 60);
                      const met = pct >= target;
                      return (
                        <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                          <td className="px-4 py-3 text-xs text-white font-mono">{item.po_id ?? item.po ?? item.outcome_code ?? `PO${i + 1}`}</td>
                          <td className="px-4 py-3 text-xs text-white">{pct}%</td>
                          <td className="px-4 py-3 text-xs text-white/50">{target}%</td>
                          <td className={`px-4 py-3 text-xs font-mono ${met ? "text-attain" : "text-alert"}`}>{met ? "Met" : "Not Met"}</td>
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

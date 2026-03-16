"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import { motion } from "framer-motion";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import apiClient from "@/lib/apiClient";

export default function LeadAYComparisonPage() {
  const { user } = useAuthStore();
  const dept = user?.department || "CSE";
  const [years, setYears] = useState(3);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLeadAYComparison({ department: dept, years });
      setData(res);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load AY comparison.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  const rows: any[] = useMemo(() => {
    if (Array.isArray(data?.items)) return data.items;
    if (Array.isArray(data?.comparison)) return data.comparison;
    if (Array.isArray(data)) return data;
    return [];
  }, [data]);

  const ayHeaders: string[] = useMemo(() => {
    if (!rows.length) return [];
    return Object.keys(rows[0]).filter(k => k !== "co" && k !== "co_id" && k !== "course_code");
  }, [rows]);

  return (
    <AccessGate feature="year_comparison" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-6xl mx-auto pb-24 space-y-6">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-4 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-display text-white">AY Comparison</h1>
            <p className="text-white/50 mt-1 text-sm">Department: {dept}</p>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="number" min={2} max={10} value={years}
              onChange={e => setYears(Number(e.target.value || 3))}
              className="w-20 bg-white/5 border border-white/10 px-2 py-1 text-xs text-white"
            />
            <button onClick={() => void load()} className="px-3 py-1 text-xs bg-brand text-white font-mono uppercase">Compare</button>
          </div>
        </motion.header>

        {loading && <p className="text-white/60">Loading...</p>}
        {error && <p className="text-alert text-sm">{error}</p>}

        {!loading && !error && (
          <motion.section variants={fadeSlideUp} className="border border-white/10">
            {rows.length === 0 ? (
              <p className="px-4 py-8 text-white/40 text-sm">No comparison data available.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="px-4 py-3 text-left text-[10px] font-mono text-white/40 uppercase">CO</th>
                      {ayHeaders.map(h => (
                        <th key={h} className="px-4 py-3 text-left text-[10px] font-mono text-white/40 uppercase">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row: any, i: number) => (
                      <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                        <td className="px-4 py-3 text-xs text-white font-mono">{row.co ?? row.co_id ?? `CO${i + 1}`}</td>
                        {ayHeaders.map(h => {
                          const val = Number(row[h] ?? 0);
                          const color = val >= 60 ? "text-attain" : val >= 40 ? "text-brand" : "text-alert";
                          return <td key={h} className={`px-4 py-3 text-xs ${color}`}>{val}%</td>;
                        })}
                      </tr>
                    ))}
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

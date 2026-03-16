"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import { motion } from "framer-motion";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import apiClient from "@/lib/apiClient";

export default function HODAYHistoryPage() {
  const { user } = useAuthStore();
  const dept = String(user?.department || "").trim();
  const [years, setYears] = useState(3);
  const [refresh, setRefresh] = useState(0);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!dept) {
        if (!cancelled) {
          setData(null);
          setError("No department is mapped to this user.");
          setLoading(false);
        }
        return;
      }
      setLoading(true);
      setError(null);
      try {
        // ay-comparison requires a course_id; fetch dept courses first
        const coursesRes = await apiClient.getCourses();
        const allCourses = Array.isArray(coursesRes) ? coursesRes : (coursesRes as any)?.items ?? [];
        const deptCourses = allCourses.filter((c: any) =>
          String(c.department ?? c.dept ?? "").toUpperCase() === String(dept).toUpperCase()
        );
        if (!deptCourses.length) {
          if (!cancelled) { setData(null); setLoading(false); }
          return;
        }
        const res = await apiClient.getLeadAYComparison({ course_id: deptCourses[0].id, department: dept, years });
        if (!cancelled) setData(res);
      } catch (e: any) {
        if (!cancelled) setError(typeof e?.message === "string" ? e.message : "Failed to load AY history.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [dept, years, refresh]);

  const rows: any[] = useMemo(() => {
    if (Array.isArray(data?.comparison)) return data.comparison;
    if (Array.isArray(data?.comparison_table)) {
      return data.comparison_table.map((row: any) => {
        const merged: any = { co: row.co ?? row.co_code ?? row.co_id ?? "CO" };
        if (row?.yearly && typeof row.yearly === "object") {
          Object.entries(row.yearly).forEach(([k, v]) => {
            merged[k] = Number(v ?? 0);
          });
        }
        return merged;
      });
    }
    if (Array.isArray(data?.items)) return data.items;
    if (Array.isArray(data)) return data;
    return [];
  }, [data]);

  const ayHeaders: string[] = useMemo(() => {
    if (Array.isArray(data?.academic_years) && data.academic_years.length > 0) {
      return data.academic_years;
    }
    if (!rows.length) return [];
    return Object.keys(rows[0]).filter(k => /^\d{4}-\d{2}$/.test(k));
  }, [data, rows]);

  return (
    <AccessGate feature="dept_summary" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-6xl mx-auto pb-24 space-y-6">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-4 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-display text-white">Academic Year History</h1>
            <p className="text-white/50 mt-1 text-sm">Department: {dept || "N/A"}</p>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="number" min={2} max={10} value={years}
              onChange={e => setYears(Number(e.target.value || 3))}
              className="w-20 bg-white/5 border border-white/10 px-2 py-1 text-xs text-white"
            />
            <button onClick={() => setRefresh(r => r + 1)} className="px-3 py-1 text-xs bg-brand text-white font-mono uppercase">Refresh</button>
          </div>
        </motion.header>

        {loading && <p className="text-white/60">Loading...</p>}
        {error && <p className="text-alert text-sm">{error}</p>}

        {!loading && !error && (
          <motion.section variants={fadeSlideUp} className="border border-white/10">
            {rows.length === 0 ? (
              <p className="px-4 py-8 text-white/40 text-sm">No historical data available.</p>
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

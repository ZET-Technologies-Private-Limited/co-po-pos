"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line, CartesianGrid, Legend } from "recharts";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import { useAuthStore } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";

export default function AnalyticsPage() {
  const { activeRole, activeAY, user } = useAuthStore();
  const dept = user?.department || "CSE";

  const [courses, setCourses] = useState<any[]>([]);
  const [attainmentData, setAttainmentData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [courseRes, attRes] = await Promise.all([
        apiClient.getCourses().catch(() => []),
        apiClient.getLeadCOAttainment({ academic_year: activeAY }).catch(() => null),
      ]);
      setCourses(Array.isArray(courseRes) ? courseRes : []);
      setAttainmentData(attRes);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load analytics.");
    } finally {
      setLoading(false);
    }
  }, [activeAY]);

  useEffect(() => { void load(); }, [load]);

  if (activeRole === "faculty" || activeRole === "subject_lead") {
    return (
      <div className="w-full min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-display text-alert mb-2">Access Restricted</h2>
          <p className="text-white/40 font-mono text-sm uppercase tracking-widest">
            Your role ({activeRole.replace("_", " ")}) does not have clearance for institutional analytics.
          </p>
        </div>
      </div>
    );
  }

  const attainmentItems: any[] = useMemo(() => {
    const list = Array.isArray(attainmentData?.items) ? attainmentData.items :
      Array.isArray(attainmentData) ? attainmentData : [];
    return list;
  }, [attainmentData]);

  const deptData = useMemo(() => {
    const byDept: Record<string, number[]> = {};
    courses.forEach((c: any) => {
      const d = c.department ?? c.dept ?? "Unknown";
      if (!byDept[d]) byDept[d] = [];
    });
    attainmentItems.forEach((item: any) => {
      const d = item.department ?? dept;
      if (!byDept[d]) byDept[d] = [];
      const pct = Number(item.attainment_percentage ?? item.percentage ?? 0);
      if (Number.isFinite(pct)) byDept[d].push(pct);
    });
    return Object.entries(byDept).map(([dept, vals]) => ({
      dept: dept.substring(0, 4).toUpperCase(),
      attainment: vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : 0,
    })).filter(d => d.attainment > 0);
  }, [courses, attainmentItems, dept]);

  const coTrendData = useMemo(() => {
    return attainmentItems.slice(0, 6).map((item: any, i: number) => ({
      co: item.co_id ?? item.co ?? `CO${i + 1}`,
      attainment: Number(item.attainment_percentage ?? item.percentage ?? 0),
    }));
  }, [attainmentItems]);

  return (
    <div className="w-full min-h-screen pb-24">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-5xl mx-auto px-6 pt-12">

        <motion.div variants={fadeSlideUp} className="flex items-end justify-between mb-12">
          <div>
            <div className="flex items-center gap-3 text-sm font-mono text-brand uppercase tracking-widest mb-4">
              <span className="w-8 h-[1px] bg-brand" /> Analytics
            </div>
            <h1 className="text-5xl font-display text-white">Insights Dashboard</h1>
            <p className="text-white/40 font-light mt-2">AY {activeAY} · {courses.length} courses</p>
          </div>
        </motion.div>

        {loading && <p className="text-white/60 py-8">Loading analytics...</p>}
        {error && <p className="text-alert py-4">{error}</p>}

        {!loading && !error && (
          <>
            {coTrendData.length > 0 && (
              <motion.div variants={fadeSlideUp} className="mb-16">
                <h2 className="text-2xl font-display text-white mb-2">CO Attainment Overview</h2>
                <p className="text-white/40 font-light mb-8">Course outcome attainment percentages for AY {activeAY}.</p>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={coTrendData} barCategoryGap="40%">
                    <XAxis dataKey="co" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }} axisLine={false} tickLine={false} domain={[0, 100]} />
                    <Tooltip contentStyle={{ background: "#0F172A", border: "1px solid rgba(255,255,255,0.1)" }} />
                    <Bar dataKey="attainment" name="Attainment %" radius={[2, 2, 0, 0]}>
                      {coTrendData.map((entry, i) => (
                        <Cell key={i} fill={entry.attainment >= 60 ? "#059669" : entry.attainment >= 40 ? "#06B6D4" : "#E11D48"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </motion.div>
            )}

            {activeRole === "admin" && deptData.length > 0 && (
              <motion.div variants={fadeSlideUp} className="mb-16">
                <h2 className="text-2xl font-display text-white mb-2">Department Comparison</h2>
                <p className="text-white/40 font-light mb-8">Average CO attainment across departments.</p>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={deptData} barCategoryGap="40%">
                    <XAxis dataKey="dept" tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12 }} axisLine={false} tickLine={false} domain={[0, 100]} />
                    <Tooltip contentStyle={{ background: "#0F172A", border: "1px solid rgba(255,255,255,0.1)" }} />
                    <Bar dataKey="attainment" name="Attainment" radius={[2, 2, 0, 0]}>
                      {deptData.map((entry, i) => (
                        <Cell key={i} fill={entry.attainment >= 60 ? "#059669" : entry.attainment >= 40 ? "#06B6D4" : "#E11D48"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </motion.div>
            )}

            {attainmentItems.length === 0 && (
              <div className="py-24 text-center text-white/20">
                <p className="text-sm font-mono uppercase tracking-widest">No attainment data available for AY {activeAY}.</p>
                <p className="text-xs mt-2">Upload marks and calculate CO attainment to see analytics.</p>
              </div>
            )}
          </>
        )}
      </motion.div>
    </div>
  );
}

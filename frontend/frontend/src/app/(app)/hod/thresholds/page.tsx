"use client";

import { useEffect, useMemo, useState } from "react";
import { AccessGate } from "@/components/auth/AccessGate";
import { useAuthStore } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";

export default function HODThresholdsViewPage() {
  const { user, activeAY } = useAuthStore();
  const dept = String(user?.department || "").trim();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
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
        const res = await apiClient.getLeadCOAttainment({ department: dept, academic_year: activeAY });
        if (!cancelled) setData(res);
      } catch (e: any) {
        if (!cancelled) setError(typeof e?.message === "string" ? e.message : "Failed to load threshold analytics.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [dept, activeAY]);

  const derived = useMemo(() => {
    const list = Array.isArray(data?.course_rows)
      ? data.course_rows.flatMap((course: any) =>
          Array.isArray(course?.cos_data)
            ? course.cos_data.map((co: any) => co?.final_percentage)
            : []
        )
      : (Array.isArray(data?.items) ? data.items.map((x: any) => x?.attainment_percentage ?? x?.percentage) : Array.isArray(data) ? data : []);
    const values = list
      .map((x: any) => Number(x ?? NaN))
      .filter((n: number) => Number.isFinite(n));
    if (!values.length) return { p33: 0, p66: 0, avg: 0 };
    const sorted = [...values].sort((a, b) => a - b);
    const p33 = sorted[Math.floor((sorted.length - 1) * 0.33)] ?? 0;
    const p66 = sorted[Math.floor((sorted.length - 1) * 0.66)] ?? 0;
    const avg = Math.round(sorted.reduce((a, b) => a + b, 0) / sorted.length);
    return { p33: Math.round(p33), p66: Math.round(p66), avg };
  }, [data]);

  return (
    <AccessGate feature="threshold_config" deny="lock">
      <div className="max-w-4xl mx-auto pb-24 space-y-6">
        <h1 className="text-3xl text-white font-display">Attainment Thresholds</h1>
        <p className="text-white/50 text-sm">Derived from live CO attainment data for AY {activeAY}.</p>
        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}
        {!loading && !error ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="border border-white/10 p-4"><p className="text-xs text-white/40">Level 1 / 2 Cutoff (33rd pct)</p><p className="text-2xl text-white font-display mt-1">{derived.p33}%</p></div>
            <div className="border border-white/10 p-4"><p className="text-xs text-white/40">Level 2 / 3 Cutoff (66th pct)</p><p className="text-2xl text-white font-display mt-1">{derived.p66}%</p></div>
            <div className="border border-white/10 p-4"><p className="text-xs text-white/40">Department Average</p><p className="text-2xl text-white font-display mt-1">{derived.avg}%</p></div>
          </div>
        ) : null}
      </div>
    </AccessGate>
  );
}

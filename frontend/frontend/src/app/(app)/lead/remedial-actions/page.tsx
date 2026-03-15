"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function LeadRemedialActionsPage() {
  const { activeAY } = useAuthStore();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await apiClient.getLeadCOAttainment({ academic_year: activeAY });
        if (!cancelled) setData(res);
      } catch (e: any) {
        if (!cancelled) setError(typeof e?.message === "string" ? e.message : "Failed to load remedial analysis.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [activeAY]);

  const weakItems = useMemo(() => {
    const list = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
    return list.filter((x: any) => Number(x?.attainment_percentage ?? x?.percentage ?? 0) < 60);
  }, [data]);

  return (
    <AccessGate feature="remedial_actions" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <h1 className="text-3xl text-white font-display">Lead Remedial Actions</h1>
        <p className="text-white/50 text-sm">Derived from live CO attainment data (below threshold).</p>
        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}
        {!loading && !error ? (
          <div className="space-y-3">
            {weakItems.length === 0 ? <p className="text-white/40 text-sm">No weak COs found.</p> : null}
            {weakItems.map((item: any, idx: number) => (
              <div key={idx} className="border border-white/10 rounded p-3">
                <p className="text-white text-sm">{item?.course_code || "Course"} - {item?.co || item?.co_id || "CO"}</p>
                <p className="text-white/60 text-xs mt-1">Attainment: {item?.attainment_percentage ?? item?.percentage ?? "N/A"}%</p>
                <p className="text-white/50 text-xs mt-1">Suggested action: extra problem-solving session + targeted quiz.</p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </AccessGate>
  );
}

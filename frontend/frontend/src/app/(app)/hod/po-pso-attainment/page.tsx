"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function DeptPOPSOAttainmentPage() {
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
        if (!cancelled) setError(typeof e?.message === "string" ? e.message : "Failed to load PO/PSO attainment.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [dept, activeAY]);

  return (
    <AccessGate feature="dept_summary" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <h1 className="text-3xl text-white font-display">Department PO/PSO Attainment</h1>
        <p className="text-white/50 text-sm">Department: {dept} | AY {activeAY}</p>
        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}
        {!loading && !error ? <pre className="text-xs text-white/70 whitespace-pre-wrap border border-white/10 rounded p-3">{JSON.stringify(data, null, 2)}</pre> : null}
      </div>
    </AccessGate>
  );
}

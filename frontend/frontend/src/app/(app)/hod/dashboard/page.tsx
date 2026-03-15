"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function HODDashboardPage() {
  const { user, activeAY } = useAuthStore();
  const dept = user?.department || "CSE";

  const [dashboard, setDashboard] = useState<any>(null);
  const [coHealth, setCOHealth] = useState<any>(null);
  const [poAtt, setPOAtt] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [d, c, p] = await Promise.all([
          apiClient.getCourseLeadDashboard(dept, activeAY),
          apiClient.getCOHealthAnalysis(dept, activeAY),
          apiClient.getLeadPOAttainment({ department: dept, academic_year: activeAY }),
        ]);
        if (cancelled) return;
        setDashboard(d);
        setCOHealth(c);
        setPOAtt(p);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load HOD dashboard.");
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
    <AccessGate feature="dashboard" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <h1 className="text-3xl text-white font-display">HOD Dashboard</h1>
        <p className="text-white/50 text-sm">Department: {dept} | AY {activeAY}</p>
        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}
        {!loading && !error ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <section className="border border-white/10 rounded p-3"><h2 className="text-sm text-white mb-2">Summary</h2><pre className="text-xs text-white/70 whitespace-pre-wrap">{JSON.stringify(dashboard, null, 2)}</pre></section>
            <section className="border border-white/10 rounded p-3"><h2 className="text-sm text-white mb-2">CO Health</h2><pre className="text-xs text-white/70 whitespace-pre-wrap">{JSON.stringify(coHealth, null, 2)}</pre></section>
            <section className="border border-white/10 rounded p-3"><h2 className="text-sm text-white mb-2">PO Attainment</h2><pre className="text-xs text-white/70 whitespace-pre-wrap">{JSON.stringify(poAtt, null, 2)}</pre></section>
          </div>
        ) : null}
      </div>
    </AccessGate>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function HODDeptReportPage() {
  const { user, activeAY } = useAuthStore();
  const dept = user?.department || "CSE";

  const [reportsData, setReportsData] = useState<any>(null);
  const [history, setHistory] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [r, h] = await Promise.all([
          apiClient.getLeadReports({ department: dept, academic_year: activeAY }),
          apiClient.getLeadReportHistory(30),
        ]);
        if (!cancelled) {
          setReportsData(r);
          setHistory(h);
        }
      } catch (e: any) {
        if (!cancelled) setError(typeof e?.message === "string" ? e.message : "Failed to load department reports.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [dept, activeAY]);

  async function generate() {
    try {
      await apiClient.generateLeadReport({ department: dept, academic_year: activeAY, format: "pdf" });
      const h = await apiClient.getLeadReportHistory(30);
      setHistory(h);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to generate report.");
    }
  }

  return (
    <AccessGate feature="dept_report" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <h1 className="text-3xl text-white font-display">Department Report</h1>
        <button onClick={() => void generate()} className="px-3 py-1 text-xs bg-brand text-white rounded">Generate Report</button>
        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}
        {!loading && !error ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <section className="border border-white/10 rounded p-3"><h2 className="text-sm text-white mb-2">Report Data</h2><pre className="text-xs text-white/70 whitespace-pre-wrap">{JSON.stringify(reportsData, null, 2)}</pre></section>
            <section className="border border-white/10 rounded p-3"><h2 className="text-sm text-white mb-2">History</h2><pre className="text-xs text-white/70 whitespace-pre-wrap">{JSON.stringify(history, null, 2)}</pre></section>
          </div>
        ) : null}
      </div>
    </AccessGate>
  );
}

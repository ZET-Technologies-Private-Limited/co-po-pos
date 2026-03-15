"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function HODAYHistoryPage() {
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
      setError(typeof e?.message === "string" ? e.message : "Failed to load AY history.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <AccessGate feature="dept_summary" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <h1 className="text-3xl text-white font-display">Academic Year History</h1>
        <div className="flex items-center gap-2">
          <input type="number" min={2} max={10} value={years} onChange={(e) => setYears(Number(e.target.value || 3))} className="w-24 bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-white" />
          <button onClick={() => void load()} className="px-3 py-1 text-xs bg-brand text-white rounded">Refresh</button>
        </div>
        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}
        {!loading && !error ? <pre className="text-xs text-white/70 whitespace-pre-wrap border border-white/10 rounded p-3">{JSON.stringify(data, null, 2)}</pre> : null}
      </div>
    </AccessGate>
  );
}

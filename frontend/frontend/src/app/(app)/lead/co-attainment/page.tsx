"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function LeadCOAttainmentPage() {
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
        if (cancelled) return;
        setData(res);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load lead CO attainment.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [activeAY]);

  return (
    <AccessGate feature="co_attainment" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <h1 className="text-3xl text-white font-display">Lead CO Attainment</h1>
        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}
        {!loading && !error ? <pre className="text-xs text-white/70 whitespace-pre-wrap border border-white/10 rounded-lg p-4">{JSON.stringify(data, null, 2)}</pre> : null}
      </div>
    </AccessGate>
  );
}

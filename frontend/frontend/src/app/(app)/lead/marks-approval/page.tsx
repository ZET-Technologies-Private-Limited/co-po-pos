"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function LeadMarksApprovalPage() {
  const { user, activeAY } = useAuthStore();
  const dept = user?.department || "CSE";

  const [dashboard, setDashboard] = useState<any>(null);
  const [selectedId, setSelectedId] = useState<string>("");
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard() {
    const d = await apiClient.getCourseLeadDashboard(dept, activeAY);
    setDashboard(d);
    const first = Array.isArray(d?.approval_queue) && d.approval_queue.length ? String(d.approval_queue[0]?.submission_id || "") : "";
    setSelectedId((prev) => prev || first);
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        await loadDashboard();
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load marks approval queue.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [dept, activeAY]);

  useEffect(() => {
    let cancelled = false;
    async function loadDetail() {
      if (!selectedId) {
        setDetail(null);
        return;
      }
      try {
        const d = await apiClient.getLeadMarksApproval(selectedId);
        if (!cancelled) setDetail(d);
      } catch {
        if (!cancelled) setDetail(null);
      }
    }
    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const queue = useMemo(() => (Array.isArray(dashboard?.approval_queue) ? dashboard.approval_queue : []), [dashboard]);

  async function approve() {
    if (!selectedId) return;
    await apiClient.approveLeadMarksApproval(selectedId, "Approved by course lead");
    await loadDashboard();
  }

  async function returnForRevision() {
    if (!selectedId) return;
    await apiClient.returnLeadMarksApproval(selectedId, "Please recheck outlier entries");
    await loadDashboard();
  }

  return (
    <AccessGate feature="marks_approval" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <h1 className="text-3xl text-white font-display">Lead Marks Approval</h1>
        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}
        {!loading && !error ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <section className="border border-white/10 rounded p-3 space-y-2">
              <h2 className="text-sm text-white">Approval Queue</h2>
              {queue.map((q: any, i: number) => {
                const id = String(q?.submission_id || i);
                return (
                  <button key={id} onClick={() => setSelectedId(id)} className={`block w-full text-left text-xs border rounded p-2 ${selectedId === id ? "border-brand text-brand" : "border-white/10 text-white/70"}`}>
                    {q?.exam_name || "Submission"} ({id})
                  </button>
                );
              })}
            </section>
            <section className="lg:col-span-2 border border-white/10 rounded p-3 space-y-3">
              <div className="flex gap-2">
                <button onClick={() => void approve()} className="px-3 py-1 text-xs bg-brand text-white rounded">Approve</button>
                <button onClick={() => void returnForRevision()} className="px-3 py-1 text-xs border border-white/20 text-white/70 rounded">Return</button>
              </div>
              <pre className="text-xs text-white/70 whitespace-pre-wrap">{JSON.stringify(detail, null, 2)}</pre>
            </section>
          </div>
        ) : null}
      </div>
    </AccessGate>
  );
}

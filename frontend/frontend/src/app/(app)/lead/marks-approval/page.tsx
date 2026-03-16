"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import { motion } from "framer-motion";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import { CheckCircle2, RotateCcw, Loader2 } from "lucide-react";
import apiClient from "@/lib/apiClient";

export default function LeadMarksApprovalPage() {
  const { user, activeAY } = useAuthStore();
  const dept = user?.department || "CSE";

  const [dashboard, setDashboard] = useState<any>(null);
  const [selectedId, setSelectedId] = useState<string>("");
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadDashboard() {
    const d = await apiClient.getCourseLeadDashboard(dept, activeAY);
    setDashboard(d);
    const first = Array.isArray(d?.approval_queue) && d.approval_queue.length
      ? String(d.approval_queue[0]?.submission_id || "")
      : "";
    setSelectedId(prev => prev || first);
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
    return () => { cancelled = true; };
  }, [dept, activeAY]);

  useEffect(() => {
    let cancelled = false;
    async function loadDetail() {
      if (!selectedId) { setDetail(null); return; }
      setDetailLoading(true);
      try {
        const d = await apiClient.getLeadMarksApproval(selectedId);
        if (!cancelled) setDetail(d);
      } catch {
        if (!cancelled) setDetail(null);
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    }
    void loadDetail();
    return () => { cancelled = true; };
  }, [selectedId]);

  const queue = useMemo(() => Array.isArray(dashboard?.approval_queue) ? dashboard.approval_queue : [], [dashboard]);

  async function approve() {
    if (!selectedId) return;
    setActing(true); setMessage(null); setError(null);
    try {
      await apiClient.approveLeadMarksApproval(selectedId, "Approved by course lead");
      setMessage("Marks approved successfully.");
      await loadDashboard();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to approve.");
    } finally {
      setActing(false);
    }
  }

  async function returnForRevision() {
    if (!selectedId) return;
    setActing(true); setMessage(null); setError(null);
    try {
      await apiClient.returnLeadMarksApproval(selectedId, "Please recheck outlier entries");
      setMessage("Returned for revision.");
      await loadDashboard();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to return.");
    } finally {
      setActing(false);
    }
  }

  const marksRows: any[] = useMemo(() => {
    if (Array.isArray(detail?.rows)) return detail.rows;
    if (Array.isArray(detail?.students)) return detail.students;
    if (Array.isArray(detail)) return detail;
    return [];
  }, [detail]);

  return (
    <AccessGate feature="marks_approval" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-6xl mx-auto pb-24 space-y-6">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-4">
          <h1 className="text-3xl font-display text-white">Marks Approval Queue</h1>
          <p className="text-white/50 mt-1 text-sm">Department: {dept} | AY {activeAY}</p>
        </motion.header>

        {loading && <p className="text-white/60">Loading...</p>}
        {error && <p className="text-alert text-sm">{error}</p>}
        {message && <p className="text-attain text-sm">{message}</p>}

        {!loading && !error && (
          <div className="flex gap-4 flex-col lg:flex-row">
            {/* Queue list */}
            <motion.section variants={fadeSlideUp} className="border border-white/10 lg:w-72 shrink-0">
              <div className="px-4 py-3 border-b border-white/10">
                <h2 className="text-sm font-mono text-white uppercase tracking-widest">Queue ({queue.length})</h2>
              </div>
              {queue.length === 0 ? (
                <div className="px-4 py-8 flex items-center gap-2 text-attain text-sm">
                  <CheckCircle2 className="w-4 h-4" /> All caught up
                </div>
              ) : (
                <div className="divide-y divide-white/5">
                  {queue.map((q: any, i: number) => {
                    const id = String(q?.submission_id || i);
                    const isSelected = selectedId === id;
                    return (
                      <button
                        key={id}
                        onClick={() => setSelectedId(id)}
                        className={`w-full text-left px-4 py-3 transition-colors ${isSelected ? "bg-brand/10 border-l-2 border-brand" : "hover:bg-white/[0.02] border-l-2 border-transparent"}`}
                      >
                        <p className={`text-sm ${isSelected ? "text-white" : "text-white/70"}`}>
                          {q?.exam_name ?? q?.course_code ?? "Submission"}
                        </p>
                        <p className="text-white/40 text-xs mt-0.5">{q?.faculty_name ?? ""}</p>
                        <p className="text-white/30 text-[10px] font-mono mt-0.5">{q?.submitted_at ?? ""}</p>
                      </button>
                    );
                  })}
                </div>
              )}
            </motion.section>

            {/* Detail panel */}
            <motion.section variants={fadeSlideUp} className="flex-1 border border-white/10 min-w-0">
              <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
                <h2 className="text-sm font-mono text-white uppercase tracking-widest">
                  {detail?.exam_name ?? detail?.course_code ?? (selectedId ? `Submission ${selectedId}` : "Select a submission")}
                </h2>
                {selectedId && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => void approve()}
                      disabled={acting || !selectedId}
                      className="flex items-center gap-1 px-3 py-1 text-xs bg-attain text-black font-mono uppercase disabled:opacity-50"
                    >
                      {acting ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                      Approve
                    </button>
                    <button
                      onClick={() => void returnForRevision()}
                      disabled={acting || !selectedId}
                      className="flex items-center gap-1 px-3 py-1 text-xs border border-white/20 text-white/70 font-mono uppercase disabled:opacity-50"
                    >
                      <RotateCcw className="w-3 h-3" /> Return
                    </button>
                  </div>
                )}
              </div>

              {detailLoading && <p className="px-4 py-6 text-white/60 text-sm">Loading detail...</p>}

              {!detailLoading && !selectedId && (
                <p className="px-4 py-8 text-white/40 text-sm">Select a submission from the queue.</p>
              )}

              {!detailLoading && selectedId && detail && (
                <div className="p-4 space-y-4">
                  {/* Meta */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                      ["Course", detail.course_code ?? detail.course_name ?? "—"],
                      ["Exam", detail.exam_name ?? detail.exam_type ?? "—"],
                      ["Faculty", detail.faculty_name ?? "—"],
                      ["Students", detail.total_students ?? marksRows.length ?? "—"],
                    ].map(([label, val]) => (
                      <div key={label} className="border border-white/10 p-3">
                        <p className="text-[10px] font-mono text-white/40 uppercase">{label}</p>
                        <p className="text-sm text-white mt-1">{val}</p>
                      </div>
                    ))}
                  </div>

                  {/* Marks table */}
                  {marksRows.length > 0 && (
                    <div className="overflow-x-auto border border-white/10">
                      <table className="w-full border-collapse">
                        <thead>
                          <tr className="border-b border-white/10">
                            <th className="px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Student</th>
                            {Object.keys(marksRows[0]?.marks ?? {}).slice(0, 8).map(k => (
                              <th key={k} className="px-3 py-2 text-center text-[10px] font-mono text-white/40 uppercase">Q{k}</th>
                            ))}
                            <th className="px-3 py-2 text-center text-[10px] font-mono text-white/40 uppercase">Total</th>
                          </tr>
                        </thead>
                        <tbody>
                          {marksRows.slice(0, 20).map((row: any, i: number) => {
                            const marks = row.marks ?? {};
                            const total = Object.values(marks).reduce((a: any, b: any) => a + Number(b), 0);
                            return (
                              <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                                <td className="px-3 py-2 text-xs text-white/70 font-mono">{row.student_id ?? row.roll ?? `S${i + 1}`}</td>
                                {Object.values(marks).slice(0, 8).map((v: any, j: number) => (
                                  <td key={j} className="px-3 py-2 text-center text-xs text-white/70">{v}</td>
                                ))}
                                <td className="px-3 py-2 text-center text-xs text-white font-mono">{total}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                      {marksRows.length > 20 && (
                        <p className="px-3 py-2 text-[10px] text-white/30 font-mono">Showing 20 of {marksRows.length} rows.</p>
                      )}
                    </div>
                  )}

                  {marksRows.length === 0 && (
                    <p className="text-white/40 text-sm">No marks rows in this submission.</p>
                  )}
                </div>
              )}
            </motion.section>
          </div>
        )}
      </motion.div>
    </AccessGate>
  );
}

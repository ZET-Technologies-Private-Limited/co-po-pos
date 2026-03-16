"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import { motion } from "framer-motion";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import { Download, Loader2 } from "lucide-react";
import apiClient from "@/lib/apiClient";

export default function HODDeptReportPage() {
  const { user, activeAY } = useAuthStore();
  const dept = String(user?.department || "").trim();

  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!dept) {
        if (!cancelled) {
          setHistory([]);
          setError("No department is mapped to this user.");
          setLoading(false);
        }
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const h = await apiClient.getLeadReportHistory(30, dept);
        if (cancelled) return;
        setHistory(
          Array.isArray(h)
            ? h
            : Array.isArray(h?.reports)
              ? h.reports
              : Array.isArray(h?.items)
                ? h.items
                : []
        );
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load department reports.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [dept, activeAY]);

  async function generate() {
    if (!dept) {
      setError("No department is mapped to this user.");
      return;
    }
    setGenerating(true);
    setError(null);
    setMessage(null);
    try {
      await apiClient.generateLeadReport({
        department: dept,
        academic_year: activeAY,
        report_type: "co_attainment",
      });
      setMessage("Department report generated successfully.");
      const h = await apiClient.getLeadReportHistory(30, dept);
      setHistory(
        Array.isArray(h)
          ? h
          : Array.isArray(h?.reports)
            ? h.reports
            : Array.isArray(h?.items)
              ? h.items
              : []
      );
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to generate report.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <AccessGate feature="dept_report" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-6xl mx-auto pb-24 space-y-6">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-4 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-display text-white">Department Report</h1>
            <p className="text-white/50 mt-1 text-sm">Department: {dept || "N/A"} | AY {activeAY}</p>
          </div>
          <button
            onClick={() => void generate()}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2 bg-brand text-white text-xs font-mono uppercase disabled:opacity-50"
          >
            {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
            Generate Report
          </button>
        </motion.header>

        {loading && <p className="text-white/60">Loading...</p>}
        {error && <p className="text-alert text-sm">{error}</p>}
        {message && <p className="text-attain text-sm">{message}</p>}

        {!loading && (
          <motion.section variants={fadeSlideUp} className="border border-white/10">
            <div className="px-4 py-3 border-b border-white/10">
              <h2 className="text-sm font-mono text-white uppercase tracking-widest">Report History</h2>
            </div>
            {history.length === 0 ? (
              <p className="px-4 py-8 text-white/40 text-sm">No reports generated yet.</p>
            ) : (
              <div className="divide-y divide-white/5">
                {history.map((r: any, i: number) => (
                  <div key={r.id ?? i} className="px-4 py-3 flex items-center justify-between">
                    <div>
                      <p className="text-white text-sm">{r.title ?? r.report_name ?? r.name ?? `Report ${i + 1}`}</p>
                      <p className="text-white/50 text-xs mt-0.5">{r.generated_at ?? r.created_at ?? ""} · {r.file_format ?? r.format ?? "PDF"}</p>
                    </div>
                    {(r.download_links?.pdf || r.download_url) && (
                      <a href={r.download_links?.pdf ?? r.download_url} target="_blank" rel="noreferrer" className="text-xs text-brand hover:text-white flex items-center gap-1">
                        <Download className="w-3 h-3" /> Download
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </motion.section>
        )}
      </motion.div>
    </AccessGate>
  );
}

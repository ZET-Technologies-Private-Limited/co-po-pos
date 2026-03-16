"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import { motion } from "framer-motion";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
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
    return () => { cancelled = true; };
  }, [activeAY]);

  const weakItems = useMemo(() => {
    const list = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
    return list.filter((x: any) => Number(x?.attainment_percentage ?? x?.percentage ?? 0) < 60);
  }, [data]);

  const REMEDIAL_SUGGESTIONS: Record<string, string> = {
    L1: "Conduct extra problem-solving sessions, targeted quizzes, and peer tutoring.",
    default: "Review teaching methodology, provide additional practice materials.",
  };

  return (
    <AccessGate feature="remedial_actions" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-6xl mx-auto pb-24 space-y-6">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-4">
          <h1 className="text-3xl font-display text-white">Remedial Actions</h1>
          <p className="text-white/50 mt-1 text-sm">COs below 60% attainment threshold · AY {activeAY}</p>
        </motion.header>

        {loading && <p className="text-white/60">Loading...</p>}
        {error && <p className="text-alert text-sm">{error}</p>}

        {!loading && !error && (
          <motion.section variants={fadeSlideUp}>
            {weakItems.length === 0 ? (
              <div className="flex items-center gap-3 py-12 text-attain">
                <CheckCircle2 className="w-6 h-6" />
                <p className="text-sm">No weak COs found — all COs above threshold.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {weakItems.map((item: any, idx: number) => {
                  const pct = Number(item.attainment_percentage ?? item.percentage ?? 0);
                  const level = pct >= 40 ? "L2" : "L1";
                  return (
                    <div key={idx} className="border border-white/10 p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <AlertTriangle className="w-4 h-4 text-alert shrink-0" />
                          <div>
                            <p className="text-white text-sm font-medium">
                              {item.course_code ?? "Course"} — {item.co_id ?? item.co ?? "CO"}
                            </p>
                            <p className="text-white/50 text-xs mt-0.5">{item.co_statement ?? ""}</p>
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-alert text-lg font-display">{pct}%</p>
                          <p className="text-[10px] font-mono text-white/30 uppercase">{level}</p>
                        </div>
                      </div>
                      <div className="h-0.5 bg-white/5">
                        <div className="h-full bg-alert/60" style={{ width: `${pct}%` }} />
                      </div>
                      <p className="text-white/50 text-xs">
                        Suggested: {REMEDIAL_SUGGESTIONS[level] ?? REMEDIAL_SUGGESTIONS.default}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </motion.section>
        )}
      </motion.div>
    </AccessGate>
  );
}

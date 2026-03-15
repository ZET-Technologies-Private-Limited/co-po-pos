"use client";

import { useMemo, useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, TrendingDown } from "lucide-react";
import Link from "next/link";
import { useAuthStore } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";
import { AccessGate } from "@/components/auth/AccessGate";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";

const DEFAULT_LEVEL2 = 55;

export default function LowCOAlertsPage() {
  const { activeRole, user, activeAY } = useAuthStore();
  const dept = user?.department || "CSE";
  const [dashboard, setDashboard] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getCourseLeadDashboard(dept, activeAY || "2024-25");
      setDashboard(data);
    } catch {
      setDashboard(null);
    } finally {
      setLoading(false);
    }
  }, [dept, activeAY]);

  useEffect(() => {
    void load();
  }, [load]);

  const isReadOnly = activeRole === "faculty";

  const alerts = useMemo(() => {
    const table = dashboard?.co_health_table ?? [];
    const result: Array<{
      courseId: string; courseCode: string; courseName: string;
      co: string; pct: number; level: number;
      hasRemedial: boolean; remedialText: string;
    }> = [];
    table.forEach((row: any) => {
      const [code = "", name = ""] = (row.course ?? "").split(" - ");
      (row.cos ?? []).forEach((c: any) => {
        if (c.level === "L1") {
          result.push({
            courseId: row.course_id ?? "", courseCode: code, courseName: name,
            co: c.code ?? "", pct: c.percentage ?? 0, level: 1,
            hasRemedial: false, remedialText: "",
          });
        }
      });
    });
    return result;
  }, [dashboard]);

  if (loading) {
    return (
      <AccessGate feature="low_co_alerts" deny="lock">
        <div className="max-w-5xl mx-auto pb-32 py-8"><p className="text-white/60">Loading alerts…</p></div>
      </AccessGate>
    );
  }

  return (
    <AccessGate feature="low_co_alerts" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-5xl mx-auto pb-32">

        {/* Header */}
        <motion.div variants={fadeSlideUp} className="pb-8 border-b border-white/5">
          <div className="flex items-center gap-2 text-[10px] font-mono text-alert uppercase tracking-widest mb-3">
            <span className="w-8 h-[1px] bg-alert" /> Performance Alerts
          </div>
          <div className="flex justify-between items-end">
            <div>
              <h1 className="text-4xl font-display text-white flex items-center gap-4">
                <AlertTriangle className="w-8 h-8 text-alert" /> Low CO Alerts
              </h1>
              <p className="text-white/40 font-light mt-1">
                {alerts.length} Level 1 CO{alerts.length !== 1 ? "s" : ""} below {DEFAULT_LEVEL2}% attainment threshold.
                {isReadOnly && " View-only — contact your Course Lead for remedial actions."}
              </p>
            </div>
            <div className="flex items-center gap-2 text-[10px] font-mono">
              <span className="text-white/20 uppercase tracking-widest">Threshold:</span>
              <span className="text-alert font-bold">&lt; {DEFAULT_LEVEL2}%</span>
            </div>
          </div>
        </motion.div>

        {alerts.length === 0 ? (
          <motion.div variants={fadeSlideUp} className="py-24 flex flex-col items-center gap-4 text-white/20">
            <CheckCircle2 className="w-12 h-12 text-attain/30" />
            <p className="text-sm font-mono uppercase tracking-widest">No Level 1 alerts — all COs above threshold</p>
          </motion.div>
        ) : (
          <motion.div variants={fadeSlideUp} className="flex flex-col divide-y divide-white/5">
            {alerts.map((alert, i) => (
              <div key={i} className="py-6 flex items-start gap-6">
                <div className="shrink-0 mt-1">
                  <TrendingDown className="w-5 h-5 text-alert" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <div>
                      <div className="flex items-center gap-3">
                        <span className="text-alert font-mono text-sm font-bold">{alert.co}</span>
                        <span className="text-[9px] font-mono border border-alert/30 text-alert px-2 py-0.5 uppercase">Level 1</span>
                        <span className="text-[9px] font-mono text-white/30 uppercase">{alert.courseCode}</span>
                      </div>
                      <p className="text-white/60 text-sm mt-0.5">{alert.courseName}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-2xl font-display text-alert">{alert.pct}%</p>
                      <p className="text-[9px] font-mono text-white/20 uppercase">Attainment</p>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="h-0.5 bg-white/5 mb-3">
                    <div className="h-full bg-alert/60" style={{ width: `${alert.pct}%` }} />
                  </div>

                  {/* Remedial action status */}
                  {alert.hasRemedial ? (
                    <div className="flex items-start gap-2 text-xs text-attain/70">
                      <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                      <p className="italic">{alert.remedialText}</p>
                    </div>
                  ) : (
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] font-mono text-alert/60 uppercase tracking-widest">No remedial action filed</span>
                      {!isReadOnly && (
                        <Link href={`/faculty/course/${alert.courseId}/co-attainment`}
                          className="text-[10px] font-mono text-brand uppercase tracking-widest hover:text-white transition-colors">
                          → File Action
                        </Link>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </motion.div>
        )}

      </motion.div>
    </AccessGate>
  );
}

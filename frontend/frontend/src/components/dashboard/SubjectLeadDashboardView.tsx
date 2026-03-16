"use client";

import { useMemo, useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Layers,
  CheckCircle2,
  Clock,
  Users,
  FileText,
} from "lucide-react";
import { useAuthStore } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";

const DEFAULT_LEVEL2 = 55;
const DEFAULT_LEVEL3 = 70;

function pctToLevel(pct: number): { level: number; label: string } {
  if (pct >= DEFAULT_LEVEL3) return { level: 3, label: "Level 3" };
  if (pct >= DEFAULT_LEVEL2) return { level: 2, label: "Level 2" };
  return { level: 1, label: "Level 1" };
}

type QueueItem = {
  courseId: string;
  courseCode: string;
  courseName: string;
  examId: string;
  examName: string;
  submittedAt?: string;
  waitDays: number;
  urgency: "Normal" | "High" | "Critical";
};

export function LeadDashboardView() {
  const { user, activeAY } = useAuthStore();
  const dept = user?.department || "CSE";
  const [dashboard, setDashboard] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getCourseLeadDashboard(dept, activeAY || "2024-25");
      setDashboard(data);
    } catch (e: any) {
      setError(e?.message || "Failed to load lead dashboard.");
    } finally {
      setLoading(false);
    }
  }, [dept, activeAY]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const onFocus = () => void load();
    if (typeof document !== "undefined" && document.addEventListener) {
      document.addEventListener("visibilitychange", onFocus);
      return () => document.removeEventListener("visibilitychange", onFocus);
    }
  }, [load]);

  const approvalQueue: QueueItem[] = useMemo(() => {
    const q = dashboard?.approval_queue ?? [];
    return q.map((item: any) => ({
      courseId: item.course_id ?? item.id?.replace("marks_", "") ?? "",
      courseCode: (item.course ?? "").split(" - ")[0] ?? "",
      courseName: (item.course ?? "").split(" - ").slice(1).join(" - ") ?? "",
      examId: item.id ?? "",
      examName: item.exam ?? "Marks Submission",
      submittedAt: item.submitted,
      waitDays: Math.floor((item.wait_time_hours ?? 0) / 24),
      urgency: (item.urgency === "Critical" ? "Critical" : item.urgency === "High" ? "High" : "Normal") as QueueItem["urgency"],
    }));
  }, [dashboard]);

  const leadStats = useMemo(() => ({
    courseCount: dashboard?.statistics?.total_courses ?? 0,
    pendingApprovals: dashboard?.statistics?.pending_approvals ?? 0,
    level1COs: dashboard?.statistics?.level1_alerts ?? 0,
    remedialNeeded: dashboard?.statistics?.overdue_remedials ?? 0,
  }), [dashboard]);

  const coHealthRows = useMemo(() => {
    const table = dashboard?.co_health_table ?? [];
    return table.map((row: any) => {
      const [code = "", name = ""] = (row.course ?? "").split(" - ");
      const levels = (row.cos ?? []).map((c: any) => {
        if (c.level === "--" || c.level == null) return null;
        const lvl = c.level === "L1" ? 1 : c.level === "L2" ? 2 : 3;
        return { co: c.code, level: lvl, pct: c.percentage ?? 0 };
      });
      return {
        course: { id: row.course_id, code, name },
        levels,
      };
    });
  }, [dashboard]);

  const totalLevel1AcrossCourses = useMemo(
    () => coHealthRows.reduce((sum, row) => sum + row.levels.filter((l) => l && l.level === 1).length, 0),
    [coHealthRows],
  );

  const poSummary = useMemo(() => {
    const rows = dashboard?.po_summary ?? [];
    const poRows: [string, { pct: number }][] = rows.map((p: any) => [p.code, { pct: p.attainment_pct ?? 0 }]);
    const psoLines: string[] = [];
    const psoRaw = dashboard?.pso_summary;
    if (typeof psoRaw === "string" && psoRaw) psoLines.push(psoRaw);
    return { poRows, psoLines };
  }, [dashboard]);

  const recentActions = useMemo(() => {
    const list = dashboard?.recent_actions ?? [];
    return list.map((a: any, i: number) => ({
      id: String(a.index ?? i + 1),
      action: a.action ?? "",
      timestamp: a.timestamp ?? "",
    }));
  }, [dashboard]);

  if (loading) {
    return (
      <div className="flex flex-col gap-10 pb-32">
        <p className="text-white/60">Loading lead dashboard…</p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="flex flex-col gap-10 pb-32">
        <p className="text-alert">{error}</p>
      </div>
    );
  }

  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
      className="flex flex-col gap-10 pb-32"
    >
      {/* HEADER */}
      <motion.section
        variants={fadeSlideUp}
        className="flex flex-col gap-3 border-b border-white/10 pb-5"
      >
        <h1 className="text-xl md:text-2xl font-mono text-white/70 uppercase tracking-widest">
          {dashboard?.header?.title ?? `Course Lead Dashboard — ${dept} | AY ${activeAY}`}
        </h1>
        <p className="text-sm text-white/50 font-mono">
          {dashboard?.header?.status_summary ?? `${leadStats.courseCount} courses | ${leadStats.pendingApprovals} pending approval | ${leadStats.level1COs} Level 1 CO alerts | ${leadStats.remedialNeeded} remedial overdue`}
        </p>
      </motion.section>

      <div className="grid lg:grid-cols-3 gap-10">
        {/* LEFT: CO HEALTH & PO SUMMARY */}
        <div className="lg:col-span-2 flex flex-col gap-10">
          {/* CO HEALTH TABLE */}
          <motion.section variants={fadeSlideUp} className="space-y-3">
            <h2 className="text-sm font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
              <Layers className="w-4 h-4 text-brand" /> CO Health by Course
            </h2>
            <div className="overflow-x-auto border border-white/10">
              <table className="w-full border-collapse text-xs">
                <thead className="bg-white/[0.02]">
                  <tr>
                    <th className="px-4 py-2 text-left text-[9px] font-mono text-white/40 uppercase tracking-widest">
                      Course
                    </th>
                    {["CO1", "CO2", "CO3", "CO4", "CO5"].map((co) => (
                      <th
                        key={co}
                        className="px-3 py-2 text-center text-[9px] font-mono text-white/40 uppercase tracking-widest"
                      >
                        {co}
                      </th>
                    ))}
                    <th className="px-4 py-2 text-left text-[9px] font-mono text-white/40 uppercase tracking-widest">
                      Faculty
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {coHealthRows.map(({ course, levels }) => (
                    <tr
                      key={course.id}
                      className="border-t border-white/10 hover:bg-white/[0.02]"
                    >
                      <td className="px-4 py-2 font-mono text-xs text-white/60">
                        {course.code}
                      </td>
                      {["CO1", "CO2", "CO3", "CO4", "CO5"].map((coId) => {
                        const info = levels.find((l) => l?.co === coId);
                        if (!info) {
                          return (
                            <td
                              key={coId}
                              className="px-3 py-2 text-center text-white/20"
                            >
                              —
                            </td>
                          );
                        }
                        const lvl = info.level;
                        const label = lvl === 3 ? "L3" : lvl === 2 ? "L2" : "L1";
                        const cls =
                          lvl === 3
                            ? "text-attain"
                            : lvl === 2
                            ? "text-amber-400"
                            : "text-alert font-bold";
                        return (
                          <td
                            key={coId}
                            className="px-3 py-2 text-center font-mono"
                          >
                            <span className={cls}>{label}</span>
                          </td>
                        );
                      })}
                      <td className="px-4 py-2 text-xs text-white/50">
                        Lead: {user?.name}
                      </td>
                    </tr>
                  ))}
                  {coHealthRows.length === 0 && (
                    <tr>
                      <td
                        colSpan={7}
                        className="px-4 py-4 text-center text-xs text-white/30 italic"
                      >
                        CO attainment will appear once marks are approved for your
                        courses.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {totalLevel1AcrossCourses > 0 && (
              <p className="text-xs text-alert font-mono">
                {totalLevel1AcrossCourses} COs at Level 1 across{" "}
                {coHealthRows.length} courses require remedial action.
              </p>
            )}
          </motion.section>

          {/* PO / PSO SUMMARY */}
          <motion.section variants={fadeSlideUp} className="space-y-3">
            <h2 className="text-sm font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
              <Layers className="w-4 h-4 text-brand" /> PO Summary
            </h2>
            <div className="overflow-x-auto border border-white/10">
              <table className="w-full border-collapse text-xs">
                <thead className="bg-white/[0.02]">
                  <tr>
                    <th className="px-4 py-2 text-left text-[9px] font-mono text-white/40 uppercase tracking-widest">
                      PO Code
                    </th>
                    <th className="px-4 py-2 text-right text-[9px] font-mono text-white/40 uppercase tracking-widest">
                      Attainment%
                    </th>
                    <th className="px-4 py-2 text-left text-[9px] font-mono text-white/40 uppercase tracking-widest">
                      Level
                    </th>
                    <th className="px-4 py-2 text-left text-[9px] font-mono text-white/40 uppercase tracking-widest">
                      Target Met
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {poSummary.poRows.map(([po, v]) => {
                    const lvl = pctToLevel(v.pct);
                    const met =
                      lvl.level === 3 ? "Yes" : lvl.level === 2 ? "Partial" : "No";
                    return (
                      <tr key={po} className="border-t border-white/10">
                        <td className="px-4 py-2 font-mono text-xs text-white/60">
                          {po}
                        </td>
                        <td className="px-4 py-2 text-right text-xs text-white/70">
                          {v.pct}%
                        </td>
                        <td className="px-4 py-2 text-xs text-white/60">
                          {lvl.label}
                        </td>
                        <td className="px-4 py-2 text-xs text-white/60">
                          {met}
                        </td>
                      </tr>
                    );
                  })}
                  {poSummary.poRows.length === 0 && (
                    <tr>
                      <td
                        colSpan={4}
                        className="px-4 py-4 text-center text-xs text-white/30 italic"
                      >
                        PO/PSO attainment will appear once CO attainment is
                        available.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {poSummary.psoLines.length > 0 && (
              <p className="text-xs text-white/50">
                {poSummary.psoLines.join(" | ")}
              </p>
            )}
          </motion.section>
        </div>

        {/* RIGHT: APPROVAL QUEUE & RECENT ACTIONS */}
        <div className="flex flex-col gap-10">
          {/* APPROVAL QUEUE */}
          <motion.section variants={fadeSlideUp} className="space-y-3">
            <h2 className="text-sm font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
              <Clock className="w-4 h-4 text-brand" /> Approval Queue
            </h2>
            <div className="space-y-3">
              {approvalQueue.length === 0 ? (
                <div className="py-12 text-center border border-dashed border-white/15 text-xs text-white/30 italic">
                  <CheckCircle2 className="w-5 h-5 mx-auto mb-2 text-attain/60" />
                  No pending approvals.
                </div>
              ) : (
                approvalQueue.map((item) => {
                  const waitColor =
                    item.waitDays > 3
                      ? "text-alert"
                      : item.waitDays >= 1
                      ? "text-amber-400"
                      : "text-attain";
                  return (
                    <div
                      key={`${item.courseId}-${item.examId}`}
                      className="p-4 border border-white/10 bg-white/[0.01] hover:bg-white/[0.03] transition-colors flex flex-col gap-2"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs text-white font-medium">
                            {item.courseCode} · {item.examName}
                          </p>
                          <p className="text-[10px] text-white/40 font-mono">
                            Submitted:{" "}
                            {item.submittedAt
                              ? item.submittedAt.slice(0, 10)
                              : "—"}
                          </p>
                        </div>
                        <span
                          className={`text-[10px] font-mono uppercase ${waitColor}`}
                        >
                          {item.waitDays} day
                          {item.waitDays === 1 ? "" : "s"} waiting
                        </span>
                      </div>
                      <div className="flex items-center justify-between pt-1 border-t border-white/10">
                        <span className="text-[10px] font-mono text-white/40">
                          Urgency: {item.urgency}
                        </span>
                        <Link
                          href="/lead/marks-approval"
                          className="text-[10px] font-mono text-brand hover:text-white uppercase tracking-widest flex items-center gap-1"
                        >
                          Review
                          <FileText className="w-3 h-3" />
                        </Link>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </motion.section>

          {/* RECENT ACTIONS */}
          <motion.section variants={fadeSlideUp} className="space-y-3">
            <h2 className="text-sm font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
              <Users className="w-4 h-4 text-brand" /> Recent Actions
            </h2>
            <ol className="space-y-1 text-xs text-white/60">
              {recentActions.length === 0 ? (
                <li className="text-white/30 italic">
                  No recent actions recorded for your courses.
                </li>
              ) : (
                recentActions.map((e, idx) => (
                  <li key={e.id} className="flex items-start gap-2">
                    <span className="text-[10px] font-mono text-white/30 w-4">
                      {idx + 1}.
                    </span>
                    <span>
                      {e.action}
                      <span className="ml-1 text-white/30 text-[10px] font-mono">
                        — {e.timestamp}
                      </span>
                    </span>
                  </li>
                ))
              )}
            </ol>
          </motion.section>
        </div>
      </div>
    </motion.div>
  );
}

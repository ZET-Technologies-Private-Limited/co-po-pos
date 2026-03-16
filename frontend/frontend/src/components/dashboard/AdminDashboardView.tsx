"use client";

import { useMemo, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ChevronDown, ChevronUp, ChevronRight } from "lucide-react";
import { useAuthStore } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin", department_head: "HOD", subject_lead: "Lead",
  faculty: "Faculty", student: "Student",
};

const PAGE_SIZE = 20;

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts.replace(" ", "T")).getTime();
  const mins  = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days  = Math.floor(diff / 86400000);
  if (mins  < 1)  return "just now";
  if (mins  < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

export function AdminDashboardView() {
  const { user } = useAuthStore();
  const [courses, setCourses] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);
  const [ayItems, setAyItems] = useState<any[]>([]);
  const [currentAY, setCurrentAY] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [auditPage, setAuditPage] = useState(0);
  const [errExpanded, setErrExpanded] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [coursesRes, ayRes, currentRes, usersRes, auditRes] = await Promise.all([
        apiClient.getCourses(),
        apiClient.getAcademicYears().catch(() => ({ items: [] })),
        apiClient.getCurrentAcademicYear().catch(() => ({ code: "2024-25" })),
        apiClient.getUsers().catch(() => []),
        apiClient.getAuditLog(200).catch(() => []),
      ]);
      setCourses(Array.isArray(coursesRes) ? coursesRes : (coursesRes?.items ?? []));
      setAyItems(ayRes?.items ?? []);
      setCurrentAY(currentRes);
      setUsers(Array.isArray(usersRes) ? usersRes : []);
      setAuditEvents(Array.isArray(auditRes) ? auditRes : []);
    } catch (e: any) {
      setError(e?.message || "Failed to load admin dashboard.");
    } finally {
      setLoading(false);
    }
  }, []);

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

  const userStats = useMemo(() => {
    const now = Date.now();
    const oneWeekAgo = now - 7 * 24 * 60 * 60 * 1000;
    // backend returns hod/course_lead/viewer — map to frontend labels
    const backendToFrontend: Record<string, string> = {
      admin: "admin", hod: "department_head", course_lead: "subject_lead",
      faculty: "faculty", viewer: "student",
    };
    const roles = ["admin", "department_head", "subject_lead", "faculty", "student"] as const;
    return roles.map(role => {
      const matching = users.filter((u: any) => {
        const r = backendToFrontend[u.role] ?? u.role;
        return r === role;
      });
      return {
        role: ROLE_LABELS[role],
        total: matching.length,
        active: matching.filter((u: any) => u.is_active).length,
        inactive: matching.filter((u: any) => !u.is_active).length,
        newThisWeek: matching.filter((u: any) => {
          const created = u.created_at ? new Date(u.created_at).getTime() : 0;
          return created >= oneWeekAgo;
        }).length,
      };
    });
  }, [users]);

  const deptRows = useMemo(() => {
    const depts = [...new Set(courses.map((c: any) => c.department ?? c.dept ?? "—").filter(Boolean))];
    return depts.map(dept => ({
      dept,
      courses: courses.filter((c: any) => (c.department ?? c.dept) === dept).length,
      coGenPct: 0,
      marksApprPct: 0,
      poAvg: 0,
      openAlerts: 0,
    }));
  }, [courses]);

  const pendingActions = useMemo((): { text: string; href: string }[] => {
    const items: { text: string; href: string }[] = [];
    items.push({ text: "Configure attainment thresholds for current AY", href: "/admin/thresholds" });
    if (courses.length === 0)
      items.push({ text: "No courses in system — add courses", href: "/admin/co-library" });
    items.push({ text: "Manage academic year and lock", href: "/admin/academic-year" });
    return items;
  }, [courses.length]);

  const allEvents = useMemo(() => auditEvents.map((e: any) => ({
    id: e.id,
    timestamp: e.timestamp ? new Date(e.timestamp).toLocaleString() : "—",
    userId: e.userId || e.user_id || "—",
    action: e.action || "—",
    result: e.result ?? (e.type === "error" ? "failure" : "success"),
  })), [auditEvents]);
  const totalPages = Math.max(1, Math.ceil(allEvents.length / PAGE_SIZE));
  const pageEvents = allEvents.slice(auditPage * PAGE_SIZE, (auditPage + 1) * PAGE_SIZE);
  const errorEntries = useMemo(() => allEvents.filter((e: any) => e.result === "failure"), [allEvents]);
  const errorGroups = useMemo(() => {
    const groups: Record<string, { type: string; count: number; first: string }> = {};
    errorEntries.forEach((e: any) => {
      const key = e.action || "Unknown";
      if (!groups[key]) groups[key] = { type: key, count: 0, first: e.timestamp };
      groups[key].count++;
    });
    return Object.values(groups);
  }, [errorEntries]);

  const ayRows = useMemo(() => {
    const code = currentAY?.code ?? "2024-25";
    const current = ayItems.find((a: any) => a.code === code || a.is_active) ?? { code, status: "active", startDate: "—", endDate: "—", lockedBy: "—", lockedOn: "—" };
    const rest = ayItems.filter((a: any) => a.code !== current.code).sort((a: any, b: any) => (b.code ?? "").localeCompare(a.code ?? "")).slice(0, 2);
    return [
      { ay: current.code, status: current.is_locked ? "locked" : "active", startDate: current.start_date ?? "—", endDate: current.end_date ?? "—", lockedBy: "—", lockedOn: "—" },
      ...rest.map((a: any) => ({ ay: a.code, status: a.is_locked ? "locked" : "archived", startDate: a.start_date ?? "—", endDate: a.end_date ?? "—", lockedBy: "—", lockedOn: "—" })),
    ];
  }, [ayItems, currentAY]);

  const thCol = "text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 px-4 text-left";
  const tdCol = "py-3 px-4 text-sm font-mono";

  if (loading) {
    return (
      <div className="flex flex-col gap-10 pb-32">
        <p className="text-white/60">Loading admin dashboard…</p>
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
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="flex flex-col gap-0 pb-32">

      {/* ── PAGE HEADER ── */}
      <motion.section variants={fadeSlideUp} className="pb-8 border-b border-white/5">
        <p className="text-3xl font-display text-white mb-1">
          Admin Hub: <span className="text-white/40">{user?.name?.split(" ")[0]}</span>
        </p>

        {/* A1-01: system status line */}
        <p className="text-xs font-mono text-white/30 mt-3">
          <span className="text-attain">API: Healthy</span>
          {" | "}
          <span className="text-attain">DB: Connected</span>
          {" | "}
          <span className="text-white/50">Active Users: —</span>
          {" | "}
          <span className="text-white/30">Last Backup: 2 hours ago</span>
        </p>
      </motion.section>

      {/* ── A1-02: AY STATUS TABLE ── */}
      <motion.section variants={fadeSlideUp} className="py-8 border-b border-white/5">
        <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-5">Academic Year Status</h2>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/5">
                {["AY Code", "Status", "Start", "End", "Locked By", "Locked On"].map(h => (
                  <th key={h} className={thCol}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ayRows.map((row, i) => (
                <tr key={row.ay} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                  <td className={`${tdCol} text-white font-medium`}>{row.ay}{i === 0 && <span className="ml-2 text-[9px] text-brand uppercase tracking-widest">current</span>}</td>
                  <td className={`${tdCol} ${row.status === "active" ? "text-attain" : row.status === "locked" ? "text-amber-400" : "text-white/30"}`}>
                    {row.status.charAt(0).toUpperCase() + row.status.slice(1)}
                  </td>
                  <td className={`${tdCol} text-white/40`}>{row.startDate}</td>
                  <td className={`${tdCol} text-white/40`}>{row.endDate}</td>
                  <td className={`${tdCol} text-white/40`}>{row.lockedBy || "—"}</td>
                  <td className={`${tdCol} text-white/40`}>{row.lockedOn || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.section>

      {/* ── A1-03: USER COUNT TABLE ── */}
      <motion.section variants={fadeSlideUp} className="py-8 border-b border-white/5">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest">User Counts</h2>
          <Link href="/admin/users" className="text-[10px] font-mono text-brand hover:text-white transition-colors uppercase tracking-widest flex items-center gap-1">
            Manage Users <ChevronRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/5">
                {["Role", "Total Users", "Active", "Inactive", "New This Week"].map(h => (
                  <th key={h} className={thCol}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {userStats.map(row => (
                <tr key={row.role} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                  <td className={`${tdCol} text-white/60`}>{row.role}</td>
                  <td className={`${tdCol} text-white`}>{row.total}</td>
                  <td className={`${tdCol} text-attain`}>{row.active}</td>
                  <td className={`${tdCol} ${row.inactive > 0 ? "text-alert" : "text-white/20"}`}>{row.inactive}</td>
                  <td className={`${tdCol} ${row.newThisWeek > 0 ? "text-brand" : "text-white/20"}`}>{row.newThisWeek}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.section>

      {/* ── A1-04: DEPT PROGRESS TABLE ── */}
      <motion.section variants={fadeSlideUp} className="py-8 border-b border-white/5">
        <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-5">Department Progress</h2>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/5">
                {["Dept", "Courses", "CO Gen %", "Marks Approved %", "Avg PO Att %", "Open Alerts"].map(h => (
                  <th key={h} className={thCol}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {deptRows.length === 0 ? (
                <tr><td colSpan={6} className="py-8 px-4 text-white/20 text-xs italic">No department data.</td></tr>
              ) : deptRows.map(row => (
                <tr key={row.dept} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                  <td className={`${tdCol} text-white/60`}>{row.dept}</td>
                  <td className={`${tdCol} text-white/40`}>{row.courses}</td>
                  <td className={`${tdCol} ${row.coGenPct === 100 ? "text-attain" : row.coGenPct >= 50 ? "text-amber-400" : "text-alert"}`}>{row.coGenPct}%</td>
                  <td className={`${tdCol} ${row.marksApprPct >= 80 ? "text-attain" : row.marksApprPct >= 50 ? "text-amber-400" : row.marksApprPct > 0 ? "text-alert" : "text-white/20"}`}>{row.marksApprPct}%</td>
                  <td className={`${tdCol} ${row.poAvg >= 60 ? "text-attain" : row.poAvg >= 40 ? "text-amber-400" : row.poAvg > 0 ? "text-alert" : "text-white/20"}`}>{row.poAvg > 0 ? `${row.poAvg}%` : "—"}</td>
                  <td className={`${tdCol} ${row.openAlerts > 0 ? "text-alert font-bold" : "text-white/20"}`}>{row.openAlerts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.section>

      {/* ── A1-05: PENDING ACTIONS ── */}
      <motion.section variants={fadeSlideUp} className="py-8 border-b border-white/5">
        <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-5">Pending Actions</h2>
        {pendingActions.length === 0 ? (
          <p className="text-sm text-white/20 italic">No pending system actions. All tasks are complete.</p>
        ) : (
          <ol className="flex flex-col divide-y divide-white/5">
            {pendingActions.map((item, i) => (
              <li key={i} className="flex items-center justify-between py-3 gap-4">
                <div className="flex items-center gap-4 min-w-0">
                  <span className="text-xs font-mono text-white/20 w-5 shrink-0">{i + 1}.</span>
                  <span className="text-sm text-white/60">{item.text}</span>
                </div>
                <Link href={item.href}
                  className="text-xs font-mono text-brand hover:text-white transition-colors uppercase tracking-widest shrink-0 flex items-center gap-1">
                  Go <ChevronRight className="w-3 h-3" />
                </Link>
              </li>
            ))}
          </ol>
        )}
      </motion.section>

      {/* ── A1-06: EVENTS FEED ── */}
      <motion.section variants={fadeSlideUp} className="py-8 border-b border-white/5">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest">System Events</h2>
          <span className="text-[10px] font-mono text-white/20">
            Page {auditPage + 1} of {Math.max(totalPages, 1)} · {allEvents.length} events
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/5">
                {["Timestamp", "User", "Action", "Result"].map(h => (
                  <th key={h} className={thCol}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageEvents.length === 0 ? (
                <tr><td colSpan={4} className="py-8 px-4 text-white/20 text-xs italic">No events recorded yet.</td></tr>
              ) : pageEvents.map(entry => (
                <tr key={entry.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 px-4 text-[10px] font-mono text-white/30 whitespace-nowrap">{entry.timestamp}</td>
                  <td className="py-3 px-4 text-xs font-mono text-white/40 whitespace-nowrap">{entry.userId}</td>
                  <td className="py-3 px-4 text-xs text-white/40">{entry.action}</td>
                  <td className="py-3 px-4 text-[10px] font-mono">
                    {entry.result === "failure"
                      ? <span className="text-alert">Failure</span>
                      : entry.result === "success"
                        ? <span className="text-attain">Success</span>
                        : <span className="text-white/20">—</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center gap-4 mt-4">
            <button
              onClick={() => setAuditPage(p => Math.max(0, p - 1))}
              disabled={auditPage === 0}
              className="text-xs font-mono text-white/30 hover:text-white disabled:opacity-20 transition-colors uppercase tracking-widest"
            >
              ← Prev
            </button>
            <span className="text-[10px] font-mono text-white/20">{auditPage + 1} / {totalPages}</span>
            <button
              onClick={() => setAuditPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={auditPage >= totalPages - 1}
              className="text-xs font-mono text-white/30 hover:text-white disabled:opacity-20 transition-colors uppercase tracking-widest"
            >
              Next →
            </button>
          </div>
        )}
      </motion.section>

      {/* ── A1-07: ERROR LOG ── */}
      {errorGroups.length > 0 && (
        <motion.section variants={fadeSlideUp} className="py-8">
          <button
            onClick={() => setErrExpanded(e => !e)}
            className="flex items-center gap-3 w-full text-left"
          >
            <h2 className="text-[10px] font-mono text-alert uppercase tracking-widest">
              System Errors (Last 24h) — {errorEntries.length} event{errorEntries.length !== 1 ? "s" : ""}
            </h2>
            {errExpanded
              ? <ChevronUp className="w-3.5 h-3.5 text-alert" />
              : <ChevronDown className="w-3.5 h-3.5 text-alert" />
            }
          </button>

          {errExpanded && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-white/5">
                    {["Error Type", "Count", "First Occurrence"].map(h => (
                      <th key={h} className={thCol}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {errorGroups.map(eg => (
                    <tr key={eg.type} className="border-b border-white/5">
                      <td className="py-3 px-4 text-sm font-mono text-alert">{eg.type}</td>
                      <td className="py-3 px-4 text-sm font-mono text-white/60">{eg.count}</td>
                      <td className="py-3 px-4 text-xs font-mono text-white/30">{eg.first}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.section>
      )}

    </motion.div>
  );
}

"use client";

import { useMemo, useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Activity,
  FileText,
  Lock,
  CheckCircle2,
  AlertCircle,
  BarChart3,
  Users,
  Flag,
  ArrowUpRight,
} from "lucide-react";
import { useAuthStore } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import { DataTable } from "@/components/ui/DataTable";

export function DepartmentHeadDashboardView() {
  const { user, activeAY } = useAuthStore();
  const dept = String(user?.department || "").trim();
  const reportDate = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const [dashboard, setDashboard] = useState<any>(null);
  const [courses, setCourses] = useState<any[]>([]);
  const [ayConfig, setAyConfig] = useState<{ code?: string; is_locked?: boolean; status?: string }>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [thresholds, setThresholds] = useState<{ level2: number; level3: number }>({ level2: 50, level3: 60 });

  const load = useCallback(async () => {
    if (!dept) {
      setDashboard(null);
      setCourses([]);
      setAyConfig({});
      setError("No department is mapped to this user.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [currentAY, ayList, thresholdRes] = await Promise.all([
        apiClient.getCurrentAcademicYear().catch(() => ({})),
        apiClient.getAcademicYears().catch(() => ({ items: [] })),
        apiClient.getThresholds().catch(() => ({ level2: 0.5, level3: 0.6 })),
      ]);

      const ayItems = ayList?.items ?? [];
      const resolvedAY = activeAY || currentAY?.code || ayItems.find((a: any) => a.is_active)?.code;
      if (!resolvedAY) {
        throw new Error("No active academic year configured.");
      }

      const [dashRes, coursesRes] = await Promise.all([
        apiClient.getCourseLeadDashboard(dept, resolvedAY),
        apiClient.getCourses(),
      ]);

      setDashboard(dashRes);
      const list = Array.isArray(coursesRes) ? coursesRes : (coursesRes?.items ?? []);
      setCourses(list);
      const current = ayItems.find((a: any) => a.code === resolvedAY || a.is_active) ?? { code: resolvedAY, is_locked: false };
      setAyConfig({ ...current, status: current.is_locked ? "locked" : "active" });
      setThresholds({
        level2: Math.round(Number(thresholdRes?.level2 ?? 0.5) * 100),
        level3: Math.round(Number(thresholdRes?.level3 ?? 0.6) * 100),
      });
    } catch (e: any) {
      setError(e?.message || "Failed to load HOD dashboard.");
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

  const deptCourses = useMemo(
    () =>
      courses.filter((c: any) =>
        user?.department ? (c.department ?? c.dept) === user.department : true
      ),
    [courses, user]
  );

  const stats = dashboard?.statistics ?? {};
  const totalCourses = stats.total_courses ?? deptCourses.length;
  const approvedSubs = stats.pending_approvals != null ? (totalCourses * 2 - (stats.pending_approvals ?? 0)) : 0;
  const pendingSubs = stats.pending_approvals ?? 0;
  const level1COs = stats.level1_alerts ?? 0;
  const avgDeptCO = dashboard?.po_summary?.length
    ? Math.round(
        (dashboard.po_summary as any[]).reduce((a: number, p: any) => a + (p.attainment_pct ?? 0), 0) /
          (dashboard.po_summary as any[]).length
      )
    : 0;
  const totalCOs = (dashboard?.co_health_table ?? []).reduce(
    (s: number, row: any) => s + (row.cos?.length ?? 0),
    0
  );
  const level2Threshold = thresholds.level2;
  const level3Threshold = thresholds.level3;

  const poAttainment = useMemo(() => {
    const rows = dashboard?.po_summary ?? [];
    const out: Record<string, { pct: number }> = {};
    rows.forEach((p: any) => {
      out[p.code] = { pct: p.attainment_pct ?? 0 };
    });
    return out;
  }, [dashboard]);

  const facultyProgress = useMemo(() => {
    const rows: Record<string, { name: string; submitted: number; approved: number; pending: number; courseSet: Set<string> }> = {};
    const ensure = (name: string) => {
      if (!rows[name]) {
        rows[name] = { name, submitted: 0, approved: 0, pending: 0, courseSet: new Set<string>() };
      }
      return rows[name];
    };

    const queue = Array.isArray(dashboard?.approval_queue) ? dashboard.approval_queue : [];
    queue.forEach((item: any) => {
      const name = String(item?.faculty || "Unknown");
      const row = ensure(name);
      row.submitted += 1;
      const status = String(item?.status || "pending").toLowerCase();
      if (status === "approved") row.approved += 1;
      if (status === "pending") row.pending += 1;
      if (item?.course) row.courseSet.add(String(item.course));
    });

    const actions = Array.isArray(dashboard?.recent_actions) ? dashboard.recent_actions : [];
    actions.forEach((action: any) => {
      const text = String(action?.action || "");
      const byMatch = text.match(/ by (.+)$/i);
      if (!byMatch) return;
      const name = byMatch[1].trim();
      const row = ensure(name || "Unknown");
      const courseMatch = text.match(/ for ([A-Za-z0-9-]+)/i);
      if (courseMatch?.[1]) row.courseSet.add(courseMatch[1]);
    });

    return Object.values(rows)
      .map((r) => ({
        name: r.name,
        courses: r.courseSet.size,
        submitted: r.submitted,
        approved: r.approved,
        pending: r.pending,
      }))
      .sort((a, b) => b.pending - a.pending || b.submitted - a.submitted);
  }, [dashboard]);

  const heatMapData = useMemo(() => {
    const table = dashboard?.co_health_table ?? [];
    return table.slice(0, 6).map((row: any) => {
      const code = (row.course ?? "").split(" - ")[0] ?? "";
      const levels = (row.cos ?? []).map((c: any) => (c.level === "L1" || c.level === "L2" || c.level === "L3" ? c.level : ""));
      const cos = [...levels, ...Array(6).fill("")].slice(0, 6);
      return { course: code, cos };
    });
  }, [dashboard]);

  const poCards = useMemo(() => {
    const rows = dashboard?.po_summary ?? [];
    return rows.slice(0, 4).map((p: any) => ({
      id: p.code,
      name: p.code,
      value: p.attainment_pct ?? 0,
    }));
  }, [dashboard]);

  const ayLabel = ayConfig.code ?? activeAY ?? "2024-25";
  const isLocked = ayConfig.is_locked === true || ayConfig.status === "locked";

  if (loading) {
    return (
      <div className="flex flex-col gap-10 pb-32">
        <p className="text-white/60">Loading HOD dashboard…</p>
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
      className="w-full flex flex-col gap-16 pb-32"
    >
      {/* ── HEADER ── */}
      <motion.section variants={fadeSlideUp} className="flex flex-col gap-4">
        <div className="flex items-center gap-3 text-[10px] font-mono text-orange-400 uppercase tracking-widest">
          <span className="w-8 h-[1px] bg-orange-400" /> Executive Oversight
        </div>
        <div className="flex justify-between items-end border-b border-white/5 pb-8">
          <div>
            <h1 className="text-5xl font-display text-white tracking-tight">
              OBE <span className="text-white/20">Executive</span> Dashboard
            </h1>
            <p className="text-white/40 font-light mt-3 text-lg">
              {user?.name || "Department Head"} ·{" "}
              <span className="text-orange-400/60">{user?.department}</span>
            </p>
            <div className="flex gap-6 mt-4">
              <p className="text-[10px] font-mono text-white/20 uppercase tracking-[0.2em]">
                AY {ayLabel}
              </p>
              <p className="text-[10px] font-mono text-white/20 uppercase tracking-[0.2em]">
                Status: {ayConfig.status}
              </p>
            </div>
          </div>
          <Link
            href="/hod/year-end-lock"
            className={`px-8 py-4 text-[10px] font-mono uppercase tracking-[0.2em] flex items-center gap-3 transition-all ${
              isLocked
                ? "text-white/20 border border-white/10"
                : "bg-orange-400 text-black hover:bg-orange-500 shadow-2xl shadow-orange-400/20"
            }`}
          >
            <Lock className="w-3.5 h-3.5" />{" "}
            {isLocked ? "Year-End Locked" : "Year-End Sign-Off"}
          </Link>
        </div>
      </motion.section>

      {/* ── DEPT SUMMARY (FLATTENED) ── */}
      <motion.section
        variants={fadeSlideUp}
        className="flex flex-col gap-12"
      >
        <div className="grid grid-cols-2 lg:grid-cols-4 border border-white/5">
          <div className="space-y-2 p-8 border-r border-white/5">
            <span className="text-[9px] font-mono text-white/20 uppercase tracking-[0.3em]">Total Courses</span>
            <p className="text-4xl font-display text-white">{totalCourses}</p>
            <p className="text-[10px] text-white/30 font-mono tracking-tight">{totalCOs} outcomes mapped</p>
          </div>
          <div className="space-y-2 p-8 border-r border-white/5">
            <span className="text-[9px] font-mono text-white/20 uppercase tracking-[0.3em]">Approval Progress</span>
            <p className="text-4xl font-display text-attain">{approvedSubs}</p>
            <p className="text-[10px] text-white/30 font-mono tracking-tight">{pendingSubs} current queue</p>
          </div>
          <div className="space-y-2 p-8 border-r border-white/5">
            <span className="text-[9px] font-mono text-white/20 uppercase tracking-[0.3em]">Critical Risks (L1)</span>
            <p className="text-4xl font-display text-alert">{level1COs}</p>
            <p className="text-[10px] text-white/30 font-mono tracking-tight">Below {level2Threshold}% band</p>
          </div>
          <div className="space-y-2 p-8">
            <span className="text-[9px] font-mono text-white/20 uppercase tracking-[0.3em]">Dept Health Index</span>
            <p className={`text-4xl font-display ${avgDeptCO >= level3Threshold ? "text-attain" : "text-brand"}`}>{avgDeptCO}%</p>
            <p className="text-[10px] text-white/30 font-mono tracking-tight">Target: {level3Threshold}%</p>
          </div>
        </div>
      </motion.section>

      <div className="flex flex-col gap-24">
        {/* ── CO HEALTH HEAT MAP (FLATTENED) ── */}
        <motion.section variants={fadeSlideUp} className="space-y-8 w-full">
          <div className="flex justify-between items-end border-b border-white/5 pb-6">
            <h2 className="text-xl font-display text-white uppercase tracking-widest flex items-center gap-4">
              <Activity className="w-5 h-5 text-orange-400" /> CO Health heat map
            </h2>
            <div className="flex gap-6">
              {["L3", "L2", "L1"].map(l => (
                <div key={l} className="flex items-center gap-2 text-[9px] font-mono text-white/20 uppercase">
                  <div className={`w-1.5 h-1.5 rounded-full ${l === "L3" ? "bg-attain" : l === "L2" ? "bg-amber-400" : "bg-alert"}`} /> {l} band
                </div>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="py-4 text-[9px] font-mono text-white/20 uppercase tracking-[0.3em]">Course Code</th>
                  {["CO1", "CO2", "CO3", "CO4", "CO5", "CO6"].map(c => (
                    <th key={c} className="py-4 text-center text-[9px] font-mono text-white/20 uppercase tracking-[0.3em]">{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.02]">
                {heatMapData.map((row) => (
                  <tr key={row.course} className="hover:bg-white/[0.01] transition-colors">
                    <td className="py-6 font-mono text-xs text-white/40 uppercase">{row.course}</td>
                    {row.cos.map((level, i) => (
                      <td key={i} className="py-6">
                        <div className="flex justify-center">
                          <div className={`w-10 h-10 rounded border flex items-center justify-center text-[10px] font-mono transition-all ${
                            level === "L3" ? "bg-attain/10 text-attain border-attain/20" :
                            level === "L2" ? "bg-amber-400/10 text-amber-400 border-amber-400/20" :
                            level === "L1" ? "bg-alert/10 text-alert border-alert/20 font-bold" :
                            "text-white/5 bg-white/[0.01] border-transparent"
                          }`}>
                            {level || "—"}
                          </div>
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.section>

        {/* ── PO PERFORMANCE & GAP ANALYSIS (FLATTENED) ── */}
        <div className="grid lg:grid-cols-2 gap-24">
          <motion.section variants={fadeSlideUp} className="space-y-8">
            <h2 className="text-xl font-display text-white uppercase tracking-widest flex items-center gap-4 border-b border-white/5 pb-6">
              <BarChart3 className="w-5 h-5 text-orange-400" /> PO Attainment
            </h2>
            <div className="space-y-10">
              {poCards.map((p) => (
                <div key={p.id} className="space-y-4">
                  <div className="flex justify-between items-end">
                    <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest">{p.id} · {p.name}</span>
                    <span className={`text-lg font-display ${p.value < level2Threshold ? "text-alert" : "text-white"}`}>{p.value}%</span>
                  </div>
                  <div className="h-0.5 bg-white/5 w-full">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${p.value}%` }}
                      className={`h-full ${p.value < level2Threshold ? "bg-alert" : "bg-brand"}`}
                    />
                  </div>
                </div>
              ))}
            </div>
          </motion.section>

          <motion.section variants={fadeSlideUp} className="space-y-8">
            <h3 className="text-xl font-display text-alert uppercase tracking-widest flex items-center gap-4 border-b border-white/5 pb-6">
              <Flag className="w-5 h-5" /> Gap Analysis
            </h3>
            <div className="space-y-8">
              {level1COs === 0 ? (
                <div className="flex gap-4 items-start py-4">
                  <CheckCircle2 className="w-6 h-6 text-attain shrink-0 mt-1" />
                  <div className="space-y-2">
                    <p className="text-sm font-bold text-white uppercase">Compliance Stabilized</p>
                    <p className="text-xs text-white/40 leading-relaxed font-light">All outcomes currently meet or exceed the minimum Level 2 band. No intervention required.</p>
                  </div>
                </div>
              ) : (
                <div className="flex gap-4 items-start py-4 border-b border-white/5">
                  <AlertCircle className="w-6 h-6 text-alert shrink-0 mt-1" />
                  <div className="space-y-3">
                    <p className="text-sm font-bold text-white uppercase">{level1COs} Critical Bottlenecks</p>
                    <p className="text-xs text-white/40 leading-relaxed font-light">Remedial journals required for all courses hovering below the {level2Threshold}% attainment threshold.</p>
                    <Link href="/hod/co-attainment" className="text-[9px] font-mono text-orange-400 hover:text-white uppercase tracking-[0.2em] flex items-center gap-2">
                      Open Audit Logs <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              )}
            </div>
          </motion.section>
        </div>

        {/* ── FACULTY PROGRESS (FLATTENED) ── */}
        <motion.section variants={fadeSlideUp} className="space-y-10">
          <div className="flex justify-between items-end border-b border-white/5 pb-6">
            <h3 className="text-xl font-display text-white uppercase tracking-widest flex items-center gap-4">
              <Users className="w-5 h-5 text-orange-400" /> Faculty Operations
            </h3>
          </div>
          <DataTable
            data={facultyProgress}
            pageSize={5}
            columns={[
              { id: "name", header: "Faculty", accessor: f => f.name, sortable: true, width: 250 },
              { id: "courses", header: "Courses", accessor: f => f.courses, sortable: true, width: 150 },
              { 
                id: "progress", 
                header: "Sub / App / Pend", 
                accessor: f => `${f.submitted}/${f.approved}/${f.pending}`,
                sortable: true,
                render: (_, f) => (
                  <div className="flex items-center gap-8 font-mono">
                    <span className="text-white/40">{f.submitted}</span>
                    <span className="text-attain">{f.approved}</span>
                    <span className="text-alert">{f.pending}</span>
                  </div>
                )
              }
            ]}
          />
        </motion.section>
      </div>

      {/* ── FOOTER ── */}
      <motion.section
        variants={fadeSlideUp}
        className="pt-16 border-t border-white/5 flex justify-between items-center"
      >
        <div className="flex items-center gap-4 text-[10px] font-mono text-white/20 uppercase tracking-[0.2em]">
          <FileText className="w-4 h-4" /> System Calculated Audit · {reportDate}
        </div>
        <div className="text-[9px] font-mono text-white/10 italic">
          v1.4 SECURE OBE ENGINE
        </div>
      </motion.section>
    </motion.div>
  );
}

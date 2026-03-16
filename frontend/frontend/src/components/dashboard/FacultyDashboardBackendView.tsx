"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Search,
  Minus,
  ArrowUp,
  ArrowDown,
  ChevronDown,
  ChevronUp,
  ArrowUpRight,
  AlertCircle,
  PlusCircle,
  CheckCircle2,
  Circle,
  BookOpen,
  ClipboardList,
  UploadCloud,
  BarChart2,
  Lock,
  Users,
  GitBranch,
} from "lucide-react";
import { useAuthStore } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";

type SortKey =
  | "urgency"
  | "course_code"
  | "course_name"
  | "semester"
  | "enrolled_students"
  | "co_status"
  | "marks_status";

type SortDir = "asc" | "desc";

interface FacultyDashboardPayload {
  header: {
    welcome_line: string;
    today_full_date: string;
    status_summary_line: string;
    ay_context_line: string;
    ay_context_color: string;
    ay_near_lock: boolean;
  };
  courses_table: {
    rows: any[];
    sort: { by: string; direction: SortDir };
    search: { query: string; matches: number };
  };
  pending_actions: {
    items: any[];
    completed_items: any[];
    show_completed: boolean;
    completed_hidden_count: number;
    empty_state: string | null;
  };
  co_attainment_summary: {
    rows: any[];
    level1_alert_line: string | null;
  };
  recent_activity: {
    items: any[];
    view_all_link: string;
  };
  academic_year: string;
}

export function FacultyDashboardBackendView() {
  const { activeRole, activeAY } = useAuthStore();

  const [data, setData] = useState<FacultyDashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<SortKey>("urgency");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [showCompleted, setShowCompleted] = useState(false);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const allowedRoles = ["faculty", "course_lead", "subject_lead"];

  useEffect(() => {
    if (!activeRole || !allowedRoles.includes(activeRole)) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await apiClient.getFacultyDashboard({
          ay_code: activeAY,
          search: search || undefined,
          sort_by: sortBy,
          sort_dir: sortDir,
          show_completed: showCompleted,
        });
        if (!cancelled) {
          setData(res);
        }
      } catch (e: any) {
        if (!cancelled) {
          setError(
            typeof e?.message === "string"
              ? e.message
              : "Failed to load faculty dashboard."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [activeRole, activeAY, search, sortBy, sortDir, showCompleted]);

  const courses = data?.courses_table.rows ?? [];

  const pendingActions = useMemo(() => {
    if (!data) return [];
    const items = data.pending_actions.items || [];
    const completed = data.pending_actions.completed_items || [];
    return showCompleted ? [...items, ...completed] : items;
  }, [data, showCompleted]);

  const coSummaryRows = data?.co_attainment_summary.rows ?? [];
  const recentActivity = data?.recent_activity.items ?? [];

  const dashboardStats = useMemo(() => {
    const coursesWithGeneratedCOs = courses.filter(
      (row: any) =>
        row.co_pending_count === 0 ||
        (row.co_status || "").toLowerCase().includes("generated")
    ).length;

    const coursesWithApprovedMarks = courses.filter((row: any) =>
      (row.marks_status || "").toLowerCase().includes("approved")
    ).length;

    const coursesNeedingAttention = courses.filter((row: any) => {
      const marks = (row.marks_status || "").toLowerCase();
      const coDone =
        row.co_pending_count === 0 &&
        (row.co_status || "").toLowerCase().includes("generated");
      const marksDone = marks.includes("approved");
      return !(coDone && marksDone);
    }).length;

    return {
      totalCourses: courses.length,
      pendingActions: pendingActions.length,
      coursesWithGeneratedCOs,
      coursesWithApprovedMarks,
      coursesNeedingAttention,
    };
  }, [courses, pendingActions]);

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortBy !== col) return <Minus className="w-3 h-3 text-white/20" />;
    return sortDir === "asc" ? (
      <ArrowUp className="w-3 h-3 text-brand" />
    ) : (
      <ArrowDown className="w-3 h-3 text-brand" />
    );
  };

  const handleSort = (col: SortKey) => {
    if (sortBy === col) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortBy(col); setSortDir("desc"); }
  };

  const thCol =
    "text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 px-4 text-left cursor-pointer hover:text-white transition-colors select-none";
  const tdCol = "py-3 px-4 text-sm align-top";

  // Workflow step derivation per course row
  function getWorkflowSteps(row: any) {
    const cosDone = row.co_pending_count === 0 && (row.co_status || "").includes("Generated");
    const examsConfigured = Array.isArray(row.marks_status_details) && row.marks_status_details.length > 0;
    const marksStatus = (row.marks_status || "").toLowerCase();
    const marksUploaded = marksStatus.includes("approved") || marksStatus.includes("pending approval") || marksStatus.includes("submitted");
    const attainmentDone = marksStatus.includes("approved");
    return [
      {
        label: "CO Generation",
        done: cosDone,
        icon: BookOpen,
        link: `/faculty/course/${row.course_id}/co-generation`,
      },
      {
        label: "Exam Config",
        done: examsConfigured,
        icon: ClipboardList,
        link: `/faculty/course/${row.course_id}/exam-config`,
      },
      {
        label: "Marks Upload",
        done: marksUploaded,
        icon: UploadCloud,
        link: `/faculty/course/${row.course_id}/marks`,
      },
      {
        label: "Attainment",
        done: attainmentDone,
        icon: BarChart2,
        link: `/faculty/course/${row.course_id}/co-attainment`,
      },
    ];
  }

  if (!activeRole || !["faculty", "course_lead", "subject_lead"].includes(activeRole)) {
    return (
      <div className="py-16 text-center text-white/40 text-sm font-mono">
        Faculty dashboard is not available for your current role.
      </div>
    );
  }

  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
      className="flex flex-col gap-0 pb-32"
    >
      {/* Header */}
      <motion.section
        variants={fadeSlideUp}
        className="pb-10 border-b border-white/5"
      >
        <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-5">
          <div>
            <p className="text-3xl font-display text-white mb-1">
              {data?.header.welcome_line || "Welcome, Faculty"}
            </p>
            <p className="text-sm text-white/30 font-mono mb-5">
              {data?.header.today_full_date}
            </p>

            <p className="text-sm text-white/50 font-mono mb-3">
              {data?.header.status_summary_line}
            </p>
            <p className="text-xs font-mono text-white/25">
              {data?.header.ay_context_line}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/faculty/course/new"
              className="inline-flex items-center gap-2 px-4 py-2 border border-brand/40 text-brand hover:text-white hover:border-white/40 transition-colors text-xs font-mono uppercase tracking-widest"
            >
              <PlusCircle className="w-3.5 h-3.5" /> Create Course
            </Link>
            <Link
              href="/reports"
              className="inline-flex items-center gap-2 px-4 py-2 border border-white/20 text-white/60 hover:text-white hover:border-white/40 transition-colors text-xs font-mono uppercase tracking-widest"
            >
              <BarChart2 className="w-3.5 h-3.5" /> View Reports
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 mt-7">
          <div className="border border-white/10 bg-white/[0.02] px-4 py-3">
            <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-2">Total Courses</p>
            <p className="text-xl font-display text-white">{dashboardStats.totalCourses}</p>
          </div>
          <div className="border border-white/10 bg-white/[0.02] px-4 py-3">
            <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-2">Pending Tasks</p>
            <p className="text-xl font-display text-alert">{dashboardStats.pendingActions}</p>
          </div>
          <div className="border border-white/10 bg-white/[0.02] px-4 py-3">
            <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-2">CO Ready Courses</p>
            <p className="text-xl font-display text-attain">{dashboardStats.coursesWithGeneratedCOs}</p>
          </div>
          <div className="border border-white/10 bg-white/[0.02] px-4 py-3">
            <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-2">Need Attention</p>
            <p className="text-xl font-display text-amber-400">{dashboardStats.coursesNeedingAttention}</p>
          </div>
        </div>
      </motion.section>

      {/* Error / loading */}
      {error && (
        <div className="py-6 text-center text-red-400 text-sm font-mono border-b border-white/10">
          {error}
        </div>
      )}
      {loading && (
        <div className="py-6 text-center text-white/30 text-sm font-mono border-b border-white/10">
          Loading dashboard…
        </div>
      )}

      {/* Courses table */}
      <motion.section
        variants={fadeSlideUp}
        className="py-8 border-b border-white/5"
      >
        <div className="flex flex-col gap-3 mb-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-6">
              <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest">
                Courses Summary
              </h2>
              <Link
                href="/faculty/course/new"
                className="flex items-center gap-1.5 text-xs font-mono text-brand hover:text-white transition-colors uppercase tracking-widest"
              >
                <PlusCircle className="w-3 h-3" /> New Course
              </Link>
            </div>
            <div className="flex items-center gap-2 border-b border-white/10 pb-1">
              <Search className="w-3.5 h-3.5 text-white/30" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by code or name..."
                className="bg-transparent text-white text-sm placeholder-white/20 outline-none w-48"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono uppercase tracking-widest">
            <p className="text-white/25">Click a course row to expand its workflow and exam status.</p>
            <p className="text-white/35">
              {dashboardStats.totalCourses} course{dashboardStats.totalCourses === 1 ? "" : "s"} in view
            </p>
          </div>
        </div>

        <div className="border border-white/10 bg-white/[0.015]">
          <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/5">
                <th className={thCol} onClick={() => handleSort("course_code")}>
                  <span className="flex items-center gap-1">
                    Code <SortIcon col="course_code" />
                  </span>
                </th>
                <th className={thCol} onClick={() => handleSort("course_name")}>
                  <span className="flex items-center gap-1">
                    Course Name <SortIcon col="course_name" />
                  </span>
                </th>
                <th className={thCol} onClick={() => handleSort("semester")}>
                  <span className="flex items-center gap-1">
                    Sem <SortIcon col="semester" />
                  </span>
                </th>
                <th className={thCol} onClick={() => handleSort("enrolled_students")}>
                  <span className="flex items-center gap-1">
                    Students <SortIcon col="enrolled_students" />
                  </span>
                </th>
                <th className={thCol} onClick={() => handleSort("co_status")}>
                  <span className="flex items-center gap-1">
                    CO Status <SortIcon col="co_status" />
                  </span>
                </th>
                <th className={thCol} onClick={() => handleSort("marks_status")}>
                  <span className="flex items-center gap-1">
                    Marks <SortIcon col="marks_status" />
                  </span>
                </th>
                <th className={thCol}>Workflow</th>
                <th className={thCol}>Action</th>
              </tr>
            </thead>
            <tbody>
              {courses.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-10 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <p className="text-sm text-white/20 italic">
                        {loading ? "Loading…" : "No courses found yet."}
                      </p>
                      {!loading && (
                        <Link
                          href="/faculty/course/new"
                          className="inline-flex items-center gap-2 px-4 py-2 border border-brand/40 text-brand hover:text-white hover:border-white/40 transition-colors text-xs font-mono uppercase tracking-widest"
                        >
                          <PlusCircle className="w-3.5 h-3.5" /> Create First Course
                        </Link>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                courses.map((row: any) => {
                  const id = row.course_id;
                  const isExpanded = expandedRows.has(id);
                  const toggleRow = () => {
                    const next = new Set(expandedRows);
                    if (next.has(id)) next.delete(id);
                    else next.add(id);
                    setExpandedRows(next);
                  };
                  const steps = getWorkflowSteps(row);
                  const completedSteps = steps.filter((s) => s.done).length;

                  return (
                    <React.Fragment key={id}>
                      <tr
                        onClick={toggleRow}
                        className="border-b border-white/5 hover:bg-white/[0.02] cursor-pointer transition-colors"
                      >
                        <td className={`${tdCol} font-mono text-white/50 text-xs`}>
                          {row.course_code}
                        </td>
                        <td className={`${tdCol} text-white font-light`}>
                          {row.course_name}
                        </td>
                        <td className={`${tdCol} text-white/40 font-mono text-xs text-center`}>
                          {row.semester}
                        </td>
                        <td className={`${tdCol} text-white/40 font-mono text-xs text-center`}>
                          {row.enrolled_students}
                        </td>
                        <td className={tdCol}>
                          <span className={`text-xs font-mono ${
                            (row.co_pending_count === 0 && (row.co_status || "").includes("Generated"))
                              ? "text-attain" : "text-alert"
                          }`}>
                            {row.co_status}
                          </span>
                        </td>
                        <td className={tdCol}>
                          <span className={`text-xs font-mono ${
                            (row.marks_status || "").toLowerCase().includes("approved")
                              ? "text-attain"
                              : (row.marks_status || "").toLowerCase().includes("not configured")
                              ? "text-alert"
                              : "text-amber-400"
                          }`}>
                            {row.marks_status}
                          </span>
                        </td>
                        {/* Mini workflow progress */}
                        <td className={tdCol}>
                          <div className="flex items-center gap-1.5">
                            {steps.map((step, i) => (
                              <span
                                key={step.label}
                                title={`${step.label}: ${step.done ? "Done" : "Pending"}`}
                                className={`w-2 h-2 rounded-full ${step.done ? "bg-attain" : "bg-white/15"}`}
                              />
                            ))}
                            <span className="text-[10px] font-mono text-white/30 ml-1">
                              {completedSteps}/{steps.length}
                            </span>
                          </div>
                        </td>
                        <td className={tdCol}>
                          <div className="flex items-center gap-2 flex-wrap">
                            {(row.actions || []).slice(0, 2).map((a: any, i: number) => (
                              <span key={`${id}-${a.label}`} className="flex items-center gap-2">
                                {i > 0 && <span className="text-white/10 text-xs">|</span>}
                                <Link
                                  href={a.link}
                                  onClick={(e) => e.stopPropagation()}
                                  className="text-xs font-mono text-brand hover:text-white transition-colors uppercase tracking-widest"
                                >
                                  {a.label}
                                </Link>
                              </span>
                            ))}
                            <button onClick={(e) => { e.stopPropagation(); toggleRow(); }} className="ml-1">
                              {isExpanded
                                ? <ChevronUp className="w-3.5 h-3.5 text-white/20" />
                                : <ChevronDown className="w-3.5 h-3.5 text-white/20" />}
                            </button>
                          </div>
                        </td>
                      </tr>

                      {/* Expanded workflow details */}
                      {isExpanded && (
                        <tr className="bg-white/[0.015]">
                          <td colSpan={8} className="px-6 py-5">
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: "auto" }}
                              exit={{ opacity: 0, height: 0 }}
                              className="overflow-hidden"
                            >
                              {/* Workflow Stepper */}
                              <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">
                                OBE Workflow — {row.course_code}
                              </p>
                              <div className="flex flex-wrap gap-0 mb-6">
                                {steps.map((step, idx) => {
                                  const StepIcon = step.icon;
                                  return (
                                    <div key={step.label} className="flex items-center">
                                      <Link
                                        href={step.link}
                                        onClick={(e) => e.stopPropagation()}
                                        className={`flex items-center gap-2 px-4 py-2.5 border transition-colors group ${
                                          step.done
                                            ? "border-attain/40 text-attain hover:border-attain"
                                            : "border-white/10 text-white/40 hover:border-white/30 hover:text-white/70"
                                        }`}
                                      >
                                        {step.done
                                          ? <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                                          : <Circle className="w-3.5 h-3.5 shrink-0" />}
                                        <StepIcon className="w-3.5 h-3.5 shrink-0" />
                                        <span className="text-[10px] font-mono uppercase tracking-widest whitespace-nowrap">
                                          {idx + 1}. {step.label}
                                        </span>
                                        <ArrowUpRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                                      </Link>
                                      {idx < steps.length - 1 && (
                                        <span className="w-6 h-[1px] bg-white/10 shrink-0" />
                                      )}
                                    </div>
                                  );
                                })}
                              </div>

                              {/* Exam status details */}
                              {(row.marks_status_details || []).length > 0 && (
                                <>
                                  <p className="text-[10px] font-mono text-white/20 uppercase tracking-widest mb-3">
                                    Exam Statuses
                                  </p>
                                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {(row.marks_status_details || []).map((m: any) => (
                                      <div
                                        key={`${m.exam_id || m.assessment}`}
                                        className="flex items-center justify-between px-4 py-3 border border-white/5"
                                      >
                                        <div>
                                          <p className="text-xs text-white font-light">
                                            {m.exam_name || m.assessment}
                                          </p>
                                          <p className="text-[10px] font-mono text-white/30 mt-0.5">
                                            {m.label}
                                          </p>
                                        </div>
                                        <span className="text-[10px] font-mono text-white/40">
                                          {m.due_date_label || ""}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </>
                              )}
                            </motion.div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
          </div>
        </div>
      </motion.section>

      {/* Pending actions */}
      <motion.section
        variants={fadeSlideUp}
        className="py-8 border-b border-white/5"
      >
        <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-5">
          Pending Actions
        </h2>
        <p className="text-xs text-white/30 mb-4">
          Prioritize these tasks first to complete the OBE cycle for each course.
        </p>

        {pendingActions.length === 0 ? (
          <div className="flex items-center gap-3 py-4">
            <AlertCircle className="w-4 h-4 text-attain" />
            <p className="text-sm text-white/40 italic">
              {data?.pending_actions.empty_state ||
                "No pending actions. All tasks are complete."}
            </p>
          </div>
        ) : (
          <ol className="flex flex-col gap-0 divide-y divide-white/5">
            {pendingActions.map((action: any, i: number) => (
              <li
                key={`${action.status}-${action.action_link}-${i}`}
                className="flex items-center justify-between py-3 gap-4"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <span className="text-xs font-mono text-white/20 w-5 shrink-0">
                    {i + 1}.
                  </span>
                  <div className="min-w-0">
                    <span className="text-sm text-white/70">
                      {action.description}
                    </span>
                    {action.course_code && (
                      <span className="text-white/30 text-xs font-mono ml-2">
                        — {action.course_code}
                      </span>
                    )}
                    {action.due_date_label && (
                      <span className="text-white/20 text-xs font-mono ml-2">
                        · {action.due_date_label}
                      </span>
                    )}
                  </div>
                </div>
                {action.action_link && (
                  <Link
                    href={action.action_link}
                    className="text-xs font-mono text-brand hover:text-white transition-colors uppercase tracking-widest shrink-0 flex items-center gap-1"
                  >
                    Go <ArrowUpRight className="w-3 h-3" />
                  </Link>
                )}
              </li>
            ))}
          </ol>
        )}

        {data?.pending_actions.completed_hidden_count ? (
          <p className="mt-4 text-xs font-mono text-white/30">
            {data.pending_actions.completed_hidden_count} completed items hidden
            (older than 24h).
          </p>
        ) : null}

        <button
          onClick={() => setShowCompleted((s) => !s)}
          className="mt-4 text-xs font-mono text-white/30 hover:text-white transition-colors"
        >
          {showCompleted ? "Hide completed" : "Show completed"}
        </button>
      </motion.section>

      {/* CO attainment summary */}
      <motion.section
        variants={fadeSlideUp}
        className="py-8 border-b border-white/5"
      >
        <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-3">
          CO Attainment Summary
        </h2>
        <p className="text-xs text-white/30 mb-4">
          Level guide: <span className="text-attain">L3</span> strong, <span className="text-amber-400">L2</span> moderate, <span className="text-alert">L1</span> needs intervention.
        </p>

        {data?.co_attainment_summary.level1_alert_line && (
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle className="w-4 h-4 text-alert shrink-0" />
            <p className="text-alert text-sm font-mono">
              {data.co_attainment_summary.level1_alert_line}
            </p>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 px-4 text-left">
                  Course
                </th>
                {["CO1", "CO2", "CO3", "CO4", "CO5"].map((co) => (
                  <th
                    key={co}
                    className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 px-3 text-center"
                  >
                    {co}
                  </th>
                ))}
                <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 px-4 text-center">
                  Overall
                </th>
              </tr>
            </thead>
            <tbody>
              {coSummaryRows.map((row: any) => (
                <tr
                  key={row.course_id}
                  className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                >
                  <td className="py-3 px-4 font-mono text-xs text-white/50">
                    {row.course}
                  </td>
                  {["CO1", "CO2", "CO3", "CO4", "CO5"].map((co) => {
                    const cell =
                      (row.co_cells || []).find(
                        (c: any) => c.co_code === co
                      ) || null;
                    if (!cell || cell.percentage == null) {
                      return (
                        <td
                          key={co}
                          className="py-3 px-3 text-center text-white/20 text-xs font-mono"
                        >
                          —
                        </td>
                      );
                    }
                    const pct = cell.percentage;
                    const level = cell.level;
                    const color =
                      level === "L3"
                        ? "text-attain"
                        : level === "L2"
                        ? "text-amber-400"
                        : "text-alert";
                    return (
                      <td key={co} className="py-3 px-3 text-center">
                        <Link
                          href={cell.drilldown_link || "#"}
                          className="flex flex-col items-center gap-0.5 hover:opacity-80 transition-opacity"
                        >
                          <span
                            className={`text-xs font-mono ${color} ${
                              level === "L1" ? "font-bold" : ""
                            }`}
                          >
                            {pct}%
                          </span>
                          <span className={`text-[9px] font-mono ${color}`}>
                            {level}
                          </span>
                        </Link>
                      </td>
                    );
                  })}
                  <td className="py-3 px-4 text-center">
                    {row.overall?.percentage != null ? (
                      <span className="text-xs font-mono text-white/60">
                        {row.overall.text}
                      </span>
                    ) : (
                      <span className="text-white/20 text-xs italic font-mono">
                        Pending marks approval
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.section>

      {/* NBA Rules */}
      <motion.section variants={fadeSlideUp} className="py-8 border-b border-white/5">
        <div className="flex items-center gap-2 mb-5">
          <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest">NBA Compliance Rules</h2>
          <span className="text-[9px] font-mono text-white/20 border border-white/10 px-1.5 py-0.5">Read-only reference</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-white/5">
          {[
            {
              icon: Lock,
              rule: "Rule 1",
              title: "PO1–PO12 are permanently fixed by NBA",
              body: "They never change. The exact wording is standardised across every engineering college in India under NBA accreditation. A faculty member cannot rewrite, reorder, or remove any of the 12 POs.",
              note: "If your system allows editing PO1–PO12, that is a bug.",
              color: "text-brand",
              border: "border-brand/20",
            },
            {
              icon: Users,
              rule: "Rule 2",
              title: "PSO1 & PSO2 are fixed per department, not per course",
              body: "PSOs are defined once when the department submits its SAR to NBA. Every course in that department uses the same PSO1 and PSO2. If one faculty changes PSO wording, every other course's attainment report becomes inconsistent — NBA will flag this during audit.",
              note: "PSOs are managed by HOD only.",
              color: "text-aurora",
              border: "border-aurora/20",
            },
            {
              icon: GitBranch,
              rule: "Rule 3",
              title: "Mapping values change per course — PO/PSO definitions never change",
              body: "What changes course-to-course is which COs map to which POs and at what strength (0/1/2/3). The PO/PSO text itself stays identical across all courses and all academic years.",
              note: "Only CO↔PO correlation strengths are course-specific.",
              color: "text-attain",
              border: "border-attain/20",
            },
          ].map(({ icon: Icon, rule, title, body, note, color, border }) => (
            <div key={rule} className={`bg-[#0a1628] px-5 py-5 border-t-2 ${border}`}>
              <div className="flex items-center gap-2 mb-3">
                <Icon className={`w-3.5 h-3.5 shrink-0 ${color}`} />
                <span className={`text-[10px] font-mono uppercase tracking-widest ${color}`}>{rule}</span>
              </div>
              <p className="text-xs text-white/80 font-medium leading-snug mb-2">{title}</p>
              <p className="text-[11px] text-white/40 leading-relaxed mb-3">{body}</p>
              <p className={`text-[10px] font-mono ${color} opacity-70`}>{note}</p>
            </div>
          ))}
        </div>
      </motion.section>

      {/* Recent activity */}
      <motion.section variants={fadeSlideUp} className="py-8">
        <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-5">
          Recent Activity
        </h2>
        <p className="text-xs text-white/30 mb-4">
          Latest course operations are listed here for quick traceability.
        </p>

        {recentActivity.length === 0 ? (
          <p className="text-white/20 text-sm italic">
            No recent activity recorded.
          </p>
        ) : (
          <ol className="flex flex-col gap-0 divide-y divide-white/5">
            {recentActivity.map((entry: any) => (
              <li key={`${entry.index}-${entry.action}`} className="flex items-center gap-4 py-3">
                <span className="text-[10px] font-mono text-white/20 w-5 shrink-0">
                  {entry.index}.
                </span>
                <p className="text-sm text-white/50 flex-1 font-light">
                  {entry.text}
                </p>
              </li>
            ))}
          </ol>
        )}

        {data?.recent_activity.view_all_link && (
          <Link
            href={data.recent_activity.view_all_link}
            className="mt-4 inline-flex items-center gap-1.5 text-xs font-mono text-brand hover:text-white transition-colors uppercase tracking-widest"
          >
            View full activity log <ArrowUpRight className="w-3 h-3" />
          </Link>
        )}
      </motion.section>
    </motion.div>
  );
}


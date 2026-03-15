"use client";

import { useMemo, useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { FileText, Download, Loader2, CheckCircle2, FileSpreadsheet, Award, Lock, TrendingUp, AlertTriangle, BarChart2, Users, Briefcase, Printer } from "lucide-react";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import { useAuthStore, Role } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";
import jsPDF from "jspdf";
import * as XLSX from "xlsx";

// ─── Report catalogue (Spec Section 11.1) ────────────────────────────────
type ReportDef = {
  id: string;
  name: string;
  desc: string;
  icon: any;
  allowedRoles: Role[];
  formats: ("PDF" | "Excel")[];
  nba?: boolean;
};

const REPORT_CATALOGUE: ReportDef[] = [
  {
    id: "co_attainment",
    name: "CO Attainment Report",
    desc: "Bar chart per CO, CIE vs SEE split, Level badges, student count per attainment level.",
    icon: BarChart2,
    allowedRoles: ["faculty", "subject_lead", "department_head", "admin"],
    formats: ["PDF", "Excel"],
  },
  {
    id: "po_attainment",
    name: "PO Attainment Report",
    desc: "PO-wise attainment %, CO contribution breakdown, target vs actual comparison.",
    icon: TrendingUp,
    allowedRoles: ["subject_lead", "department_head", "admin"],
    formats: ["PDF", "Excel"],
  },
  {
    id: "pso_attainment",
    name: "PSO Attainment Report",
    desc: "PSO-wise attainment %, mapping trace back to contributing COs and weights.",
    icon: Briefcase,
    allowedRoles: ["subject_lead", "department_head", "admin"],
    formats: ["PDF", "Excel"],
  },
  {
    id: "student_performance",
    name: "Student Performance Report",
    desc: "Student-wise CO score table, pass/fail breakdown per CO. Marks-level detail.",
    icon: Users,
    allowedRoles: ["faculty", "admin"],
    formats: ["Excel"],
  },
  {
    id: "ay_trend",
    name: "3-Year Trend Report",
    desc: "CO/PO line charts across AY-2 → AY-1 → Current AY. HOD and Admin only.",
    icon: TrendingUp,
    allowedRoles: ["department_head", "admin"],
    formats: ["PDF", "Excel"],
  },
  {
    id: "curricular_gap",
    name: "Curricular Gap Report",
    desc: "COs consistently below Level 2 for 2+ years, with curriculum improvement recommendations.",
    icon: AlertTriangle,
    allowedRoles: ["department_head", "admin"],
    formats: ["PDF"],
  },
  {
    id: "dept_summary",
    name: "Department Summary Report",
    desc: "All courses, all COs, PO/PSO aggregated at department level for accreditation.",
    icon: FileText,
    allowedRoles: ["department_head", "admin"],
    formats: ["PDF", "Excel"],
    nba: true,
  },
  {
    id: "nba_naac",
    name: "NBA / NAAC Export",
    desc: "One-click export of CO-PO attainment in the exact format required for NBA accreditation.",
    icon: Award,
    allowedRoles: ["admin"],
    formats: ["PDF", "Excel"],
    nba: true,
  },
];

export default function ReportsPage() {
  const { activeRole, activeAY, user } = useAuthStore();
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const [generating, setGenerating] = useState<string | null>(null);
  const [ready, setReady] = useState<string[]>([]);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [courseFilter, setCourseFilter] = useState("all");

  const loadCourses = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.getCourses();
      setCourses(Array.isArray(res) ? res : (res?.items ?? []));
    } catch {
      setCourses([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCourses();
  }, [loadCourses]);

  const visibleReports = REPORT_CATALOGUE.filter(r =>
    activeRole && r.allowedRoles.includes(activeRole)
  );

  const scopedCourses = useMemo(() => {
    if (activeRole === "faculty" && user?.id) {
      return courses.filter((c: any) => (c.created_by ?? c.facultyId) === user.id);
    }
    return courses;
  }, [activeRole, user?.id, courses]);

  const filteredCourses = useMemo(() => {
    if (courseFilter === "all") return scopedCourses;
    return scopedCourses.filter(c => c.id === courseFilter);
  }, [scopedCourses, courseFilter]);

  const buildRows = (reportName: string) => {
    return filteredCourses.map((c, idx) => ({
      SNo: idx + 1,
      Report: reportName,
      AY: activeAY,
      CourseCode: c.course_code ?? c.code,
      CourseName: c.course_name ?? c.name,
      Semester: c.semester,
      Section: c.section ?? "-",
      Students: c.students ?? "-",
    }));
  };

  const generate = (id: string) => {
    setGenerating(id);
    setTimeout(() => {
      setGenerating(null);
      setReady(prev => (prev.includes(id) ? prev : [...prev, id]));
    }, 900);
  };

  const download = (id: string, fmt: "PDF" | "Excel") => {
    const report = REPORT_CATALOGUE.find(r => r.id === id);
    if (!report) return;

    setDownloading(`${id}-${fmt}`);
    const rows = buildRows(report.name);
    const stamp = new Date().toISOString().slice(0, 10);
    const baseName = `${id}-${activeRole || "role"}-${activeAY}-${stamp}`;

    try {
      if (fmt === "Excel") {
        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.json_to_sheet(
          rows.length > 0
            ? rows
            : [{ Report: report.name, AY: activeAY, Note: "No rows for selected filter" }],
        );
        XLSX.utils.book_append_sheet(wb, ws, "Report");
        XLSX.writeFile(wb, `${baseName}.xlsx`);
      } else {
        const doc = new jsPDF();
        doc.setFontSize(14);
        doc.text(report.name, 14, 16);
        doc.setFontSize(10);
        doc.text(`Role: ${activeRole || "-"} | AY: ${activeAY}`, 14, 24);
        doc.text(`Generated: ${new Date().toLocaleString("en-IN")}`, 14, 30);

        let y = 38;
        if (!rows.length) {
          doc.text("No rows for selected filter.", 14, y);
        } else {
          rows.forEach((row, idx) => {
            if (y > 280) {
              doc.addPage();
              y = 20;
            }
            doc.text(
              `${idx + 1}. ${row.CourseCode} - ${row.CourseName} | Sem ${row.Semester} | Sec ${row.Section} | Students ${row.Students}`,
              14,
              y,
            );
            y += 7;
          });
        }
        doc.save(`${baseName}.pdf`);
      }
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="w-full min-h-screen pb-24">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-5xl mx-auto px-6 pt-12">

        {/* Header */}
        <motion.div variants={fadeSlideUp} className="mb-16">
          <div className="flex items-center gap-3 text-sm font-mono text-brand uppercase tracking-widest mb-4">
            <span className="w-8 h-[1px] bg-brand" />
            Reporting Suite
          </div>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-5xl font-display text-white mb-4">Reports</h1>
              <p className="text-white/40 font-light max-w-xl">
                All reports are role-gated. You are viewing reports available to{" "}
                <span className="text-white font-medium">{activeRole?.replace("_", " ")}</span>.
              </p>
              <div className="mt-4 flex items-center gap-3">
                <label className="text-[10px] font-mono uppercase tracking-widest text-white/40">
                  Course Filter
                </label>
                <select
                  value={courseFilter}
                  onChange={e => setCourseFilter(e.target.value)}
                  className="bg-transparent border border-white/20 px-3 py-1.5 text-xs text-white/70 outline-none"
                >
                  <option value="all" className="bg-[#050509]">All Courses</option>
                  {scopedCourses.map(c => (
                    <option key={c.id} value={c.id} className="bg-[#050509]">
                      {c.course_code ?? c.code} - {c.course_name ?? c.name}
                    </option>
                  ))}
                </select>
                <span className="text-[10px] font-mono text-white/30">AY {activeAY}</span>
              </div>
            </div>
            <button
              onClick={() => window.print()}
              aria-label="Print this page"
              className="shrink-0 flex items-center gap-2 px-4 py-2.5 border border-white/20 text-white/60 text-xs font-mono uppercase tracking-widest hover:text-white hover:border-white/40 transition-colors print:hidden focus:outline-none focus:ring-2 focus:ring-brand"
            >
              <Printer className="w-3.5 h-3.5" aria-hidden="true" /> Print
            </button>
          </div>
        </motion.div>

        {/* Report tiles */}
        <motion.div variants={staggerContainer} className="flex flex-col divide-y divide-white/10">
          {visibleReports.map((report, i) => {
            const isGenerating = generating === report.id;
            const isReady = ready.includes(report.id);
            const Icon = report.icon;
            return (
              <motion.div key={report.id} variants={fadeSlideUp}
                className="flex flex-col md:flex-row md:items-center gap-6 md:gap-12 py-10 group hover:pl-2 transition-all"
              >
                <div className="flex items-start gap-6 flex-1 min-w-0">
                  <Icon className="w-5 h-5 text-white/30 mt-0.5 shrink-0 group-hover:text-brand transition-colors" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-display text-white group-hover:text-brand transition-colors">
                        {report.name}
                      </h3>
                      {report.nba && (
                        <span className="px-2 py-0.5 bg-attain/10 border border-attain/30 text-attain text-[10px] font-mono uppercase tracking-widest">
                          NBA
                        </span>
                      )}
                    </div>
                    <p className="text-white/40 text-sm font-light leading-relaxed">{report.desc}</p>
                    <div className="flex gap-3 mt-3">
                      {report.formats.map(fmt => (
                        <span key={fmt} className="text-[10px] font-mono text-white/30 bg-white/5 px-2 py-1 uppercase">
                          {fmt}
                        </span>
                      ))}
                      <span className="text-[10px] font-mono text-white/20">
                        {report.allowedRoles.join(" · ")}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {isReady ? (
                    <>
                      {report.formats.map(fmt => (
                        <button key={fmt} onClick={() => download(report.id, fmt)}
                          className="flex items-center gap-2 px-4 py-2.5 border border-attain/50 text-attain text-xs font-mono uppercase tracking-widest hover:bg-attain hover:text-black transition-all"
                        >
                          {downloading === `${report.id}-${fmt}` ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Download className="w-3 h-3" />
                          )}
                          {fmt}
                        </button>
                      ))}
                    </>
                  ) : (
                    <button onClick={() => generate(report.id)} disabled={isGenerating}
                      className={`flex items-center gap-2 px-6 py-3 text-xs font-mono uppercase tracking-widest border transition-all ${
                        isGenerating
                          ? "border-white/10 text-white/30 cursor-wait"
                          : "border-white/30 text-white hover:bg-white hover:text-black"
                      }`}
                    >
                      {isGenerating ? (
                        <><Loader2 className="w-3 h-3 animate-spin" /> Generating…</>
                      ) : (
                        <><FileText className="w-3 h-3" /> Generate</>
                      )}
                    </button>
                  )}
                </div>
              </motion.div>
            );
          })}
        </motion.div>

        {visibleReports.length === 0 && (
          <div className="py-24 text-center">
            <Lock className="w-8 h-8 text-white/20 mx-auto mb-4" />
            <p className="text-white/30 font-mono uppercase tracking-widest text-sm">No reports available for your role.</p>
          </div>
        )}

      </motion.div>
    </div>
  );
}

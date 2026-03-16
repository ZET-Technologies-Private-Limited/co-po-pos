"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, usePathname } from "next/navigation";
import Link from "next/link";
import apiClient from "@/lib/apiClient";
import { CourseErrorDisplay } from "@/components/course/CourseErrorDisplay";
import {
  ChevronLeft,
  Sparkles,
  Settings,
  BrainCircuit,
  FileSpreadsheet,
  BarChart2,
  Bot,
  Target,
  FileText,
  GitBranch,
} from "lucide-react";

const NAV = [
  { href: "co-generation", label: "CO Generation", icon: Sparkles },
  { href: "exam-config", label: "Exam Config", icon: Settings },
  { href: "question-analyser", label: "Question Analyser", icon: BrainCircuit },
  { href: "marks", label: "Marks Upload", icon: FileSpreadsheet },
  { href: "co-attainment", label: "CO Attainment", icon: BarChart2 },
  { href: "po-pso-attainment", label: "PO/PSO Attainment", icon: Target },
  { href: "correlations", label: "CO-PO Correlations", icon: GitBranch },
  { href: "chatbot", label: "OBE Chatbot", icon: Bot },
  { href: "reports", label: "Reports", icon: FileText },
];

export default function FacultyCourseLayout({ children }: { children: React.ReactNode }) {
  const { id } = useParams();
  const pathname = usePathname();
  const courseId = id as string;

  const [course, setCourse] = useState<any>(null);
  const [exams, setExams] = useState<any[]>([]);
  const [outcomes, setOutcomes] = useState<any[]>([]);
  const [marksStatus, setMarksStatus] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true); setError(null);
      try {
        const [c, ex, cos] = await Promise.all([
          apiClient.getCourse(courseId),
          apiClient.getExams(courseId),
          apiClient.getCourseOutcomes(courseId),
        ]);
        if (cancelled) return;
        setCourse(c);
        setExams(Array.isArray(ex) ? ex : []);
        setOutcomes(Array.isArray(cos) ? cos : []);

        const statusMap: Record<string, string> = {};
        for (const exam of Array.isArray(ex) ? ex : []) {
          try {
            const marks = await apiClient.getMarks(String(exam.id));
            const hasRows = Array.isArray(marks?.rows) ? marks.rows.length > 0 : (marks?.total_students || 0) > 0;
            statusMap[String(exam.id)] = hasRows ? "uploaded" : "pending";
          } catch {
            statusMap[String(exam.id)] = "pending";
          }
        }
        if (!cancelled) setMarksStatus(statusMap);
      } catch (e: any) {
        if (!cancelled) {
          setError(typeof e?.message === "string" ? e.message : "Failed to load course data.");
          setCourse(null); setExams([]); setOutcomes([]); setMarksStatus({});
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [courseId]);

  function getHref(seg: string) {
    return `/faculty/course/${courseId}/${seg}`;
  }

  function isActive(seg: string) {
    if (seg === "marks") return pathname.includes("/marks");
    return pathname.includes(`/${seg}`);
  }

  return (
    <div className="flex min-h-[calc(100vh-64px)] bg-cosmic">
      {error ? (
        <CourseErrorDisplay
          message={error}
          suggestion="This usually means the course ID is invalid or the course has been deleted. Please go back to the dashboard and select a course again."
        />
      ) : (
        <>
          {/* Sidebar */}
          <aside className="w-60 lg:w-64 shrink-0 border-r border-white/10 flex flex-col sticky top-16 h-[calc(100vh-64px)]">
            <div className="p-4 border-b border-white/10">
              <Link
                href="/faculty/dashboard"
                className="flex items-center gap-1.5 text-[9px] text-white/40 hover:text-white mb-3 transition-colors"
              >
                <ChevronLeft className="w-3 h-3" /> Dashboard
              </Link>
              <p className="text-[9px] text-brand uppercase tracking-widest font-mono">
                {course?.course_code || "Course"}
              </p>
              <p className="text-sm text-white mt-0.5 leading-tight font-light">
                {course?.course_name || (loading ? "Loading..." : "Unknown")}
              </p>
              <p className="text-[9px] text-white/30 mt-1 font-mono">
                Sem {course?.semester ?? "—"} · {course?.credits ?? "—"} Credits
              </p>
            </div>

            {/* CO Status */}
            <div className="px-4 py-2.5 border-b border-white/10">
              <div className="flex items-center justify-between">
                <span className="text-[9px] text-white/30 uppercase font-mono">COs</span>
                <span className={`text-[9px] uppercase font-mono ${outcomes.length > 0 ? "text-emerald-400" : "text-amber-400"}`}>
                  {outcomes.length > 0 ? `${outcomes.length} ready` : "not generated"}
                </span>
              </div>
            </div>

            <div className="px-4 py-2.5 border-b border-white/10">
              <div className="flex items-center justify-between">
                <span className="text-[9px] text-white/30 uppercase font-mono">Exams</span>
                <span className="text-[9px] uppercase font-mono text-white/60">{exams.length}</span>
              </div>
            </div>

            {/* Navigation */}
            <nav className="flex flex-col flex-1 overflow-y-auto">
              <p className="px-4 pt-3 pb-2 text-[9px] text-white/25 uppercase tracking-widest font-mono">Workflow</p>
              {NAV.map(({ href, label, icon: Icon }) => {
                const active = isActive(href);
                return (
                  <Link
                    key={href}
                    href={getHref(href)}
                    className={`flex items-center gap-2.5 px-4 py-3 text-[10px] uppercase tracking-widest transition-colors border-l-2 rounded-r-md ${
                      active
                        ? "text-brand bg-brand/10 border-l-brand"
                        : "text-white/40 hover:text-white hover:bg-white/[0.02] border-l-transparent"
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 shrink-0" />
                    <span className="font-mono">{label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Marks Status */}
            {exams.length > 0 && (
              <div className="p-4 border-t border-white/10">
                <p className="text-[9px] text-white/30 uppercase font-mono mb-2">Marks Status</p>
                {exams.slice(0, 5).map((exam) => {
                  const examId = String(exam.id);
                  const status = marksStatus[examId] || "pending";
                  return (
                    <div key={examId} className="flex items-center justify-between mb-1">
                      <span className="text-[9px] text-white/40 font-mono truncate max-w-[80px]">
                        {exam.assessment_code || exam.exam_name || examId}
                      </span>
                      <span className={`text-[9px] uppercase font-mono ${status === "uploaded" ? "text-emerald-400" : "text-amber-400"}`}>
                        {status}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </aside>

          {/* Main Content — full width */}
          <main className="flex-1 overflow-auto px-6 lg:px-10 py-8">
            <div className="max-w-[1200px]">{children}</div>
          </main>
        </>
      )}
    </div>
  );
}

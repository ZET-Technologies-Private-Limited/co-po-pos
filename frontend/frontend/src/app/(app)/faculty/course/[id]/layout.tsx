"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, usePathname } from "next/navigation";
import Link from "next/link";
import apiClient from "@/lib/apiClient";
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
} from "lucide-react";

const NAV = [
  { href: "co-generation", label: "CO Generation", icon: Sparkles },
  { href: "exam-config", label: "Exam Configuration", icon: Settings },
  { href: "question-mapping", label: "AI Question Analyser", icon: BrainCircuit },
  { href: "marks", label: "Marks Upload", icon: FileSpreadsheet },
  { href: "co-attainment", label: "CO Attainment", icon: BarChart2 },
  { href: "chatbot", label: "OBE Chatbot", icon: Bot },
  { href: "po-pso-attainment", label: "PO/PSO Attainment", icon: Target },
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

  useEffect(() => {
    let cancelled = false;
    async function load() {
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
      } catch {
        if (!cancelled) {
          setCourse(null);
          setExams([]);
          setOutcomes([]);
          setMarksStatus({});
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  const firstExamId = useMemo(() => String(exams[0]?.id || "t1"), [exams]);

  function getHref(seg: string) {
    if (seg === "marks") return `/faculty/course/${courseId}/marks/${firstExamId}`;
    return `/faculty/course/${courseId}/${seg}`;
  }

  function isActive(seg: string) {
    if (seg === "marks") return pathname.includes("/marks/");
    return pathname.includes(`/${seg}`);
  }

  return (
    <div className="flex min-h-[calc(100vh-64px)]">
      <aside className="w-56 shrink-0 border-r border-white/10 flex flex-col">
        <div className="p-5 border-b border-white/10">
          <Link href="/faculty/dashboard" className="flex items-center gap-1.5 text-[9px] text-white/40 hover:text-white mb-4">
            <ChevronLeft className="w-3 h-3" /> Dashboard
          </Link>
          <p className="text-[9px] text-brand uppercase tracking-widest">{course?.course_code || "Course"}</p>
          <p className="text-sm text-white mt-1 leading-tight">{course?.course_name || "Loading..."}</p>
          <p className="text-[9px] text-white/30 mt-1">
            Sem {course?.semester ?? "-"} | {course?.students || course?.enrolled_students || "-"} Students
          </p>
        </div>

        <div className="px-5 py-3 border-b border-white/10">
          <div className="flex items-center justify-between">
            <span className="text-[9px] text-white/30 uppercase">COs</span>
            <span className={`text-[9px] uppercase ${outcomes.length > 0 ? "text-attain" : "text-alert"}`}>
              {outcomes.length > 0 ? `${outcomes.length} Generated` : "Not Generated"}
            </span>
          </div>
        </div>

        <nav className="flex flex-col divide-y divide-white/10 flex-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={getHref(href)}
                className={`flex items-center gap-3 px-5 py-4 text-[10px] uppercase tracking-widest ${
                  active
                    ? "text-brand bg-brand/5 border-l-2 border-brand"
                    : "text-white/40 hover:text-white hover:bg-white/[0.02] border-l-2 border-transparent"
                }`}
              >
                <Icon className="w-3.5 h-3.5 shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="p-5 border-t border-white/10 flex flex-col gap-2">
          <p className="text-[9px] text-white/30 uppercase">Marks Status</p>
          {exams.slice(0, 6).map((exam) => {
            const examId = String(exam.id);
            const status = marksStatus[examId] || "pending";
            return (
              <div key={examId} className="flex items-center justify-between">
                <span className="text-[9px] text-white/40">{exam.assessment_code || exam.exam_name || examId}</span>
                <span className={`text-[9px] uppercase ${status === "uploaded" ? "text-attain" : "text-amber-400"}`}>
                  {status}
                </span>
              </div>
            );
          })}
        </div>
      </aside>

      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  );
}

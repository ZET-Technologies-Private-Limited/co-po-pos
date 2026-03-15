"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function StudentCourseMarksPage() {
  const { id } = useParams();
  const courseId = id as string;

  const [course, setCourse] = useState<any>(null);
  const [exams, setExams] = useState<any[]>([]);
  const [marksByExam, setMarksByExam] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [c, ex] = await Promise.all([apiClient.getCourse(courseId), apiClient.getExams(courseId)]);
        const examList = Array.isArray(ex) ? ex : [];
        const byExam: Record<string, any> = {};
        for (const e of examList) {
          try {
            byExam[String(e.id)] = await apiClient.getMarks(String(e.id));
          } catch {
            byExam[String(e.id)] = null;
          }
        }
        if (cancelled) return;
        setCourse(c);
        setExams(examList);
        setMarksByExam(byExam);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load course marks.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  return (
    <AccessGate feature="dashboard" deny="lock">
      <div className="max-w-5xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">Course Marks</h1>
          <p className="text-white/50 mt-1">{course?.course_name || "Course"}</p>
        </div>

        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading && !error ? (
          <section className="border border-white/10 rounded-lg p-4 space-y-3">
            {exams.map((e) => {
              const marks = marksByExam[String(e.id)];
              return (
                <div key={e.id} className="border border-white/10 rounded p-3">
                  <p className="text-white text-sm font-medium">{e.exam_name}</p>
                  <p className="text-white/50 text-xs mt-1">Type: {e.exam_type} | Total Marks: {e.total_marks}</p>
                  <p className="text-white/70 text-xs mt-2">Students with marks: {marks?.total_students ?? marks?.count ?? 0}</p>
                </div>
              );
            })}
            {exams.length === 0 ? <p className="text-white/40 text-sm">No exams found for this course.</p> : null}
          </section>
        ) : null}
      </div>
    </AccessGate>
  );
}

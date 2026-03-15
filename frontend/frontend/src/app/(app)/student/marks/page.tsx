"use client";

import { useEffect, useState } from "react";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function StudentMarksPage() {
  const [courses, setCourses] = useState<any[]>([]);
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const courseList = await apiClient.getCourses();
        const safeCourses = Array.isArray(courseList) ? courseList : [];
        if (cancelled) return;
        setCourses(safeCourses);

        const out: any[] = [];
        for (const c of safeCourses) {
          try {
            const exams = await apiClient.getExams(String(c.id));
            const safeExams = Array.isArray(exams) ? exams : [];
            for (const e of safeExams) {
              try {
                const marks = await apiClient.getMarks(String(e.id));
                out.push({
                  course_id: c.id,
                  course_code: c.course_code,
                  exam_name: e.exam_name,
                  exam_id: e.id,
                  total_students: marks?.total_students ?? marks?.count ?? 0,
                });
              } catch {
                out.push({
                  course_id: c.id,
                  course_code: c.course_code,
                  exam_name: e.exam_name,
                  exam_id: e.id,
                  total_students: 0,
                });
              }
            }
          } catch {
            // no-op
          }
        }
        if (!cancelled) setRows(out);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load marks overview.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AccessGate feature="dashboard" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">Marks Overview</h1>
          <p className="text-white/50 mt-1">Live exam marks status from backend</p>
        </div>

        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading && !error ? (
          <section className="border border-white/10 rounded-lg p-4">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-white/[0.03] text-white/50">
                  <tr>
                    <th className="px-3 py-2">Course</th>
                    <th className="px-3 py-2">Exam</th>
                    <th className="px-3 py-2">Students With Marks</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, idx) => (
                    <tr key={`${r.course_id}-${r.exam_id}-${idx}`} className="border-t border-white/10">
                      <td className="px-3 py-2 text-white/80">{r.course_code}</td>
                      <td className="px-3 py-2 text-white/70">{r.exam_name}</td>
                      <td className="px-3 py-2 text-white/70">{r.total_students}</td>
                    </tr>
                  ))}
                  {rows.length === 0 ? <tr><td colSpan={3} className="px-3 py-4 text-white/40">No mark rows available.</td></tr> : null}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
      </div>
    </AccessGate>
  );
}

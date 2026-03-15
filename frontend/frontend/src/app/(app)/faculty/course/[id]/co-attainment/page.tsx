"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function FacultyCOAttainmentPage() {
  const { id } = useParams();
  const courseId = id as string;

  const [course, setCourse] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [students, setStudents] = useState<any[]>([]);
  const [weighted, setWeighted] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, s, st, w] = await Promise.all([
        apiClient.getCourse(courseId),
        apiClient.getCourseAttainment(courseId),
        apiClient.getStudentPerformance(courseId),
        apiClient.getWeightedCOAttainment(courseId),
      ]);
      setCourse(c);
      setSummary(s);
      setStudents(Array.isArray(st?.students) ? st.students : Array.isArray(st) ? st : []);
      setWeighted(w);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load attainment data.");
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const onFocus = () => {
      void load();
    };
    if (typeof document !== "undefined" && document.addEventListener) {
      document.addEventListener("visibilitychange", onFocus);
      return () => document.removeEventListener("visibilitychange", onFocus);
    }
  }, [load]);

  return (
    <AccessGate feature="co_attainment" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">CO Attainment</h1>
          <p className="text-white/50 mt-1">{course?.course_name || "Course"}</p>
        </div>

        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading && !error ? (
          <>
            <section className="border border-white/10 rounded-lg p-4">
              <h2 className="text-sm text-white mb-2">Course Summary</h2>
              <pre className="text-xs text-white/70 whitespace-pre-wrap">{summary ? JSON.stringify(summary, null, 2) : "No summary available."}</pre>
            </section>

            <section className="border border-white/10 rounded-lg p-4">
              <h2 className="text-sm text-white mb-2">Weighted CO Attainment</h2>
              <pre className="text-xs text-white/70 whitespace-pre-wrap">{weighted ? JSON.stringify(weighted, null, 2) : "No weighted data."}</pre>
            </section>

            <section className="border border-white/10 rounded-lg p-4">
              <h2 className="text-sm text-white mb-3">Student Performance</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-white/[0.03] text-white/50">
                    <tr>
                      <th className="px-3 py-2">Student</th>
                      <th className="px-3 py-2">Performance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {students.map((s, idx) => (
                      <tr key={idx} className="border-t border-white/10">
                        <td className="px-3 py-2 text-white/80">{s.student_id || s.roll || s.name || `Student ${idx + 1}`}</td>
                        <td className="px-3 py-2 text-white/70">{typeof s.score === "number" ? s.score : JSON.stringify(s)}</td>
                      </tr>
                    ))}
                    {students.length === 0 ? (
                      <tr>
                        <td className="px-3 py-4 text-white/40" colSpan={2}>No student-level attainment data available.</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : null}
      </div>
    </AccessGate>
  );
}

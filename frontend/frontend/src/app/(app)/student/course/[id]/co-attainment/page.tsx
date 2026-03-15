"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function StudentCourseCOAttainmentPage() {
  const { id } = useParams();
  const courseId = id as string;

  const [course, setCourse] = useState<any>(null);
  const [courseSummary, setCourseSummary] = useState<any>(null);
  const [weighted, setWeighted] = useState<any>(null);
  const [students, setStudents] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [c, s, w, st] = await Promise.all([
          apiClient.getCourse(courseId),
          apiClient.getCourseAttainment(courseId),
          apiClient.getWeightedCOAttainment(courseId),
          apiClient.getStudentPerformance(courseId),
        ]);
        if (cancelled) return;
        setCourse(c);
        setCourseSummary(s);
        setWeighted(w);
        setStudents(st);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load CO attainment.");
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
          <h1 className="text-3xl text-white font-display">CO Attainment</h1>
          <p className="text-white/50 mt-1">{course?.course_name || "Course"}</p>
        </div>

        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading && !error ? (
          <>
            <section className="border border-white/10 rounded-lg p-4">
              <h2 className="text-sm text-white mb-2">Course Attainment Summary</h2>
              <pre className="text-xs text-white/70 whitespace-pre-wrap">{JSON.stringify(courseSummary, null, 2)}</pre>
            </section>
            <section className="border border-white/10 rounded-lg p-4">
              <h2 className="text-sm text-white mb-2">Weighted CO Attainment</h2>
              <pre className="text-xs text-white/70 whitespace-pre-wrap">{JSON.stringify(weighted, null, 2)}</pre>
            </section>
            <section className="border border-white/10 rounded-lg p-4">
              <h2 className="text-sm text-white mb-2">Student Performance</h2>
              <pre className="text-xs text-white/70 whitespace-pre-wrap">{JSON.stringify(students, null, 2)}</pre>
            </section>
          </>
        ) : null}
      </div>
    </AccessGate>
  );
}

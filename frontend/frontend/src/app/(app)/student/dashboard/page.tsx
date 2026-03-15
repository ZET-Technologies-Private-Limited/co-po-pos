"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AccessGate } from "@/components/auth/AccessGate";
import { useAuthStore } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";

export default function StudentDashboardPage() {
  const { user } = useAuthStore();
  const [courses, setCourses] = useState<any[]>([]);
  const [academicYear, setAcademicYear] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [courseRes, ayRes] = await Promise.all([apiClient.getCourses(), apiClient.getCurrentAcademicYear()]);
        if (cancelled) return;
        setCourses(Array.isArray(courseRes) ? courseRes : []);
        setAcademicYear(ayRes);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load student dashboard.");
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
          <h1 className="text-3xl text-white font-display">Student Dashboard</h1>
          <p className="text-white/50 mt-1">{user?.name || "Student"} | AY {academicYear?.code || academicYear?.ay || "-"}</p>
        </div>

        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading && !error ? (
          <section className="border border-white/10 rounded-lg p-4">
            <h2 className="text-sm text-white mb-3">Enrolled / Available Courses</h2>
            <div className="space-y-2">
              {courses.map((c) => (
                <div key={c.id} className="border border-white/10 rounded p-3 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-white text-sm">{c.course_name}</p>
                    <p className="text-white/50 text-xs mt-1">{c.course_code} | Sem {c.semester}</p>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <Link href={`/student/course/${c.id}/marks`} className="text-brand hover:text-white">Marks</Link>
                    <Link href={`/student/course/${c.id}/co-attainment`} className="text-brand hover:text-white">CO Attainment</Link>
                  </div>
                </div>
              ))}
              {courses.length === 0 ? <p className="text-white/40 text-sm">No courses available.</p> : null}
            </div>
          </section>
        ) : null}
      </div>
    </AccessGate>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function StudentCoursesPage() {
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await apiClient.getCourses();
        if (cancelled) return;
        setCourses(Array.isArray(res) ? res : []);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load courses.");
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
          <h1 className="text-3xl text-white font-display">Student Courses</h1>
          <p className="text-white/50 mt-1">Live data from backend services</p>
        </div>

        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading && !error ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {courses.map((c) => (
              <div key={c.id} className="border border-white/10 rounded p-4">
                <p className="text-white text-sm font-medium">{c.course_name}</p>
                <p className="text-white/50 text-xs mt-1">{c.course_code} | Sem {c.semester} | Credits {c.credits}</p>
                <div className="flex items-center gap-4 mt-3 text-xs">
                  <Link href={`/student/course/${c.id}/marks`} className="text-brand hover:text-white">Marks</Link>
                  <Link href={`/student/course/${c.id}/co-attainment`} className="text-brand hover:text-white">CO Attainment</Link>
                </div>
              </div>
            ))}
            {courses.length === 0 ? <p className="text-white/40 text-sm">No courses found.</p> : null}
          </div>
        ) : null}
      </div>
    </AccessGate>
  );
}

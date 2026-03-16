"use client";

import { useMemo, useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { AccessGate } from "@/components/auth/AccessGate";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import apiClient from "@/lib/apiClient";
import { useUIStore } from "@/lib/uiStore";

export default function CourseAssignmentPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { addToast } = useUIStore();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [u, c] = await Promise.all([
        apiClient.getUsers().catch(() => []),
        apiClient.getCourses().catch(() => []),
      ]);
      setUsers(Array.isArray(u) ? u : []);
      setCourses(Array.isArray(c) ? c : c?.items ?? []);
    } catch (e: any) {
      setError(e?.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const faculties = useMemo(
    () => users.filter((u: any) => (u.role || "").toLowerCase() === "faculty" && u.is_active !== false),
    [users]
  );

  const [matrix, setMatrix] = useState<Record<string, Record<string, boolean>>>({});
  useEffect(() => {
    const base: Record<string, Record<string, boolean>> = {};
    faculties.forEach((f: any) => {
      base[f.id] = {};
      courses.forEach((c: any) => {
        base[f.id][c.id] = (c.created_by || c.facultyId) === f.id;
      });
    });
    setMatrix(base);
  }, [faculties, courses]);

  async function assignFaculty(facultyId: string, courseId: string, checked: boolean) {
    setMatrix((prev) => ({
      ...prev,
      [facultyId]: { ...(prev[facultyId] || {}), [courseId]: checked },
    }));
    try {
      await apiClient.updateCourse(courseId, { created_by: checked ? facultyId : (null as any) });
      addToast(checked ? "Faculty assigned." : "Assignment cleared.", "success");
      void load();
    } catch (err: any) {
      addToast(err?.message || "Update failed", "error");
    }
  }

  function copyFromPreviousAY() {
    // Pre-fill matrix from current DB state (created_by already reflects AY-1 assignments)
    const base: Record<string, Record<string, boolean>> = {};
    faculties.forEach((f: any) => {
      base[f.id] = {};
      courses.forEach((c: any) => {
        base[f.id][c.id] = (c.created_by || c.facultyId) === f.id;
      });
    });
    setMatrix(base);
    addToast("Matrix pre-filled from current course assignments.", "info");
  }

  if (loading) return (<AccessGate feature="user_management" deny="lock"><div className="max-w-7xl mx-auto pb-24 py-8"><p className="text-white/60">Loading...</p></div></AccessGate>);
  if (error) return (<AccessGate feature="user_management" deny="lock"><div className="max-w-7xl mx-auto pb-24 py-8"><p className="text-alert">{error}</p></div></AccessGate>);

  return (
    <AccessGate feature="user_management" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-7xl mx-auto pb-24 space-y-5">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-4 flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-display text-white">Course Assignment Matrix</h1>
            <p className="text-xs font-mono text-white/30 mt-2">Rows = faculty, Columns = courses with assignment checkbox.</p>
          </div>
          <button onClick={copyFromPreviousAY} className="px-3 py-2 border border-white/10 text-xs font-mono text-white/70 uppercase">
            Copy from AY-1
          </button>
        </motion.header>

        <motion.section variants={fadeSlideUp} className="overflow-x-auto border border-white/10">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/10">
                <th className="px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Faculty</th>
                {courses.map((c: any) => (
                  <th key={c.id} className="px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase whitespace-nowrap">{c.course_code ?? c.code}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {faculties.map((f: any) => (
                <tr key={f.id} className="border-b border-white/5">
                  <td className="px-3 py-2 text-xs text-white">{f.full_name ?? f.name}</td>
                  {courses.map((c: any) => (
                    <td key={`${f.id}-${c.id}`} className="px-3 py-2 text-center">
                      <input
                        type="checkbox"
                        checked={Boolean(matrix[f.id]?.[c.id])}
                        onChange={(e) => assignFaculty(f.id, c.id, e.target.checked)}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </motion.section>

        <motion.section variants={fadeSlideUp} className="overflow-x-auto border border-white/10">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/10">
                <th className="px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Course</th>
                <th className="px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Department</th>
                <th className="px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Assigned Faculty</th>
              </tr>
            </thead>
            <tbody>
              {courses.map((course: any) => {
                const assignedFaculty = faculties.filter((f: any) => Boolean(matrix[f.id]?.[course.id]));
                return (
                  <tr key={course.id} className="border-b border-white/5">
                    <td className="px-3 py-2 text-xs text-white">{course.course_code ?? course.code} — {course.course_name ?? course.name}</td>
                    <td className="px-3 py-2 text-xs text-white/60">{course.department ?? course.dept ?? "—"}</td>
                    <td className="px-3 py-2 text-xs text-white/60">
                      {assignedFaculty.length === 0 ? <span className="text-alert">Unassigned</span> : assignedFaculty.map((f: any) => f.full_name ?? f.name).join(", ")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </motion.section>
      </motion.div>
    </AccessGate>
  );
}

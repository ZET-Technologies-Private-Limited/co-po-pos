"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { BookOpen, Search, GitCommit } from "lucide-react";
import apiClient from "@/lib/apiClient";
import { AccessGate } from "@/components/auth/AccessGate";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";

export default function COLibraryViewPage() {
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
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
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return courses.filter((c: any) =>
      (c.course_code ?? c.code ?? "").toLowerCase().includes(q) ||
      (c.course_name ?? c.name ?? "").toLowerCase().includes(q) ||
      (c.department ?? c.dept ?? "").toLowerCase().includes(q)
    );
  }, [courses, search]);

  return (
    <AccessGate feature="co_library_view" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-6xl mx-auto pb-32">

        {/* Header */}
        <motion.div variants={fadeSlideUp} className="pb-8 border-b border-white/5">
          <div className="flex items-center gap-2 text-[10px] font-mono text-brand uppercase tracking-widest mb-3">
            <span className="w-8 h-[1px] bg-brand" /> Standard Repository
          </div>
          <div className="flex justify-between items-end">
            <div>
              <h1 className="text-4xl font-display text-white flex items-center gap-4">
                <BookOpen className="w-8 h-8 text-brand" /> Default CO Library
              </h1>
              <p className="text-white/40 font-light mt-1">University-wide standard Course Outcome sets. Read-only view.</p>
            </div>
          </div>
        </motion.div>

        {/* Filters */}
        <motion.div variants={fadeSlideUp} className="flex gap-4 py-5 border-b border-white/5">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/20" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search by course code, name or department..."
              className="w-full bg-white/[0.02] border border-white/10 pl-10 pr-4 py-2.5 text-sm text-white outline-none focus:border-brand transition-colors" />
          </div>
        </motion.div>

        {/* Course list as CO library (real-time from backend) */}
        <motion.div variants={fadeSlideUp} className="flex flex-col divide-y divide-white/5">
          {loading ? (
            <div className="py-12 text-center text-white/40">Loading courses…</div>
          ) : filtered.length === 0 ? (
            <div className="py-24 text-center text-white/20">
              <BookOpen className="w-10 h-10 mx-auto mb-4 opacity-20" />
              <p className="text-sm font-mono uppercase tracking-widest">No courses found</p>
            </div>
          ) : filtered.map((c: any) => (
            <div key={c.id} className="py-8">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="text-xl font-display text-white">{c.course_code ?? c.code} — {c.course_name ?? c.name}</h3>
                    <span className="text-[9px] font-mono border border-brand/30 text-brand px-2 py-0.5 uppercase flex items-center gap-1">
                      <GitCommit className="w-2.5 h-2.5" /> {c.department ?? c.dept ?? "—"}
                    </span>
                  </div>
                  <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest">
                    Dept: {c.department ?? c.dept ?? "—"} · Semester: {c.semester ?? "—"} · Outcomes: see course page
                  </p>
                </div>
                <Link href={`/faculty/course/${c.id}/co-generation`} className="text-[10px] font-mono text-brand hover:text-white uppercase tracking-widest">
                  View COs →
                </Link>
              </div>
            </div>
          ))}
        </motion.div>

      </motion.div>
    </AccessGate>
  );
}

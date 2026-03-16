"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Database, Search } from "lucide-react";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import apiClient from "@/lib/apiClient";
import { AccessGate } from "@/components/auth/AccessGate";

export default function AdminCOLibraryPage() {
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const c = await apiClient.getCourses();
      setCourses(Array.isArray(c) ? c : c?.items ?? []);
    } catch (e: any) {
      setError(e?.message || "Failed to load courses");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return courses.filter((c: any) =>
      (deptFilter === "all" || (c.department ?? c.dept ?? "").toLowerCase() === deptFilter.toLowerCase()) &&
      (!q ||
        (c.course_code ?? c.code ?? "").toLowerCase().includes(q) ||
        (c.course_name ?? c.name ?? "").toLowerCase().includes(q))
    );
  }, [courses, search, deptFilter]);

  // Excel/CSV import
  const deptOptions = useMemo(() => {
    const set = new Set<string>();
    courses.forEach((c: any) => { const d = c.department ?? c.dept; if (d) set.add(d); });
    return ["all", ...Array.from(set)];
  }, [courses]);

  const renderContent = () => {
    if (loading) {
      return (
        <div className="max-w-6xl mx-auto pb-32 py-8">
          <p className="text-white/60">Loading courses...</p>
        </div>
      );
    }
    
    if (error) {
      return (
        <div className="max-w-6xl mx-auto pb-32 py-8">
          <p className="text-alert">{error}</p>
        </div>
      );
    }

    return (
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-6xl mx-auto pb-32">
        <motion.div variants={fadeSlideUp} className="flex justify-between items-end pb-8 border-b border-white/5">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-mono text-brand uppercase tracking-widest mb-3">
              <span className="w-8 h-[1px] bg-brand" /> Standard Repository
            </div>
            <h1 className="text-4xl font-display text-white flex items-center gap-4">
              <Database className="w-8 h-8 text-brand" /> CO Library
            </h1>
            <p className="text-white/40 font-light mt-1">Courses and their Course Outcomes. Manage COs from the course CO Generation page.</p>
          </div>
        </motion.div>

        <motion.div variants={fadeSlideUp} className="flex gap-4 py-5 border-b border-white/5">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/20" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search by name or course code..."
              className="w-full bg-white/[0.02] border border-white/10 pl-10 pr-4 py-2.5 text-sm text-white outline-none focus:border-brand transition-colors" />
          </div>
          <select value={deptFilter} onChange={e => setDeptFilter(e.target.value)}
            className="bg-white/[0.02] border border-white/10 px-4 py-2.5 text-sm text-white outline-none text-[10px] font-mono uppercase">
            {deptOptions.map(d => (
              <option key={d} value={d} className="bg-[#0a0a0f]">{d === "all" ? "All Depts" : d}</option>
            ))}
          </select>
        </motion.div>

        <div className="flex flex-col divide-y divide-white/5">
          {filtered.length === 0 ? (
            <div className="py-24 text-center text-white/20">
              <Database className="w-10 h-10 mx-auto mb-4 opacity-20" />
              <p className="text-sm font-mono uppercase tracking-widest">No courses found</p>
            </div>
          ) : (
            filtered.map((c: any) => (
              <motion.div key={c.id} variants={fadeSlideUp} className="py-6 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-display text-white">{c.course_code ?? c.code} — {c.course_name ?? c.name}</h3>
                  <p className="text-[10px] font-mono text-white/20 uppercase tracking-widest mt-1">
                    Dept: {c.department ?? c.dept ?? "—"}
                  </p>
                </div>
                <Link href={`/faculty/course/${c.id}/co-generation`}
                  className="px-4 py-2 bg-brand text-white text-[10px] font-mono uppercase tracking-widest hover:bg-brand/90 transition-colors">
                  View / Edit COs
                </Link>
              </motion.div>
            ))
          )}
        </div>
      </motion.div>
    );
  };

  return (
    <AccessGate feature="co_library_manage" deny="lock">
      {renderContent()}
    </AccessGate>
  );
}

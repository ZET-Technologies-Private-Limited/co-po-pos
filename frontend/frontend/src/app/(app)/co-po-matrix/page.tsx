"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { Layers, Save, CheckCircle2 } from "lucide-react";
import { useAuthStore } from "@/lib/authStore";
import { AccessGate } from "@/components/auth/AccessGate";
import { useUIStore } from "@/lib/uiStore";
import apiClient from "@/lib/apiClient";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";

const DEFAULT_PO_PSO = ["PO1", "PO2", "PO3", "PO4", "PO5", "PO6", "PSO1", "PSO2"];

export default function COPOMatrixPage() {
  const { activeRole } = useAuthStore();
  const { addToast } = useUIStore();
  const [courses, setCourses] = useState<any[]>([]);
  const [detail, setDetail] = useState<any[]>([]);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [localMapping, setLocalMapping] = useState<Record<string, Record<string, number>>>({});
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  const isReadOnly = activeRole === "subject_lead";

  const loadCourses = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.getCourses();
      const list = Array.isArray(res) ? res : (res?.items ?? []);
      setCourses(list);
      if (!selectedCourse && list.length) setSelectedCourse(list[0].id);
    } catch {
      setCourses([]);
    } finally {
      setLoading(false);
    }
  }, [selectedCourse]);

  useEffect(() => {
    void loadCourses();
  }, [loadCourses]);

  useEffect(() => {
    if (!selectedCourse) {
      setDetail([]);
      return;
    }
    setDetailLoading(true);
    apiClient.getCourseOutcomesDetail(selectedCourse)
      .then((data: any[]) => {
        setDetail(Array.isArray(data) ? data : []);
      })
      .catch(() => setDetail([]))
      .finally(() => setDetailLoading(false));
  }, [selectedCourse]);

  const courseCOs = useMemo(() => {
    return detail.map((d: any) => ({
      co: d.code ?? d.id,
      desc: d.statement ?? d.description ?? "",
      id: d.id,
      po_mappings: d.po_mappings ?? [],
      pso_mappings: d.pso_mappings ?? [],
    }));
  }, [detail]);

  const existingMapping = useMemo(() => {
    const out: Record<string, Record<string, number>> = {};
    courseCOs.forEach((co: any) => {
      const row: Record<string, number> = {};
      (co.po_mappings || []).forEach((m: any) => { row[m.code] = Math.min(3, Math.max(0, m.level ?? 0)); });
      (co.pso_mappings || []).forEach((m: any) => { row[m.code] = Math.min(3, Math.max(0, m.level ?? 0)); });
      out[co.co] = row;
    });
    return out;
  }, [courseCOs]);

  const ALL_PO_PSO = useMemo(() => {
    const codes = new Set<string>();
    courseCOs.forEach((co: any) => {
      (co.po_mappings || []).forEach((m: any) => codes.add(m.code));
      (co.pso_mappings || []).forEach((m: any) => codes.add(m.code));
    });
    return codes.size ? [...codes].sort() : DEFAULT_PO_PSO;
  }, [courseCOs]);

  const getVal = (co: string, po: string): number => {
    if (localMapping[co]?.[po] !== undefined) return localMapping[co][po];
    return existingMapping[co]?.[po] ?? 0;
  };

  const setVal = (co: string, po: string, val: number) => {
    if (isReadOnly) return;
    setSaved(false);
    setLocalMapping(prev => ({
      ...prev,
      [co]: { ...(prev[co] || {}), [po]: val },
    }));
  };

  const handleSave = async () => {
    if (!selectedCourse) return;
    try {
      for (const co of courseCOs) {
        const merged = { ...(existingMapping[co.co] || {}), ...(localMapping[co.co] || {}) };
        const poCodes = ALL_PO_PSO.filter(p => p.startsWith("PO") && merged[p] > 0);
        const psoCodes = ALL_PO_PSO.filter(p => p.startsWith("PSO") && merged[p] > 0);
        const poLevels: Record<string, number> = {};
        const psoLevels: Record<string, number> = {};
        poCodes.forEach(p => { poLevels[p] = merged[p]; });
        psoCodes.forEach(p => { psoLevels[p] = merged[p]; });
        await apiClient.updateCOMappings(selectedCourse, co.id, {
          po_codes: poCodes,
          pso_codes: psoCodes,
          po_levels: poLevels,
          pso_levels: psoLevels,
        });
      }
      setLocalMapping({});
      setSaved(true);
      addToast("CO-PO mapping saved.", "success");
      const data = await apiClient.getCourseOutcomesDetail(selectedCourse);
      setDetail(Array.isArray(data) ? data : []);
    } catch (e: any) {
      addToast(e?.message ?? "Failed to save mappings", "error");
    }
  };

  const cellColor = (val: number) => {
    if (val === 3) return "bg-attain/20 text-attain border-attain/30";
    if (val === 2) return "bg-brand/20 text-brand border-brand/30";
    if (val === 1) return "bg-amber-400/20 text-amber-400 border-amber-400/30";
    return "bg-white/5 text-white/20 border-white/10";
  };

  return (
    <AccessGate feature="co_po_matrix" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="pb-32">

        {/* Header */}
        <motion.div variants={fadeSlideUp} className="flex justify-between items-end pb-8 border-b border-white/5">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-mono text-brand uppercase tracking-widest mb-3">
              <span className="w-8 h-[1px] bg-brand" /> Correlation Matrix
            </div>
            <h1 className="text-4xl font-display text-white flex items-center gap-4">
              <Layers className="w-8 h-8 text-brand" /> CO-PO-PSO Matrix
            </h1>
            <p className="text-white/40 font-light mt-1">
              {isReadOnly ? "View-only. Contact faculty to modify mappings." : "Set correlation weights: 1 = Low, 2 = Medium, 3 = High"}
            </p>
          </div>
          {!isReadOnly && (
            <button onClick={handleSave}
              className="px-5 py-2.5 bg-brand text-white text-[10px] font-mono uppercase tracking-widest hover:bg-brand/90 transition-colors flex items-center gap-2">
              {saved ? <><CheckCircle2 className="w-3.5 h-3.5" /> Saved</> : <><Save className="w-3.5 h-3.5" /> Save Matrix</>}
            </button>
          )}
        </motion.div>

        {/* Course selector */}
        <div className="flex gap-2 py-5 border-b border-white/5 flex-wrap">
          {courses.map((c: any) => (
            <button key={c.id} onClick={() => { setSelectedCourse(c.id); setLocalMapping({}); setSaved(false); }}
              className={`px-4 py-1.5 border text-[10px] font-mono uppercase tracking-widest transition-colors ${
                selectedCourse === c.id ? "border-brand text-brand bg-brand/5" : "border-white/10 text-white/30 hover:border-white/30"
              }`}>
              {c.course_code ?? c.code}
            </button>
          ))}
        </div>

        {detailLoading ? (
          <div className="py-24 text-center text-white/40">Loading COs…</div>
        ) : courseCOs.length === 0 ? (
          <div className="py-24 text-center text-white/20">
            <p className="text-sm italic">No COs generated for this course yet.</p>
          </div>
        ) : (
          <motion.div variants={fadeSlideUp} className="overflow-x-auto mt-0">
            <table className="text-left border-collapse min-w-max">
              <thead>
                <tr className="border-b border-white/10 bg-white/[0.02]">
                  <th className="px-5 py-4 text-[9px] font-mono text-white/30 uppercase tracking-widest w-32 sticky left-0 bg-[#0c0c12]">CO</th>
                  <th className="px-5 py-4 text-[9px] font-mono text-white/30 uppercase tracking-widest min-w-[200px]">Statement</th>
                  {ALL_PO_PSO.map(po => (
                    <th key={po} className={`px-3 py-4 text-center text-[9px] font-mono uppercase tracking-widest ${po.startsWith("PSO") ? "text-amber-400/50" : "text-white/30"}`}>
                      {po}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {courseCOs.map(co => (
                  <tr key={co.co} className="border-b border-white/5 hover:bg-white/[0.01] transition-colors">
                    <td className="px-5 py-4 font-mono text-sm text-brand sticky left-0 bg-[#0c0c12]">{co.co}</td>
                    <td className="px-5 py-4 text-xs text-white/50 max-w-[200px] truncate">{co.desc}</td>
                    {ALL_PO_PSO.map(po => {
                      const val = getVal(co.co, po);
                      return (
                        <td key={po} className="px-2 py-3 text-center">
                          {isReadOnly ? (
                            <span className={`inline-block w-8 h-7 border text-[10px] font-mono flex items-center justify-center ${cellColor(val)}`}>
                              {val || "—"}
                            </span>
                          ) : (
                            <select value={val} onChange={e => setVal(co.co, po, parseInt(e.target.value))}
                              className={`w-10 text-center text-[10px] font-mono border outline-none py-1 cursor-pointer ${cellColor(val)}`}>
                              <option value={0} className="bg-[#0a0a0f]">—</option>
                              <option value={1} className="bg-[#0a0a0f]">1</option>
                              <option value={2} className="bg-[#0a0a0f]">2</option>
                              <option value={3} className="bg-[#0a0a0f]">3</option>
                            </select>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Legend */}
            <div className="flex items-center gap-6 mt-6 text-[9px] font-mono text-white/20 uppercase">
              <span className="flex items-center gap-1.5"><span className="w-4 h-3 bg-attain/20 border border-attain/30 inline-block" /> 3 — High</span>
              <span className="flex items-center gap-1.5"><span className="w-4 h-3 bg-brand/20 border border-brand/30 inline-block" /> 2 — Medium</span>
              <span className="flex items-center gap-1.5"><span className="w-4 h-3 bg-amber-400/20 border border-amber-400/30 inline-block" /> 1 — Low</span>
              <span className="flex items-center gap-1.5"><span className="w-4 h-3 bg-white/5 border border-white/10 inline-block" /> — None</span>
            </div>
          </motion.div>
        )}

      </motion.div>
    </AccessGate>
  );
}

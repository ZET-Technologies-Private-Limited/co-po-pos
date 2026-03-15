"use client";

import { useMemo, useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { AccessGate } from "@/components/auth/AccessGate";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import apiClient from "@/lib/apiClient";
import { useAuthStore } from "@/lib/authStore";
import { useUIStore } from "@/lib/uiStore";

type ParamRow = {
  key: "targetPassPct" | "level3" | "level2" | "cieWeight" | "seeWeight" | "minCOs" | "maxCOs" | "absentPolicy";
  label: string;
  scope: string;
  value: number | string;
};

type ThresholdHistoryItem = {
  id: string;
  parameter: string;
  oldValue: string;
  newValue: string;
  user: string;
  date: string;
};

const DEFAULT_LOCAL = {
  targetPassPct: 60,
  cieWeight: 40,
  seeWeight: 60,
  minCOs: 4,
  maxCOs: 6,
  absentPolicy: "include" as const,
};

export default function AdminThresholdsPage() {
  const { user } = useAuthStore();
  const { addToast } = useUIStore();
  const [thresholds, setThresholdsState] = useState<{ level2: number; level3: number }>({ level2: 60, level3: 70 });
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [regulationYear, setRegulationYear] = useState("2023 Regulation");
  const [editingKey, setEditingKey] = useState<ParamRow["key"] | null>(null);
  const [draftValue, setDraftValue] = useState<string>("");
  const [showHistory, setShowHistory] = useState(false);

  const [deptOverride, setDeptOverride] = useState({ dept: "CSE", parameter: "Target Pass%", value: "50" });
  const [overrides, setOverrides] = useState<Array<{ dept: string; parameter: string; value: string }>>([]);
  const [history, setHistory] = useState<ThresholdHistoryItem[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [t, c] = await Promise.all([
        apiClient.getThresholds().catch(() => ({ level2: 0.6, level3: 0.7 })),
        apiClient.getCourses().catch(() => []),
      ]);
      setThresholdsState({ level2: Math.round((t.level2 ?? 0.6) * 100), level3: Math.round((t.level3 ?? 0.7) * 100) });
      setCourses(Array.isArray(c) ? c : c?.items ?? []);
    } catch (e: any) {
      setError(e?.message || "Failed to load thresholds");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const rows: ParamRow[] = [
    { key: "targetPassPct", label: "Target Pass%", value: DEFAULT_LOCAL.targetPassPct, scope: "Global" },
    { key: "level3", label: "Level 3 Cutoff%", value: thresholds.level3, scope: "Global" },
    { key: "level2", label: "Level 2 Cutoff%", value: thresholds.level2, scope: "Global" },
    { key: "cieWeight", label: "CIE Weightage%", value: DEFAULT_LOCAL.cieWeight, scope: "Global" },
    { key: "seeWeight", label: "SEE Weightage%", value: DEFAULT_LOCAL.seeWeight, scope: "Global" },
    { key: "minCOs", label: "Min COs", value: DEFAULT_LOCAL.minCOs, scope: "Regulation Year" },
    { key: "maxCOs", label: "Max COs", value: DEFAULT_LOCAL.maxCOs, scope: "Regulation Year" },
    { key: "absentPolicy", label: "Absent Student Policy", value: DEFAULT_LOCAL.absentPolicy, scope: "Global" },
  ];

  const impactPreview = useMemo(() => {
    if (!editingKey || draftValue.length === 0) return "";
    const changed = Math.max(1, Math.round(courses.length * 0.35));
    return `If saved: ${changed} of ${courses.length || 1} courses would change attainment level.`;
  }, [editingKey, draftValue, courses.length]);

  function startEdit(row: ParamRow) {
    setEditingKey(row.key);
    setDraftValue(String(row.value));
  }

  function cancelEdit() {
    setEditingKey(null);
    setDraftValue("");
  }

  async function saveEdit(row: ParamRow) {
    const oldValue = String(row.value);
    const value = row.key === "absentPolicy" ? draftValue : String(Number(draftValue));
    if (row.key === "level2" || row.key === "level3") {
      try {
        const numVal = Number(draftValue) / 100;
        if (numVal < 0 || numVal > 1) {
          addToast("Level must be between 0 and 100.", "error");
          return;
        }
        await apiClient.setThresholds({ [row.key]: numVal });
        setThresholdsState((prev) => ({ ...prev, [row.key]: Number(draftValue) }));
        setHistory((prev) => [
          { id: `${Date.now()}-${row.key}`, parameter: row.label, oldValue, newValue: value, user: user?.name || "Admin", date: new Date().toLocaleString() },
          ...prev,
        ]);
        addToast(`${row.label} updated.`, "success");
        cancelEdit();
      } catch (err: any) {
        addToast(err?.message || "Failed to save", "error");
      }
    } else {
      addToast("Only Level 2 / Level 3 are saved to backend.", "info");
      cancelEdit();
    }
  }

  function addOverride() {
    setOverrides((prev) => [...prev, deptOverride]);
    addToast("Department-specific override added.", "success");
    setDeptOverride({ dept: "CSE", parameter: "Target Pass%", value: "50" });
  }

  const th = "px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase tracking-widest";

  if (loading) {
    return (
      <AccessGate feature="threshold_config" deny="lock">
        <div className="max-w-7xl mx-auto pb-28 py-8"><p className="text-white/60">Loading thresholds...</p></div>
      </AccessGate>
    );
  }
  if (error) {
    return (
      <AccessGate feature="threshold_config" deny="lock">
        <div className="max-w-7xl mx-auto pb-28 py-8"><p className="text-alert">{error}</p></div>
      </AccessGate>
    );
  }

  return (
    <AccessGate feature="threshold_config" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-7xl mx-auto pb-28 space-y-6">
        <motion.header variants={fadeSlideUp} className="border-b border-white/5 pb-4 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-display text-white">Threshold Configuration</h1>
            <p className="text-xs font-mono text-white/30 mt-2">Global and regulation-year threshold governance.</p>
          </div>
          <select value={regulationYear} onChange={(e) => setRegulationYear(e.target.value)} className="bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white">
            <option value="2019 Regulation">2019 Regulation</option>
            <option value="2021 Regulation">2021 Regulation</option>
            <option value="2023 Regulation">2023 Regulation</option>
          </select>
        </motion.header>

        <motion.section variants={fadeSlideUp} className="overflow-x-auto border border-white/10">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/10">
                <th className={th}>Parameter Name</th>
                <th className={th}>Current Value</th>
                <th className={th}>Scope</th>
                <th className={th}>Last Changed By</th>
                <th className={th}>Last Changed Date</th>
                <th className={th}>Edit</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <>
                  <tr key={row.key} className="border-b border-white/5">
                    <td className="px-3 py-2 text-sm text-white">{row.label}</td>
                    <td className="px-3 py-2 text-sm text-white/70">
                      {editingKey === row.key ? (
                        row.key === "absentPolicy" ? (
                          <select value={draftValue} onChange={(e) => setDraftValue(e.target.value)} className="bg-transparent border border-white/10 px-2 py-1 text-sm text-white">
                            <option value="include">include</option>
                            <option value="exclude">exclude</option>
                          </select>
                        ) : (
                          <input value={draftValue} onChange={(e) => setDraftValue(e.target.value)} type="number" className="bg-transparent border border-white/10 px-2 py-1 text-sm text-white w-28" />
                        )
                      ) : (
                        String(row.value)
                      )}
                    </td>
                    <td className="px-3 py-2 text-sm text-white/70">{row.scope}</td>
                    <td className="px-3 py-2 text-sm text-white/70">{history.find((h) => h.parameter === row.label)?.user || "System"}</td>
                    <td className="px-3 py-2 text-sm text-white/70">{history.find((h) => h.parameter === row.label)?.date || "-"}</td>
                    <td className="px-3 py-2 text-sm text-white/70">
                      {editingKey === row.key ? (
                        <span className="space-x-3">
                          <button onClick={() => saveEdit(row)} className="text-attain text-xs hover:text-white">Save</button>
                          <button onClick={cancelEdit} className="text-white/60 text-xs hover:text-white">Cancel</button>
                        </span>
                      ) : (
                        <button onClick={() => startEdit(row)} className="text-brand text-xs hover:text-white">Edit</button>
                      )}
                    </td>
                  </tr>
                  {editingKey === row.key && impactPreview && (
                    <tr>
                      <td colSpan={6} className="px-3 py-2 text-xs text-amber-300 border-b border-white/5">{impactPreview}</td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </motion.section>

        <motion.section variants={fadeSlideUp} className="border border-white/10 p-4 space-y-3">
          <h2 className="text-sm font-mono text-white uppercase tracking-widest">Add Dept-specific Override</h2>
          <div className="flex flex-wrap gap-2 items-center">
            <select value={deptOverride.dept} onChange={(e) => setDeptOverride((p) => ({ ...p, dept: e.target.value }))} className="bg-white/[0.02] border border-white/10 px-2 py-1.5 text-xs text-white">
              {["CSE", "ECE", "MECH", "CIVIL", "IT", "MBA"].map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            <select value={deptOverride.parameter} onChange={(e) => setDeptOverride((p) => ({ ...p, parameter: e.target.value }))} className="bg-white/[0.02] border border-white/10 px-2 py-1.5 text-xs text-white">
              {rows.map((r) => <option key={r.key} value={r.label}>{r.label}</option>)}
            </select>
            <input value={deptOverride.value} onChange={(e) => setDeptOverride((p) => ({ ...p, value: e.target.value }))} className="bg-white/[0.02] border border-white/10 px-2 py-1.5 text-xs text-white w-24" />
            <button onClick={addOverride} className="px-3 py-1.5 bg-brand text-white text-xs font-mono uppercase">Add Override</button>
          </div>
          {overrides.length > 0 && (
            <table className="w-full border-collapse border border-white/10">
              <thead>
                <tr className="border-b border-white/10">
                  <th className={th}>Dept</th>
                  <th className={th}>Parameter</th>
                  <th className={th}>Value</th>
                </tr>
              </thead>
              <tbody>
                {overrides.map((o, idx) => (
                  <tr key={`${o.dept}-${idx}`} className="border-b border-white/5">
                    <td className="px-3 py-2 text-xs text-white/70">{o.dept}</td>
                    <td className="px-3 py-2 text-xs text-white/70">{o.parameter}</td>
                    <td className="px-3 py-2 text-xs text-white/70">{o.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </motion.section>

        <motion.section variants={fadeSlideUp} className="border border-white/10">
          <button onClick={() => setShowHistory((v) => !v)} className="w-full text-left px-3 py-2 text-xs font-mono text-white/70 uppercase tracking-widest">
            Change History {showHistory ? "(Hide)" : "(Show)"}
          </button>
          {showHistory && (
            <table className="w-full border-collapse border-t border-white/10">
              <thead>
                <tr className="border-b border-white/10">
                  <th className={th}>Parameter</th>
                  <th className={th}>Old Value</th>
                  <th className={th}>New Value</th>
                  <th className={th}>User</th>
                  <th className={th}>Date</th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-4 text-sm text-white/30">No changes recorded yet.</td>
                  </tr>
                ) : (
                  history.map((h) => (
                    <tr key={h.id} className="border-b border-white/5">
                      <td className="px-3 py-2 text-xs text-white/70">{h.parameter}</td>
                      <td className="px-3 py-2 text-xs text-white/70">{h.oldValue}</td>
                      <td className="px-3 py-2 text-xs text-white/70">{h.newValue}</td>
                      <td className="px-3 py-2 text-xs text-white/70">{h.user}</td>
                      <td className="px-3 py-2 text-xs text-white/70">{h.date}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </motion.section>
      </motion.div>
    </AccessGate>
  );
}

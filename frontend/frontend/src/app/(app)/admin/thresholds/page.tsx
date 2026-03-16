"use client";

import { useMemo, useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { AccessGate } from "@/components/auth/AccessGate";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import apiClient from "@/lib/apiClient";
import { useAuthStore } from "@/lib/authStore";
import { useUIStore } from "@/lib/uiStore";

type ParamKey = "targetPassPct" | "level3" | "level2" | "cieWeight" | "seeWeight" | "minCOs" | "maxCOs" | "absentPolicy";

type ParamRow = {
  key: ParamKey;
  label: string;
  scope: string;
  value: number | string;
  backendKey?: string; // set if this param is persisted to backend
};

type ThresholdHistoryItem = {
  id: string;
  parameter: string;
  oldValue: string;
  newValue: string;
  user: string;
  date: string;
};

const LS_EXTRAS = "admin_threshold_extras";
const LS_OVERRIDES = "admin_threshold_overrides";
const LS_HISTORY = "admin_threshold_history";

function lsGet(key: string, fallback: any) {
  try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch { return fallback; }
}
function lsSet(key: string, val: any) {
  try { localStorage.setItem(key, JSON.stringify(val)); } catch {}
}

const EXTRAS_DEFAULTS = { targetPassPct: 60, cieWeight: 40, seeWeight: 60, minCOs: 4, maxCOs: 6, absentPolicy: "include" };

export default function AdminThresholdsPage() {
  const { user } = useAuthStore();
  const { addToast } = useUIStore();

  const [thresholds, setThresholdsState] = useState<{ level2: number; level3: number }>({ level2: 60, level3: 70 });
  const [extras, setExtras] = useState<Record<string, any>>(EXTRAS_DEFAULTS);
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [regulationYear, setRegulationYear] = useState("2023 Regulation");
  const [editingKey, setEditingKey] = useState<ParamKey | null>(null);
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
      setCourses(Array.isArray(c) ? c : (c as any)?.items ?? []);
    } catch (e: any) {
      setError(e?.message || "Failed to load thresholds");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    setExtras({ ...EXTRAS_DEFAULTS, ...lsGet(LS_EXTRAS, {}) });
    setOverrides(lsGet(LS_OVERRIDES, []));
    setHistory(lsGet(LS_HISTORY, []));
  }, [load]);

  const rows: ParamRow[] = [
    { key: "targetPassPct", label: "Target Pass%", value: extras.targetPassPct, scope: "Global" },
    { key: "level3", label: "Level 3 Cutoff%", value: thresholds.level3, scope: "Global", backendKey: "level3" },
    { key: "level2", label: "Level 2 Cutoff%", value: thresholds.level2, scope: "Global", backendKey: "level2" },
    { key: "cieWeight", label: "CIE Weightage%", value: extras.cieWeight, scope: "Global" },
    { key: "seeWeight", label: "SEE Weightage%", value: extras.seeWeight, scope: "Global" },
    { key: "minCOs", label: "Min COs", value: extras.minCOs, scope: "Regulation Year" },
    { key: "maxCOs", label: "Max COs", value: extras.maxCOs, scope: "Regulation Year" },
    { key: "absentPolicy", label: "Absent Student Policy", value: extras.absentPolicy, scope: "Global" },
  ];

  const impactPreview = useMemo(() => {
    if (!editingKey || draftValue.length === 0) return "";
    const changed = Math.max(1, Math.round(courses.length * 0.35));
    return `If saved: ~${changed} of ${courses.length || 1} courses may change attainment level.`;
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
    const isAbsent = row.key === "absentPolicy";
    const newValue = isAbsent ? draftValue : String(Number(draftValue));

    if (row.backendKey) {
      // level2 / level3 → save to backend
      try {
        const numVal = Number(draftValue) / 100;
        if (numVal < 0 || numVal > 1) { addToast("Value must be between 0 and 100.", "error"); return; }
        await apiClient.setThresholds({ [row.backendKey]: numVal });
        setThresholdsState((prev) => ({ ...prev, [row.key]: Number(draftValue) }));
      } catch (err: any) {
        addToast(err?.message || "Failed to save", "error");
        return;
      }
    } else {
      // All other params → persist to localStorage
      const updated = { ...extras, [row.key]: isAbsent ? draftValue : Number(draftValue) };
      setExtras(updated);
      lsSet(LS_EXTRAS, updated);
    }

    const entry: ThresholdHistoryItem = {
      id: `${Date.now()}-${row.key}`,
      parameter: row.label,
      oldValue,
      newValue,
      user: user?.name || "Admin",
      date: new Date().toLocaleString(),
    };
    const updatedHistory = [entry, ...history];
    setHistory(updatedHistory);
    lsSet(LS_HISTORY, updatedHistory.slice(0, 50));
    addToast(`${row.label} saved.`, "success");
    cancelEdit();
  }

  function addOverride() {
    const updated = [...overrides, deptOverride];
    setOverrides(updated);
    lsSet(LS_OVERRIDES, updated);
    addToast("Department-specific override saved.", "success");
    setDeptOverride({ dept: "CSE", parameter: "Target Pass%", value: "50" });
  }

  function removeOverride(idx: number) {
    const updated = overrides.filter((_, i) => i !== idx);
    setOverrides(updated);
    lsSet(LS_OVERRIDES, updated);
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
            <p className="text-xs font-mono text-white/30 mt-2">
              Level 2 / Level 3 saved to backend. Other params persisted locally per browser.
            </p>
          </div>
          <select value={regulationYear} onChange={(e) => setRegulationYear(e.target.value)} className="bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white">
            <option value="2019 Regulation">2019 Regulation</option>
            <option value="2021 Regulation">2021 Regulation</option>
            <option value="2023 Regulation">2023 Regulation</option>
          </select>
        </motion.header>

        {/* Parameters table */}
        <motion.section variants={fadeSlideUp} className="overflow-x-auto border border-white/10">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/10">
                <th className={th}>Parameter</th>
                <th className={th}>Value</th>
                <th className={th}>Scope</th>
                <th className={th}>Storage</th>
                <th className={th}>Last Changed By</th>
                <th className={th}>Date</th>
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
                    <td className="px-3 py-2 text-sm text-white/50">{row.scope}</td>
                    <td className="px-3 py-2 text-xs font-mono">
                      {row.backendKey
                        ? <span className="text-attain">Backend</span>
                        : <span className="text-amber-400">Local</span>}
                    </td>
                    <td className="px-3 py-2 text-sm text-white/50">{history.find((h) => h.parameter === row.label)?.user || "System"}</td>
                    <td className="px-3 py-2 text-sm text-white/50">{history.find((h) => h.parameter === row.label)?.date || "—"}</td>
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
                    <tr key={`${row.key}-impact`}>
                      <td colSpan={7} className="px-3 py-2 text-xs text-amber-300 border-b border-white/5">{impactPreview}</td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </motion.section>

        {/* Dept overrides */}
        <motion.section variants={fadeSlideUp} className="border border-white/10 p-4 space-y-3">
          <h2 className="text-sm font-mono text-white uppercase tracking-widest">Dept-specific Overrides</h2>
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
                  <th className={th}>Dept</th><th className={th}>Parameter</th><th className={th}>Value</th><th className={th}></th>
                </tr>
              </thead>
              <tbody>
                {overrides.map((o, idx) => (
                  <tr key={`${o.dept}-${idx}`} className="border-b border-white/5">
                    <td className="px-3 py-2 text-xs text-white/70">{o.dept}</td>
                    <td className="px-3 py-2 text-xs text-white/70">{o.parameter}</td>
                    <td className="px-3 py-2 text-xs text-white/70">{o.value}</td>
                    <td className="px-3 py-2">
                      <button onClick={() => removeOverride(idx)} className="text-xs text-alert hover:text-white">Remove</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </motion.section>

        {/* Change history */}
        <motion.section variants={fadeSlideUp} className="border border-white/10">
          <button onClick={() => setShowHistory((v) => !v)} className="w-full text-left px-3 py-2 text-xs font-mono text-white/70 uppercase tracking-widest">
            Change History {showHistory ? "(Hide)" : "(Show)"}
          </button>
          {showHistory && (
            <table className="w-full border-collapse border-t border-white/10">
              <thead>
                <tr className="border-b border-white/10">
                  <th className={th}>Parameter</th><th className={th}>Old</th><th className={th}>New</th><th className={th}>User</th><th className={th}>Date</th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 ? (
                  <tr><td colSpan={5} className="px-3 py-4 text-sm text-white/30">No changes recorded yet.</td></tr>
                ) : history.map((h) => (
                  <tr key={h.id} className="border-b border-white/5">
                    <td className="px-3 py-2 text-xs text-white/70">{h.parameter}</td>
                    <td className="px-3 py-2 text-xs text-white/70">{h.oldValue}</td>
                    <td className="px-3 py-2 text-xs text-white/70">{h.newValue}</td>
                    <td className="px-3 py-2 text-xs text-white/70">{h.user}</td>
                    <td className="px-3 py-2 text-xs text-white/70">{h.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </motion.section>
      </motion.div>
    </AccessGate>
  );
}

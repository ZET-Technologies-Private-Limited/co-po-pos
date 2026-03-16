"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";
import { AlertCircle, ChevronDown, ChevronUp, Info, RefreshCw } from "lucide-react";

// ── helpers ──────────────────────────────────────────────────────────────────

function lvlColor(level: string | undefined) {
  const l = (level || "").toUpperCase();
  if (l.includes("3")) return "text-emerald-400";
  if (l.includes("2")) return "text-amber-400";
  return "text-red-400";
}

function lvlBg(level: string | undefined) {
  const l = (level || "").toUpperCase();
  if (l.includes("3")) return "bg-emerald-500/10 border-emerald-500/30";
  if (l.includes("2")) return "bg-amber-500/10 border-amber-500/30";
  return "bg-red-500/10 border-red-500/30";
}

function PctBar({ pct, l3, l2 }: { pct: number; l3: number; l2: number }) {
  const c = Math.min(100, Math.max(0, pct));
  const color = c >= l3 ? "bg-emerald-500" : c >= l2 ? "bg-amber-500" : "bg-red-500";
  const lvl = c >= l3 ? "L3" : c >= l2 ? "L2" : "L1";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${c}%` }} />
      </div>
      <span className={`text-xs font-mono w-12 text-right ${lvlColor(lvl)}`}>
        {c.toFixed(1)}%
      </span>
    </div>
  );
}

function FormulaBox({ text }: { text: string }) {
  return (
    <div className="mt-1 px-2 py-1 bg-white/[0.03] border border-white/10 rounded text-[10px] font-mono text-white/40 break-all">
      {text}
    </div>
  );
}

function getCOPct(value: any): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string") {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }
  if (value && typeof value === "object") {
    const candidate = value.percent ?? value.percentage ?? value.pct;
    const n = Number(candidate);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

// ── NBA level thresholds — fetched from backend, not hardcoded ───────────────
function getNbaLevels(l3: number, l2: number) {
  return [
    { level: "Level 3", range: `≥ ${l3}%`, label: "Target fully achieved", color: "text-emerald-400" },
    { level: "Level 2", range: `${l2}–${l3 - 1}%`, label: "Target mostly achieved", color: "text-amber-400" },
    { level: "Level 1", range: `< ${l2}%`, label: "Below expectation — CAP required", color: "text-red-400" },
  ];
}

// ── main component ────────────────────────────────────────────────────────────

export default function FacultyCOAttainmentPage() {
  const { id } = useParams();
  const courseId = Array.isArray(id) ? id[0] : id;

  const [course, setCourse] = useState<any>(null);
  const [workflow, setWorkflow] = useState<any>(null);
  const [students, setStudents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [showFormulas, setShowFormulas] = useState(false);
  const [expandedCO, setExpandedCO] = useState<string | null>(null);

  const [thresholdPct, setThresholdPct] = useState(0.40);
  const [faMethod, setFaMethod] = useState<"best_n_of_m" | "simple_avg" | "weighted">("best_n_of_m");
  const [faBestN, setFaBestN] = useState(3);
  // live NBA level thresholds from backend (admin-configurable)
  const [l3, setL3] = useState(60);
  const [l2, setL2] = useState(50);

  // fetch live thresholds once on mount
  useEffect(() => {
    apiClient.getThresholds?.().then((t: any) => {
      if (t?.level3) setL3(Math.round(t.level3 * 100));
      if (t?.level2) setL2(Math.round(t.level2 * 100));
      if (t?.pass_threshold) setThresholdPct(t.pass_threshold);
    }).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    if (!courseId || typeof courseId !== "string") {
      setError("Invalid course id in route.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setWarning(null);
    try {
      const c = await apiClient.getCourse(courseId);
      setCourse(c);

      const resolvedCourseId = typeof c?.id === "string" && c.id ? c.id : courseId;
      const [wf, st] = await Promise.allSettled([
        apiClient.getOBEWorkflow(resolvedCourseId, {
          threshold_pct: thresholdPct,
          fa_method: faMethod,
          fa_best_n: faBestN,
        }),
        apiClient.getStudentPerformance(resolvedCourseId),
      ]);

      if (wf.status === "fulfilled") {
        setWorkflow(wf.value);
      } else {
        setWorkflow({ co_attainments: [], po_attainments: [], config: {}, nba_formulas: {} });
        const msg = typeof wf.reason?.message === "string" ? wf.reason.message : "Workflow data is unavailable.";
        setWarning(
          /not found|http 404/i.test(msg)
            ? "OBE workflow data is not available yet for this course. Complete exam configuration, question mapping, and marks approval in order, then recalculate."
            : msg
        );
      }

      if (st.status === "fulfilled") {
        setStudents(Array.isArray(st.value?.students) ? st.value.students : Array.isArray(st.value) ? st.value : []);
      } else {
        setStudents([]);
        const msg = typeof st.reason?.message === "string" ? st.reason.message : "Student performance data is unavailable.";
        setWarning((prev) => prev ?? msg);
      }
    } catch (e: any) {
      const msg = typeof e?.message === "string" ? e.message : "Failed to load attainment data.";
      setError(msg === "Not Found" ? "Requested course/attainment endpoint not found for this course." : msg);
    } finally {
      setLoading(false);
    }
  }, [courseId, thresholdPct, faMethod, faBestN]);

  useEffect(() => { void load(); }, [load]);

  const coRows: any[] = Array.isArray(workflow?.co_attainments) ? workflow.co_attainments : [];
  const poRows: any[] = Array.isArray(workflow?.po_attainments) ? workflow.po_attainments : [];
  const gapCOs = coRows.filter((r) => r.gap_flag && !r.not_assessed);
  const config = workflow?.config || {};
  const formulas = workflow?.nba_formulas || {};
  const studentCoKeys = useMemo(() => {
    const keys = students[0]?.co_breakdown ? Object.keys(students[0].co_breakdown) : [];
    return keys
      .slice(0, 6)
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }));
  }, [students]);

  return (
    <AccessGate feature="co_attainment" deny="lock">
      <div className="w-full pb-24 space-y-8">

        {/* Header */}
        <section className="border border-white/10 bg-gradient-to-r from-white/[0.04] to-white/[0.01] px-6 py-5">
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
            <div>
              <h1 className="text-3xl text-white font-display">CO Attainment</h1>
              <p className="text-white/40 text-sm mt-1 font-mono">
                {course?.course_code} — {course?.course_name || "Loading..."}
              </p>
            </div>
            <button
              onClick={() => void load()}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono border border-white/20 text-white/50 hover:text-white hover:border-white/40 transition-colors disabled:opacity-40"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} /> Recalculate
            </button>
          </div>

          {/* Config row */}
          <div className="flex flex-wrap items-center gap-4 mt-5">
            <label className="flex items-center gap-2 text-xs font-mono text-white/50">
              Threshold
              <select
                value={thresholdPct}
                onChange={(e) => setThresholdPct(Number(e.target.value))}
                className="bg-transparent border border-white/20 px-2 py-1 text-white text-xs focus:outline-none"
              >
                <option value={0.40}>40%</option>
                <option value={0.50}>50%</option>
                <option value={0.60}>60%</option>
              </select>
            </label>
            <label className="flex items-center gap-2 text-xs font-mono text-white/50">
              FA Method
              <select
                value={faMethod}
                onChange={(e) => setFaMethod(e.target.value as any)}
                className="bg-transparent border border-white/20 px-2 py-1 text-white text-xs focus:outline-none"
              >
                <option value="best_n_of_m">Best N of M (NBA default)</option>
                <option value="simple_avg">Simple Average</option>
                <option value="weighted">Weighted (T1=10%…T5=30%)</option>
              </select>
            </label>
            {faMethod === "best_n_of_m" && (
              <label className="flex items-center gap-2 text-xs font-mono text-white/50">
                Best N
                <select
                  value={faBestN}
                  onChange={(e) => setFaBestN(Number(e.target.value))}
                  className="bg-transparent border border-white/20 px-2 py-1 text-white text-xs focus:outline-none"
                >
                  {[2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </label>
            )}
            <button
              onClick={() => setShowFormulas((v) => !v)}
              className="flex items-center gap-1.5 text-xs font-mono text-white/30 hover:text-white/60 transition-colors"
            >
              <Info className="w-3 h-3" /> {showFormulas ? "Hide" : "Show"} NBA Formulas
            </button>
          </div>

          {/* NBA level legend */}
          <div className="flex flex-wrap gap-3 mt-4">
            {getNbaLevels(l3, l2).map((l) => (
              <span key={l.level} className={`text-[10px] font-mono px-2 py-1 border ${lvlBg(l.level)} ${l.color}`}>
                {l.level} ({l.range}) — {l.label}
              </span>
            ))}
          </div>
        </section>

        {loading && <p className="text-white/50 text-sm px-2">Calculating attainment...</p>}
        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm border border-red-500/30 bg-red-500/5 px-4 py-3">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}
        {warning && !error && (
          <div className="flex items-center gap-2 text-amber-300 text-sm border border-amber-500/30 bg-amber-500/5 px-4 py-3">
            <Info className="w-4 h-4 shrink-0" /> {warning}
          </div>
        )}

        {/* NBA Formulas panel */}
        {showFormulas && formulas && (
          <section className="border border-white/10 bg-white/[0.015] p-5 space-y-2">
            <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-3">NBA Calculation Formulas</h2>
            {Object.entries(formulas).map(([k, v]) => (
              <div key={k} className="flex gap-3">
                <span className="text-[10px] font-mono text-white/30 w-28 shrink-0 uppercase">{k.replace(/_/g, " ")}</span>
                <span className="text-[10px] font-mono text-white/60 break-all">{String(v)}</span>
              </div>
            ))}
            <div className="mt-3 pt-3 border-t border-white/10 text-[10px] font-mono text-white/30">
              Config active: threshold={config.threshold_pct}% | FA={config.fa_method} | FA_w={config.fa_weight} | SA_w={config.sa_weight} | Direct_w={config.direct_weight} | Indirect_w={config.indirect_weight}
            </div>
          </section>
        )}

        {!loading && !error && (
          <>
            {/* CO Attainment Table — full NBA breakdown */}
            <section className="border border-white/10 bg-white/[0.015] p-5">
              <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">
                Course Outcome Attainment — NBA 80:20 Blend ({coRows.length} COs)
              </h2>

              {coRows.length === 0 ? (
                <p className="text-white/30 text-sm italic py-6">
                  No attainment data. Upload marks and ensure questions are mapped to COs.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-white/10 bg-white/[0.02]">
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-left px-3 w-16">CO</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-left px-3">Statement</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-center px-2 w-20">FA%</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-center px-2 w-20">SA%</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-center px-2 w-20">Direct%</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-center px-2 w-20">Indirect%</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-left px-3 w-40">Final%</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-center px-2 w-20">Level</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-center px-2 w-28">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {coRows.map((row: any) => {
                        const isExpanded = expandedCO === row.co_code;
                        const isGap = row.gap_flag;
                        return (
                          <>
                            <tr
                              key={row.co_code}
                              className={`border-b border-white/5 hover:bg-white/[0.02] transition-colors cursor-pointer ${isGap ? "bg-red-500/[0.03]" : ""}`}
                              onClick={() => setExpandedCO(isExpanded ? null : row.co_code)}
                            >
                              <td className="py-3 px-3 font-mono text-xs text-brand font-medium">{row.co_code}</td>
                              <td className="py-3 px-3 text-white/70 text-xs max-w-xs pr-4">
                                <span className="line-clamp-2">{row.co_statement || "—"}</span>
                                <span className="text-[10px] text-white/30 font-mono ml-1">({row.bloom_level})</span>
                              </td>
                              <td className="py-3 px-2 text-center font-mono text-xs text-white/60">{row.fa_att?.toFixed(1) ?? "—"}</td>
                              <td className="py-3 px-2 text-center font-mono text-xs text-white/60">{row.sa_att?.toFixed(1) ?? "—"}</td>
                              <td className="py-3 px-2 text-center font-mono text-xs text-white/70">{row.direct_att?.toFixed(1) ?? "—"}</td>
                              <td className="py-3 px-2 text-center font-mono text-xs text-white/50">
                                {row.indirect_att != null ? `${row.indirect_att.toFixed(1)}` : <span className="text-white/20">N/A</span>}
                              </td>
                              <td className="py-3 px-3 w-40"><PctBar pct={row.final_att ?? 0} l3={l3} l2={l2} /></td>
                              <td className="py-3 px-2 text-center">
                                <span className={`text-xs font-mono font-bold ${lvlColor(row.attainment_level)}`}>
                                  {row.attainment_level || "—"}
                                </span>
                              </td>
                              <td className="py-3 px-2 text-center">
                                {row.not_assessed ? (
                                  <span className="text-[10px] font-mono px-2 py-0.5 border border-white/20 text-white/30 bg-white/5">
                                    Not Assessed
                                  </span>
                                ) : (
                                  <span className={`text-[10px] font-mono px-2 py-0.5 border ${isGap ? "border-red-500/40 text-red-400 bg-red-500/10" : "border-emerald-500/30 text-emerald-400 bg-emerald-500/5"}`}>
                                    {isGap ? "CAP Required ✗" : "Attained ✓"}
                                  </span>
                                )}
                              </td>
                            </tr>
                            {isExpanded && (
                              <tr key={`${row.co_code}-detail`} className="border-b border-white/5 bg-white/[0.015]">
                                <td colSpan={9} className="px-6 py-4">
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                                    <div>
                                      <p className="text-[10px] font-mono text-white/30 uppercase mb-2">Calculation Steps</p>
                                      <div className="space-y-2">
                                        <div>
                                          <span className="text-white/40 font-mono">FA Attainment:</span>
                                          <FormulaBox text={row.fa_formula || "—"} />
                                        </div>
                                        <div>
                                          <span className="text-white/40 font-mono">SA Attainment:</span>
                                          <FormulaBox text={row.sa_formula || "—"} />
                                        </div>
                                        <div>
                                          <span className="text-white/40 font-mono">Direct Attainment:</span>
                                          <FormulaBox text={row.direct_formula || "—"} />
                                        </div>
                                        <div>
                                          <span className="text-white/40 font-mono">Final (80:20 blend):</span>
                                          <FormulaBox text={row.final_formula || "—"} />
                                        </div>
                                      </div>
                                    </div>
                                    {row.gap_flag && row.cap_action && (
                                      <div className="border border-red-500/20 bg-red-500/5 p-3">
                                        <p className="text-[10px] font-mono text-red-400 uppercase mb-2">Corrective Action Plan (CAP)</p>
                                        <p className="text-xs text-red-300/80">{row.cap_action}</p>
                                        <p className="text-[10px] text-white/30 mt-2 font-mono">
                                          Target: Level {row.target_level} | Achieved: {row.attainment_level}
                                        </p>
                                      </div>
                                    )}
                                    {!row.has_indirect && (
                                      <div className="border border-amber-500/20 bg-amber-500/5 p-3">
                                        <p className="text-[10px] font-mono text-amber-400 uppercase mb-1">Indirect Survey Missing</p>
                                        <p className="text-xs text-amber-300/70">
                                          No exit survey data found. Final attainment = Direct attainment only.
                                          Submit survey data via the indirect attainment endpoint to enable 80:20 blend.
                                        </p>
                                      </div>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            )}
                          </>
                        );
                      })}
                    </tbody>
                  </table>
                  <p className="text-[10px] font-mono text-white/20 mt-2">Click any row to expand calculation steps and CAP details.</p>
                </div>
              )}
            </section>

            {/* Gap Analysis Summary */}
            {gapCOs.length > 0 && (
              <section className="border border-red-500/20 bg-red-500/[0.03] p-5">
                <h2 className="text-[10px] font-mono text-red-400 uppercase tracking-widest mb-4">
                  Gap Analysis — {gapCOs.length} CO(s) Below Target Level
                </h2>
                <div className="space-y-3">
                  {gapCOs.map((co: any) => (
                    <div key={co.co_code} className="flex flex-col sm:flex-row sm:items-start gap-3 border border-red-500/10 bg-red-500/5 p-3">
                      <div className="shrink-0">
                        <span className="text-xs font-mono text-red-400 font-bold">{co.co_code}</span>
                        <span className={`ml-2 text-xs font-mono ${lvlColor(co.attainment_level)}`}>{co.attainment_level}</span>
                        <span className="ml-2 text-xs font-mono text-white/40">{co.final_att?.toFixed(1)}%</span>
                      </div>
                      <div className="flex-1">
                        <p className="text-xs text-white/60 mb-1">{co.co_statement}</p>
                        {co.cap_action && (
                          <p className="text-[11px] text-red-300/80 font-mono">
                            ▶ CAP: {co.cap_action}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* PO Attainment Summary */}
            {poRows.length > 0 && (
              <section className="border border-white/10 bg-white/[0.015] p-5">
                <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">
                  PO Attainment — Weighted by CO-PO Mapping Level
                </h2>
                <p className="text-[10px] font-mono text-white/25 mb-3">
                  Formula: PO_att = Σ(Final_CO_att × mapping_weight) / Σ(mapping_weight) | mapping: sim≥0.75→3, sim≥0.50→2, sim≥0.30→1
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left px-3 w-16">PO</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left px-3">Statement</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left px-3 w-40">Attainment</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center px-2 w-20">Level</th>
                      </tr>
                    </thead>
                    <tbody>
                      {poRows.map((po: any, i: number) => {
                        const pct = Number(po.attainment_percentage ?? po.percentage ?? 0);
                        return (
                          <tr key={po.po_code ?? i} className="border-b border-white/5 hover:bg-white/[0.02]">
                            <td className="py-2 px-3 font-mono text-xs text-brand">{po.po_code ?? po.code ?? `PO${i + 1}`}</td>
                            <td className="py-2 px-3 text-white/60 text-xs max-w-xs">{po.statement ?? po.po_statement ?? "—"}</td>
                            <td className="py-2 px-3 w-40"><PctBar pct={pct} l3={l3} l2={l2} /></td>
                            <td className="py-2 px-2 text-center">
                              <span className={`text-xs font-mono font-bold ${lvlColor(po.attainment_level ?? po.level)}`}>
                                {po.attainment_level ?? po.level ?? "—"}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* Student Performance */}
            {students.length > 0 && (
              <section className="border border-white/10 bg-white/[0.015] p-5">
                <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">
                  Student Performance ({students.length} students)
                </h2>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left px-3">Student</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center px-2 w-24">Total%</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center px-2 w-16">Grade</th>
                        {studentCoKeys.length > 0 &&
                          studentCoKeys.map((k) => (
                            <th key={k} className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center px-2 w-16">{k}</th>
                          ))}
                      </tr>
                    </thead>
                    <tbody>
                      {students.slice(0, 50).map((s: any, idx: number) => (
                        <tr key={idx} className="border-b border-white/5 hover:bg-white/[0.02]">
                          <td className="py-2 px-3 text-white/60 text-xs font-mono">{s.student_id ?? `S${idx + 1}`}</td>
                          <td className="py-2 px-2 text-center">
                            <span className={`text-xs font-mono ${lvlColor(s.level)}`}>{s.percentage?.toFixed(1) ?? "—"}%</span>
                          </td>
                          <td className="py-2 px-2 text-center text-xs font-mono text-white/50">{s.grade ?? "—"}</td>
                          {studentCoKeys.map((k) => {
                            const pct = getCOPct(s?.co_breakdown?.[k]);
                            return (
                              <td key={k} className="py-2 px-2 text-center text-xs font-mono text-white/40">
                                {pct != null ? `${pct.toFixed(0)}%` : "—"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {students.length > 50 && (
                    <p className="text-[10px] font-mono text-white/20 mt-2">Showing 50 of {students.length} students.</p>
                  )}
                </div>
              </section>
            )}

            {/* Summary stats */}
            {workflow?.summary && (
              <section className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: "Total COs", value: workflow.summary.total_cos },
                  { label: "COs Attained", value: workflow.summary.cos_attained, color: "text-emerald-400" },
                  { label: "COs with Gap", value: workflow.summary.cos_gap, color: workflow.summary.cos_gap > 0 ? "text-red-400" : "text-white" },
                  { label: "Avg Final Att%", value: `${workflow.summary.avg_final_attainment?.toFixed(1)}%`, color: lvlColor(workflow.summary.overall_level) },
                ].map((s) => (
                  <div key={s.label} className="border border-white/10 bg-white/[0.02] px-4 py-3">
                    <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-1">{s.label}</p>
                    <p className={`text-lg font-mono font-bold ${s.color || "text-white"}`}>{s.value}</p>
                  </div>
                ))}
              </section>
            )}
          </>
        )}
      </div>
    </AccessGate>
  );
}

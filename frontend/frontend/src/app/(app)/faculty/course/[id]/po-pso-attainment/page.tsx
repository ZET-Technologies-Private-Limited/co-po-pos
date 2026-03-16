"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";
import { ChevronDown, ChevronRight, Info } from "lucide-react";

const NBA_PO_DEFINITIONS: Record<string, string> = {
  PO1: "Engineering Knowledge — Apply mathematics, science, and engineering fundamentals to solve complex problems.",
  PO2: "Problem Analysis — Identify, formulate, and analyze complex engineering problems using first principles.",
  PO3: "Design/Development — Design solutions for complex problems meeting specified needs with societal/environmental constraints.",
  PO4: "Conduct Investigations — Use research-based knowledge to investigate complex problems and draw valid conclusions.",
  PO5: "Modern Tool Usage — Create, select, and apply appropriate techniques and modern engineering tools.",
  PO6: "Engineer & Society — Apply reasoning to assess societal, health, safety, legal, and cultural issues.",
  PO7: "Environment & Sustainability — Understand the impact of engineering solutions in societal and environmental contexts.",
  PO8: "Ethics — Apply ethical principles and commit to professional ethics and responsibilities.",
  PO9: "Individual & Team Work — Function effectively as an individual and as a member or leader in diverse teams.",
  PO10: "Communication — Communicate effectively on complex engineering activities with the engineering community.",
  PO11: "Project Management — Demonstrate knowledge and understanding of engineering management principles.",
  PO12: "Life-long Learning — Recognize the need for and engage in independent and life-long learning.",
};

function asArray<T = any>(value: any): T[] {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.items)) return value.items;
  if (Array.isArray(value?.rows)) return value.rows;
  if (Array.isArray(value?.attainments)) return value.attainments;
  if (Array.isArray(value?.mappings)) return value.mappings;
  return [];
}

export default function FacultyPOPsoAttainmentPage() {
  const { id } = useParams();
  const courseId = id as string;

  const [course, setCourse] = useState<any>(null);
  const [programOutcomes, setProgramOutcomes] = useState<any[]>([]);
  const [programSpecificOutcomes, setProgramSpecificOutcomes] = useState<any[]>([]);
  const [coPoMappings, setCoPoMappings] = useState<any>(null);
  const [coPsoMappings, setCoPsoMappings] = useState<any>(null);
  const [poResult, setPoResult] = useState<any>(null);
  const [psoResult, setPsoResult] = useState<any>(null);
  const [mappingThreshold, setMappingThreshold] = useState(0.3);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFormula, setShowFormula] = useState(false);
  const [showPODefs, setShowPODefs] = useState(false);

  const programId = useMemo(
    () => String(course?.program_id || course?.programId || ""),
    [course?.program_id, course?.programId],
  );

  const departmentProgramId = useMemo(() => {
    const dept = String(course?.department || "").trim().toUpperCase();
    return dept ? `DEPT:${dept}` : "";
  }, [course?.department]);

  const effectiveProgramId = useMemo(
    () => programId || departmentProgramId,
    [programId, departmentProgramId],
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const c = await apiClient.getCourse(courseId);
        if (cancelled) return;
        setCourse(c);
        const pid = String(c?.program_id || c?.programId || "");
        const dept = String(c?.department || "").trim();

        let pos: any[] = [];
        let psos: any[] = [];

        if (pid) {
          pos = asArray(await apiClient.getProgramOutcomes(pid));
          psos = asArray(await apiClient.getPSOs(pid));
        }

        if (pos.length === 0) {
          const nbaPos = asArray(await apiClient.getNBAPOs());
          pos = nbaPos.map((po: any) => ({
            code: po?.code,
            statement: po?.statement ?? po?.name ?? po?.description ?? "",
            description: po?.description ?? po?.name ?? "",
          }));
        }

        if (psos.length === 0 && dept) {
          psos = asArray(await apiClient.getDepartmentPSOs(dept));
        }

        if (cancelled) return;
        setProgramOutcomes(pos);
        setProgramSpecificOutcomes(psos);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load PO/PSO context.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [courseId]);

  async function mapToPO() {
    if (!effectiveProgramId) return;
    setWorking(true); setError(null);
    try { setCoPoMappings(await apiClient.mapCOToPO(courseId, effectiveProgramId, mappingThreshold)); }
    catch (e: any) { setError(typeof e?.message === "string" ? e.message : "Failed to map CO to PO."); }
    finally { setWorking(false); }
  }

  async function mapToPSO() {
    if (!effectiveProgramId) return;
    setWorking(true); setError(null);
    try { setCoPsoMappings(await apiClient.mapCOToPSO(courseId, effectiveProgramId, mappingThreshold)); }
    catch (e: any) { setError(typeof e?.message === "string" ? e.message : "Failed to map CO to PSO."); }
    finally { setWorking(false); }
  }

  async function calculatePO() {
    if (!effectiveProgramId) return;
    setWorking(true); setError(null);
    try { setPoResult(await apiClient.calculatePOAttainment(courseId, effectiveProgramId)); }
    catch (e: any) { setError(typeof e?.message === "string" ? e.message : "Failed to calculate PO attainment."); }
    finally { setWorking(false); }
  }

  async function calculatePSO() {
    if (!effectiveProgramId) return;
    setWorking(true); setError(null);
    try { setPsoResult(await apiClient.calculatePSOAttainment(courseId, effectiveProgramId)); }
    catch (e: any) { setError(typeof e?.message === "string" ? e.message : "Failed to calculate PSO attainment."); }
    finally { setWorking(false); }
  }

  const poRows = asArray(poResult?.attainments ?? poResult?.po_attainments ?? poResult);
  const psoRows = asArray(psoResult?.attainments ?? psoResult?.pso_attainments ?? psoResult);
  const poMapRows = asArray(coPoMappings?.mappings || coPoMappings);
  const psoMapRows = asArray(coPsoMappings?.mappings || coPsoMappings);

  const th = "px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase tracking-widest";

  return (
    <AccessGate feature="po_attainment" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">PO/PSO Attainment</h1>
          <p className="text-white/50 mt-1 text-sm">
            {course?.course_code || "Course"} — {course?.course_name || "Loading..."}
          </p>
        </div>

        {loading && <p className="text-white/60">Loading attainment context...</p>}
        {error && <p className="text-alert text-sm">{error}</p>}

        {!loading && (
          <>
            {/* NBA Formula Panel */}
            <section className="border border-white/10">
              <button
                onClick={() => setShowFormula(v => !v)}
                className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/[0.02] transition-colors"
              >
                <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
                  <Info className="w-3 h-3" /> NBA PO/PSO Weighted Formula
                </span>
                {showFormula ? <ChevronDown className="w-3.5 h-3.5 text-white/30" /> : <ChevronRight className="w-3.5 h-3.5 text-white/30" />}
              </button>
              {showFormula && (
                <div className="px-4 pb-4 space-y-3 border-t border-white/5">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                    <div className="bg-white/[0.02] border border-white/5 p-3 space-y-2">
                      <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest">PO Attainment Formula</p>
                      <p className="text-xs font-mono text-white/70">PO_att = Σ(CO_att × mapping_level) / Σ(mapping_level)</p>
                      <p className="text-[10px] text-white/40">Weighted average of CO attainments using CO-PO mapping strength (1=Low, 2=Medium, 3=High) as weights.</p>
                    </div>
                    <div className="bg-white/[0.02] border border-white/5 p-3 space-y-2">
                      <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest">PSO Attainment Formula</p>
                      <p className="text-xs font-mono text-white/70">PSO_att = Σ(CO_att × mapping_level) / Σ(mapping_level)</p>
                      <p className="text-[10px] text-white/40">Same weighted formula as PO. PSOs with no CO mapping are excluded.</p>
                    </div>
                    <div className="bg-white/[0.02] border border-white/5 p-3 space-y-2">
                      <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest">CO Attainment (input)</p>
                      <p className="text-xs font-mono text-white/70">CO_att = Direct×0.80 + Indirect×0.20</p>
                      <p className="text-[10px] text-white/40">Direct = FA×0.40 + SA×0.60. Indirect from survey (if available).</p>
                    </div>
                    <div className="bg-white/[0.02] border border-white/5 p-3 space-y-2">
                      <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest">Attainment Levels</p>
                      <div className="space-y-1">
                        <p className="text-[10px] font-mono"><span className="text-emerald-400">L3 (High)</span> — ≥ 60%</p>
                        <p className="text-[10px] font-mono"><span className="text-amber-400">L2 (Medium)</span> — 50–59%</p>
                        <p className="text-[10px] font-mono"><span className="text-red-400">L1 (Low)</span> — &lt; 50%</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* NBA PO Definitions Panel */}
            <section className="border border-white/10">
              <button
                onClick={() => setShowPODefs(v => !v)}
                className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/[0.02] transition-colors"
              >
                <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
                  <Info className="w-3 h-3" /> NBA Standard PO Definitions (PO1–PO12)
                </span>
                {showPODefs ? <ChevronDown className="w-3.5 h-3.5 text-white/30" /> : <ChevronRight className="w-3.5 h-3.5 text-white/30" />}
              </button>
              {showPODefs && (
                <div className="px-4 pb-4 border-t border-white/5">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3">
                    {Object.entries(NBA_PO_DEFINITIONS).map(([code, def]) => (
                      <div key={code} className="flex gap-3 bg-white/[0.02] border border-white/5 p-3">
                        <span className="text-xs font-mono text-brand shrink-0">{code}</span>
                        <span className="text-[11px] text-white/50 leading-relaxed">{def}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>

            {/* Controls */}
            <section className="border border-white/10 p-4 space-y-3">
              <h2 className="text-sm font-mono text-white uppercase tracking-widest">Mapping Controls</h2>
              <div className="flex flex-wrap gap-3 items-end">
                <label className="text-xs text-white/60">
                  Similarity Threshold
                  <input
                    type="number" min={0} max={1} step={0.05} value={mappingThreshold}
                    onChange={e => setMappingThreshold(Number(e.target.value))}
                    className="ml-2 w-24 bg-transparent border border-white/20 px-2 py-1 text-white text-xs"
                  />
                </label>
                <button onClick={() => void mapToPO()} disabled={working || !effectiveProgramId} className="px-3 py-1 text-xs bg-brand text-white disabled:opacity-60">Map CO to PO</button>
                <button onClick={() => void mapToPSO()} disabled={working || !effectiveProgramId} className="px-3 py-1 text-xs bg-brand text-white disabled:opacity-60">Map CO to PSO</button>
                <button onClick={() => void calculatePO()} disabled={working || !effectiveProgramId} className="px-3 py-1 text-xs bg-attain text-black disabled:opacity-60">Calculate PO</button>
                <button onClick={() => void calculatePSO()} disabled={working || !effectiveProgramId} className="px-3 py-1 text-xs bg-attain text-black disabled:opacity-60">Calculate PSO</button>
              </div>
              {!programId && effectiveProgramId && <p className="text-amber-300 text-xs">Program ID not set on course. Using department context: {effectiveProgramId}.</p>}
              {!effectiveProgramId && <p className="text-amber-300 text-xs">This course is missing program and department mapping.</p>}
              {effectiveProgramId && programOutcomes.length === 0 && <p className="text-amber-300 text-xs">No POs found for this program context.</p>}
              {effectiveProgramId && programSpecificOutcomes.length === 0 && <p className="text-amber-300 text-xs">No PSOs found for this program context.</p>}
            </section>

            {/* PO / PSO lists */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-white/10 p-4">
                <h2 className="text-sm font-mono text-white uppercase tracking-widest mb-3">Program Outcomes ({programOutcomes.length})</h2>
                {programOutcomes.length === 0 ? <p className="text-white/40 text-xs">No POs found.</p> : (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {programOutcomes.map((po: any, i: number) => (
                      <div key={po.id ?? i} className="flex gap-3">
                        <span className="text-xs font-mono text-brand shrink-0">{po.code ?? `PO${i + 1}`}</span>
                        <span className="text-xs text-white/60">{po.statement ?? po.description ?? ""}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="border border-white/10 p-4">
                <h2 className="text-sm font-mono text-white uppercase tracking-widest mb-3">Program Specific Outcomes ({programSpecificOutcomes.length})</h2>
                {programSpecificOutcomes.length === 0 ? <p className="text-white/40 text-xs">No PSOs found.</p> : (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {programSpecificOutcomes.map((pso: any, i: number) => (
                      <div key={pso.id ?? i} className="flex gap-3">
                        <span className="text-xs font-mono text-aurora shrink-0">{pso.code ?? `PSO${i + 1}`}</span>
                        <span className="text-xs text-white/60">{pso.statement ?? pso.description ?? ""}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>

            {/* Mapping results */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-white/10 p-4">
                <h2 className="text-sm font-mono text-white uppercase tracking-widest mb-2">CO-PO Mappings ({poMapRows.length})</h2>
                {coPoMappings === null ? <p className="text-white/40 text-xs">Click &apos;Map CO to PO&apos; to generate.</p> : (
                  <div className="overflow-x-auto max-h-48 overflow-y-auto">
                    <table className="w-full border-collapse">
                      <thead><tr className="border-b border-white/10"><th className={th}>CO</th><th className={th}>PO</th><th className={th}>Score</th></tr></thead>
                      <tbody>
                        {poMapRows.map((m: any, i: number) => (
                          <tr key={i} className="border-b border-white/5">
                            <td className="px-3 py-1 text-xs text-white/70 font-mono">{m.co_code ?? m.co ?? "—"}</td>
                            <td className="px-3 py-1 text-xs text-white/70 font-mono">{m.po_code ?? m.po ?? "—"}</td>
                            <td className="px-3 py-1 text-xs text-white/70">{m.similarity_score ?? m.score ?? "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
              <div className="border border-white/10 p-4">
                <h2 className="text-sm font-mono text-white uppercase tracking-widest mb-2">CO-PSO Mappings ({psoMapRows.length})</h2>
                {coPsoMappings === null ? <p className="text-white/40 text-xs">Click &apos;Map CO to PSO&apos; to generate.</p> : (
                  <div className="overflow-x-auto max-h-48 overflow-y-auto">
                    <table className="w-full border-collapse">
                      <thead><tr className="border-b border-white/10"><th className={th}>CO</th><th className={th}>PSO</th><th className={th}>Score</th></tr></thead>
                      <tbody>
                        {psoMapRows.map((m: any, i: number) => (
                          <tr key={i} className="border-b border-white/5">
                            <td className="px-3 py-1 text-xs text-white/70 font-mono">{m.co_code ?? m.co ?? "—"}</td>
                            <td className="px-3 py-1 text-xs text-white/70 font-mono">{m.pso_code ?? m.pso ?? "—"}</td>
                            <td className="px-3 py-1 text-xs text-white/70">{m.similarity_score ?? m.score ?? "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </section>

            {/* Attainment results */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-white/10 p-4">
                <h2 className="text-sm font-mono text-white uppercase tracking-widest mb-2">PO Attainment ({poRows.length})</h2>
                {poResult === null ? <p className="text-white/40 text-xs">Run &apos;Calculate PO&apos; after CO-PO mapping and CO attainment are available.</p> : (
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                      <thead><tr className="border-b border-white/10"><th className={th}>PO</th><th className={th}>Attainment %</th><th className={th}>Level</th><th className={th}>Bar</th></tr></thead>
                      <tbody>
                        {poRows.map((r: any, i: number) => {
                          const pct = Number(r.attainment_percentage ?? r.percentage ?? 0);
                          const level = pct >= 60 ? "L3" : pct >= 50 ? "L2" : "L1";
                          const color = pct >= 60 ? "text-emerald-400" : pct >= 50 ? "text-amber-400" : "text-red-400";
                          const barColor = pct >= 60 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
                          const poCode = r.po_code ?? r.po ?? `PO${i + 1}`;
                          const poDef = NBA_PO_DEFINITIONS[poCode];
                          return (
                            <tr key={i} className="border-b border-white/5 group">
                              <td className="px-3 py-2">
                                <span className="text-xs font-mono text-brand">{poCode}</span>
                                {poDef && <p className="text-[10px] text-white/30 mt-0.5 max-w-[180px] leading-tight hidden group-hover:block">{poDef.split("—")[0]}</p>}
                              </td>
                              <td className={`px-3 py-2 text-xs font-mono ${color}`}>{pct.toFixed(1)}%</td>
                              <td className={`px-3 py-2 text-xs font-mono font-bold ${color}`}>{level}</td>
                              <td className="px-3 py-2 w-24">
                                <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                                  <div className={`h-full rounded-full ${barColor}`} style={{ width: `${Math.min(100, pct)}%` }} />
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
              <div className="border border-white/10 p-4">
                <h2 className="text-sm font-mono text-white uppercase tracking-widest mb-2">PSO Attainment ({psoRows.length})</h2>
                {psoResult === null ? <p className="text-white/40 text-xs">Run &apos;Calculate PSO&apos; after CO-PSO mapping and CO attainment are available.</p> : (
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                      <thead><tr className="border-b border-white/10"><th className={th}>PSO</th><th className={th}>Attainment %</th><th className={th}>Level</th><th className={th}>Bar</th></tr></thead>
                      <tbody>
                        {psoRows.map((r: any, i: number) => {
                          const pct = Number(r.attainment_percentage ?? r.percentage ?? 0);
                          const level = pct >= 60 ? "L3" : pct >= 50 ? "L2" : "L1";
                          const color = pct >= 60 ? "text-emerald-400" : pct >= 50 ? "text-amber-400" : "text-red-400";
                          const barColor = pct >= 60 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
                          return (
                            <tr key={i} className="border-b border-white/5">
                              <td className="px-3 py-2 text-xs font-mono text-aurora">{r.pso_code ?? r.pso ?? `PSO${i + 1}`}</td>
                              <td className={`px-3 py-2 text-xs font-mono ${color}`}>{pct.toFixed(1)}%</td>
                              <td className={`px-3 py-2 text-xs font-mono font-bold ${color}`}>{level}</td>
                              <td className="px-3 py-2 w-24">
                                <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                                  <div className={`h-full rounded-full ${barColor}`} style={{ width: `${Math.min(100, pct)}%` }} />
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </AccessGate>
  );
}

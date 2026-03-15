"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

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

  const programId = useMemo(
    () => String(course?.program_id || course?.programId || ""),
    [course?.program_id, course?.programId],
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
        if (!pid) {
          setProgramOutcomes([]);
          setProgramSpecificOutcomes([]);
          setLoading(false);
          return;
        }

        const [pos, psos] = await Promise.all([apiClient.getProgramOutcomes(pid), apiClient.getPSOs(pid)]);
        if (cancelled) return;
        setProgramOutcomes(asArray(pos));
        setProgramSpecificOutcomes(asArray(psos));
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load PO/PSO context.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  async function mapToPO() {
    if (!programId) return;
    setWorking(true);
    setError(null);
    try {
      const result = await apiClient.mapCOToPO(courseId, programId, mappingThreshold);
      setCoPoMappings(result);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to map CO to PO.");
    } finally {
      setWorking(false);
    }
  }

  async function mapToPSO() {
    if (!programId) return;
    setWorking(true);
    setError(null);
    try {
      const result = await apiClient.mapCOToPSO(courseId, programId, mappingThreshold);
      setCoPsoMappings(result);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to map CO to PSO.");
    } finally {
      setWorking(false);
    }
  }

  async function calculatePO() {
    if (!programId) return;
    setWorking(true);
    setError(null);
    try {
      const result = await apiClient.calculatePOAttainment(courseId, programId);
      setPoResult(result);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to calculate PO attainment.");
    } finally {
      setWorking(false);
    }
  }

  async function calculatePSO() {
    if (!programId) return;
    setWorking(true);
    setError(null);
    try {
      const result = await apiClient.calculatePSOAttainment(courseId, programId);
      setPsoResult(result);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to calculate PSO attainment.");
    } finally {
      setWorking(false);
    }
  }

  const poRows = asArray(poResult?.attainments || poResult);
  const psoRows = asArray(psoResult?.attainments || psoResult);

  return (
    <AccessGate feature="po_attainment" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">PO/PSO Attainment</h1>
          <p className="text-white/50 mt-1">
            {course?.course_code || "Course"} - {course?.course_name || "Loading..."}
          </p>
        </div>

        {loading ? <p className="text-white/60">Loading attainment context...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading ? (
          <>
            <section className="border border-white/10 rounded-lg p-4 space-y-3">
              <h2 className="text-sm text-white">Mapping Controls</h2>
              <div className="flex flex-wrap gap-3 items-end">
                <label className="text-xs text-white/60">
                  Similarity Threshold
                  <input
                    type="number"
                    min={0}
                    max={1}
                    step={0.05}
                    value={mappingThreshold}
                    onChange={(e) => setMappingThreshold(Number(e.target.value))}
                    className="ml-2 w-24 bg-transparent border border-white/20 rounded px-2 py-1 text-white"
                  />
                </label>
                <button
                  type="button"
                  onClick={() => void mapToPO()}
                  disabled={working || !programId}
                  className="px-3 py-1 text-xs bg-brand text-white rounded disabled:opacity-60"
                >
                  Map CO to PO
                </button>
                <button
                  type="button"
                  onClick={() => void mapToPSO()}
                  disabled={working || !programId}
                  className="px-3 py-1 text-xs bg-brand text-white rounded disabled:opacity-60"
                >
                  Map CO to PSO
                </button>
                <button
                  type="button"
                  onClick={() => void calculatePO()}
                  disabled={working || !programId}
                  className="px-3 py-1 text-xs bg-attain text-black rounded disabled:opacity-60"
                >
                  Calculate PO
                </button>
                <button
                  type="button"
                  onClick={() => void calculatePSO()}
                  disabled={working || !programId}
                  className="px-3 py-1 text-xs bg-attain text-black rounded disabled:opacity-60"
                >
                  Calculate PSO
                </button>
              </div>
              {!programId ? <p className="text-amber-300 text-xs">This course is missing a program ID mapping.</p> : null}
            </section>

            <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-white/10 rounded-lg p-4">
                <h2 className="text-sm text-white mb-2">Program Outcomes ({programOutcomes.length})</h2>
                <pre className="text-xs text-white/70 whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {JSON.stringify(programOutcomes, null, 2)}
                </pre>
              </div>
              <div className="border border-white/10 rounded-lg p-4">
                <h2 className="text-sm text-white mb-2">Program Specific Outcomes ({programSpecificOutcomes.length})</h2>
                <pre className="text-xs text-white/70 whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {JSON.stringify(programSpecificOutcomes, null, 2)}
                </pre>
              </div>
            </section>

            <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-white/10 rounded-lg p-4">
                <h2 className="text-sm text-white mb-2">CO-PO Mapping Result</h2>
                <p className="text-xs text-white/50 mb-2">Mappings: {asArray(coPoMappings?.mappings || coPoMappings).length}</p>
                <pre className="text-xs text-white/70 whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {JSON.stringify(coPoMappings, null, 2)}
                </pre>
              </div>
              <div className="border border-white/10 rounded-lg p-4">
                <h2 className="text-sm text-white mb-2">CO-PSO Mapping Result</h2>
                <p className="text-xs text-white/50 mb-2">Mappings: {asArray(coPsoMappings?.mappings || coPsoMappings).length}</p>
                <pre className="text-xs text-white/70 whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {JSON.stringify(coPsoMappings, null, 2)}
                </pre>
              </div>
            </section>

            <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-white/10 rounded-lg p-4">
                <h2 className="text-sm text-white mb-2">PO Attainment</h2>
                <p className="text-xs text-white/50 mb-2">Rows: {poRows.length}</p>
                <pre className="text-xs text-white/70 whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {JSON.stringify(poResult, null, 2)}
                </pre>
              </div>
              <div className="border border-white/10 rounded-lg p-4">
                <h2 className="text-sm text-white mb-2">PSO Attainment</h2>
                <p className="text-xs text-white/50 mb-2">Rows: {psoRows.length}</p>
                <pre className="text-xs text-white/70 whitespace-pre-wrap max-h-64 overflow-y-auto">
                  {JSON.stringify(psoResult, null, 2)}
                </pre>
              </div>
            </section>
          </>
        ) : null}
      </div>
    </AccessGate>
  );
}

"use client";

import { useEffect, useMemo, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

type ReportType = "co_attainment" | "po_attainment" | "student_performance" | "full";
type DownloadFormat = "pdf" | "excel" | "nba";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export default function FacultyCourseReportsPage() {
  const { id } = useParams();
  const courseId = id as string;

  const [course, setCourse] = useState<any>(null);
  const [visualization, setVisualization] = useState<any>(null);
  const [reportType, setReportType] = useState<ReportType>("full");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [c, viz] = await Promise.all([apiClient.getCourse(courseId), apiClient.getVisualizationData(courseId)]);
      setCourse(c);
      setVisualization(viz);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load report data.");
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    const onFocus = () => void load();
    document.addEventListener("visibilitychange", onFocus);
    return () => document.removeEventListener("visibilitychange", onFocus);
  }, [load]);

  async function generateReport() {
    setWorking(true); setError(null); setMessage(null);
    try {
      const result = await apiClient.generateReport(courseId, reportType);
      setMessage(`Report generated successfully (${result?.report_id || "id unavailable"}).`);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to generate report.");
    } finally {
      setWorking(false);
    }
  }

  async function exportReport(format: DownloadFormat) {
    setWorking(true); setError(null); setMessage(null);
    try {
      const blob = await apiClient.downloadReport(courseId, format);
      const suffix = format === "excel" || format === "nba" ? "xlsx" : "pdf";
      downloadBlob(blob, `${course?.course_code || "course"}_${reportType}_report.${suffix}`);
      setMessage(`${format.toUpperCase()} export downloaded.`);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : `Failed to download ${format.toUpperCase()} report.`);
    } finally {
      setWorking(false);
    }
  }

  const summaryStats = useMemo(() => {
    const co = Array.isArray(visualization?.co_attainment) ? visualization.co_attainment.length : 0;
    const po = Array.isArray(visualization?.po_attainment) ? visualization.po_attainment.length : 0;
    const pso = Array.isArray(visualization?.pso_attainment) ? visualization.pso_attainment.length : 0;
    const grades = Array.isArray(visualization?.grade_distribution) ? visualization.grade_distribution.length : 0;
    return { co, po, pso, grades };
  }, [visualization]);

  const coRows: any[] = useMemo(() => Array.isArray(visualization?.co_attainment) ? visualization.co_attainment : [], [visualization]);
  const gradeRows: any[] = useMemo(() => Array.isArray(visualization?.grade_distribution) ? visualization.grade_distribution : [], [visualization]);

  const th = "px-3 py-2 text-left text-[10px] font-mono text-white/40 uppercase tracking-widest";

  return (
    <AccessGate feature="export_pdf" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">Reports and Visualization</h1>
          <p className="text-white/50 mt-1 text-sm">
            {course?.course_code || "Course"} — {course?.course_name || "Loading..."}
          </p>
        </div>

        {loading && <p className="text-white/60">Loading report inputs...</p>}
        {error && <p className="text-alert text-sm">{error}</p>}
        {message && <p className="text-attain text-sm">{message}</p>}

        {!loading && (
          <>
            {/* Actions */}
            <section className="border border-white/10 p-4 space-y-3">
              <h2 className="text-sm font-mono text-white uppercase tracking-widest">Report Actions</h2>
              <div className="flex flex-wrap gap-3 items-end">
                <label className="text-xs text-white/60">
                  Report Type
                  <select
                    value={reportType}
                    onChange={e => setReportType(e.target.value as ReportType)}
                    className="ml-2 bg-transparent border border-white/20 px-2 py-1 text-white text-xs"
                  >
                    <option value="co_attainment">CO Attainment</option>
                    <option value="po_attainment">PO Attainment</option>
                    <option value="student_performance">Student Performance</option>
                    <option value="full">Full OBE Report</option>
                  </select>
                </label>
                <button onClick={() => void generateReport()} disabled={working} className="px-3 py-1 text-xs bg-brand text-white disabled:opacity-60">Generate</button>
                <button onClick={() => void exportReport("pdf")} disabled={working} className="px-3 py-1 text-xs bg-white/10 text-white disabled:opacity-60">Export PDF</button>
                <button onClick={() => void exportReport("excel")} disabled={working} className="px-3 py-1 text-xs bg-white/10 text-white disabled:opacity-60">Export Excel</button>
                <button onClick={() => void exportReport("nba")} disabled={working} className="px-3 py-1 text-xs bg-white/10 text-white disabled:opacity-60">Export NBA</button>
              </div>
            </section>

            {/* Summary stats */}
            <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "CO Series", val: summaryStats.co },
                { label: "PO Series", val: summaryStats.po },
                { label: "PSO Series", val: summaryStats.pso },
                { label: "Grade Buckets", val: summaryStats.grades },
              ].map(({ label, val }) => (
                <div key={label} className="border border-white/10 p-3">
                  <p className="text-[10px] font-mono text-white/40 uppercase">{label}</p>
                  <p className="text-xl text-white mt-1">{val}</p>
                </div>
              ))}
            </section>

            {/* CO Attainment table */}
            {coRows.length > 0 && (
              <section className="border border-white/10">
                <div className="px-4 py-3 border-b border-white/10">
                  <h2 className="text-sm font-mono text-white uppercase tracking-widest">CO Attainment</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className={th}>CO</th>
                        <th className={th}>Attainment %</th>
                        <th className={th}>Level</th>
                      </tr>
                    </thead>
                    <tbody>
                      {coRows.map((item: any, i: number) => {
                        const pct = Number(item.attainment_percentage ?? item.percentage ?? 0);
                        const level = pct >= 60 ? "L3" : pct >= 40 ? "L2" : "L1";
                        const color = pct >= 60 ? "text-attain" : pct >= 40 ? "text-brand" : "text-alert";
                        return (
                          <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                            <td className="px-3 py-2 text-xs text-white/70 font-mono">{item.co_code ?? item.co ?? `CO${i + 1}`}</td>
                            <td className="px-3 py-2 text-xs text-white">{pct}%</td>
                            <td className={`px-3 py-2 text-xs font-mono font-bold ${color}`}>{level}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* Grade distribution table */}
            {gradeRows.length > 0 && (
              <section className="border border-white/10">
                <div className="px-4 py-3 border-b border-white/10">
                  <h2 className="text-sm font-mono text-white uppercase tracking-widest">Grade Distribution</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className={th}>Grade</th>
                        <th className={th}>Count</th>
                        <th className={th}>Percentage</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gradeRows.map((item: any, i: number) => (
                        <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                          <td className="px-3 py-2 text-xs text-white/70">{item.grade ?? item.label ?? `Grade ${i + 1}`}</td>
                          <td className="px-3 py-2 text-xs text-white/70">{item.count ?? item.value ?? 0}</td>
                          <td className="px-3 py-2 text-xs text-white/70">{item.percentage ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {coRows.length === 0 && gradeRows.length === 0 && (
              <p className="text-white/40 text-sm">No visualization data available. Generate CO attainment first.</p>
            )}
          </>
        )}
      </div>
    </AccessGate>
  );
}

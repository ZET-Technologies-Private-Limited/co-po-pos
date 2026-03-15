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

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const onFocus = () => void load();
    if (typeof document !== "undefined" && document.addEventListener) {
      document.addEventListener("visibilitychange", onFocus);
      return () => document.removeEventListener("visibilitychange", onFocus);
    }
  }, [load]);

  async function generateReport() {
    setWorking(true);
    setError(null);
    setMessage(null);
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
    setWorking(true);
    setError(null);
    setMessage(null);
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

  return (
    <AccessGate feature="export_pdf" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">Reports and Visualization</h1>
          <p className="text-white/50 mt-1">
            {course?.course_code || "Course"} - {course?.course_name || "Loading..."}
          </p>
        </div>

        {loading ? <p className="text-white/60">Loading report inputs...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}
        {message ? <p className="text-attain">{message}</p> : null}

        {!loading ? (
          <>
            <section className="border border-white/10 rounded-lg p-4 space-y-3">
              <h2 className="text-sm text-white">Report Actions</h2>
              <div className="flex flex-wrap gap-3 items-end">
                <label className="text-xs text-white/60">
                  Report Type
                  <select
                    value={reportType}
                    onChange={(e) => setReportType(e.target.value as ReportType)}
                    className="ml-2 bg-transparent border border-white/20 rounded px-2 py-1 text-white"
                  >
                    <option value="co_attainment">CO Attainment</option>
                    <option value="po_attainment">PO Attainment</option>
                    <option value="student_performance">Student Performance</option>
                    <option value="full">Full OBE Report</option>
                  </select>
                </label>

                <button
                  type="button"
                  onClick={() => void generateReport()}
                  disabled={working}
                  className="px-3 py-1 text-xs bg-brand text-white rounded disabled:opacity-60"
                >
                  Generate
                </button>
                <button
                  type="button"
                  onClick={() => void exportReport("pdf")}
                  disabled={working}
                  className="px-3 py-1 text-xs bg-white/10 text-white rounded disabled:opacity-60"
                >
                  Export PDF
                </button>
                <button
                  type="button"
                  onClick={() => void exportReport("excel")}
                  disabled={working}
                  className="px-3 py-1 text-xs bg-white/10 text-white rounded disabled:opacity-60"
                >
                  Export Excel
                </button>
                <button
                  type="button"
                  onClick={() => void exportReport("nba")}
                  disabled={working}
                  className="px-3 py-1 text-xs bg-white/10 text-white rounded disabled:opacity-60"
                >
                  Export NBA
                </button>
              </div>
            </section>

            <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="border border-white/10 rounded-lg p-3">
                <p className="text-[10px] text-white/50 uppercase">CO Series</p>
                <p className="text-xl text-white mt-1">{summaryStats.co}</p>
              </div>
              <div className="border border-white/10 rounded-lg p-3">
                <p className="text-[10px] text-white/50 uppercase">PO Series</p>
                <p className="text-xl text-white mt-1">{summaryStats.po}</p>
              </div>
              <div className="border border-white/10 rounded-lg p-3">
                <p className="text-[10px] text-white/50 uppercase">PSO Series</p>
                <p className="text-xl text-white mt-1">{summaryStats.pso}</p>
              </div>
              <div className="border border-white/10 rounded-lg p-3">
                <p className="text-[10px] text-white/50 uppercase">Grade Buckets</p>
                <p className="text-xl text-white mt-1">{summaryStats.grades}</p>
              </div>
            </section>

            <section className="border border-white/10 rounded-lg p-4">
              <h2 className="text-sm text-white mb-2">Visualization Payload</h2>
              <pre className="text-xs text-white/70 whitespace-pre-wrap max-h-[480px] overflow-y-auto">
                {JSON.stringify(visualization, null, 2)}
              </pre>
            </section>
          </>
        ) : null}
      </div>
    </AccessGate>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

type MappingRow = {
  id: string;
  code: string;
  statement: string;
  po_codes: string[];
  pso_codes: string[];
};

export default function COPOMatrixPage() {
  const params = useParams();
  const courseId = params.id as string;

  const [course, setCourse] = useState<any>(null);
  const [rows, setRows] = useState<MappingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [c, detail] = await Promise.all([apiClient.getCourse(courseId), apiClient.getCourseOutcomesDetail(courseId)]);
      const list = Array.isArray(detail) ? detail : [];
      setCourse(c);
      setRows(
        list.map((item: any) => ({
          id: String(item.id),
          code: item.code || item.co_code || "CO",
          statement: item.statement || item.co_statement || item.description || "",
          po_codes: Array.isArray(item.po_codes) ? item.po_codes : [],
          pso_codes: Array.isArray(item.pso_codes) ? item.pso_codes : [],
        })),
      );
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load mappings.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [courseId]);

  function updatePO(index: number, value: string) {
    const poCodes = value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, po_codes: poCodes } : r)));
  }

  function updatePSO(index: number, value: string) {
    const psoCodes = value
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, pso_codes: psoCodes } : r)));
  }

  async function saveRow(row: MappingRow) {
    setSavingId(row.id);
    setError(null);
    try {
      await apiClient.updateCOMappings(courseId, row.id, {
        po_codes: row.po_codes,
        pso_codes: row.pso_codes,
      });
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to save mapping.");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <AccessGate feature="co_generation" deny="lock">
      <div className="max-w-5xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">CO-PO / CO-PSO Correlations</h1>
          <p className="text-white/50 mt-1">{course?.course_name || "Course"}</p>
        </div>

        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading ? (
          <section className="border border-white/10 rounded-lg p-4 space-y-3">
            {rows.map((row, idx) => (
              <div key={row.id} className="border border-white/10 rounded p-3">
                <p className="text-white text-sm font-medium">{row.code}</p>
                <p className="text-white/60 text-xs mt-1">{row.statement}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                  <div>
                    <label className="text-[11px] text-white/50">PO Codes (comma separated)</label>
                    <input
                      value={row.po_codes.join(", ")}
                      onChange={(e) => updatePO(idx, e.target.value)}
                      className="w-full mt-1 bg-transparent border border-white/20 rounded px-2 py-2 text-white text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] text-white/50">PSO Codes (comma separated)</label>
                    <input
                      value={row.pso_codes.join(", ")}
                      onChange={(e) => updatePSO(idx, e.target.value)}
                      className="w-full mt-1 bg-transparent border border-white/20 rounded px-2 py-2 text-white text-sm"
                    />
                  </div>
                </div>
                <button
                  onClick={() => void saveRow(row)}
                  disabled={savingId === row.id}
                  className="mt-3 px-3 py-1 text-xs bg-brand text-white rounded"
                >
                  {savingId === row.id ? "Saving..." : "Save Mapping"}
                </button>
              </div>
            ))}
            {rows.length === 0 ? <p className="text-white/40 text-sm">No CO rows available.</p> : null}
          </section>
        ) : null}
      </div>
    </AccessGate>
  );
}

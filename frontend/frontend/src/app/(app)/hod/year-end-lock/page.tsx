"use client";

import { useEffect, useState } from "react";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function HODYearEndLockPage() {
  const [years, setYears] = useState<any[]>([]);
  const [selected, setSelected] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getAcademicYears();
      const list = Array.isArray(res?.items) ? res.items : Array.isArray(res) ? res : [];
      setYears(list);
      if (list.length && !selected) setSelected(String(list[0]?.code || ""));
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load academic years.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function lock() {
    if (!selected) return;
    setMessage(null);
    try {
      await apiClient.lockAcademicYear(selected);
      setMessage(`Locked academic year ${selected}.`);
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to lock academic year.");
    }
  }

  return (
    <AccessGate feature="year_end_lock" deny="lock">
      <div className="max-w-4xl mx-auto pb-24 space-y-6">
        <h1 className="text-3xl text-white font-display">Year-End Lock</h1>
        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}
        {message ? <p className="text-attain">{message}</p> : null}
        {!loading && !error ? (
          <>
            <div className="flex gap-2">
              <select value={selected} onChange={(e) => setSelected(e.target.value)} className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-white">
                {years.map((y: any, i) => (
                  <option key={i} value={String(y?.code || y?.ay || "")}>{String(y?.name || y?.code || y?.ay || `AY ${i + 1}`)}</option>
                ))}
              </select>
              <button onClick={() => void lock()} className="px-3 py-1 text-xs bg-alert text-white rounded">Lock AY</button>
            </div>
            <div className="border border-white/10">
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="px-4 py-2 text-left text-[10px] font-mono text-white/40 uppercase">AY Code</th>
                      <th className="px-4 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Status</th>
                      <th className="px-4 py-2 text-left text-[10px] font-mono text-white/40 uppercase">Locked By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {years.map((y: any, i: number) => (
                      <tr key={i} className="border-b border-white/5">
                        <td className="px-4 py-2 text-xs text-white font-mono">{String(y?.code ?? y?.ay ?? `AY ${i + 1}`)}</td>
                        <td className="px-4 py-2 text-xs">
                          <span className={y?.is_locked ? "text-alert" : y?.is_active ? "text-attain" : "text-white/50"}>
                            {y?.is_locked ? "Locked" : y?.is_active ? "Active" : "Archived"}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-xs text-white/50">{y?.locked_by ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </AccessGate>
  );
}

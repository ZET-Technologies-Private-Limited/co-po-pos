"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Target, Award, Edit3, Plus, Trash2, CheckCircle2, X, GitCommit, Loader2 } from "lucide-react";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import apiClient from "@/lib/apiClient";
import { useUIStore } from "@/lib/uiStore";
import { AccessGate } from "@/components/auth/AccessGate";

const DEPTS = ["CSE", "ECE", "MECH", "CIVIL", "IT", "MBA"];
const REGS  = ["R21", "R20", "R18"];

type PORow = { id: string; code: string; statement: string; description?: string };
type PSORow = { id: string; code: string; statement: string; description?: string };

export default function AdminPOPSOMasterPage() {
  const { addToast } = useUIStore();
  const [programs, setPrograms] = useState<{ id: string; code: string; name: string }[]>([]);
  const [programId, setProgramId] = useState("");
  const [poDefinitions, setPODefinitions] = useState<PORow[]>([]);
  const [psoDefinitions, setPSODefinitions] = useState<PSORow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editingPO, setEditingPO]   = useState<string | null>(null);
  const [editingPSO, setEditingPSO] = useState<string | null>(null);
  const [poText, setPOText]         = useState("");
  const [psoText, setPSOText]       = useState("");
  const [psoName, setPSOName]       = useState("");
  const [psoCode, setPSOCode]       = useState("");
  const [showAddPSO, setShowAddPSO] = useState(false);
  const [newPSO, setNewPSO]         = useState({ code: "", statement: "", description: "" });
  const [saving, setSaving]         = useState(false);
  const [activeTab, setActiveTab]   = useState<"po" | "pso">("po");

  const loadPrograms = useCallback(async () => {
    try {
      const list = await apiClient.getPrograms();
      setPrograms(Array.isArray(list) ? list : []);
      if (list?.length && !programId) setProgramId(list[0].id);
    } catch (e: any) {
      setError(e?.message || "Failed to load programs");
    }
  }, [programId]);

  const loadPOPSO = useCallback(async () => {
    if (!programId) return;
    setLoading(true);
    setError(null);
    try {
      const [pos, psos] = await Promise.all([
        apiClient.getProgramOutcomes(programId),
        apiClient.getPSOs(programId),
      ]);
      setPODefinitions(Array.isArray(pos) ? pos : []);
      setPSODefinitions(Array.isArray(psos) ? psos : []);
    } catch (e: any) {
      setError(e?.message || "Failed to load PO/PSO");
    } finally {
      setLoading(false);
    }
  }, [programId]);

  useEffect(() => {
    void loadPrograms();
  }, [loadPrograms]);

  useEffect(() => {
    void loadPOPSO();
  }, [loadPOPSO]);

  const startEditPO = (po: PORow) => {
    setEditingPO(po.id); setPOText(po.statement);
  };
  const savePO = async (id: string) => {
    if (!programId) return;
    setSaving(true);
    try {
      await apiClient.updateProgramOutcome(programId, id, { statement: poText });
      addToast(`${id} updated.`, "success");
      setEditingPO(null);
      void loadPOPSO();
    } catch (err: any) {
      addToast(err?.message || "Failed to update", "error");
    } finally {
      setSaving(false);
    }
  };

  const startEditPSO = (pso: PSORow) => {
    setEditingPSO(pso.id); setPSOText(pso.statement); setPSOName(pso.code); setPSOCode(pso.code);
  };
  const savePSO = async (id: string) => {
    if (!programId) return;
    setSaving(true);
    try {
      await apiClient.updatePSO(programId, id, { statement: psoText, code: psoCode });
      addToast(`${id} updated.`, "success");
      setEditingPSO(null);
      void loadPOPSO();
    } catch (err: any) {
      addToast(err?.message || "Failed to update", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleAddPSO = async () => {
    if (!programId || !newPSO.code || !newPSO.statement) { addToast("Code and statement are required.", "warning"); return; }
    setSaving(true);
    try {
      await apiClient.createPSO(programId, { code: newPSO.code, statement: newPSO.statement, description: newPSO.description });
      addToast(`${newPSO.code} added.`, "success");
      setNewPSO({ code: "", statement: "", description: "" });
      setShowAddPSO(false);
      void loadPOPSO();
    } catch (err: any) {
      addToast(err?.message || "Failed to add PSO", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleDeletePSO = async (pso: PSORow) => {
    if (!programId) return;
    try {
      await apiClient.deletePSO(programId, pso.id);
      addToast(`${pso.code} deleted.`, "info");
      void loadPOPSO();
    } catch (err: any) {
      addToast(err?.message || "Failed to delete", "error");
    }
  };

  const categoryColor = (cat: string) => {
    if (cat === "Technical")     return "text-brand border-brand/20";
    if (cat === "Professional")  return "text-aurora border-aurora/20";
    return "text-attain border-attain/20";
  };

  return (
    <AccessGate feature="user_management" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-6xl mx-auto pb-32">

        {/* Header */}
        <motion.div variants={fadeSlideUp} className="flex justify-between items-end pb-8 border-b border-white/5">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-mono text-brand uppercase tracking-widest mb-3">
              <span className="w-8 h-[1px] bg-brand" /> NBA Framework
            </div>
            <h1 className="text-4xl font-display text-white">PO & PSO Master Dictionary</h1>
            <p className="text-white/40 font-light mt-1">Global declarations for Program and Program Specific Outcomes.</p>
          </div>
          {programs.length > 0 && (
            <select value={programId} onChange={(e) => setProgramId(e.target.value)} className="bg-white/[0.02] border border-white/10 px-3 py-2 text-sm text-white">
              {programs.map((p) => (
                <option key={p.id} value={p.id} className="bg-[#0a0a0f]">{p.code} – {p.name}</option>
              ))}
            </select>
          )}
        </motion.div>

        {loading && <p className="text-white/60 py-4">Loading PO/PSO...</p>}
        {error && <p className="text-alert py-4">{error}</p>}
        {!programId && programs.length === 0 && !loading && <p className="text-white/50 py-4">No program found. Create a program in the database first.</p>}

        {/* Tabs */}
        <div className="flex border-b border-white/5">
          {(["po", "pso"] as const).map(t => (
            <button key={t} onClick={() => setActiveTab(t)}
              className={`px-6 py-4 text-[10px] font-mono uppercase tracking-widest border-b-2 transition-all ${
                activeTab === t ? "border-brand text-brand" : "border-transparent text-white/30 hover:text-white"
              }`}>
              {t === "po" ? `Program Outcomes (PO1–PO12)` : `Program Specific Outcomes (PSOs)`}
            </button>
          ))}
        </div>

        {/* PO tab */}
        {activeTab === "po" && (
          <motion.div variants={fadeSlideUp} className="flex flex-col divide-y divide-white/5">
            {poDefinitions.map(po => (
              <div key={po.id} className="py-5 flex items-start gap-6 group">
                <div className="shrink-0 w-24">
                  <p className="text-lg font-bold text-white font-mono">{po.code}</p>
                </div>
                <div className="flex-1">
                  <p className="text-[10px] font-mono text-white/50 uppercase tracking-widest mb-1">{po.code}</p>
                  {editingPO === po.id ? (
                    <textarea value={poText} onChange={e => setPOText(e.target.value)}
                      className="w-full h-24 bg-white/[0.02] border border-brand/30 p-3 text-sm text-white outline-none resize-none" />
                  ) : (
                    <p className="text-sm font-light text-white/60 leading-relaxed">{po.statement}</p>
                  )}
                </div>
                <div className="shrink-0">
                  {editingPO === po.id ? (
                    <div className="flex gap-2">
                      <button onClick={() => setEditingPO(null)} className="p-1.5 text-white/30 hover:text-white transition-colors"><X className="w-4 h-4" /></button>
                      <button onClick={() => savePO(po.id)} disabled={saving}
                        className="p-1.5 text-attain hover:text-white transition-colors">
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                      </button>
                    </div>
                  ) : (
                    <button onClick={() => startEditPO(po)}
                      className="opacity-0 group-hover:opacity-100 p-1.5 text-white/30 hover:text-brand transition-all">
                      <Edit3 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </motion.div>
        )}

        {/* PSO tab */}
        {activeTab === "pso" && (
          <motion.div variants={fadeSlideUp} className="flex flex-col">
            <div className="flex justify-end py-4 border-b border-white/5">
              <button onClick={() => setShowAddPSO(true)}
                className="px-5 py-2.5 bg-brand text-white text-[10px] font-mono uppercase tracking-widest hover:bg-brand/90 transition-colors flex items-center gap-2">
                <Plus className="w-3.5 h-3.5" /> Add PSO
              </button>
            </div>

            <div className="flex flex-col divide-y divide-white/5">
              {psoDefinitions.map(pso => (
                <div key={pso.id} className="py-5 flex items-start gap-6 group">
                  <div className="shrink-0 w-24">
                    <p className="text-lg font-bold text-white font-mono">{pso.code}</p>
                  </div>
                  <div className="flex-1">
                    <p className="text-[10px] font-mono text-white/50 uppercase tracking-widest mb-1">{pso.code}</p>
                    {editingPSO === pso.id ? (
                      <div className="flex flex-col gap-3">
                        <input value={psoCode} onChange={e => setPSOCode(e.target.value)}
                          placeholder="Code" className="bg-white/[0.02] border border-white/10 px-3 py-2 text-white text-sm outline-none focus:border-brand" />
                        <textarea value={psoText} onChange={e => setPSOText(e.target.value)}
                          className="w-full h-20 bg-white/[0.02] border border-brand/30 p-3 text-sm text-white outline-none resize-none" />
                      </div>
                    ) : (
                      <p className="text-sm font-light text-white/60 leading-relaxed">{pso.statement}</p>
                    )}
                  </div>
                  <div className="shrink-0 flex gap-1">
                    {editingPSO === pso.id ? (
                      <>
                        <button onClick={() => setEditingPSO(null)} className="p-1.5 text-white/30 hover:text-white transition-colors"><X className="w-4 h-4" /></button>
                        <button onClick={() => savePSO(pso.id)} disabled={saving}
                          className="p-1.5 text-attain hover:text-white transition-colors">
                          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                        </button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => startEditPSO(pso)}
                          className="opacity-0 group-hover:opacity-100 p-1.5 text-white/30 hover:text-brand transition-all">
                          <Edit3 className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDeletePSO(pso)}
                          className="opacity-0 group-hover:opacity-100 p-1.5 text-white/30 hover:text-alert transition-all">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Add PSO modal */}
            <AnimatePresence>
              {showAddPSO && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-8">
                  <motion.div initial={{ scale: 0.95 }} animate={{ scale: 1 }}
                    className="w-full max-w-md bg-[#0a0a0f] border border-white/10 p-8">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-xl font-display text-white">Add New PSO</h3>
                      <button onClick={() => setShowAddPSO(false)} className="text-white/30 hover:text-white"><X className="w-5 h-5" /></button>
                    </div>
                    <div className="flex flex-col gap-4">
                      <div className="flex flex-col gap-1">
                        <label className="text-[9px] font-mono text-white/30 uppercase tracking-widest">Code</label>
                        <input value={newPSO.code} onChange={e => setNewPSO(p => ({ ...p, code: e.target.value }))}
                          placeholder="PSO1" className="bg-white/[0.02] border border-white/10 px-4 py-2.5 text-white text-sm outline-none focus:border-brand" />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[9px] font-mono text-white/30 uppercase tracking-widest">Statement</label>
                        <textarea value={newPSO.statement} onChange={e => setNewPSO(p => ({ ...p, statement: e.target.value }))}
                          placeholder="Describe this PSO..." rows={3}
                          className="bg-white/[0.02] border border-white/10 px-4 py-2.5 text-white text-sm outline-none focus:border-brand resize-none" />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[9px] font-mono text-white/30 uppercase tracking-widest">Description (optional)</label>
                        <input value={newPSO.description} onChange={e => setNewPSO(p => ({ ...p, description: e.target.value }))}
                          placeholder="Optional" className="bg-white/[0.02] border border-white/10 px-4 py-2.5 text-white text-sm outline-none focus:border-brand" />
                      </div>
                      <div className="flex gap-3 pt-2 border-t border-white/5">
                        <button onClick={() => setShowAddPSO(false)}
                          className="flex-1 py-2.5 border border-white/10 text-white/40 hover:text-white text-[10px] font-mono uppercase tracking-widest transition-colors">
                          Cancel
                        </button>
                        <button onClick={handleAddPSO} disabled={saving}
                          className="flex-1 py-2.5 bg-brand text-white text-[10px] font-mono uppercase tracking-widest flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-brand/90 transition-colors">
                          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />} Add PSO
                        </button>
                      </div>
                    </div>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}

      </motion.div>
    </AccessGate>
  );
}

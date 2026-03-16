"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { UploadCloud, Download, Loader2, CheckCircle2, AlertTriangle, ArrowRight, Zap, Info } from "lucide-react";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import apiClient from "@/lib/apiClient";

type MarkRow = { student_id: string; marks: Record<string, number | ""> };

function validateMark(val: number | "", maxMarks: number) {
  if (val === "") return "empty";
  if (val > maxMarks) return "over";
  if (val < 0) return "under";
  return "ok";
}

export default function MarksPage({ params }: { params: Promise<{ examId: string }> }) {
  const { examId } = use(params);
  const router = useRouter();

  const [exam, setExam] = useState<any>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [rows, setRows] = useState<MarkRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [qRes, mRes] = await Promise.all([
          apiClient.getQuestions(examId),
          apiClient.getMarks(examId),
        ]);
        if (cancelled) return;
        const qList = Array.isArray(qRes?.questions) ? qRes.questions : [];
        setQuestions(qList);
        const dataRows = Array.isArray(mRes?.rows)
          ? mRes.rows
          : Array.isArray(mRes?.students)
          ? mRes.students.map((s: any) => ({ student_id: s.student_id || s.roll || "", marks: s.marks || {} }))
          : [];
        setRows(dataRows.map((r: any) => ({ student_id: String(r.student_id || ""), marks: r.marks || {} })));
      } catch (e: any) {
        if (!cancelled) setError(typeof e?.message === "string" ? e.message : "Failed to load marks.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [examId]);

  function addRow() {
    setRows(prev => [...prev, { student_id: "", marks: {} }]);
  }

  function updateStudent(idx: number, val: string) {
    setRows(prev => prev.map((r, i) => i === idx ? { ...r, student_id: val } : r));
  }

  function updateMark(idx: number, qNo: string, val: string) {
    const num = Number(val);
    setRows(prev => prev.map((r, i) =>
      i === idx ? { ...r, marks: { ...r.marks, [qNo]: Number.isFinite(num) ? num : 0 } } : r
    ));
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const payload = rows.filter(r => r.student_id.trim()).map(r => ({ student_id: r.student_id.trim(), marks: r.marks }));
      await apiClient.submitMarks(examId, { rows: payload });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to save marks.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmitForApproval() {
    setError(null);
    try {
      await apiClient.submitMarksForApproval(examId);
      router.back();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to submit for approval.");
    }
  }

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto py-12">
        <p className="text-white/60">Loading marks workspace...</p>
      </div>
    );
  }

  return (
    <div className="w-full min-h-screen pb-32 pt-4">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="max-w-5xl mx-auto flex flex-col gap-12">

        <motion.section variants={fadeSlideUp} className="flex flex-col gap-4">
          <div className="flex items-center gap-3 text-sm font-mono text-attain uppercase tracking-widest">
            <span className="w-8 h-[1px] bg-attain" /> Performance Ledger
          </div>
          <div className="flex items-end justify-between flex-wrap gap-4">
            <h1 className="text-4xl font-display text-white">Marks Upload</h1>
            <div className="flex gap-3">
              <button onClick={addRow} className="flex items-center gap-2 px-4 py-2 border border-white/10 text-white/60 text-xs font-mono uppercase hover:text-white hover:border-white/30 transition-colors">
                + Add Row
              </button>
              <button onClick={() => void handleSubmitForApproval()} className="flex items-center gap-2 px-4 py-2 border border-white/20 text-white/70 text-xs font-mono uppercase hover:text-white transition-colors">
                Submit for Approval
              </button>
            </div>
          </div>
          {error && <p className="text-alert text-sm">{error}</p>}
        </motion.section>

        {questions.length > 0 && (
          <motion.section variants={fadeSlideUp} className="flex flex-wrap items-center gap-8 py-6 border-y border-white/10 bg-white/[0.02]">
            <div className="flex items-center gap-3 px-4">
              <Zap className="w-4 h-4 text-attain" />
              <span className="text-xs font-mono text-white/30 uppercase tracking-widest">Questions:</span>
            </div>
            {questions.map(q => (
              <div key={q.id || q.question_number} className="flex items-end gap-2 px-3">
                <span className="text-[10px] font-mono text-white/20 uppercase">Q{q.question_number}</span>
                <span className="text-lg font-mono text-white font-light">/{q.marks}</span>
              </div>
            ))}
          </motion.section>
        )}

        <motion.section variants={fadeSlideUp} className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/10">
                <th className="py-4 text-[10px] font-mono text-white/20 uppercase tracking-widest pr-8">Student ID</th>
                {questions.map(q => (
                  <th key={q.id || q.question_number} className="py-4 text-center text-[10px] font-mono text-white/20 uppercase tracking-widest px-4">
                    Q{q.question_number}
                  </th>
                ))}
                <th className="py-4 text-center text-[10px] font-mono text-white/20 uppercase tracking-widest px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {rows.map((row, idx) => {
                const allValid = questions.every(q => validateMark(row.marks[q.question_number], q.marks) === "ok");
                const hasError = questions.some(q => {
                  const s = validateMark(row.marks[q.question_number], q.marks);
                  return s === "over" || s === "under";
                });
                return (
                  <tr key={idx} className="group hover:bg-white/[0.02] transition-colors">
                    <td className="py-4 pr-8">
                      <input
                        value={row.student_id}
                        onChange={e => updateStudent(idx, e.target.value)}
                        placeholder="Student ID"
                        className="w-full bg-transparent border-b border-white/10 focus:border-brand py-1 text-white text-sm outline-none"
                      />
                    </td>
                    {questions.map(q => {
                      const state = validateMark(row.marks[q.question_number], q.marks);
                      return (
                        <td key={`${idx}-${q.id || q.question_number}`} className="py-4 px-4 text-center">
                          <input
                            type="number"
                            value={row.marks[q.question_number] ?? ""}
                            onChange={e => updateMark(idx, String(q.question_number), e.target.value)}
                            className={`w-20 text-center bg-transparent border-b py-2 text-white outline-none font-mono ${
                              state === "over" || state === "under" ? "border-alert text-alert" :
                              state === "ok" ? "border-white/10 focus:border-attain" : "border-white/5 text-white/30"
                            }`}
                          />
                        </td>
                      );
                    })}
                    <td className="py-4 px-4 text-center">
                      {hasError ? <AlertTriangle className="w-4 h-4 text-alert mx-auto" /> :
                        allValid && questions.length > 0 ? <CheckCircle2 className="w-4 h-4 text-attain mx-auto" /> :
                        <div className="w-2 h-2 rounded-full bg-white/10 mx-auto" />}
                    </td>
                  </tr>
                );
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={questions.length + 2} className="py-12 text-center text-white/30 text-sm">
                    No marks loaded. Add rows or upload a file.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </motion.section>

        <motion.section variants={fadeSlideUp} className="flex items-center justify-between gap-8 pt-8 border-t border-white/10">
          <div className="flex items-start gap-3">
            <Info className="w-4 h-4 text-white/20 mt-0.5" />
            <p className="text-white/30 text-sm font-light max-w-md leading-relaxed">
              Save draft to preserve progress. Submit for approval when all marks are finalized.
            </p>
          </div>
          <button
            onClick={() => void handleSave()}
            disabled={saving}
            className={`flex items-center gap-4 px-10 py-4 font-mono text-sm uppercase tracking-widest transition-all ${
              saved ? "bg-attain text-white" : "bg-white text-black hover:bg-white/95"
            } disabled:opacity-50`}
          >
            {saving ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</> :
              saved ? <><CheckCircle2 className="w-4 h-4" /> Saved</> :
              <><ArrowRight className="w-4 h-4" /> Save Draft</>}
          </button>
        </motion.section>
      </motion.div>
    </div>
  );
}

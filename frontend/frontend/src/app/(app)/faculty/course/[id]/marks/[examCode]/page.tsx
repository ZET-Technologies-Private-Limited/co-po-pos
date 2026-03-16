"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import { FileUploadSection } from "@/components/workflow/FileUploadSection";
import apiClient from "@/lib/apiClient";
import { AlertCircle, CheckCircle2, ChevronDown, ChevronRight, Info, Loader2, Plus, Send, Save } from "lucide-react";

type MarkRow = {
  student_id: string;
  marks: Record<string, number>;
};

export default function MarksPortalPage() {
  const { id, examCode } = useParams();
  const courseId = id as string;
  const examToken = examCode as string;

  const [course, setCourse] = useState<any>(null);
  const [exams, setExams] = useState<any[]>([]);
  const [exam, setExam] = useState<any>(null);
  const [questions, setQuestions] = useState<any[]>([]);
  const [rows, setRows] = useState<MarkRow[]>([]);
  const [preview, setPreview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(40);
  const [faMethod, setFaMethod] = useState<"best_n_of_m" | "simple_avg" | "weighted">("best_n_of_m");
  const [showConfig, setShowConfig] = useState(false);

  async function load() {
    setLoading(true); setError(null);
    try {
      const [c, ex] = await Promise.all([apiClient.getCourse(courseId), apiClient.getExams(courseId)]);
      const examList = Array.isArray(ex) ? ex : [];
      const selected =
        examList.find((e) => String(e.id) === examToken || String(e.assessment_code || "").toLowerCase() === examToken.toLowerCase()) ||
        examList[0];

      setCourse(c); setExams(examList); setExam(selected || null);

      if (!selected) { setQuestions([]); setRows([]); setPreview(null); return; }

      const [qRes, mRes] = await Promise.all([
        apiClient.getQuestions(String(selected.id)),
        apiClient.getMarks(String(selected.id)),
      ]);
      const qList = Array.isArray(qRes?.questions) ? qRes.questions : [];
      setQuestions(qList);

      const dataRows = Array.isArray(mRes?.rows)
        ? mRes.rows
        : Array.isArray(mRes?.students)
        ? mRes.students.map((s: any) => ({ student_id: s.student_id || s.roll || "", marks: s.marks || {} }))
        : [];
      setRows(dataRows.map((r: any) => ({ student_id: String(r.student_id || ""), marks: r.marks || {} })));

      try {
        const p = await apiClient.getMarksPreview(String(selected.id), threshold / 100);
        setPreview(p);
      } catch { setPreview(null); }
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load marks page.");
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [courseId, examToken]);

  function addStudentRow() {
    setRows((prev) => [...prev, { student_id: "", marks: {} }]);
  }

  function updateStudent(index: number, studentId: string) {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, student_id: studentId } : r)));
  }

  function updateMark(index: number, qNo: string, value: string) {
    const num = Number(value);
    setRows((prev) =>
      prev.map((r, i) =>
        i === index ? { ...r, marks: { ...r.marks, [qNo]: Number.isFinite(num) ? num : 0 } } : r,
      ),
    );
  }

  async function saveDraft() {
    if (!exam) return;
    setSaving(true); setError(null); setMessage(null);
    try {
      const payloadRows = rows.filter((r) => r.student_id.trim()).map((r) => ({ student_id: r.student_id.trim(), marks: r.marks }));
      await apiClient.submitMarks(String(exam.id), { rows: payloadRows });
      setMessage("Marks saved successfully.");
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to save marks.");
    } finally { setSaving(false); }
  }

  async function submitForApproval() {
    if (!exam) return;
    setSubmitting(true); setError(null); setMessage(null);
    try {
      await apiClient.submitMarksForApproval(String(exam.id));
      setMessage("Marks submitted for approval.");
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to submit marks for approval.");
    } finally { setSubmitting(false); }
  }

  // CO preview rows from preview data
  const coPreviewRows: any[] = useMemo(() => {
    if (!preview) return [];
    if (Array.isArray(preview?.co_attainment)) return preview.co_attainment;
    if (Array.isArray(preview?.attainments)) return preview.attainments;
    if (Array.isArray(preview)) return preview;
    return [];
  }, [preview]);

  const totalMarks = useMemo(() => {
    return rows.reduce((sum, r) => {
      return sum + Object.values(r.marks).reduce((s, v) => s + (Number(v) || 0), 0);
    }, 0);
  }, [rows]);

  return (
    <AccessGate feature="marks_upload" deny="lock">
      <div className="w-full pb-24 space-y-0">
        {/* Header */}
        <div className="border-b border-white/10 pb-6 mb-8">
          <h1 className="text-3xl text-white font-display">Marks Upload</h1>
          <p className="text-white/40 text-sm mt-1 font-mono">
            {course?.course_name || "Course"} · {exam?.exam_name || "Exam"}
          </p>
          {exam && (
            <p className="text-white/20 text-xs mt-1 font-mono">
              Total Marks: {exam.total_marks} · Type: {exam.exam_type?.replace(/_/g, " ")}
              {exam.weightage_pct != null ? ` · Weightage: ${exam.weightage_pct}%` : ""}
            </p>
          )}
        </div>

        {/* NBA Config Panel */}
        <div className="border border-white/10 mb-6">
          <button
            onClick={() => setShowConfig(v => !v)}
            className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/[0.02] transition-colors"
          >
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
              <Info className="w-3 h-3" /> NBA Attainment Config — Threshold: {threshold}% · FA Method: {faMethod.replace(/_/g, " ")}
            </span>
            {showConfig ? <ChevronDown className="w-3.5 h-3.5 text-white/30" /> : <ChevronRight className="w-3.5 h-3.5 text-white/30" />}
          </button>
          {showConfig && (
            <div className="px-4 pb-4 border-t border-white/5 space-y-4 mt-3">
              <div className="flex flex-wrap gap-6">
                <div>
                  <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest mb-2">Pass Threshold</p>
                  <div className="flex gap-2">
                    {[40, 50, 60].map(t => (
                      <button
                        key={t}
                        onClick={() => setThreshold(t)}
                        className={`px-3 py-1.5 text-xs font-mono border transition-colors ${
                          threshold === t ? "border-brand text-brand" : "border-white/20 text-white/40 hover:border-white/40"
                        }`}
                      >
                        {t}%
                      </button>
                    ))}
                  </div>
                  <p className="text-[10px] text-white/30 mt-1">Students scoring ≥ threshold are counted as &apos;passed&apos; for CO attainment.</p>
                </div>
                <div>
                  <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest mb-2">FA Calculation Method</p>
                  <div className="flex gap-2">
                    {(["best_n_of_m", "simple_avg", "weighted"] as const).map(m => (
                      <button
                        key={m}
                        onClick={() => setFaMethod(m)}
                        className={`px-3 py-1.5 text-xs font-mono border transition-colors ${
                          faMethod === m ? "border-brand text-brand" : "border-white/20 text-white/40 hover:border-white/40"
                        }`}
                      >
                        {m.replace(/_/g, " ")}
                      </button>
                    ))}
                  </div>
                  <p className="text-[10px] text-white/30 mt-1">Best N-of-M: top 3 of 5 FAs. Simple avg: mean of all. Weighted: by FA weight.</p>
                </div>
              </div>
              <div className="bg-white/[0.02] border border-white/5 p-3 space-y-1">
                <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest">Active Formula</p>
                <p className="text-xs font-mono text-white/60">CO_att = (students ≥ {threshold}% threshold) / total_students × 100</p>
                <p className="text-xs font-mono text-white/60">Direct = FA×0.40 + SA×0.60 · Final = Direct×0.80 + Indirect×0.20</p>
              </div>
            </div>
          )}
        </div>

        {loading && <p className="text-white/50 text-sm py-8">Loading marks workspace...</p>}
        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm py-4">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}
        {message && (
          <div className="flex items-center gap-2 text-emerald-400 text-sm py-4">
            <CheckCircle2 className="w-4 h-4 shrink-0" /> {message}
          </div>
        )}

        {!loading && exam && (
          <>
            {/* Exam Selector */}
            {exams.length > 1 && (
              <section className="border-b border-white/5 pb-6 mb-8">
                <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-3">Switch Exam</h2>
                <div className="flex flex-wrap gap-2">
                  {exams.map((e: any) => (
                    <a
                      key={e.id}
                      href={`/faculty/course/${courseId}/marks/${e.id}`}
                      className={`px-3 py-1.5 text-xs font-mono border transition-colors ${
                        String(e.id) === examToken
                          ? "border-brand text-brand"
                          : "border-white/20 text-white/40 hover:text-white hover:border-white/40"
                      }`}
                    >
                      {e.exam_name}
                    </a>
                  ))}
                </div>
              </section>
            )}

            {/* File Upload */}
            <section className="border-b border-white/5 pb-8 mb-8">
              <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">Import from File</h2>
              <FileUploadSection
                title="Upload Marks CSV"
                description="CSV format: student_id, Q1, Q2, Q3... (header row required)"
                acceptedFormats={[".csv", ".xlsx", ".xls"]}
                maxSizeMB={25}
                onFileSelect={async (file) => {
                  const text = await file.text();
                  const lines = text.split("\n").filter((l) => l.trim());
                  const importedRows = lines.slice(1).map((line) => {
                    const [studentId, ...marksStrings] = line.split(",").map((s) => s.trim());
                    const marks: Record<string, number> = {};
                    questions.forEach((q, idx) => {
                      marks[String(q.question_number)] = parseInt(marksStrings[idx] || "0");
                    });
                    return { student_id: studentId, marks };
                  });
                  if (importedRows.length > 0) setRows((prev) => [...prev, ...importedRows]);
                  return { rows_count: importedRows.length };
                }}
              />
            </section>

            {/* Marks Entry Table */}
            <section className="border-b border-white/5 pb-8 mb-8">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest">
                  Marks Entry ({rows.length} students)
                </h2>
                <button
                  onClick={addStudentRow}
                  className="flex items-center gap-1.5 text-xs font-mono text-white/40 hover:text-white transition-colors"
                >
                  <Plus className="w-3 h-3" /> Add Row
                </button>
              </div>

              {questions.length === 0 ? (
                <div className="flex items-center gap-2 text-amber-400 text-sm py-4">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  No questions configured for this exam. Go to Exam Configuration to add questions first.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-white/5">
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left pr-4 w-36">
                          Student ID
                        </th>
                        {questions.map((q) => (
                          <th
                            key={q.id || q.question_number}
                            className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center px-2 w-16"
                            title={q.question_text}
                          >
                            Q{q.question_number}
                            <span className="block text-[8px] text-white/20 normal-case">{q.marks}m</span>
                            {q.co_code && <span className="block text-[8px] text-brand/60 normal-case">{q.co_code}</span>}
                          </th>
                        ))}
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center px-2 w-16">
                          Total
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, idx) => {
                        const rowTotal = Object.values(row.marks).reduce((s, v) => s + (Number(v) || 0), 0);
                        return (
                          <tr key={idx} className="border-b border-white/5 hover:bg-white/[0.02]">
                            <td className="py-2 pr-4">
                              <input
                                value={row.student_id}
                                onChange={(e) => updateStudent(idx, e.target.value)}
                                placeholder="Student ID"
                                className="w-full bg-transparent border border-white/20 px-2 py-1 text-white text-xs font-mono placeholder-white/20 focus:outline-none focus:border-white/40"
                              />
                            </td>
                            {questions.map((q) => (
                              <td key={`${idx}-${q.id || q.question_number}`} className="py-2 px-2">
                                <input
                                  type="number"
                                  min={0}
                                  max={q.marks}
                                  value={row.marks[q.question_number] ?? ""}
                                  onChange={(e) => updateMark(idx, String(q.question_number), e.target.value)}
                                  className={`w-14 bg-transparent border px-2 py-1 text-white text-xs font-mono text-center focus:outline-none focus:border-white/40 ${
                                    (row.marks[q.question_number] ?? 0) > q.marks
                                      ? "border-red-500/60"
                                      : "border-white/20"
                                  }`}
                                />
                              </td>
                            ))}
                            <td className="py-2 px-2 text-center font-mono text-xs text-white/50">{rowTotal}</td>
                          </tr>
                        );
                      })}
                      {rows.length === 0 && (
                        <tr>
                          <td colSpan={questions.length + 2} className="py-8 text-center text-white/30 text-sm italic">
                            No marks entered yet. Add rows manually or import from file.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              {rows.length > 0 && (
                <div className="flex flex-col gap-3 mt-6">
                  {(() => {
                    const overMax = rows.flatMap((r, ri) =>
                      questions
                        .filter(q => (r.marks[q.question_number] ?? 0) > q.marks)
                        .map(q => `Row ${ri + 1} Q${q.question_number}: ${r.marks[q.question_number]} > max ${q.marks}`)
                    );
                    const missingIds = rows.filter(r => !r.student_id.trim()).length;
                    if (overMax.length === 0 && missingIds === 0) return null;
                    return (
                      <div className="border border-red-500/30 bg-red-500/5 px-3 py-2 space-y-1">
                        {missingIds > 0 && <p className="text-xs text-red-400 flex items-center gap-1.5"><AlertCircle className="w-3 h-3" /> {missingIds} row(s) missing Student ID</p>}
                        {overMax.map((msg, i) => <p key={i} className="text-xs text-red-400 flex items-center gap-1.5"><AlertCircle className="w-3 h-3" /> {msg}</p>)}
                      </div>
                    );
                  })()}
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => void saveDraft()}
                      disabled={saving}
                      className="flex items-center gap-2 px-4 py-2 text-xs font-mono text-white border border-white/20 hover:border-white/50 disabled:opacity-40 transition-colors"
                    >
                      {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                      Save Draft
                    </button>
                    <button
                      onClick={() => void submitForApproval()}
                      disabled={submitting}
                      className="flex items-center gap-2 px-4 py-2 text-xs font-mono text-white border border-brand/40 hover:border-brand text-brand/80 hover:text-brand disabled:opacity-40 transition-colors"
                    >
                      {submitting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                      Submit for Approval
                    </button>
                  </div>
                </div>
              )}
            </section>

            {/* CO Attainment Preview */}
            {coPreviewRows.length > 0 && (
              <section className="pb-8">
                <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">
                  Live CO Attainment Preview — threshold {threshold}%
                </h2>
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-white/5">
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left w-20">CO</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left">
                        Attainment
                      </th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center w-20">Level</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center w-28">
                        Students Cleared
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {coPreviewRows.map((row: any, idx: number) => {
                      const pct = Number(row.attainment_percentage ?? row.percentage ?? 0);
                      const level = row.attainment_level ?? row.level ?? "";
                      const levelColor =
                        level === "L3" || pct >= 60
                          ? "text-emerald-400"
                          : level === "L2" || pct >= 50
                          ? "text-amber-400"
                          : "text-red-400";
                      const barColor =
                        pct >= 60 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
                      return (
                        <tr key={row.co_code ?? idx} className="border-b border-white/5 hover:bg-white/[0.02]">
                          <td className="py-3 font-mono text-xs text-white/60">{row.co_code ?? row.code ?? `CO${idx + 1}`}</td>
                          <td className="py-3 pr-8">
                            <div className="flex items-center gap-3">
                              <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${barColor}`}
                                  style={{ width: `${Math.min(100, pct)}%` }}
                                />
                              </div>
                              <span className={`text-xs font-mono w-10 text-right ${levelColor}`}>
                                {pct.toFixed(1)}%
                              </span>
                            </div>
                          </td>
                          <td className="py-3 text-center">
                            <span className={`text-xs font-mono font-bold ${levelColor}`}>{level || "—"}</span>
                          </td>
                          <td className="py-3 text-center font-mono text-xs text-white/40">
                            {row.students_cleared != null ? `${row.students_cleared} / ${row.total_students ?? "?"}` : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </section>
            )}

            {!exam && (
              <div className="py-12 text-center">
                <p className="text-white/30 text-sm italic">
                  No exams found. Create an exam in Exam Configuration first.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </AccessGate>
  );
}

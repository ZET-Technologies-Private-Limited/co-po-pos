"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import { FileUploadSection } from "@/components/workflow/FileUploadSection";
import apiClient from "@/lib/apiClient";
import { AlertCircle, BrainCircuit, Loader2, Plus, RefreshCw } from "lucide-react";

function bloomColor(level: string | undefined) {
  const l = (level || "").toLowerCase();
  if (l === "create" || l === "evaluate") return "text-purple-400";
  if (l === "analyze" || l === "analyse") return "text-blue-400";
  if (l === "apply") return "text-emerald-400";
  if (l === "understand") return "text-amber-400";
  return "text-white/40";
}

export default function QuestionAnalyserPage() {
  const { id } = useParams();
  const courseId = id as string;

  const [exams, setExams] = useState<any[]>([]);
  const [outcomes, setOutcomes] = useState<any[]>([]);
  const [selectedExamId, setSelectedExamId] = useState("");
  const [questionText, setQuestionText] = useState("");
  const [marks, setMarks] = useState(5);
  const [coId, setCoId] = useState("");
  const [questions, setQuestions] = useState<any[]>([]);
  const [analysis, setAnalysis] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true); setError(null);
    try {
      const [ex, cos] = await Promise.all([apiClient.getExams(courseId), apiClient.getCourseOutcomes(courseId)]);
      const examList = Array.isArray(ex) ? ex : [];
      const coList = Array.isArray(cos) ? cos : [];
      setExams(examList);
      setOutcomes(coList);
      const examId = selectedExamId || String(examList[0]?.id || "");
      setSelectedExamId(examId);
      if (!coId && coList.length) setCoId(String(coList[0]?.id || ""));
      if (examId) {
        const q = await apiClient.getQuestions(examId);
        setQuestions(Array.isArray(q?.questions) ? q.questions : []);
      }
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load analyser data.");
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [courseId]);

  async function selectExam(examId: string) {
    setSelectedExamId(examId);
    setAnalysis(null);
    try {
      const q = await apiClient.getQuestions(examId);
      setQuestions(Array.isArray(q?.questions) ? q.questions : []);
    } catch { setQuestions([]); }
  }

  async function addQuestion() {
    if (!selectedExamId || !questionText.trim()) return;
    setWorking(true); setError(null);
    try {
      await apiClient.addQuestions(selectedExamId, [{
        question_number: questions.length + 1,
        question_text: questionText,
        marks,
        question_type: "short_answer",
        bloom_level: "apply",
        co_mapped: coId ? [coId] : [],
        override_reason: "manual entry",
      }]);
      setQuestionText("");
      await selectExam(selectedExamId);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to add question.");
    } finally { setWorking(false); }
  }

  async function runAnalysis() {
    if (!selectedExamId) return;
    setWorking(true); setError(null);
    try {
      const res = await apiClient.analyzeQuestions(selectedExamId);
      setAnalysis(res);
      // Reload questions to get updated bloom levels
      const q = await apiClient.getQuestions(selectedExamId);
      setQuestions(Array.isArray(q?.questions) ? q.questions : []);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Question analysis failed.");
    } finally { setWorking(false); }
  }

  async function redetectBloom() {
    if (!selectedExamId) return;
    setWorking(true); setError(null);
    try {
      await apiClient.detectBloomLevels(selectedExamId);
      await selectExam(selectedExamId);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Bloom detection failed.");
    } finally { setWorking(false); }
  }

  const selectedExam = useMemo(() => exams.find((e) => String(e.id) === selectedExamId), [exams, selectedExamId]);

  const analysisRows: any[] = Array.isArray(analysis?.questions)
    ? analysis.questions
    : Array.isArray(analysis?.results)
    ? analysis.results
    : Array.isArray(analysis)
    ? analysis
    : [];

  const bloomSummary: Record<string, number> = useMemo(() => {
    const map: Record<string, number> = {};
    questions.forEach((q) => {
      const l = q.bloom_level || "unknown";
      map[l] = (map[l] || 0) + 1;
    });
    return map;
  }, [questions]);

  return (
    <AccessGate feature="ai_question_mapping" deny="lock">
      <div className="w-full pb-24 space-y-0">
        {/* Header */}
        <div className="border-b border-white/10 pb-6 mb-8">
          <h1 className="text-3xl text-white font-display">AI Question Analyser</h1>
          <p className="text-white/40 text-sm mt-1 font-mono">
            {selectedExam?.exam_name || "Select an exam to begin"}
          </p>
        </div>

        {loading && <p className="text-white/50 text-sm py-8">Loading...</p>}
        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm py-4">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        {!loading && (
          <>
            {/* Exam Selector + Actions */}
            <section className="border-b border-white/5 pb-8 mb-8">
              <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-5">Exam Selection & Actions</h2>
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                  <label className="text-xs text-white/50 font-mono">Exam</label>
                  <select
                    value={selectedExamId}
                    onChange={(e) => void selectExam(e.target.value)}
                    className="bg-transparent border border-white/20 px-3 py-1.5 text-white text-xs font-mono focus:outline-none focus:border-white/40"
                  >
                    {exams.length === 0 && <option value="">No exams found</option>}
                    {exams.map((e) => (
                      <option key={e.id} value={String(e.id)}>{e.exam_name} ({e.exam_type})</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={() => void runAnalysis()}
                  disabled={working || !selectedExamId}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-mono text-white border border-white/20 hover:border-white/50 disabled:opacity-40 transition-colors"
                >
                  {working ? <Loader2 className="w-3 h-3 animate-spin" /> : <BrainCircuit className="w-3 h-3" />}
                  Analyse Questions
                </button>
                <button
                  onClick={() => void redetectBloom()}
                  disabled={working || !selectedExamId}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-mono text-white/70 border border-white/10 hover:border-white/30 hover:text-white disabled:opacity-40 transition-colors"
                >
                  {working ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                  Re-detect Bloom Levels
                </button>
              </div>
            </section>

            {/* File Upload */}
            <section className="border-b border-white/5 pb-8 mb-8">
              <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">Import Questions from File</h2>
              <FileUploadSection
                title="Upload Questions File"
                description="Supported: CSV, Excel (XLS/XLSX/ODS), DOC/DOCX, ODT/ODF, TXT"
                acceptedFormats={[".csv", ".xlsx", ".xls", ".ods", ".doc", ".docx", ".odt", ".odf", ".txt"]}
                maxSizeMB={10}
                onFileSelect={async (file) => {
                  if (!selectedExamId) {
                    throw new Error("Select an exam before uploading questions.");
                  }
                  const result = await apiClient.uploadQuestionsFile(selectedExamId, file);
                  await selectExam(selectedExamId);
                  return result;
                }}
              />
            </section>

            {/* Add Question Form */}
            <section className="border-b border-white/5 pb-8 mb-8">
              <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-5">Add Question Manually</h2>
              <div className="flex flex-wrap items-end gap-3">
                <div className="flex-1 min-w-64">
                  <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest block mb-1">Question Text</label>
                  <input
                    value={questionText}
                    onChange={(e) => setQuestionText(e.target.value)}
                    placeholder="Enter question text..."
                    className="w-full bg-transparent border border-white/20 px-3 py-2 text-white text-sm placeholder-white/20 focus:outline-none focus:border-white/40"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest block mb-1">Marks</label>
                  <input
                    type="number" value={marks}
                    onChange={(e) => setMarks(Number(e.target.value))}
                    className="w-20 bg-transparent border border-white/20 px-3 py-2 text-white text-sm focus:outline-none focus:border-white/40"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest block mb-1">CO Mapping</label>
                  <select
                    value={coId}
                    onChange={(e) => setCoId(e.target.value)}
                    className="bg-transparent border border-white/20 px-3 py-2 text-white text-sm focus:outline-none focus:border-white/40"
                  >
                    <option value="">None</option>
                    {outcomes.map((co) => (
                      <option key={co.id} value={String(co.id)}>{co.code ?? co.co_code}</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={() => void addQuestion()}
                  disabled={working || !questionText.trim() || !selectedExamId}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-mono text-white border border-white/20 hover:border-white/50 disabled:opacity-40 transition-colors"
                >
                  {working ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
                  Add
                </button>
              </div>
            </section>

            {/* Bloom Summary */}
            {Object.keys(bloomSummary).length > 0 && (
              <section className="border-b border-white/5 pb-8 mb-8">
                <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">Bloom's Taxonomy Distribution</h2>
                <div className="flex flex-wrap gap-6">
                  {Object.entries(bloomSummary).map(([level, count]) => (
                    <div key={level} className="flex items-center gap-2">
                      <span className={`text-sm font-mono font-bold ${bloomColor(level)}`}>{count}</span>
                      <span className="text-xs text-white/40 capitalize">{level}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Questions Table */}
            <section className="border-b border-white/5 pb-8 mb-8">
              <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">
                Questions ({questions.length})
              </h2>
              {questions.length === 0 ? (
                <p className="text-white/30 text-sm italic py-4">No questions configured for this exam.</p>
              ) : (
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-white/5">
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left w-10">#</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left">Question</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center w-16">Marks</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center w-28">Bloom Level</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center w-20">Confidence</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left w-24">CO Mapped</th>
                    </tr>
                  </thead>
                  <tbody>
                    {questions.map((q: any) => (
                      <tr key={q.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                        <td className="py-3 font-mono text-xs text-white/30">{q.question_number}</td>
                        <td className="py-3 text-white/70 pr-4">{q.question_text}</td>
                        <td className="py-3 text-center font-mono text-xs text-white/50">{q.marks}</td>
                        <td className="py-3 text-center">
                          <span className={`text-xs font-mono capitalize ${bloomColor(q.bloom_level)}`}>
                            {q.bloom_level || "—"}
                          </span>
                        </td>
                        <td className="py-3 text-center font-mono text-xs text-white/40">
                          {q.bloom_confidence != null ? `${(q.bloom_confidence * 100).toFixed(0)}%` : "—"}
                        </td>
                        <td className="py-3 font-mono text-xs text-white/40">
                          {Array.isArray(q.mapped_cos) && q.mapped_cos.length > 0
                            ? q.mapped_cos.map((c: any) => c.co_code ?? c).join(", ")
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>

            {/* Analysis Results */}
            {analysisRows.length > 0 && (
              <section className="pb-8">
                <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">
                  AI Analysis Results
                </h2>
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-white/5">
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left">#</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left">Question</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center">Detected Bloom</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center">Confidence</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left">Suggested CO</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysisRows.map((r: any, idx: number) => (
                      <tr key={idx} className="border-b border-white/5 hover:bg-white/[0.02]">
                        <td className="py-3 font-mono text-xs text-white/30">{r.question_number ?? idx + 1}</td>
                        <td className="py-3 text-white/60 pr-4 text-xs">{r.question_text ?? "—"}</td>
                        <td className="py-3 text-center">
                          <span className={`text-xs font-mono capitalize ${bloomColor(r.bloom_level ?? r.detected_bloom)}`}>
                            {r.bloom_level ?? r.detected_bloom ?? "—"}
                          </span>
                        </td>
                        <td className="py-3 text-center font-mono text-xs text-white/40">
                          {r.confidence != null ? `${(r.confidence * 100).toFixed(0)}%` : "—"}
                        </td>
                        <td className="py-3 font-mono text-xs text-white/40">
                          {Array.isArray(r.suggested_cos) ? r.suggested_cos.join(", ") : (r.suggested_co ?? "—")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            )}

            {analysis && analysisRows.length === 0 && (
              <section className="pb-8">
                <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">Analysis Summary</h2>
                <div className="space-y-2">
                  {Object.entries(analysis).map(([key, val]) => (
                    typeof val !== "object" ? (
                      <div key={key} className="flex items-center gap-4 py-2 border-b border-white/5">
                        <span className="text-xs font-mono text-white/30 w-40 capitalize">{key.replace(/_/g, " ")}</span>
                        <span className="text-sm text-white/60">{String(val)}</span>
                      </div>
                    ) : null
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </AccessGate>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import { FileUploadSection } from "@/components/workflow/FileUploadSection";
import apiClient from "@/lib/apiClient";
import { AlertCircle, Loader2, Plus, Trash2 } from "lucide-react";

function buildWorkflowExamSummary(config: any) {
  if (!config || !Array.isArray(config.exams)) return null;
  const exams = config.exams.filter((item: any) => item && typeof item === "object");
  if (exams.length === 0) return null;

  const faExams = exams.filter((item: any) => String(item.exam_type || "").toUpperCase() === "FA");
  const saExams = exams.filter((item: any) => String(item.exam_type || "").toUpperCase() === "SA");

  return {
    faWeight: Number(config.fa_weight ?? 40),
    saWeight: Number(config.sa_weight ?? 60),
    thresholdPct: Number(config.threshold_pct ?? 40),
    directWeight: Number(config.direct_weight ?? 80),
    indirectWeight: Number(config.indirect_weight ?? 20),
    faMethod: String(config.fa_method || "best_n_of_m"),
    faBestN: Number(config.fa_best_n ?? 3),
    faExams,
    saExams,
  };
}

export default function ExamConfigPage() {
  const { id } = useParams();
  const courseId = id as string;

  const [course, setCourse] = useState<any>(null);
  const [chatState, setChatState] = useState<any>(null);
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<string>("");
  const [questions, setQuestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [newExamName, setNewExamName] = useState("T1");
  const [newExamType, setNewExamType] = useState("mid_term");
  const [newExamMarks, setNewExamMarks] = useState(20);

  async function load() {
    setLoading(true); setError(null);
    try {
      const [c, ex, state] = await Promise.all([
        apiClient.getCourse(courseId),
        apiClient.getExams(courseId),
        apiClient.getChatbotState(courseId).catch(() => null),
      ]);
      const examList = Array.isArray(ex) ? ex : [];
      setCourse(c); setExams(examList); setChatState(state);
      const current = selectedExamId || String(examList[0]?.id || "");
      setSelectedExamId(current);
      if (current) {
        const qRes = await apiClient.getQuestions(current);
        setQuestions(Array.isArray(qRes?.questions) ? qRes.questions : []);
      } else { setQuestions([]); }
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load exam config.");
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [courseId]);

  const workflowExamConfig = useMemo(() => {
    const liveState = chatState?.session_data?.live_state;
    const threeFlow = chatState?.session_data?.three_flow;
    return liveState?.exam_config || liveState?.pending_exam_config || threeFlow?.exam_config || null;
  }, [chatState]);

  const workflowExamSummary = useMemo(() => buildWorkflowExamSummary(workflowExamConfig), [workflowExamConfig]);

  async function selectExam(examId: string) {
    setSelectedExamId(examId);
    try {
      const qRes = await apiClient.getQuestions(examId);
      setQuestions(Array.isArray(qRes?.questions) ? qRes.questions : []);
    } catch { setQuestions([]); }
  }

  async function createExam() {
    setWorking(true); setError(null);
    try {
      await apiClient.createExam(courseId, {
        exam_name: newExamName,
        exam_type: newExamType,
        total_marks: newExamMarks,
      });
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to create exam.");
    } finally { setWorking(false); }
  }

  async function deleteExam(examId: string) {
    if (!confirm("Delete this exam and all its questions?")) return;
    setWorking(true); setError(null);
    try {
      await apiClient.deleteExam(courseId, examId);
      setSelectedExamId("");
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to delete exam.");
    } finally { setWorking(false); }
  }

  async function addQuestion() {
    if (!selectedExamId) return;
    setWorking(true); setError(null);
    try {
      await apiClient.addQuestions(selectedExamId, [{
        question_number: questions.length + 1,
        question_text: `Question ${questions.length + 1}`,
        marks: 5,
        question_type: "short_answer",
        bloom_level: "understand",
        co_mapped: [],
        override_reason: "manual_default",
      }]);
      await selectExam(selectedExamId);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to add question.");
    } finally { setWorking(false); }
  }

  async function deleteQuestion(questionId: string) {
    if (!selectedExamId) return;
    setWorking(true); setError(null);
    try {
      await apiClient.deleteQuestion(selectedExamId, questionId);
      await selectExam(selectedExamId);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to delete question.");
    } finally { setWorking(false); }
  }

  const selectedExam = useMemo(() => exams.find((e) => String(e.id) === selectedExamId), [exams, selectedExamId]);

  return (
    <AccessGate feature="exam_config" deny="lock">
      <div className="w-full pb-24 space-y-0">
        {/* Header */}
        <div className="border-b border-white/10 pb-6 mb-8">
          <h1 className="text-3xl text-white font-display">Exam Configuration</h1>
          <p className="text-white/40 text-sm mt-1 font-mono">{course?.course_name || "Loading..."}</p>
        </div>

        {loading && <p className="text-white/50 text-sm py-8">Loading...</p>}
        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm py-4">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        {!loading && (
          <>
            {workflowExamSummary && (
              <section className="border-b border-white/5 pb-8 mb-8">
                <div className="flex flex-col gap-4 border border-white/10 bg-white/[0.02] p-5">
                  <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-3">
                    <div>
                      <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Chatbot Configuration Snapshot</p>
                      <h2 className="text-white text-lg mt-1">Saved Exam Workflow</h2>
                    </div>
                    <p className="text-xs font-mono text-white/40">
                      Stage: {chatState?.session_data?.live_state?.stage || chatState?.step || "course_info"}
                    </p>
                  </div>

                  <div className="grid gap-3 md:grid-cols-4 text-sm">
                    <div className="border border-white/10 p-3">
                      <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest">FA / SA</p>
                      <p className="text-white mt-2">{workflowExamSummary.faWeight}% / {workflowExamSummary.saWeight}%</p>
                    </div>
                    <div className="border border-white/10 p-3">
                      <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Pass Threshold</p>
                      <p className="text-white mt-2">{workflowExamSummary.thresholdPct}%</p>
                    </div>
                    <div className="border border-white/10 p-3">
                      <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest">FA Aggregation</p>
                      <p className="text-white mt-2">
                        {workflowExamSummary.faMethod === "best_n_of_m" ? `Best ${workflowExamSummary.faBestN}` : workflowExamSummary.faMethod.replace(/_/g, " ")}
                      </p>
                    </div>
                    <div className="border border-white/10 p-3">
                      <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Direct : Indirect</p>
                      <p className="text-white mt-2">{workflowExamSummary.directWeight} : {workflowExamSummary.indirectWeight}</p>
                    </div>
                  </div>

                  <div className="grid gap-4 lg:grid-cols-2">
                    <div className="border border-white/10 p-4">
                      <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-3">Formative Assessments</p>
                      {workflowExamSummary.faExams.length === 0 ? (
                        <p className="text-white/30 text-sm italic">No FA exams captured yet.</p>
                      ) : (
                        <div className="space-y-2">
                          {workflowExamSummary.faExams.map((exam: any) => {
                            const marksPerQuestion = exam.question_marks ? Object.values(exam.question_marks)[0] : null;
                            return (
                              <div key={String(exam.exam_id)} className="border border-white/5 p-3 text-sm">
                                <div className="flex items-center justify-between gap-3">
                                  <p className="text-white font-medium">{exam.display_name || exam.exam_id}</p>
                                  <p className="text-white/40 font-mono text-xs">{exam.duration_minutes || 60} min</p>
                                </div>
                                <p className="text-white/50 text-xs mt-2 font-mono">
                                  {exam.question_count} questions · {marksPerQuestion ?? "—"} marks each · total {exam.total_marks}
                                </p>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    <div className="border border-white/10 p-4">
                      <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-3">Summative Assessments</p>
                      {workflowExamSummary.saExams.length === 0 ? (
                        <p className="text-white/30 text-sm italic">No SA exams captured yet.</p>
                      ) : (
                        <div className="space-y-2">
                          {workflowExamSummary.saExams.map((exam: any) => {
                            const marksPerQuestion = exam.question_marks ? Object.values(exam.question_marks)[0] : null;
                            return (
                              <div key={String(exam.exam_id)} className="border border-white/5 p-3 text-sm">
                                <div className="flex items-center justify-between gap-3">
                                  <p className="text-white font-medium">{exam.display_name || exam.exam_id}</p>
                                  <p className="text-white/40 font-mono text-xs">{exam.duration_minutes || 180} min</p>
                                </div>
                                <p className="text-white/50 text-xs mt-2 font-mono">
                                  {exam.question_count} questions · {marksPerQuestion ?? "—"} marks each · total {exam.total_marks}
                                </p>
                                <p className="text-white/40 text-xs mt-1 font-mono">Internal choice: {exam.internal_choice || "No"}</p>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* Create Assessment */}
            <section className="border-b border-white/5 pb-8 mb-8">
              <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-5">Create Assessment</h2>
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest block mb-1">Name</label>
                  <input
                    value={newExamName}
                    onChange={(e) => setNewExamName(e.target.value)}
                    placeholder="e.g. T1, Mid-Sem"
                    className="bg-transparent border border-white/20 px-3 py-2 text-white text-sm placeholder-white/20 focus:outline-none focus:border-white/40 w-32"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest block mb-1">Type</label>
                  <select
                    value={newExamType}
                    onChange={(e) => setNewExamType(e.target.value)}
                    className="bg-transparent border border-white/20 px-3 py-2 text-white text-sm focus:outline-none focus:border-white/40"
                  >
                    <option value="mid_term">Mid Term</option>
                    <option value="end_term">End Term</option>
                    <option value="quiz">Quiz</option>
                    <option value="assignment">Assignment</option>
                    <option value="lab">Lab</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest block mb-1">Total Marks</label>
                  <input
                    type="number"
                    value={newExamMarks}
                    onChange={(e) => setNewExamMarks(Number(e.target.value))}
                    className="bg-transparent border border-white/20 px-3 py-2 text-white text-sm focus:outline-none focus:border-white/40 w-24"
                  />
                </div>
                <button
                  onClick={() => void createExam()}
                  disabled={working || !newExamName.trim()}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-mono text-white border border-white/20 hover:border-white/50 disabled:opacity-40 transition-colors"
                >
                  {working ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
                  Create
                </button>
              </div>
            </section>

            {/* Assessments List */}
            <section className="border-b border-white/5 pb-8 mb-8">
              <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">
                Assessments ({exams.length})
              </h2>
              {exams.length === 0 ? (
                <p className="text-white/30 text-sm italic py-4">No assessments created yet.</p>
              ) : (
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-white/5">
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left">Name</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left">Type</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center">Total Marks</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center">Weightage</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center">Questions</th>
                      <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exams.map((e: any) => (
                      <tr
                        key={e.id}
                        onClick={() => void selectExam(String(e.id))}
                        className={`border-b border-white/5 cursor-pointer transition-colors ${
                          String(e.id) === selectedExamId ? "bg-brand/5 border-l-2 border-l-brand" : "hover:bg-white/[0.02]"
                        }`}
                      >
                        <td className="py-3 text-white font-medium">{e.exam_name}</td>
                        <td className="py-3 text-white/50 text-xs font-mono capitalize">{e.exam_type?.replace(/_/g, " ")}</td>
                        <td className="py-3 text-center text-white/50 text-xs font-mono">{e.total_marks}</td>
                        <td className="py-3 text-center text-white/50 text-xs font-mono">
                          {e.weightage_pct != null ? `${e.weightage_pct}%` : "—"}
                        </td>
                        <td className="py-3 text-center text-white/50 text-xs font-mono">
                          {e.question_count ?? e.number_of_questions ?? "—"}
                        </td>
                        <td className="py-3 text-right">
                          <button
                            onClick={(ev) => { ev.stopPropagation(); void deleteExam(String(e.id)); }}
                            disabled={working}
                            className="text-red-400/60 hover:text-red-400 transition-colors disabled:opacity-40"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>

            {/* File Upload for Questions */}
            {selectedExamId && (
              <section className="border-b border-white/5 pb-8 mb-8">
                <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">
                  Import Questions — {selectedExam?.exam_name}
                </h2>
                <FileUploadSection
                  title="Upload Questions File"
                  description="Supported: CSV, Excel (XLS/XLSX/ODS), DOC/DOCX, ODT/ODF, TXT"
                  acceptedFormats={[".csv", ".xlsx", ".xls", ".ods", ".doc", ".docx", ".odt", ".odf", ".txt"]}
                  maxSizeMB={10}
                  onFileSelect={async (file) => {
                    const result = await apiClient.uploadQuestionsFile(selectedExamId, file);
                    await selectExam(selectedExamId);
                    return result;
                  }}
                  onSuccess={() => void load()}
                />
              </section>
            )}

            {/* Questions Table */}
            {selectedExamId && (
              <section className="pb-8">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest">
                    Questions — {selectedExam?.exam_name} ({questions.length})
                  </h2>
                  <button
                    onClick={() => void addQuestion()}
                    disabled={working}
                    className="flex items-center gap-2 text-xs font-mono text-white/60 hover:text-white transition-colors disabled:opacity-40"
                  >
                    <Plus className="w-3 h-3" /> Add Question
                  </button>
                </div>
                {questions.length === 0 ? (
                  <p className="text-white/30 text-sm italic py-4">No questions configured. Add manually or import from file.</p>
                ) : (
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-white/5">
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left w-10">#</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-left">Question</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center w-16">Marks</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-center w-28">Bloom Level</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-2 text-right w-16">Delete</th>
                      </tr>
                    </thead>
                    <tbody>
                      {questions.map((q: any) => (
                        <tr key={q.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                          <td className="py-3 font-mono text-xs text-white/30">{q.question_number}</td>
                          <td className="py-3 text-white/70 pr-4">{q.question_text}</td>
                          <td className="py-3 text-center font-mono text-xs text-white/50">{q.marks}</td>
                          <td className="py-3 text-center font-mono text-xs text-white/50 capitalize">{q.bloom_level || "—"}</td>
                          <td className="py-3 text-right">
                            <button
                              onClick={() => void deleteQuestion(String(q.id))}
                              disabled={working}
                              className="text-red-400/40 hover:text-red-400 transition-colors disabled:opacity-40"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </section>
            )}
          </>
        )}
      </div>
    </AccessGate>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

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
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
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
      } else {
        setQuestions([]);
      }
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load analyser data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [courseId]);

  async function selectExam(examId: string) {
    setSelectedExamId(examId);
    const q = await apiClient.getQuestions(examId);
    setQuestions(Array.isArray(q?.questions) ? q.questions : []);
  }

  async function addQuestion() {
    if (!selectedExamId || !questionText.trim()) return;
    setError(null);
    try {
      await apiClient.addQuestions(selectedExamId, [
        {
          question_number: questions.length + 1,
          question_text: questionText,
          marks,
          question_type: "short_answer",
          bloom_level: "apply",
          co_mapped: coId ? [coId] : [],
          override_reason: "manual",
        },
      ]);
      setQuestionText("");
      await selectExam(selectedExamId);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to add question.");
    }
  }

  async function runAnalysis() {
    if (!selectedExamId) return;
    setError(null);
    try {
      const res = await apiClient.analyzeQuestions(selectedExamId);
      setAnalysis(res);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Question analysis failed.");
    }
  }

  async function redetectBloom() {
    if (!selectedExamId) return;
    setError(null);
    try {
      await apiClient.detectBloomLevels(selectedExamId);
      await selectExam(selectedExamId);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Bloom detection failed.");
    }
  }

  const selectedExam = useMemo(() => exams.find((e) => String(e.id) === selectedExamId), [exams, selectedExamId]);

  return (
    <AccessGate feature="ai_question_mapping" deny="lock">
      <div className="max-w-5xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">AI Question Analyser</h1>
          <p className="text-white/50 mt-1">{selectedExam?.exam_name || "Select an exam"}</p>
        </div>

        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading ? (
          <>
            <section className="border border-white/10 rounded-lg p-4 space-y-3">
              <h2 className="text-sm text-white">Add Question</h2>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <select value={selectedExamId} onChange={(e) => void selectExam(e.target.value)} className="bg-transparent border border-white/20 rounded px-2 py-2 text-white">
                  {exams.map((e) => (
                    <option key={e.id} value={String(e.id)}>{e.exam_name}</option>
                  ))}
                </select>
                <input value={questionText} onChange={(e) => setQuestionText(e.target.value)} placeholder="Question text" className="md:col-span-2 bg-transparent border border-white/20 rounded px-2 py-2 text-white" />
                <input type="number" value={marks} onChange={(e) => setMarks(Number(e.target.value))} className="bg-transparent border border-white/20 rounded px-2 py-2 text-white" />
              </div>
              <div className="flex items-center gap-3">
                <select value={coId} onChange={(e) => setCoId(e.target.value)} className="bg-transparent border border-white/20 rounded px-2 py-1 text-white text-sm">
                  <option value="">CO Mapping (optional)</option>
                  {outcomes.map((co) => (
                    <option key={co.id} value={String(co.id)}>{co.code || co.co_code}</option>
                  ))}
                </select>
                <button onClick={() => void addQuestion()} className="bg-brand text-white rounded px-3 py-1 text-xs">Add</button>
                <button onClick={() => void runAnalysis()} className="border border-white/20 text-white/80 rounded px-3 py-1 text-xs">Analyze</button>
                <button onClick={() => void redetectBloom()} className="border border-white/20 text-white/80 rounded px-3 py-1 text-xs">Re-detect Bloom</button>
              </div>
            </section>

            <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="border border-white/10 rounded-lg p-4">
                <h2 className="text-sm text-white mb-3">Questions</h2>
                <div className="space-y-2">
                  {questions.map((q) => (
                    <div key={q.id} className="border border-white/10 rounded p-2">
                      <p className="text-white text-sm">Q{q.question_number}: {q.question_text}</p>
                      <p className="text-white/50 text-xs mt-1">Marks: {q.marks} | Bloom: {q.bloom_level || "-"}</p>
                    </div>
                  ))}
                  {questions.length === 0 ? <p className="text-white/40 text-sm">No questions available.</p> : null}
                </div>
              </div>

              <div className="border border-white/10 rounded-lg p-4">
                <h2 className="text-sm text-white mb-3">Analysis</h2>
                <pre className="text-xs text-white/70 whitespace-pre-wrap">{analysis ? JSON.stringify(analysis, null, 2) : "Run analysis to view AI diagnostics."}</pre>
              </div>
            </section>
          </>
        ) : null}
      </div>
    </AccessGate>
  );
}

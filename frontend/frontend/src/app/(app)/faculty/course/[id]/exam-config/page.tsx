"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function ExamConfigPage() {
  const { id } = useParams();
  const courseId = id as string;

  const [course, setCourse] = useState<any>(null);
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<string>("");
  const [questions, setQuestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newExamName, setNewExamName] = useState("T1");
  const [newExamType, setNewExamType] = useState("mid_term");
  const [newExamMarks, setNewExamMarks] = useState(20);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [c, ex] = await Promise.all([apiClient.getCourse(courseId), apiClient.getExams(courseId)]);
      const examList = Array.isArray(ex) ? ex : [];
      setCourse(c);
      setExams(examList);
      const current = selectedExamId || String(examList[0]?.id || "");
      setSelectedExamId(current);
      if (current) {
        const qRes = await apiClient.getQuestions(current);
        setQuestions(Array.isArray(qRes?.questions) ? qRes.questions : []);
      } else {
        setQuestions([]);
      }
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load exam config.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [courseId]);

  async function selectExam(examId: string) {
    setSelectedExamId(examId);
    try {
      const qRes = await apiClient.getQuestions(examId);
      setQuestions(Array.isArray(qRes?.questions) ? qRes.questions : []);
    } catch {
      setQuestions([]);
    }
  }

  async function createExam() {
    try {
      await apiClient.createExam(courseId, {
        exam_name: newExamName,
        exam_type: newExamType,
        total_marks: newExamMarks,
      });
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to create exam.");
    }
  }

  async function deleteExam(examId: string) {
    try {
      await apiClient.deleteExam(courseId, examId);
      setSelectedExamId("");
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to delete exam.");
    }
  }

  async function addQuestion() {
    if (!selectedExamId) return;
    try {
      await apiClient.addQuestions(selectedExamId, [
        {
          question_number: questions.length + 1,
          question_text: `Question ${questions.length + 1}`,
          marks: 5,
          question_type: "short_answer",
          bloom_level: "understand",
          co_mapped: [],
        },
      ]);
      await selectExam(selectedExamId);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to add question.");
    }
  }

  const selectedExam = useMemo(() => exams.find((e) => String(e.id) === selectedExamId), [exams, selectedExamId]);

  return (
    <AccessGate feature="exam_config" deny="lock">
      <div className="max-w-5xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">Exam Configuration</h1>
          <p className="text-white/50 mt-1">{course?.course_name || "Course"}</p>
        </div>

        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading ? (
          <>
            <section className="border border-white/10 rounded-lg p-4 space-y-3">
              <h2 className="text-sm text-white">Create Assessment</h2>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <input value={newExamName} onChange={(e) => setNewExamName(e.target.value)} className="bg-transparent border border-white/20 rounded px-2 py-2 text-white" placeholder="Exam name" />
                <input value={newExamType} onChange={(e) => setNewExamType(e.target.value)} className="bg-transparent border border-white/20 rounded px-2 py-2 text-white" placeholder="Exam type" />
                <input type="number" value={newExamMarks} onChange={(e) => setNewExamMarks(Number(e.target.value))} className="bg-transparent border border-white/20 rounded px-2 py-2 text-white" />
                <button onClick={() => void createExam()} className="bg-brand text-white rounded px-3 py-2 text-sm">Create</button>
              </div>
            </section>

            <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="border border-white/10 rounded-lg p-4">
                <h2 className="text-sm text-white mb-3">Assessments</h2>
                <div className="space-y-2">
                  {exams.map((e) => (
                    <div key={e.id} className="flex items-center justify-between gap-2 border border-white/10 rounded p-2">
                      <button className="text-left flex-1" onClick={() => void selectExam(String(e.id))}>
                        <p className="text-white text-sm">{e.exam_name}</p>
                        <p className="text-white/50 text-xs">{e.exam_type} | {e.total_marks}</p>
                      </button>
                      <button className="text-xs text-alert" onClick={() => void deleteExam(String(e.id))}>Delete</button>
                    </div>
                  ))}
                  {exams.length === 0 ? <p className="text-white/40 text-sm">No assessments yet.</p> : null}
                </div>
              </div>

              <div className="lg:col-span-2 border border-white/10 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm text-white">Questions {selectedExam ? `for ${selectedExam.exam_name}` : ""}</h2>
                  <button onClick={() => void addQuestion()} disabled={!selectedExamId} className="text-xs text-brand">Add Question</button>
                </div>
                <div className="space-y-2">
                  {questions.map((q) => (
                    <div key={q.id} className="border border-white/10 rounded p-2">
                      <p className="text-white text-sm">Q{q.question_number}: {q.question_text}</p>
                      <p className="text-white/50 text-xs mt-1">Marks: {q.marks} | Bloom: {q.bloom_level || "-"}</p>
                    </div>
                  ))}
                  {selectedExamId && questions.length === 0 ? <p className="text-white/40 text-sm">No questions configured.</p> : null}
                </div>
              </div>
            </section>
          </>
        ) : null}
      </div>
    </AccessGate>
  );
}

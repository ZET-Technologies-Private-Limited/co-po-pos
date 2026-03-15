"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

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
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [c, ex] = await Promise.all([apiClient.getCourse(courseId), apiClient.getExams(courseId)]);
      const examList = Array.isArray(ex) ? ex : [];
      const selected = examList.find((e) => String(e.id) === examToken || String(e.assessment_code || "").toLowerCase() === examToken.toLowerCase()) || examList[0];

      setCourse(c);
      setExams(examList);
      setExam(selected || null);

      if (!selected) {
        setQuestions([]);
        setRows([]);
        setPreview(null);
        return;
      }

      const [qRes, mRes] = await Promise.all([apiClient.getQuestions(String(selected.id)), apiClient.getMarks(String(selected.id))]);
      const qList = Array.isArray(qRes?.questions) ? qRes.questions : [];
      setQuestions(qList);

      const dataRows = Array.isArray(mRes?.rows)
        ? mRes.rows
        : Array.isArray(mRes?.students)
        ? mRes.students.map((s: any) => ({ student_id: s.student_id || s.roll || "", marks: s.marks || {} }))
        : [];

      setRows(dataRows.map((r: any) => ({ student_id: String(r.student_id || ""), marks: r.marks || {} })));

      try {
        const p = await apiClient.getMarksPreview(String(selected.id), 0.6);
        setPreview(p);
      } catch {
        setPreview(null);
      }
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load marks page.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [courseId, examToken]);

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
    setError(null);
    try {
      const payloadRows = rows.filter((r) => r.student_id.trim()).map((r) => ({ student_id: r.student_id.trim(), marks: r.marks }));
      await apiClient.submitMarks(String(exam.id), { rows: payloadRows });
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to save marks.");
    }
  }

  async function submitForApproval() {
    if (!exam) return;
    setError(null);
    try {
      await apiClient.submitMarksForApproval(String(exam.id));
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to submit marks for approval.");
    }
  }

  const totalRows = useMemo(() => rows.length, [rows]);

  return (
    <AccessGate feature="marks_upload" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">Marks Upload</h1>
          <p className="text-white/50 mt-1">
            {course?.course_name || "Course"} | {exam?.exam_name || "Exam"}
          </p>
        </div>

        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading && exam ? (
          <>
            <section className="border border-white/10 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm text-white">Entry Grid ({totalRows} rows)</h2>
                <button onClick={addStudentRow} className="text-xs text-brand">Add Student Row</button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-white/[0.03] text-white/50">
                    <tr>
                      <th className="px-2 py-2">Student ID</th>
                      {questions.map((q) => (
                        <th key={q.id || q.question_number} className="px-2 py-2">Q{q.question_number}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, idx) => (
                      <tr key={idx} className="border-t border-white/10">
                        <td className="px-2 py-2">
                          <input value={row.student_id} onChange={(e) => updateStudent(idx, e.target.value)} className="w-full bg-transparent border border-white/20 rounded px-2 py-1 text-white" />
                        </td>
                        {questions.map((q) => (
                          <td key={`${idx}-${q.id || q.question_number}`} className="px-2 py-2">
                            <input
                              type="number"
                              value={row.marks[q.question_number] ?? ""}
                              onChange={(e) => updateMark(idx, String(q.question_number), e.target.value)}
                              className="w-20 bg-transparent border border-white/20 rounded px-2 py-1 text-white"
                            />
                          </td>
                        ))}
                      </tr>
                    ))}
                    {rows.length === 0 ? (
                      <tr>
                        <td className="px-2 py-4 text-white/40" colSpan={Math.max(2, questions.length + 1)}>
                          No marks loaded yet.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center gap-3 mt-4">
                <button onClick={() => void saveDraft()} className="px-3 py-1 bg-brand text-white rounded text-xs">Save Draft</button>
                <button onClick={() => void submitForApproval()} className="px-3 py-1 border border-white/20 text-white/80 rounded text-xs">Submit For Approval</button>
              </div>
            </section>

            <section className="border border-white/10 rounded-lg p-4">
              <h2 className="text-sm text-white mb-2">Live CO Preview</h2>
              <pre className="text-xs text-white/70 whitespace-pre-wrap">{preview ? JSON.stringify(preview, null, 2) : "Preview unavailable."}</pre>
            </section>
          </>
        ) : null}
      </div>
    </AccessGate>
  );
}

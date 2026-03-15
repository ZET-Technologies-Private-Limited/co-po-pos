"use client";

import { FormEvent, useEffect, useState } from "react";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

export default function StudentGrievancePage() {
  const [courses, setCourses] = useState<any[]>([]);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const c = await apiClient.getCourses();
        if (cancelled) return;
        const list = Array.isArray(c) ? c : [];
        setCourses(list);
        if (list.length) setSelectedCourse(String(list[0].id));
        const notifications = await apiClient.getNotifications();
        const items = Array.isArray(notifications?.items) ? notifications.items : [];
        setHistory(items);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load grievance data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiClient.sendChatMessage({
        message: `Student grievance: ${message}`,
        course_id: selectedCourse || undefined,
      });
      setMessage("");
      const notifications = await apiClient.getNotifications();
      const items = Array.isArray(notifications?.items) ? notifications.items : [];
      setHistory(items);
    } catch (err: any) {
      setError(typeof err?.message === "string" ? err.message : "Failed to submit grievance message.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AccessGate feature="dashboard" deny="lock">
      <div className="max-w-4xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">Student Grievance</h1>
          <p className="text-white/50 mt-1">Live service integration (chatbot + notification stream)</p>
        </div>

        {loading ? <p className="text-white/60">Loading...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading ? (
          <>
            <form onSubmit={submit} className="border border-white/10 rounded-lg p-4 space-y-3">
              <label className="text-xs text-white/50">Course</label>
              <select value={selectedCourse} onChange={(e) => setSelectedCourse(e.target.value)} className="w-full bg-transparent border border-white/20 rounded px-2 py-2 text-white">
                {courses.map((c) => (
                  <option key={c.id} value={String(c.id)}>{c.course_code} - {c.course_name}</option>
                ))}
              </select>

              <label className="text-xs text-white/50">Message</label>
              <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={5} className="w-full bg-transparent border border-white/20 rounded px-2 py-2 text-white" />
              <button type="submit" disabled={submitting} className="px-3 py-1 bg-brand text-white rounded text-xs">
                {submitting ? "Submitting..." : "Submit"}
              </button>
            </form>

            <section className="border border-white/10 rounded-lg p-4">
              <h2 className="text-sm text-white mb-3">Recent Service Updates</h2>
              <div className="space-y-2">
                {history.map((h, idx) => (
                  <div key={idx} className="border border-white/10 rounded p-2">
                    <p className="text-white text-sm">{h.title || "Notification"}</p>
                    <p className="text-white/60 text-xs mt-1">{h.message || ""}</p>
                  </div>
                ))}
                {history.length === 0 ? <p className="text-white/40 text-sm">No updates found.</p> : null}
              </div>
            </section>
          </>
        ) : null}
      </div>
    </AccessGate>
  );
}

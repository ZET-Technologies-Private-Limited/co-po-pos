"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

type ChatItem = {
  role: "user" | "assistant";
  text: string;
  timestamp: string;
};

const STEP_OPTIONS = ["course_info", "syllabus", "po_pso_confirm", "co_count", "generate", "review", "save"];

export default function FacultyCourseChatbotPage() {
  const { id } = useParams();
  const courseId = id as string;

  const [course, setCourse] = useState<any>(null);
  const [chatState, setChatState] = useState<any>(null);
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [input, setInput] = useState("");
  const [updatingStep, setUpdatingStep] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSend = useMemo(() => input.trim().length > 0 && !sending, [input, sending]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [c, state] = await Promise.all([apiClient.getCourse(courseId), apiClient.getChatbotState(courseId)]);
        if (cancelled) return;
        setCourse(c);
        setChatState(state);
        setMessages([
          {
            role: "assistant",
            text: "OBE assistant is ready. Ask for CO generation, syllabus checks, mapping hints, or workflow guidance.",
            timestamp: new Date().toISOString(),
          },
        ]);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load chatbot session.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  async function sendMessage(e: FormEvent) {
    e.preventDefault();
    if (!canSend) return;

    const userText = input.trim();
    const now = new Date().toISOString();

    setSending(true);
    setError(null);
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: userText, timestamp: now }]);

    try {
      const reply = await apiClient.sendChatMessage({
        message: userText,
        course_id: courseId,
      });

      const replyText =
        typeof reply?.reply === "string"
          ? reply.reply
          : typeof reply?.message === "string"
            ? reply.message
            : typeof reply?.response === "string"
              ? reply.response
              : JSON.stringify(reply);

      setMessages((prev) => [...prev, { role: "assistant", text: replyText, timestamp: new Date().toISOString() }]);

      const refreshedState = await apiClient.getChatbotState(courseId);
      setChatState(refreshedState);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to send chatbot message.");
    } finally {
      setSending(false);
    }
  }

  async function updateStep(step: string) {
    setUpdatingStep(true);
    setError(null);
    try {
      const payload = {
        ...(chatState?.session_data || {}),
        course_id: courseId,
        course_code: course?.course_code,
        course_name: course?.course_name,
      };
      const updated = await apiClient.updateChatbotState(courseId, step, payload);
      setChatState(updated);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to update chatbot step.");
    } finally {
      setUpdatingStep(false);
    }
  }

  async function resetSession() {
    setError(null);
    try {
      await apiClient.resetChatbotSession(courseId);
      const refreshedState = await apiClient.getChatbotState(courseId);
      setChatState(refreshedState);
      setMessages([
        {
          role: "assistant",
          text: "Session reset complete. You can start the OBE workflow again.",
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to reset chatbot session.");
    }
  }

  return (
    <AccessGate feature="co_generation" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">Faculty OBE Chatbot</h1>
          <p className="text-white/50 mt-1">
            {course?.course_code || "Course"} - {course?.course_name || "Loading..."}
          </p>
        </div>

        {loading ? <p className="text-white/60">Loading chatbot session...</p> : null}
        {error ? <p className="text-alert">{error}</p> : null}

        {!loading ? (
          <>
            <section className="border border-white/10 rounded-lg p-4 space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <p className="text-xs text-white/50 uppercase tracking-widest">Workflow Step</p>
                <select
                  value={chatState?.step || "course_info"}
                  onChange={(e) => void updateStep(e.target.value)}
                  disabled={updatingStep}
                  className="bg-transparent border border-white/20 rounded px-2 py-1 text-sm text-white"
                >
                  {STEP_OPTIONS.map((step) => (
                    <option key={step} value={step}>
                      {step}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => void resetSession()}
                  className="px-3 py-1 text-xs rounded bg-white/10 text-white hover:bg-white/20"
                >
                  Reset Session
                </button>
              </div>
              <pre className="text-xs text-white/60 whitespace-pre-wrap">
                {JSON.stringify(chatState || { step: "course_info", session_data: {} }, null, 2)}
              </pre>
            </section>

            <section className="border border-white/10 rounded-lg p-4">
              <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                {messages.map((m, idx) => (
                  <div
                    key={`${m.timestamp}-${idx}`}
                    className={`rounded-lg px-3 py-2 text-sm ${
                      m.role === "user" ? "bg-brand/20 text-white ml-8" : "bg-white/[0.04] text-white/85 mr-8"
                    }`}
                  >
                    <p className="text-[10px] uppercase tracking-widest mb-1 text-white/50">{m.role}</p>
                    <p className="whitespace-pre-wrap">{m.text}</p>
                  </div>
                ))}
              </div>

              <form onSubmit={sendMessage} className="mt-4 flex gap-2">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask the OBE assistant about CO generation, mappings, or attainment..."
                  className="flex-1 bg-transparent border border-white/20 rounded px-3 py-2 text-sm text-white"
                />
                <button
                  type="submit"
                  disabled={!canSend}
                  className="px-4 py-2 text-sm bg-brand text-white rounded disabled:opacity-60"
                >
                  {sending ? "Sending..." : "Send"}
                </button>
              </form>
            </section>
          </>
        ) : null}
      </div>
    </AccessGate>
  );
}

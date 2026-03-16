"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";

type ChatItem = { role: "user" | "assistant"; text: string; timestamp: string };

const STEP_GUIDE = [
  "STEP 1: course details, syllabus, NBA POs, PSOs, CO count",
  "STEP 2: confirm CO-PO-PSO mapping matrix",
  "STEP 3: confirm exam configuration",
  "STEP 4: confirm question to CO and BT mapping",
  "STEP 5: enter marks and calculate attainment",
];

function createSessionId(courseId: string): string {
  const randomPart = Math.random().toString(36).slice(2, 10);
  return `three-flow-${courseId}-${Date.now()}-${randomPart}`;
}

function mapWorkflowToMessageNumber(step: number): 1 | 2 | 3 {
  if (step <= 1) return 1;
  if (step === 2) return 2;
  return 3;
}

function inferWorkflowStepFromStatus(status: string | undefined): number {
  const s = String(status || "").toLowerCase();
  if (["course_saved", "course_partial", "cos_generated", "co_confirmation_required", "co_edit_requested"].includes(s)) {
    return 1;
  }
  if (["co_confirmed", "mapping_preview", "mapping_invalid", "mapping_edit_requested"].includes(s)) {
    return 2;
  }
  if (s) return 3;
  return 1;
}

export default function FacultyCourseChatbotPage() {
  const { id } = useParams();
  const courseId = id as string;

  const [course, setCourse] = useState<any>(null);
  const [chatState, setChatState] = useState<any>(null);
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flowSessionId] = useState(() => createSessionId(courseId));
  const [workflowStep, setWorkflowStep] = useState(1);
  const [nbaPOs, setNbaPOs] = useState<any[]>([]);
  const [deptPSOs, setDeptPSOs] = useState<any[]>([]);

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
        // Silently pre-load NBA POs and department PSOs
        const [pos, psos] = await Promise.all([
          apiClient.getNBAPOs().catch(() => []),
          c?.department ? apiClient.getDepartmentPSOs(c.department).catch(() => []) : Promise.resolve([]),
        ]);
        if (!cancelled) { setNbaPOs(pos); setDeptPSOs(psos); }
        if (Number(state?.session_data?.workflow_step) >= 1) {
          setWorkflowStep(Number(state.session_data.workflow_step));
        }
        setMessages([{
          role: "assistant",
          text: "OBE assistant is ready. This workflow is strictly sequential: STEP 1 CO generation, STEP 2 CO-PO-PSO mapping, STEP 3 exam configuration, STEP 4 question mapping, STEP 5 marks and attainment. For STEP 3 you can use plain English, and for STEP 4 you can send shorthand like `T1: Q1=CO1, Q2=CO2`.",
          timestamp: new Date().toISOString(),
        }]);
      } catch (e: any) {
        if (cancelled) return;
        setError(typeof e?.message === "string" ? e.message : "Failed to load chatbot session.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [courseId]);

  async function sendMessage(e: FormEvent) {
    e.preventDefault();
    if (!canSend) return;
    const userText = input.trim();
    const now = new Date().toISOString();
    setSending(true); setError(null); setInput("");
    setMessages(prev => [...prev, { role: "user", text: userText, timestamp: now }]);
    try {
      // For Message 2 (syllabus), append PO/PSO context so backend has them available
      const msgNumber = mapWorkflowToMessageNumber(workflowStep);
      let messageText = userText;
      if (msgNumber === 2 && (nbaPOs.length > 0 || deptPSOs.length > 0)) {
        const poLines = nbaPOs.map((p: any) => `${p.code}: ${p.statement || p.name || p.code}`).join("\n");
        const psoLines = deptPSOs.map((p: any) => `${p.code}: ${p.statement || p.code}`).join("\n");
        const poBlock = poLines ? `\n\nNBA Standard POs:\n${poLines}` : "";
        const psoBlock = psoLines ? `\n\nDepartment PSOs:\n${psoLines}` : "";
        messageText = userText + poBlock + psoBlock;
      }
      const reply = await apiClient.sendChatMessage({
        message: messageText,
        course_id: courseId,
        session_id: flowSessionId,
        message_number: msgNumber,
      });
      const replyText =
        typeof reply?.reply === "string" ? reply.reply :
        typeof reply?.message === "string" ? reply.message :
        typeof reply?.response === "string" ? reply.response :
        JSON.stringify(reply);

      // Append unit complexity analysis when COs are generated
      let displayText = replyText;
      if (reply?.status === "cos_generated" && Array.isArray(reply?.unit_analysis) && reply.unit_analysis.length > 0) {
        const unitLines = (reply.unit_analysis as any[]).map((u: any) => {
          const hours = u.hours != null ? ` (${u.hours}h)` : "";
          const priority = u.is_priority ? " ★ priority" : "";
          return `  ${u.unit}${hours}: ${u.bt_level} (${u.bloom_level}) — verb: ${u.suggested_action_verb}${priority}`;
        }).join("\n");
        displayText = replyText + "\n\nUnit Complexity Analysis:\n" + unitLines;
      }
      setMessages(prev => [...prev, { role: "assistant", text: displayText, timestamp: new Date().toISOString() }]);
      const nextStep = Number(reply?.workflow_step);
      if (!Number.isNaN(nextStep) && nextStep >= 1) {
        setWorkflowStep(nextStep);
      } else {
        setWorkflowStep(inferWorkflowStepFromStatus(reply?.status));
      }
      const refreshedState = await apiClient.getChatbotState(courseId);
      setChatState(refreshedState);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to send chatbot message.");
    } finally {
      setSending(false);
    }
  }

  async function resetSession() {
    setError(null);
    try {
      await apiClient.resetChatbotSession(courseId);
      const refreshedState = await apiClient.getChatbotState(courseId);
      setChatState(refreshedState);
      setWorkflowStep(1);
      setMessages([{ role: "assistant", text: "Session reset. You can start the OBE workflow again.", timestamp: new Date().toISOString() }]);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to reset chatbot session.");
    }
  }

  return (
    <AccessGate feature="co_generation" deny="lock">
      <div className="max-w-6xl mx-auto pb-24 space-y-6">
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-3xl text-white font-display">Faculty OBE Chatbot</h1>
          <p className="text-white/50 mt-1 text-sm">
            {course?.course_code || "Course"} — {course?.course_name || "Loading..."}
          </p>
        </div>

        {loading && <p className="text-white/60">Loading chatbot session...</p>}
        {error && <p className="text-alert text-sm">{error}</p>}

        {!loading && (
          <>
            {/* Workflow step controls */}
            <section className="border border-white/10 p-4 space-y-3">
              <div className="space-y-2">
                <p className="text-xs text-white/50 uppercase tracking-widest font-mono">Guided Workflow</p>
                {STEP_GUIDE.map((step, index) => {
                  const active = workflowStep === index + 1;
                  const completed = workflowStep > index + 1;
                  return (
                    <div
                      key={step}
                      className={`text-xs font-mono px-3 py-2 border ${completed ? "border-emerald-500/30 text-emerald-300 bg-emerald-500/5" : active ? "border-amber-500/30 text-amber-200 bg-amber-500/5" : "border-white/10 text-white/35"}`}
                    >
                      {step}
                    </div>
                  );
                })}
                <div className="flex items-center gap-2">
                  <span className="text-xs text-white/30 font-mono">Current backend stage:</span>
                  <span className="text-xs text-white/50 font-mono">{chatState?.session_data?.live_state?.stage || chatState?.step || "course_info"}</span>
                </div>
                <button
                  onClick={() => void resetSession()}
                  className="px-3 py-1 text-xs bg-white/10 text-white hover:bg-white/20"
                >
                  Reset Session
                </button>
              </div>
            </section>

            {/* Chat messages */}
            <section className="border border-white/10 p-4">
              <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                {messages.map((m, idx) => (
                  <div
                    key={`${m.timestamp}-${idx}`}
                    className={`px-3 py-2 text-sm ${m.role === "user" ? "bg-brand/20 text-white ml-8" : "bg-white/[0.04] text-white/85 mr-8"}`}
                  >
                    <p className="text-[10px] uppercase tracking-widest mb-1 text-white/50">{m.role}</p>
                    <p className="whitespace-pre-wrap">{m.text}</p>
                  </div>
                ))}
              </div>

              <form onSubmit={sendMessage} className="mt-4 flex gap-2">
                <input
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder={workflowStep === 3 ? "Describe FA/SA exams in plain English or paste JSON..." : workflowStep === 4 ? "Send T1: Q1=CO1, Q2=CO2 or paste question text..." : "Ask the OBE assistant about CO generation, mappings, or attainment..."}
                  className="flex-1 bg-transparent border border-white/20 px-3 py-2 text-sm text-white"
                />
                <button
                  type="submit"
                  disabled={!canSend}
                  className="px-4 py-2 text-sm bg-brand text-white disabled:opacity-60"
                >
                  {sending ? "Sending..." : "Send"}
                </button>
              </form>
            </section>
          </>
        )}
      </div>
    </AccessGate>
  );
}

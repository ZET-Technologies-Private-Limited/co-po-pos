"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, BrainCircuit, Loader2, RotateCcw } from "lucide-react";
import apiClient from "@/lib/apiClient";

const DEFAULT_SUGGESTIONS = [
  "Start OBE wizard",
  "Show CO attainment for my course",
  "Which CO has lowest attainment?",
  "Generate PO attainment summary",
];

function newSessionId() {
  return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

function extractReply(res: any): string {
  if (typeof res === "string") return res;
  // LangGraph response
  if (res?.reply) return res.reply;
  // ThreeMessageFlowService direct response
  if (res?.message) return res.message;
  if (res?.response) return res.response;
  return "No response.";
}

export default function ChatbotPage() {
  const [courses, setCourses] = useState<any[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState("");
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string }[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionIdRef = useRef<string>(newSessionId());
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadCourses = useCallback(async () => {
    try {
      const res = await apiClient.getCourses();
      const list = Array.isArray(res) ? res : ((res as any)?.items ?? []);
      setCourses(list);
      if (list.length && !selectedCourseId) setSelectedCourseId(list[0].id);
    } catch {
      setCourses([]);
    }
  }, [selectedCourseId]);

  useEffect(() => { void loadCourses(); }, [loadCourses]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const send = async (text: string) => {
    const q = (text || input).trim();
    if (!q || sending) return;
    setInput("");
    setError(null);
    setMessages(prev => [...prev, { role: "user", text: q }]);
    setSending(true);
    try {
      const res = await apiClient.sendChatMessage({
        message: q,
        course_id: selectedCourseId || undefined,
        session_id: sessionIdRef.current,
      });
      setMessages(prev => [...prev, { role: "assistant", text: extractReply(res) }]);
    } catch (e: any) {
      setError(e?.message ?? "Failed to get reply.");
      setMessages(prev => [...prev, { role: "assistant", text: "Sorry, the assistant is unavailable. Please try again." }]);
    } finally {
      setSending(false);
    }
  };

  const resetConversation = async () => {
    if (selectedCourseId) {
      try { await apiClient.resetChatbotSession(selectedCourseId); } catch { /* ignore */ }
    }
    sessionIdRef.current = newSessionId();
    setMessages([]);
    setInput("");
    setError(null);
  };

  const handleCourseChange = async (courseId: string) => {
    if (selectedCourseId && selectedCourseId !== courseId) {
      try { await apiClient.resetChatbotSession(selectedCourseId); } catch { /* ignore */ }
      sessionIdRef.current = newSessionId();
      setMessages([]);
      setError(null);
    }
    setSelectedCourseId(courseId);
  };

  return (
    <div className="w-full flex flex-col h-screen pb-0">
      <div className="max-w-3xl mx-auto w-full px-6 pt-12 flex flex-col h-full">

        <div className="mb-8 shrink-0">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 text-sm font-mono text-aurora uppercase tracking-widest mb-4">
                <BrainCircuit className="w-4 h-4" /> Nexus Intelligence
              </div>
              <h1 className="text-4xl font-display text-white">AI Assistant</h1>
            </div>
            <button onClick={resetConversation} className="flex items-center gap-2 border border-white/10 px-3 py-2 text-[10px] font-mono uppercase tracking-widest text-white/50 hover:border-white/30 hover:text-white transition-colors">
              <RotateCcw className="w-3.5 h-3.5" /> Clear session
            </button>
          </div>
          <div className="mt-6 grid gap-4 rounded-2xl border border-white/10 bg-white/[0.02] p-4">
            <p className="text-[10px] font-mono uppercase tracking-widest text-white/35">Course context</p>
            <select
              value={selectedCourseId}
              onChange={e => handleCourseChange(e.target.value)}
              className="min-w-[240px] border border-white/10 bg-transparent px-3 py-2 text-sm text-white outline-none transition-colors hover:border-white/30"
            >
              <option value="" className="bg-[#0D1829]">General (no course)</option>
              {courses.map((c: any) => (
                <option key={c.id} value={c.id} className="bg-[#0D1829]">
                  {c.course_code ?? c.code} - {c.course_name ?? c.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex gap-3 flex-wrap mb-6 shrink-0">
          {DEFAULT_SUGGESTIONS.map(s => (
            <button key={s} onClick={() => send(s)}
              className="px-4 py-2 border border-white/10 text-white/50 text-xs font-mono hover:border-aurora/50 hover:text-aurora transition-colors uppercase tracking-wide">
              {s}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto flex flex-col gap-8 py-4 pr-2 mb-4">
          <AnimatePresence>
            {messages.map((msg, i) => (
              <motion.div key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && (
                  <div className="w-8 h-8 rounded-full border border-aurora/50 flex items-center justify-center shrink-0 mt-1">
                    <Sparkles className="w-4 h-4 text-aurora" />
                  </div>
                )}
                <div className={`max-w-xl ${msg.role === "user" ? "text-right" : ""}`}>
                  <p className={`leading-relaxed whitespace-pre-line font-light text-lg ${msg.role === "assistant" ? "text-white/80" : "text-white"}`}>
                    {msg.text}
                  </p>
                  <p className="mt-2 text-xs font-mono text-white/20">{msg.role === "assistant" ? "Nexus AI" : "You"}</p>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          {sending && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-4">
              <div className="w-8 h-8 rounded-full border border-aurora/50 flex items-center justify-center shrink-0">
                <Sparkles className="w-4 h-4 text-aurora" />
              </div>
              <div className="flex gap-1 items-center h-8">
                <Loader2 className="w-5 h-5 text-aurora animate-spin" />
              </div>
            </motion.div>
          )}
          {error && <p className="text-alert text-sm">{error}</p>}
          <div ref={bottomRef} />
        </div>

        <div className="shrink-0 border-t border-white/10 pt-6 pb-8">
          <div className="flex items-center gap-4">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && !e.shiftKey && send(input)}
              placeholder="Ask about attainment, outcomes, or generate reports..."
              className="flex-1 bg-transparent border-b border-white/20 focus:border-white py-3 text-white placeholder-white/30 outline-none transition-colors text-lg"
            />
            <button onClick={() => send(input)} disabled={!input.trim() || sending}
              className="w-12 h-12 flex items-center justify-center border border-white/20 hover:border-white hover:bg-white hover:text-black text-white transition-all disabled:opacity-30 shrink-0">
              {sending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

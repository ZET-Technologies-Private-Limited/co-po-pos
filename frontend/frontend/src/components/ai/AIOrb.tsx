"use client";

import { motion, AnimatePresence } from "framer-motion";
import { spring } from "@/lib/animations";
import { useState, useRef, useEffect } from "react";
import { usePathname } from "next/navigation";
import { MessageSquare, X, Sparkles, Send } from "lucide-react";
import apiClient from "@/lib/apiClient";
import { useUIStore } from "@/lib/uiStore";

type ChatItem = { role: "user" | "assistant"; text: string };

function getCourseIdFromPath(pathname: string): string | undefined {
  const m = pathname.match(/^\/faculty\/course\/([^/]+)/);
  return m ? m[1] : undefined;
}

interface AIOrbProps {
  thinking?: boolean;
}

export function AIOrb({ thinking = false }: AIOrbProps) {
  const { chatOpen, openChat, closeChat } = useUIStore();
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const courseId = getCourseIdFromPath(pathname ?? "");

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", text }]);
    setSending(true);
    try {
      const res = await apiClient.sendChatMessage({
        message: text,
        course_id: courseId,
      });
      const replyText =
        typeof res?.reply === "string"
          ? res.reply
          : typeof res?.message === "string"
            ? res.message
            : typeof res?.response === "string"
              ? res.response
              : res?.data ? JSON.stringify(res.data) : "I’m your OBE assistant. Type **help** for features.";
      setMessages((prev) => [...prev, { role: "assistant", text: replyText }]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to send message.";
      setError(msg);
      setMessages((prev) => [...prev, { role: "assistant", text: `Error: ${msg}` }]);
    } finally {
      setSending(false);
    }
  };

  const welcomeMessage: ChatItem = {
    role: "assistant",
    text: courseId
      ? "OBE Assistant ready. Ask about CO generation, exam setup, question mapping, marks, attainment, or reports for this course."
      : "OBE Assistant ready. Ask about courses, CO-PO mapping, attainment, or reports. Open a course for course-specific actions.",
  };
  const displayMessages = messages.length ? messages : [welcomeMessage];

  return (
    <>
      {/* Floating Chatbot Icon – visible on all app pages */}
      <AnimatePresence>
        {!chatOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={openChat}
            aria-label="Open OBE Chatbot"
            className="fixed bottom-8 right-8 w-14 h-14 rounded-full bg-brand flex items-center justify-center text-white shadow-lg shadow-brand/30 z-50 overflow-hidden"
          >
            <motion.div
              animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.6, 0.3] }}
              transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
              className="absolute inset-0 bg-aurora/50 rounded-full"
            />
            <MessageSquare className="w-7 h-7 relative z-10" />
            {thinking && (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 4, ease: "linear" }}
                className="absolute inset-[-2px] rounded-full border-t-2 border-r-2 border-white/80"
              />
            )}
          </motion.button>
        )}
      </AnimatePresence>

      {/* Real-time Chat Panel – no mock conversations; all via backend LLM */}
      <AnimatePresence>
        {chatOpen && (
          <motion.div
            initial={{ opacity: 0, y: 100, scale: 0.9, originX: 1, originY: 1 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 100, scale: 0.9 }}
            transition={spring.smooth}
            className="fixed bottom-8 right-8 w-[min(96vw,800px)] max-h-[75vh] bg-cosmic border border-white/10 rounded-2xl shadow-2xl z-50 flex overflow-hidden backdrop-blur-xl"
            style={{ backgroundColor: "rgba(15, 23, 42, 0.95)" }}
          >
            {/* Left: Real-time chat (backend + LLM) */}
            <div className="w-[45%] min-w-[320px] border-r border-white/10 flex flex-col flex-1 min-h-0">
              <div className="p-4 border-b border-white/10 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2 text-white font-display">
                  <Sparkles className="text-aurora w-5 h-5" aria-hidden />
                  <h3 className="text-sm font-semibold">Academic Intelligence</h3>
                  {courseId && (
                    <span className="text-[10px] font-mono text-white/50 truncate max-w-[100px]" title={courseId}>
                      Course
                    </span>
                  )}
                </div>
                <button
                  onClick={closeChat}
                  aria-label="Close chat"
                  className="p-1.5 text-white/50 hover:text-white transition-colors rounded"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div
                ref={scrollRef}
                className="flex-1 p-4 overflow-y-auto flex flex-col gap-3 min-h-0"
              >
                {displayMessages.map((m, i) => (
                  <div
                    key={i}
                    className={`rounded-lg px-3 py-2 text-sm max-w-[85%] ${
                      m.role === "user"
                        ? "bg-brand/20 border border-brand/30 self-end text-white"
                        : "bg-white/5 text-white/90 self-start"
                    }`}
                  >
                    <p className="whitespace-pre-wrap break-words">{m.text}</p>
                  </div>
                ))}
                {sending && (
                  <div className="bg-white/5 rounded-lg px-3 py-2 text-sm text-white/70 self-start flex gap-1 items-center">
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-aurora animate-pulse" />
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-aurora animate-pulse [animation-delay:0.15s]" />
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-aurora animate-pulse [animation-delay:0.3s]" />
                  </div>
                )}
                {error && (
                  <p className="text-[11px] text-alert px-2">{error}</p>
                )}
              </div>

              <div className="p-4 border-t border-white/10 shrink-0 flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                  placeholder="Ask about CO, attainment, reports..."
                  className="flex-1 bg-white/5 border border-white/10 rounded-full px-4 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-aurora/50"
                  disabled={sending}
                />
                <button
                  type="button"
                  onClick={() => handleSend()}
                  disabled={sending || !input.trim()}
                  aria-label="Send message"
                  className="p-2.5 rounded-full bg-brand text-white hover:bg-brand/90 disabled:opacity-50 disabled:pointer-events-none transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Right: Contextual visualizations (driven by backend/LLM responses) */}
            <div className="w-[55%] p-6 flex flex-col items-center justify-center bg-white/[0.02] min-w-0">
              <p className="text-sm text-white/40 text-center mb-4">
                Contextual visualizations will appear here
              </p>
              <p className="text-[11px] text-white/30 text-center max-w-[260px] mb-6">
                Ask for CO attainment, reports, or course data — charts and summaries from the backend will show here when the assistant returns them.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                <span className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs text-white/50">
                  Show CO below threshold
                </span>
                <span className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs text-white/50">
                  Generate attainment report
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useUIStore } from "@/lib/uiStore";
import { useAuthStore } from "@/lib/authStore";
import { useRouter } from "next/navigation";
import { Clock } from "lucide-react";

const SESSION_MS = 30 * 60 * 1000;   // 30 min total
const WARN_MS   = 25 * 60 * 1000;    // warn at 25 min

export function SessionTimeoutModal() {
  const { sessionWarning, setSessionWarning } = useUIStore();
  const { isAuthenticated, logout } = useAuthStore();
  const router = useRouter();
  const warnTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const logoutTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [countdown, setCountdown] = useState(300); // 5 min in seconds

  function resetTimers() {
    if (warnTimer.current) clearTimeout(warnTimer.current);
    if (logoutTimer.current) clearTimeout(logoutTimer.current);
    setSessionWarning(false);
    setCountdown(300);

    warnTimer.current = setTimeout(() => {
      setSessionWarning(true);
      setCountdown(300);
    }, WARN_MS);

    logoutTimer.current = setTimeout(() => {
      logout();
      router.push("/login");
    }, SESSION_MS);
  }

  useEffect(() => {
    if (!isAuthenticated) return;
    resetTimers();
    const events = ["mousemove", "keydown", "click", "scroll"];
    const onActivity = () => { if (!sessionWarning) resetTimers(); };
    events.forEach(e => window.addEventListener(e, onActivity));
    return () => {
      events.forEach(e => window.removeEventListener(e, onActivity));
      if (warnTimer.current) clearTimeout(warnTimer.current);
      if (logoutTimer.current) clearTimeout(logoutTimer.current);
    };
  }, [isAuthenticated]);

  // Countdown tick
  useEffect(() => {
    if (!sessionWarning) return;
    const tick = setInterval(() => setCountdown(c => Math.max(0, c - 1)), 1000);
    return () => clearInterval(tick);
  }, [sessionWarning]);

  function handleContinue() { resetTimers(); }
  function handleLogout() { setSessionWarning(false); logout(); router.push("/login"); }

  const mins = Math.floor(countdown / 60);
  const secs = countdown % 60;

  return (
    <AnimatePresence>
      {sessionWarning && (
        <>
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[300] bg-black/60 backdrop-blur-sm"
            aria-hidden="true"
          />
          <motion.div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="session-title"
            aria-describedby="session-desc"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[310] w-full max-w-sm bg-[#0D1829] border border-white/10 shadow-2xl p-8 flex flex-col items-center gap-6"
          >
            <div className="w-14 h-14 rounded-full bg-alert/10 border border-alert/20 flex items-center justify-center">
              <Clock className="w-6 h-6 text-alert" aria-hidden="true" />
            </div>
            <div className="text-center">
              <h2 id="session-title" className="text-white font-display text-xl mb-2">Session Expiring</h2>
              <p id="session-desc" className="text-white/50 text-sm font-light">
                Your session will expire in{" "}
                <span className="text-alert font-mono font-medium">{mins}:{secs.toString().padStart(2, "0")}</span>.
                Continue to stay logged in.
              </p>
            </div>
            <div className="flex gap-3 w-full">
              <button
                onClick={handleContinue}
                autoFocus
                className="flex-1 py-3 bg-brand text-white text-sm font-medium hover:bg-brand/80 transition-colors focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-2 focus:ring-offset-[#0D1829]"
              >
                Yes, Continue
              </button>
              <button
                onClick={handleLogout}
                className="flex-1 py-3 border border-white/10 text-white/60 text-sm hover:text-white hover:border-white/30 transition-colors focus:outline-none focus:ring-2 focus:ring-white/20"
              >
                Logout
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

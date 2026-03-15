"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowRight, Eye, EyeOff, Loader2, AlertCircle,
  ShieldAlert, GraduationCap, Lock, KeyRound,
} from "lucide-react";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import { useAuthStore } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";

const MAX_ATTEMPTS = 5;
const ACTIVE_AYS = ["2024-25", "2023-24", "2022-23"];

export default function StudentLoginPage() {
  const router = useRouter();
  const { login, setActiveAY, loginError, isAuthenticated, user } = useAuthStore();

  const [roll, setRoll]           = useState("");
  const [password, setPassword]   = useState("");
  const [ay, setAY]               = useState("2024-25");
  const [showPass, setShowPass]   = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // First-login password change
  const [showPwChange, setShowPwChange]     = useState(false);
  const [newPw, setNewPw]                   = useState("");
  const [confirmPw, setConfirmPw]           = useState("");
  const [showNewPw, setShowNewPw]           = useState(false);
  const [pwChangeError, setPwChangeError]   = useState("");
  const [pwChanging, setPwChanging]         = useState(false);

  // Field validation
  const [touched, setTouched]         = useState<{ roll?: boolean; password?: boolean }>({});
  const [fieldErrors, setFieldErrors] = useState<{ roll?: string; password?: string }>({});

  // Lockout (sessionStorage so it resets on tab close)
  const [attempts, setAttempts] = useState<number>(() =>
    typeof window !== "undefined" ? Number(sessionStorage.getItem("sl_attempts") || "0") : 0
  );
  const [locked, setLocked] = useState<boolean>(() =>
    typeof window !== "undefined" ? sessionStorage.getItem("sl_locked") === "1" : false
  );

  useEffect(() => {
    if (isAuthenticated && user?.roles.includes("student") && !user.firstLogin) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, user, router]);

  function validateRoll(v: string) {
    if (!v.trim()) return "Roll number is required";
    return "";
  }
  function validatePassword(v: string) {
    if (!v) return "Password is required";
    if (v.length < 6) return "Minimum 6 characters";
    return "";
  }
  function validateNewPw(v: string) {
    if (!v) return "New password is required";
    if (v.length < 8) return "Minimum 8 characters";
    if (!/[A-Z]/.test(v)) return "Must contain an uppercase letter";
    if (!/[0-9]/.test(v)) return "Must contain a number";
    return "";
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (locked) return;

    const rollErr = validateRoll(roll);
    const passErr = validatePassword(password);
    setTouched({ roll: true, password: true });
    setFieldErrors({ roll: rollErr, password: passErr });
    if (rollErr || passErr) return;

    setIsLoading(true);

    // For student portal we treat roll number as employee_id for backend login
    const identifier = roll.trim();
    const success = await login(identifier, password, {
      academicYear: ay,
    });
    if (success) {
      sessionStorage.removeItem("sl_attempts");
      sessionStorage.removeItem("sl_locked");
      setAttempts(0);
      setActiveAY(ay);
      const freshUser = useAuthStore.getState().user;
      if (freshUser?.firstLogin) {
        setShowPwChange(true);
        setIsLoading(false);
      } else {
        router.push("/dashboard");
      }
    } else {
      const n = attempts + 1;
      setAttempts(n);
      sessionStorage.setItem("sl_attempts", String(n));
      if (n >= MAX_ATTEMPTS) { setLocked(true); sessionStorage.setItem("sl_locked", "1"); }
      setIsLoading(false);
    }
  };

  const handlePwChange = async (e: React.FormEvent) => {
    e.preventDefault();
    const err = validateNewPw(newPw);
    if (err) { setPwChangeError(err); return; }
    if (newPw !== confirmPw) { setPwChangeError("Passwords do not match"); return; }
    if (newPw === password) { setPwChangeError("New password must differ from current password"); return; }

    setPwChanging(true);
    setPwChangeError("");
    try {
      await apiClient.changePassword({
        old_password: password,
        new_password: newPw,
        confirm_password: confirmPw,
      });
      useAuthStore.setState(s => ({ user: s.user ? { ...s.user, firstLogin: false } : null }));
      router.push("/dashboard");
    } catch (e: any) {
      setPwChangeError(e?.message || "Password change failed. Please try again.");
    } finally {
      setPwChanging(false);
    }
  };

  const remaining = MAX_ATTEMPTS - attempts;

  // ── FIRST LOGIN: FORCE PASSWORD CHANGE ──────────────────────────────────
  if (showPwChange) {
    return (
      <div className="min-h-screen bg-[#020817] flex items-center justify-center px-4">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
          <div className="flex items-center gap-3 mb-12">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <GraduationCap className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-white font-display text-sm font-medium">Student Portal</p>
              <p className="text-white/30 text-[10px] font-mono uppercase tracking-widest">Nexus Engine</p>
            </div>
          </div>

          <div className="mb-10">
            <div className="flex items-center gap-2 text-[10px] font-mono text-cyan-400 uppercase tracking-widest mb-4">
              <span className="w-6 h-[1px] bg-cyan-400" /> First Login
            </div>
            <h1 className="text-3xl font-display text-white mb-2">Set your password</h1>
            <p className="text-white/40 text-sm font-light leading-relaxed">
              You must set a new password before accessing your dashboard.
            </p>
          </div>

          <form onSubmit={handlePwChange} className="flex flex-col gap-6" noValidate>
            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
                <KeyRound className="w-3 h-3" /> New Password
              </label>
              <div className="flex items-center gap-3 border-b border-white/20 pb-3 focus-within:border-cyan-400 transition-colors">
                <input
                  type={showNewPw ? "text" : "password"}
                  value={newPw}
                  onChange={e => { setNewPw(e.target.value); setPwChangeError(""); }}
                  placeholder="Min 8 chars · 1 uppercase · 1 number"
                  autoFocus
                  className="bg-transparent text-white flex-1 outline-none text-xl placeholder-white/20 font-light"
                />
                <button type="button" onClick={() => setShowNewPw(v => !v)} className="text-white/20 hover:text-white/60 transition-colors">
                  {showNewPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-[10px] font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
                <Lock className="w-3 h-3" /> Confirm Password
              </label>
              <input
                type="password"
                value={confirmPw}
                onChange={e => { setConfirmPw(e.target.value); setPwChangeError(""); }}
                placeholder="Re-enter new password"
                className="bg-transparent text-white outline-none text-xl placeholder-white/20 font-light border-b border-white/20 pb-3 focus:border-cyan-400 transition-colors"
              />
            </div>

            <AnimatePresence>
              {pwChangeError && (
                <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  className="text-red-400 text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-3 h-3" /> {pwChangeError}
                </motion.p>
              )}
            </AnimatePresence>

            <div className="p-4 bg-cyan-400/5 border border-cyan-400/20 text-[10px] font-mono text-cyan-400/70 leading-relaxed">
              Requirements: 8+ characters · 1 uppercase letter · 1 number
            </div>

            <button
              type="submit"
              disabled={pwChanging || !newPw || !confirmPw}
              className="flex items-center justify-center gap-3 py-4 bg-cyan-500 text-white font-medium text-sm hover:bg-cyan-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {pwChanging
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
                : <>Set Password &amp; Continue <ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>
        </motion.div>
      </div>
    );
  }

  // ── MAIN LOGIN ───────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#020817] flex">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col justify-between w-5/12 bg-gradient-to-b from-cyan-950/40 to-blue-950/20 border-r border-white/5 px-16 py-16">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="text-white font-display text-sm font-medium">Student Portal</p>
            <p className="text-white/30 text-[10px] font-mono uppercase tracking-widest">Nexus Engine</p>
          </div>
        </div>

        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-2 text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
            <span className="w-6 h-[1px] bg-cyan-400" /> Academic Year {ay}
          </div>
          <h1 className="text-5xl font-display text-white leading-tight">
            Track your<br /><span className="text-cyan-400">outcomes.</span>
          </h1>
          <p className="text-white/40 font-light leading-relaxed text-lg max-w-xs">
            View your CO attainment, exam marks, and academic progress in one place.
          </p>
        </div>

        <div className="flex flex-col gap-2 text-[10px] font-mono text-white/20 uppercase tracking-widest">
          <p>Student access</p>
          <div className="flex flex-col gap-1 text-white/40">
            <span>Use your institution-issued roll number and password.</span>
          </div>
        </div>
      </div>

      {/* Right form */}
      <div className="flex-1 flex items-center justify-center px-8 lg:px-16 py-16">
        <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="w-full max-w-sm">

          <div className="flex items-center gap-3 mb-12 lg:hidden">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <GraduationCap className="w-5 h-5 text-white" />
            </div>
            <p className="text-white font-display text-sm font-medium">Student Portal</p>
          </div>

          <motion.div variants={fadeSlideUp} className="mb-10">
            <div className="flex items-center gap-2 text-[10px] font-mono text-cyan-400 uppercase tracking-widest mb-4">
              <span className="w-6 h-[1px] bg-cyan-400" /> Secure Access
            </div>
            <h2 className="text-4xl font-display text-white">Welcome back.</h2>
          </motion.div>

          {locked ? (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-6">
              <div className="flex items-start gap-4 p-5 bg-red-500/5 border border-red-500/30">
                <ShieldAlert className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-red-400 text-sm font-mono font-medium mb-1">Account locked</p>
                  <p className="text-white/50 text-sm font-light leading-relaxed">
                    Too many failed attempts. Contact your faculty advisor or reset your password.
                  </p>
                </div>
              </div>
              <Link href="/forgot-password"
                className="flex items-center justify-between px-6 py-4 bg-white text-black text-sm font-medium hover:bg-white/90 transition-colors">
                Reset Password <ArrowRight className="w-4 h-4" />
              </Link>
            </motion.div>
          ) : (
            <motion.form variants={staggerContainer} onSubmit={handleLogin} className="flex flex-col gap-0" noValidate>

              {/* AY Selector */}
              <motion.div variants={fadeSlideUp} className="flex flex-col gap-2 pb-6 mb-2 border-b border-white/10">
                <label className="text-[10px] font-mono text-white/40 uppercase tracking-widest">Academic Year</label>
                <select
                  value={ay}
                  onChange={e => setAY(e.target.value)}
                  className="bg-transparent text-white text-sm outline-none font-light appearance-none cursor-pointer"
                >
                  {ACTIVE_AYS.map(a => (
                    <option key={a} value={a} className="bg-[#020817]">{a}</option>
                  ))}
                </select>
              </motion.div>

              {/* Roll Number */}
              <motion.div variants={fadeSlideUp} className="flex flex-col gap-2 py-6">
                <label className="text-[10px] font-mono text-white/40 uppercase tracking-widest">Roll Number</label>
                <input
                  type="text"
                  value={roll}
                  onChange={e => { setRoll(e.target.value); if (touched.roll) setFieldErrors(f => ({ ...f, roll: validateRoll(e.target.value) })); }}
                  onBlur={() => { setTouched(t => ({ ...t, roll: true })); setFieldErrors(f => ({ ...f, roll: validateRoll(roll) })); }}
                  placeholder="e.g. 21CS001"
                  autoComplete="username"
                  className={`bg-transparent text-white text-2xl placeholder-white/20 outline-none font-light border-b pb-3 transition-colors ${
                    touched.roll && fieldErrors.roll ? "border-red-500" : "border-white/20 focus:border-cyan-400"
                  }`}
                />
                <AnimatePresence>
                  {touched.roll && fieldErrors.roll && (
                    <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                      className="text-red-400 text-xs font-mono flex items-center gap-1.5">
                      <AlertCircle className="w-3 h-3" /> {fieldErrors.roll}
                    </motion.p>
                  )}
                </AnimatePresence>
              </motion.div>

              {/* Password */}
              <motion.div variants={fadeSlideUp} className="flex flex-col gap-2 py-6">
                <label className="text-[10px] font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
                  <Lock className="w-3 h-3" /> Password
                </label>
                <div className={`flex items-center gap-3 border-b pb-3 transition-colors ${
                  touched.password && fieldErrors.password ? "border-red-500" : "border-white/20 focus-within:border-cyan-400"
                }`}>
                  <input
                    type={showPass ? "text" : "password"}
                    value={password}
                    onChange={e => { setPassword(e.target.value); if (touched.password) setFieldErrors(f => ({ ...f, password: validatePassword(e.target.value) })); }}
                    onBlur={() => { setTouched(t => ({ ...t, password: true })); setFieldErrors(f => ({ ...f, password: validatePassword(password) })); }}
                    placeholder="••••••••"
                    autoComplete="current-password"
                    className="bg-transparent text-white text-2xl placeholder-white/20 outline-none flex-1 font-light"
                  />
                  <button type="button" onClick={() => setShowPass(v => !v)} className="text-white/20 hover:text-white/60 transition-colors pb-1">
                    {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <AnimatePresence>
                  {touched.password && fieldErrors.password && (
                    <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                      className="text-red-400 text-xs font-mono flex items-center gap-1.5">
                      <AlertCircle className="w-3 h-3" /> {fieldErrors.password}
                    </motion.p>
                  )}
                </AnimatePresence>
                <div className="flex justify-end mt-1">
                  <Link href="/forgot-password" className="text-[10px] font-mono text-white/30 hover:text-cyan-400 transition-colors uppercase tracking-widest">
                    Forgot password?
                  </Link>
                </div>
              </motion.div>

              {/* Error banner */}
              <AnimatePresence>
                {loginError && !locked && (
                  <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    className="flex items-start gap-3 p-4 bg-red-500/5 border border-red-500/30 mb-4">
                    <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-red-400 text-sm font-mono">Incorrect roll number or password.</p>
                      {remaining > 0 && remaining < MAX_ATTEMPTS && (
                        <p className="text-white/40 text-xs mt-1 font-mono">
                          {remaining} attempt{remaining !== 1 ? "s" : ""} remaining before lockout.
                        </p>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Submit */}
              <motion.div variants={fadeSlideUp} className="pt-2">
                <button
                  type="submit"
                  disabled={isLoading || !roll || !password}
                  className="w-full flex items-center justify-center gap-3 py-4 bg-cyan-500 text-white font-medium text-sm hover:bg-cyan-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isLoading
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Signing in…</>
                    : <>Sign In <ArrowRight className="w-4 h-4" /></>}
                </button>
              </motion.div>
            </motion.form>
          )}

          <p className="mt-10 text-white/20 text-xs font-mono text-center">
            Faculty or staff?{" "}
            <Link href="/login" className="text-white/40 hover:text-cyan-400 transition-colors">
              Use the main portal →
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}

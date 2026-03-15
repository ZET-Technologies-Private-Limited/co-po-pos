"use client";

import { Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import { Lock, CheckCircle2, Eye, EyeOff } from "lucide-react";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import { useAuthStore } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const isFirstLogin = searchParams.get("first") === "1";
  const { user } = useAuthStore();

  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{ current?: string; password?: string; confirm?: string }>({});

  const submit = async () => {
    if (!user) return;
    const e: typeof errors = {};
    if (!currentPassword) e.current = "Current password is required";
    if (password.length < 8) e.password = "Min. 8 characters required";
    if (!/[A-Z]/.test(password)) e.password = "Must include an uppercase letter";
    if (!/[0-9]/.test(password)) e.password = "Must include a number";
    if (!/[^A-Za-z0-9]/.test(password)) e.password = "Must include a special character";
    if (password !== confirm) e.confirm = "Passwords do not match";
    if (Object.keys(e).length) { setErrors(e); return; }
    setLoading(true);
    setErrors({});
    try {
      if (user) {
        await apiClient.changePassword({
          old_password: currentPassword,
          new_password: password,
          confirm_password: confirm,
        });
        if (isFirstLogin) useAuthStore.setState(s => ({ user: s.user ? { ...s.user, firstLogin: false } : null }));
      }
      setDone(true);
      if (isFirstLogin) {
        setTimeout(() => {
          const role = useAuthStore.getState().activeRole;
          const ROLE_HOME: Record<string, string> = {
            admin: "/dashboard", department_head: "/dashboard",
            subject_lead: "/dashboard", faculty: "/faculty/dashboard", student: "/student/dashboard",
          };
          router.push(role ? ROLE_HOME[role] || "/dashboard" : "/dashboard");
        }, 2000);
      }
    } catch (err: any) {
      setErrors({ password: err?.message || "Password change failed" });
    } finally {
      setLoading(false);
    }
  };

  const strength = [password.length >= 8, /[A-Z]/.test(password), /[0-9]/.test(password), /[^A-Za-z0-9]/.test(password)];
  const strengthColor = ["bg-alert", "bg-alert", "bg-aurora", "bg-brand"];
  const filled = strength.filter(Boolean).length;

  return (
    <div className="min-h-screen bg-cosmic flex items-center justify-center px-4">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="w-full max-w-md">
        {!done ? (
          <>
            <motion.div variants={fadeSlideUp} className="mb-12">
              <div className="flex items-center gap-3 text-sm font-mono text-white/40 uppercase tracking-widest mb-8">
                <span className="w-8 h-[1px] bg-white/20"></span>
                Account Recovery
              </div>
              <h1 className="text-4xl font-display text-white mb-4">Reset your password</h1>
              <p className="text-white/50 font-light text-lg">Choose a new strong password for your Nexus Engine account.</p>
            </motion.div>

            <motion.div variants={fadeSlideUp} className="flex flex-col gap-6">
              {user ? (
                <label className="flex flex-col gap-3">
                  <span className="text-xs font-mono text-white/50 uppercase tracking-widest flex items-center gap-2"><Lock className="w-3 h-3" /> Current Password</span>
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={e => setCurrentPassword(e.target.value)}
                    placeholder="Your current password"
                    className="bg-transparent border-b border-white/20 focus:border-white py-3 text-white placeholder-white/30 outline-none transition-colors text-xl w-full"
                  />
                  {errors.current && <span className="text-alert text-sm font-mono">{errors.current}</span>}
                </label>
              ) : (
                <p className="text-white/50 text-sm">Log in first to change your password, or use <Link href="/forgot-password" className="text-brand underline">Forgot password</Link>.</p>
              )}
              <label className="flex flex-col gap-3">
                <span className="text-xs font-mono text-white/50 uppercase tracking-widest flex items-center gap-2"><Lock className="w-3 h-3" /> New Password</span>
                <div className="relative">
                  <input
                    type={show ? "text" : "password"}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="Min. 8 characters"
                    className="bg-transparent border-b border-white/20 focus:border-white py-3 text-white placeholder-white/30 outline-none transition-colors text-xl w-full pr-10"
                  />
                  <button onClick={() => setShow(s => !s)} className="absolute right-0 top-1/2 -translate-y-1/2 text-white/40 hover:text-white">
                    {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {errors.password && <span className="text-alert text-sm font-mono">{errors.password}</span>}
                
                {/* Strength bar */}
                <div className="flex gap-2">
                  {[0,1,2,3].map(i => (
                    <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${i < filled ? strengthColor[filled - 1] : "bg-white/10"}`} />
                  ))}
                </div>
                <span className="text-xs text-white/40 font-mono">{["", "Weak", "Fair", "Good", "Strong"][filled]} password</span>
              </label>

              <label className="flex flex-col gap-3">
                <span className="text-xs font-mono text-white/50 uppercase tracking-widest flex items-center gap-2"><Lock className="w-3 h-3" /> Confirm Password</span>
                <input
                  type="password"
                  value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  placeholder="Repeat your password"
                  className="bg-transparent border-b border-white/20 focus:border-white py-3 text-white placeholder-white/30 outline-none transition-colors text-xl"
                />
                {errors.confirm && <span className="text-alert text-sm font-mono">{errors.confirm}</span>}
              </label>

              <button onClick={submit} disabled={!!user && !currentPassword} className="mt-4 px-8 py-4 bg-white text-black font-medium text-sm self-start hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                {loading ? "Updating…" : "Reset Password"}
              </button>
            </motion.div>
          </>
        ) : (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-8">
            <CheckCircle2 className="w-16 h-16 text-brand" />
            <h1 className="text-4xl font-display text-white">Password updated.</h1>
            <p className="text-white/50 text-lg font-light">You can now use your new password to sign in.</p>
            <Link href="/login" className="px-8 py-4 bg-white text-black font-medium text-sm self-start hover:bg-white/90 transition-colors">
              Go to Sign In →
            </Link>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-cosmic" />}>
      <ResetPasswordContent />
    </Suspense>
  );
}

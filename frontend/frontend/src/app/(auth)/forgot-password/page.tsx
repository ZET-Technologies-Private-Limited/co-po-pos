"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Lock, Eye, EyeOff, CheckCircle2, ArrowRight, AlertCircle, RefreshCw } from "lucide-react";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import apiClient from "@/lib/apiClient";

const STEPS = ["Identity", "Verify OTP", "New Password", "Done"];
const OTP_EXPIRY_SECS = 600; // 10 minutes
const RESEND_COOLDOWN = 60;

function StrengthMeter({ password }: { password: string }) {
  const checks = [
    { label: "At least 8 characters",       met: password.length >= 8 },
    { label: "One uppercase letter",         met: /[A-Z]/.test(password) },
    { label: "One number",                   met: /[0-9]/.test(password) },
    { label: "One special character",        met: /[^A-Za-z0-9]/.test(password) },
  ];
  const score = checks.filter(c => c.met).length;
  const labels = ["", "Weak", "Fair", "Good", "Strong"];
  const colors = ["", "bg-red-500", "bg-alert", "bg-aurora", "bg-attain"];

  return (
    <div className="flex flex-col gap-3 mt-2">
      <div className="flex gap-1.5">
        {[0, 1, 2, 3].map(i => (
          <div key={i} className={`h-1 flex-1 transition-colors ${i < score ? colors[score] : "bg-white/10"}`} />
        ))}
      </div>
      <p className="text-xs font-mono text-white/40">{labels[score] || "Enter a password"}</p>
      <div className="flex flex-col gap-1.5 mt-1">
        {checks.map(c => (
          <div key={c.label} className={`flex items-center gap-2 text-xs font-mono transition-colors ${c.met ? "text-attain" : "text-white/30"}`}>
            <span className={`w-3 h-3 rounded-full border flex items-center justify-center shrink-0 transition-colors ${c.met ? "border-attain bg-attain/20" : "border-white/20"}`}>
              {c.met && <span className="text-[8px]">✓</span>}
            </span>
            {c.label}
          </div>
        ))}
      </div>
    </div>
  );
}

function OTPInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = value.padEnd(6, "").split("").slice(0, 6);

  const handleKey = (i: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace") {
      const next = digits.map((d, idx) => idx === i ? "" : d).join("");
      onChange(next);
      if (i > 0) inputs.current[i - 1]?.focus();
    }
  };

  const handleChange = (i: number, v: string) => {
    const char = v.replace(/\D/g, "").slice(-1);
    const next = digits.map((d, idx) => idx === i ? char : d).join("");
    onChange(next);
    if (char && i < 5) inputs.current[i + 1]?.focus();
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    onChange(pasted.padEnd(6, "").slice(0, 6));
    inputs.current[Math.min(pasted.length, 5)]?.focus();
    e.preventDefault();
  };

  return (
    <div className="flex gap-3">
      {digits.map((d, i) => (
        <input
          key={i}
          ref={el => { inputs.current[i] = el; }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={d}
          onChange={e => handleChange(i, e.target.value)}
          onKeyDown={e => handleKey(i, e)}
          onPaste={handlePaste}
          className={`w-12 h-14 text-center text-2xl font-mono text-white bg-transparent border transition-colors outline-none ${
            d ? "border-brand" : "border-white/20 focus:border-white"
          }`}
        />
      ))}
    </div>
  );
}

function formatTime(secs: number) {
  const m = Math.floor(secs / 60).toString().padStart(2, "0");
  const s = (secs % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [step, setStep]           = useState(0);
  const [empId, setEmpId]         = useState("");
  const [email, setEmail]         = useState("");
  const [otp, setOtp]             = useState("");
  const [password, setPassword]   = useState("");
  const [confirm, setConfirm]     = useState("");
  const [showPass, setShowPass]   = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors]       = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [otpTimer, setOtpTimer]   = useState(OTP_EXPIRY_SECS);
  const [resendTimer, setResendTimer] = useState(RESEND_COOLDOWN);
  const [redirectCount, setRedirectCount] = useState(3);

  // OTP countdown
  useEffect(() => {
    if (step !== 1) return;
    const t = setInterval(() => setOtpTimer(s => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [step]);

  // Resend cooldown
  useEffect(() => {
    if (step !== 1 || resendTimer <= 0) return;
    const t = setInterval(() => setResendTimer(s => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [step, resendTimer]);

  // Auto-redirect after success
  useEffect(() => {
    if (step !== 3) return;
    if (redirectCount <= 0) { router.push("/login"); return; }
    const t = setTimeout(() => setRedirectCount(s => s - 1), 1000);
    return () => clearTimeout(t);
  }, [step, redirectCount, router]);

  const submitStep1 = async () => {
    const e: Record<string, string> = {};
    if (!empId.trim()) e.empId = "Employee ID is required";
    if (!email.includes("@")) e.email = "Enter a valid email address";
    if (Object.keys(e).length) { setErrors(e); return; }
    setErrors({});
    setIsSubmitting(true);
    try {
      const response = await apiClient.forgotPassword({
        employee_id: empId.trim(),
        email: email.trim(),
      });
      setStep(1);
      setOtpTimer(response?.expires_in_seconds ?? OTP_EXPIRY_SECS);
      setResendTimer(response?.resend_in_seconds ?? RESEND_COOLDOWN);
      // dev_otp is returned by the backend when DEBUG=True (no SMTP configured)
      if (response?.dev_otp) setOtp(String(response.dev_otp));
    } catch (err: any) {
      setErrors({ form: err?.message || "Unable to send OTP. Please try again." });
    } finally {
      setIsSubmitting(false);
    }
  };

  const submitStep2 = async () => {
    if (otp.replace(/\D/g, "").length < 6) {
      setErrors({ otp: "Enter all 6 digits" });
      return;
    }
    setErrors({});
    setIsSubmitting(true);
    try {
      await apiClient.verifyOtp({
        employee_id: empId.trim(),
        email: email.trim(),
        otp: otp.replace(/\D/g, "").slice(0, 6),
      });
      setStep(2);
    } catch (err: any) {
      setErrors({ otp: err?.message || "Invalid or expired OTP" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const submitStep3 = async () => {
    const e: Record<string, string> = {};
    const checks = [password.length >= 8, /[A-Z]/.test(password), /[0-9]/.test(password), /[^A-Za-z0-9]/.test(password)];
    if (!checks.every(Boolean)) e.password = "Password does not meet all requirements";
    if (password !== confirm) e.confirm = "Passwords do not match";
    if (Object.keys(e).length) { setErrors(e); return; }
    setErrors({});
    setIsSubmitting(true);
    try {
      await apiClient.resetPassword({
        employee_id: empId.trim(),
        email: email.trim(),
        otp: otp.replace(/\D/g, "").slice(0, 6),
        new_password: password,
        confirm_password: confirm,
      });
      setStep(3);
    } catch (err: any) {
      setErrors({ form: err?.message || "Unable to reset password. Please try again." });
    } finally {
      setIsSubmitting(false);
    }
  };

  const resendOtp = async () => {
    setErrors({});
    setIsSubmitting(true);
    try {
      const response = await apiClient.resendOtp({
        employee_id: empId.trim(),
        email: email.trim(),
      });
      setOtp("");
      setOtpTimer(response?.expires_in_seconds ?? OTP_EXPIRY_SECS);
      setResendTimer(response?.resend_in_seconds ?? RESEND_COOLDOWN);
    } catch (err: any) {
      setErrors({ otp: err?.message || "Unable to resend OTP right now." });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-cosmic flex items-center justify-center px-4 py-16">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="w-full max-w-md">

        {/* Logo */}
        <motion.div variants={fadeSlideUp} className="flex items-center gap-3 mb-12">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand to-aurora flex items-center justify-center">
            <span className="text-white text-xs font-bold">N</span>
          </div>
          <span className="font-display font-medium text-white tracking-widest uppercase text-sm">Nexus Engine</span>
        </motion.div>

        {/* Step progress */}
        {step < 3 && (
          <motion.div variants={fadeSlideUp} className="flex items-center gap-0 mb-12">
            {STEPS.slice(0, 3).map((s, i) => (
              <div key={s} className="flex items-center">
                <div className={`flex items-center gap-2 text-xs font-mono uppercase tracking-widest transition-colors ${
                  i === step ? "text-white" : i < step ? "text-brand" : "text-white/20"
                }`}>
                  {i < step
                    ? <CheckCircle2 className="w-3.5 h-3.5" />
                    : <span className="w-4 h-4 rounded-full border border-current flex items-center justify-center text-[9px]">{i + 1}</span>
                  }
                  <span className="hidden sm:inline">{s}</span>
                </div>
                {i < 2 && <div className={`w-8 h-[1px] mx-3 transition-colors ${i < step ? "bg-brand" : "bg-white/10"}`} />}
              </div>
            ))}
          </motion.div>
        )}

        <AnimatePresence mode="wait">

          {/* ── STEP 1: IDENTITY ── */}
          {step === 0 && (
            <motion.div key="s0" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-8">
              <div>
                <div className="flex items-center gap-3 text-xs font-mono text-white/30 uppercase tracking-widest mb-6">
                  <span className="w-8 h-[1px] bg-white/20" /> Account Recovery
                </div>
                <h1 className="text-4xl font-display text-white mb-3">Forgot your password?</h1>
                <p className="text-white/50 font-light leading-relaxed">
                  Enter your Employee ID and registered email. We will send a one-time verification code.
                </p>
              </div>

              <div className="flex flex-col gap-6">
                {errors.form && <p className="text-red-400 text-xs font-mono">{errors.form}</p>}
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-mono text-white/40 uppercase tracking-widest">Employee ID</label>
                  <input
                    value={empId}
                    onChange={e => setEmpId(e.target.value)}
                    placeholder="FAC2024001"
                    className={`bg-transparent border-b py-3 text-white placeholder-white/20 outline-none transition-colors text-xl ${errors.empId ? "border-red-500" : "border-white/20 focus:border-white"}`}
                  />
                  {errors.empId && <p className="text-red-400 text-xs font-mono">{errors.empId}</p>}
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
                    <Mail className="w-3 h-3" /> Registered Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && submitStep1()}
                    placeholder="you@university.edu"
                    className={`bg-transparent border-b py-3 text-white placeholder-white/20 outline-none transition-colors text-xl ${errors.email ? "border-red-500" : "border-white/20 focus:border-white"}`}
                  />
                  {errors.email && <p className="text-red-400 text-xs font-mono">{errors.email}</p>}
                </div>
              </div>

              <button onClick={submitStep1}
                disabled={isSubmitting}
                className="flex items-center gap-3 px-8 py-4 bg-white text-black font-medium text-sm self-start hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                Send OTP <ArrowRight className="w-4 h-4" />
              </button>
            </motion.div>
          )}

          {/* ── STEP 2: OTP ENTRY ── */}
          {step === 1 && (
            <motion.div key="s1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-8">
              <div>
                <h1 className="text-4xl font-display text-white mb-3">Enter verification code</h1>
                <p className="text-white/50 font-light leading-relaxed">
                  A 6-digit code was sent to <span className="text-white font-medium">{email}</span>
                </p>
              </div>

              <div className="flex flex-col gap-4">
                <OTPInput value={otp} onChange={setOtp} />
                {errors.otp && <p className="text-red-400 text-xs font-mono">{errors.otp}</p>}

                {/* Timer */}
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className={`${otpTimer < 60 ? "text-alert" : "text-white/30"}`}>
                    Code expires in {formatTime(otpTimer)}
                  </span>
                  {resendTimer > 0
                    ? <span className="text-white/20">Resend in {resendTimer}s</span>
                    : (
                      <button onClick={resendOtp} disabled={isSubmitting} className="flex items-center gap-1.5 text-brand hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                        <RefreshCw className="w-3 h-3" /> Resend OTP
                      </button>
                    )
                  }
                </div>

                {otpTimer === 0 && (
                  <div className="flex items-center gap-2 text-alert text-xs font-mono p-3 bg-alert/5 border border-alert/20">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0" /> OTP expired. Please request a new one.
                  </div>
                )}
              </div>

              <div className="flex items-center gap-6">
                <button onClick={() => setStep(0)} className="text-white/30 hover:text-white transition-colors text-sm font-mono">← Back</button>
                <button
                  onClick={submitStep2}
                  disabled={otpTimer === 0 || isSubmitting}
                  className="flex items-center gap-3 px-8 py-4 bg-white text-black font-medium text-sm hover:bg-white/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Verify <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          )}

          {/* ── STEP 3: NEW PASSWORD ── */}
          {step === 2 && (
            <motion.div key="s2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-8">
              <div>
                <h1 className="text-4xl font-display text-white mb-3">Set new password</h1>
                <p className="text-white/50 font-light">Choose a strong password for your account.</p>
              </div>

              <div className="flex flex-col gap-6">
                {errors.form && <p className="text-red-400 text-xs font-mono">{errors.form}</p>}
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
                    <Lock className="w-3 h-3" /> New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPass ? "text" : "password"}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      placeholder="Min. 8 characters"
                      className={`bg-transparent border-b py-3 text-white placeholder-white/20 outline-none transition-colors text-xl w-full pr-10 ${errors.password ? "border-red-500" : "border-white/20 focus:border-white"}`}
                    />
                    <button type="button" onClick={() => setShowPass(s => !s)}
                      className="absolute right-0 top-1/2 -translate-y-1/2 text-white/30 hover:text-white pb-3">
                      {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {errors.password && <p className="text-red-400 text-xs font-mono">{errors.password}</p>}
                  <StrengthMeter password={password} />
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
                    <Lock className="w-3 h-3" /> Confirm Password
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirm ? "text" : "password"}
                      value={confirm}
                      onChange={e => setConfirm(e.target.value)}
                      placeholder="Repeat your password"
                      className={`bg-transparent border-b py-3 text-white placeholder-white/20 outline-none transition-colors text-xl w-full pr-10 ${errors.confirm ? "border-red-500" : "border-white/20 focus:border-white"}`}
                    />
                    <button type="button" onClick={() => setShowConfirm(s => !s)}
                      className="absolute right-0 top-1/2 -translate-y-1/2 text-white/30 hover:text-white pb-3">
                      {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {errors.confirm && <p className="text-red-400 text-xs font-mono">{errors.confirm}</p>}
                </div>
              </div>

              <div className="flex items-center gap-6">
                <button onClick={() => setStep(1)} className="text-white/30 hover:text-white transition-colors text-sm font-mono">← Back</button>
                <button onClick={submitStep3}
                  disabled={isSubmitting}
                  className="flex items-center gap-3 px-8 py-4 bg-white text-black font-medium text-sm self-start hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                  Update Password <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          )}

          {/* ── STEP 4: SUCCESS ── */}
          {step === 3 && (
            <motion.div key="s3" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-8">
              <CheckCircle2 className="w-16 h-16 text-attain" />
              <div>
                <h1 className="text-4xl font-display text-white mb-3">Password updated successfully.</h1>
                <p className="text-white/50 font-light leading-relaxed">
                  You will be redirected to login in{" "}
                  <span className="text-white font-mono">{redirectCount}</span> second{redirectCount !== 1 ? "s" : ""}.
                </p>
              </div>
              <Link href="/login"
                className="flex items-center gap-3 px-8 py-4 bg-white text-black font-medium text-sm self-start hover:bg-white/90 transition-colors">
                Go to Sign In <ArrowRight className="w-4 h-4" />
              </Link>
            </motion.div>
          )}

        </AnimatePresence>

        {step < 3 && (
          <motion.p variants={fadeSlideUp} className="mt-16 text-white/40 text-sm">
            Remember your password?{" "}
            <Link href="/login" className="text-white hover:underline">Sign in →</Link>
          </motion.p>
        )}
      </motion.div>
    </div>
  );
}

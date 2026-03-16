"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Mail, Lock, Eye, EyeOff, Loader2, AlertCircle, ShieldAlert, MonitorSmartphone } from "lucide-react";
import { staggerContainer, fadeSlideUp } from "@/lib/animations";
import { LoginBackground } from "@/components/auth/LoginBackground";
import { useAuthStore } from "@/lib/authStore";
import { useUIStore } from "@/lib/uiStore";

const DEPARTMENTS = ["Administration", "CSE", "ECE", "MECH", "CIVIL", "IT"];
const ACTIVE_AYS  = ["2025-26", "2024-25", "2023-24", "2022-23"];
const MAX_ATTEMPTS = 5;
const REMEMBER_KEY = "obe-remembered-login";

const ROLE_HOME: Record<string, string> = {
  admin: "/admin/dashboard",
  department_head: "/dashboard",
  subject_lead: "/dashboard",
  faculty: "/faculty/dashboard",
  student: "/student/dashboard",
};

// Accept either a strict alphanumeric employee ID or a valid email address.
const EMP_ID_RE = /^[a-zA-Z0-9]+$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validateEmployeeId(val: string) {
  if (!val) return "Employee ID or email is required";
  if (!EMP_ID_RE.test(val) && !EMAIL_RE.test(val)) {
    return "Enter a valid Employee ID or Email";
  }
  return "";
}

function validatePassword(val: string) {
  if (!val) return "Password is required";
  if (val.length < 8) return "Password must be at least 8 characters";
  return "";
}

const ROLE_META: Record<string, { label: string; desc: string; color: string }> = {
  faculty:         { label: "Faculty",          desc: "Manage courses, upload marks, generate COs",          color: "text-brand border-brand/30 hover:bg-brand/5" },
  subject_lead:    { label: "Course Lead",       desc: "Approve marks, track CO/PO attainment across courses", color: "text-insight border-insight/30 hover:bg-insight/5" },
  department_head: { label: "Head of Department",desc: "Full department view, reports, year-end sign-off",    color: "text-aurora border-aurora/30 hover:bg-aurora/5" },
  admin:           { label: "System Admin",      desc: "User management, AY config, full system access",      color: "text-alert border-alert/30 hover:bg-alert/5" },
  student:         { label: "Student",           desc: "View enrolled courses, marks, and CO attainment",     color: "text-cyan-400 border-cyan-400/30 hover:bg-cyan-400/5" },
};

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { addToast } = useUIStore();
  const { login, setActiveRole, setActiveAY, loginError, isAuthenticated } = useAuthStore();

  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [dept, setDept]         = useState("");
  const [ay, setAY]             = useState("2025-26");
  const [showPass, setShowPass] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading]   = useState(false);

  // Dual-role full-page selector
  const [showRoleSelect, setShowRoleSelect] = useState(false);
  const [pendingRoles, setPendingRoles]     = useState<string[]>([]);

  // Pre-selected role from left panel
  const [selectedRole, setSelectedRole] = useState<string>("");

  // Inline field validation errors
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string; dept?: string }>({});
  const [touched, setTouched]         = useState<{ email?: boolean; password?: boolean; dept?: boolean }>({});

  // Lockout state (persisted in sessionStorage for this browser session)
  const [attempts, setAttempts]   = useState<number>(0);
  const [locked, setLocked]       = useState<boolean>(false);

  // Session-already-active warning
  const [showSessionWarning, setShowSessionWarning] = useState(false);

  // Check if already authenticated on mount + show session expired toast if redirected
  useEffect(() => {
    const reason = searchParams.get('reason');
    if (reason === 'session_expired') {
      addToast('Your session has ended. Please log in again.', 'error');
    }
    if (isAuthenticated) setShowSessionWarning(true);
  }, [isAuthenticated, searchParams, addToast]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const remembered = localStorage.getItem(REMEMBER_KEY);
      if (remembered) {
        const parsed = JSON.parse(remembered) as { email?: string; dept?: string; ay?: string };
        if (parsed.email) setEmail(parsed.email);
        if (parsed.dept) setDept(parsed.dept);
        if (parsed.ay) setAY(parsed.ay);
        setRememberMe(true);
      }
    } catch {}

    const storedAttempts = Number(sessionStorage.getItem("login_attempts") || "0");
    const storedLocked = sessionStorage.getItem("login_locked") === "1";
    setAttempts(storedAttempts);
    setLocked(storedLocked);
  }, []);

  const handleEmailChange = (val: string) => {
    setEmail(val);
    if (touched.email) setFieldErrors(e => ({ ...e, email: validateEmployeeId(val) }));
  };

  const handlePasswordChange = (val: string) => {
    setPassword(val);
    if (touched.password) setFieldErrors(e => ({ ...e, password: validatePassword(val) }));
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (locked) return;

    // Validate fields
    const emailErr = validateEmployeeId(email);
    const passErr  = validatePassword(password);
    const deptErr  = !dept ? "Department is required" : "";
    const roleErr  = !selectedRole ? "Please select a role from the left panel" : "";
    setTouched({ email: true, password: true, dept: true });
    setFieldErrors({ email: emailErr, password: passErr, dept: deptErr });
    if (emailErr || passErr || deptErr || roleErr) {
      if (roleErr) addToast(roleErr, "error");
      return;
    }

    setIsLoading(true);

    const identifier = email.trim();
    const success = await login(identifier, password, {
      // Only pass department if user selected one — backend rejects if it doesn't match DB
      department: dept || undefined,
      rememberMe,
    });
    if (success) {
      // Reset lockout on success
      sessionStorage.removeItem("login_attempts");
      sessionStorage.removeItem("login_locked");
      setAttempts(0);

      if (rememberMe) {
        localStorage.setItem(REMEMBER_KEY, JSON.stringify({ email, dept, ay }));
      } else {
        localStorage.removeItem(REMEMBER_KEY);
      }

      const { user } = useAuthStore.getState();
      if (user && user.roles.length > 1) {
        // If user pre-selected a role from the left panel and it's in their roles, use it directly
        if (selectedRole && user.roles.includes(selectedRole as any)) {
          setActiveAY(ay);
          setActiveRole(selectedRole as any);
          router.push(ROLE_HOME[selectedRole] || "/dashboard");
        } else {
          setPendingRoles(user.roles as string[]);
          setShowRoleSelect(true);
          setIsLoading(false);
        }
      } else {
        setActiveAY(ay);
        const role = selectedRole || user?.roles?.[0];
        if (role) setActiveRole(role as any);
        if (user?.firstLogin) {
          router.push("/reset-password?first=1");
        } else {
          router.push(role ? ROLE_HOME[role] || "/dashboard" : "/dashboard");
        }
      }
    } else {
      const newAttempts = attempts + 1;
      setAttempts(newAttempts);
      sessionStorage.setItem("login_attempts", String(newAttempts));
      if (newAttempts >= MAX_ATTEMPTS) {
        setLocked(true);
        sessionStorage.setItem("login_locked", "1");
      }
      setIsLoading(false);
    }
  };

  const handleRoleSelect = (role: string) => {
    setActiveRole(role as any);
    setActiveAY(ay);
    setShowRoleSelect(false);
    router.push(ROLE_HOME[role] || "/dashboard");
  };

  const continueExistingSession = () => {
    setShowSessionWarning(false);
    const { activeRole } = useAuthStore.getState();
    router.push(activeRole ? ROLE_HOME[activeRole] || "/dashboard" : "/dashboard");
  };

  const remaining = MAX_ATTEMPTS - attempts;

  // ── DUAL-ROLE FULL-PAGE SELECTOR ──────────────────────────────────────────
  if (showRoleSelect) {
    return (
      <div className="min-h-screen bg-cosmic flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-lg"
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand to-aurora flex items-center justify-center">
              <span className="text-white text-xs font-bold">N</span>
            </div>
            <span className="font-display font-medium text-white tracking-widest uppercase text-sm">Nexus Engine</span>
          </div>

          <div className="mt-12 mb-4 flex items-center gap-3 text-xs font-mono text-white/30 uppercase tracking-widest">
            <span className="w-8 h-[1px] bg-white/20" /> Dual-Role Account
          </div>
          <h1 className="text-4xl font-display text-white mb-3">Select your dashboard</h1>
          <p className="text-white/40 font-light mb-12">
            Your account has multiple roles. Choose which dashboard to open for this session.
          </p>

          <div className="flex flex-col gap-4">
            {pendingRoles.map(role => {
              const m = ROLE_META[role] ?? { label: role, desc: "", color: "text-white border-white/20 hover:bg-white/5" };
              return (
                <button
                  key={role}
                  suppressHydrationWarning
                  onClick={() => handleRoleSelect(role)}
                  className={`flex items-center justify-between px-8 py-6 border transition-all ${m.color}`}
                >
                  <div className="text-left">
                    <p className="font-mono text-sm uppercase tracking-widest mb-1">{m.label}</p>
                    <p className="text-xs text-white/40 font-light">{m.desc}</p>
                  </div>
                  <ArrowRight className="w-5 h-5 opacity-40 shrink-0" />
                </button>
              );
            })}
          </div>

          <button
            suppressHydrationWarning
            onClick={() => { setShowRoleSelect(false); useAuthStore.getState().logout(); }}
            className="mt-8 text-sm text-white/30 hover:text-white transition-colors font-mono"
          >
            ← Sign out and go back
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-cosmic overflow-hidden selection:bg-brand/30 selection:text-white">
      <LoginBackground />

      {/* ── SESSION ALREADY ACTIVE WARNING ── */}
      <AnimatePresence>
        {showSessionWarning && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-8"
          >
            <motion.div
              initial={{ scale: 0.95, y: 16 }}
              animate={{ scale: 1, y: 0 }}
              className="w-full max-w-md bg-[#0D1829] border border-white/10 p-10"
            >
              <div className="flex items-center gap-3 mb-6">
                <MonitorSmartphone className="w-5 h-5 text-amber-400" />
                <p className="text-xs font-mono text-amber-400 uppercase tracking-widest">Active Session Detected</p>
              </div>
              <p className="text-white text-lg font-display mb-3">You are already signed in</p>
              <p className="text-white/50 text-sm font-light leading-relaxed mb-8">
                An active session exists on this device. Continuing will reopen your saved role and academic-year context on this browser.
              </p>
              <div className="flex flex-col gap-3">
                <button
                  suppressHydrationWarning
                  onClick={continueExistingSession}
                  className="flex items-center justify-between px-6 py-4 bg-white text-black text-sm font-medium hover:bg-white/90 transition-colors"
                >
                  Continue to Dashboard <ArrowRight className="w-4 h-4" />
                </button>
                <button
                  suppressHydrationWarning
                  onClick={() => { useAuthStore.getState().logout(); setShowSessionWarning(false); }}
                  className="px-6 py-4 border border-white/10 text-white/50 text-sm font-mono hover:border-white/30 hover:text-white transition-colors"
                >
                  Sign out and log in as different user
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="relative z-10 min-h-screen flex">
        {/* ── LEFT PANEL ── */}
        <div className="hidden lg:flex flex-col justify-between w-1/2 px-20 py-16">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand to-aurora flex items-center justify-center">
              <span className="text-white text-xs font-bold">N</span>
            </div>
            <span className="font-display font-medium text-white tracking-widest uppercase text-sm">Nexus Engine</span>
          </div>

          <div className="flex flex-col gap-8">
            <div className="flex items-center gap-3 text-sm font-mono text-brand uppercase tracking-widest">
              <span className="w-8 h-[1px] bg-brand" />
              Academic Intelligence Platform
            </div>
            <h1 className="text-5xl lg:text-6xl font-display font-medium text-white leading-tight tracking-tight">
              Map outcomes.<br />
              <span className="text-white/50">Measure attainment.</span>
            </h1>
            <p className="text-lg text-white/40 font-light leading-relaxed max-w-md">
              The complete CO-PO-PSO intelligence platform for accreditation-ready universities.
            </p>
          </div>

          {/* Role selector buttons */}
          <div className="flex flex-col gap-3">
            <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest mb-1">Platform Roles — select to access</span>
            {([
              { role: "faculty",         label: "Faculty",      desc: "Manage courses, upload marks, generate COs",          accent: "text-brand",   border: "border-brand/30",   bg: "bg-brand/5",   dot: "bg-brand" },
              { role: "subject_lead",    label: "Course Lead",  desc: "Approve marks, track CO/PO attainment",               accent: "text-insight", border: "border-insight/30", bg: "bg-insight/5", dot: "bg-insight" },
              { role: "department_head", label: "HOD",          desc: "Department view, reports, year-end sign-off",          accent: "text-aurora",  border: "border-aurora/30",  bg: "bg-aurora/5",  dot: "bg-aurora" },
              { role: "admin",           label: "Admin",        desc: "User management, AY config, full system access",       accent: "text-alert",   border: "border-alert/30",   bg: "bg-alert/5",   dot: "bg-alert" },
            ] as const).map(({ role, label, desc, accent, border, bg, dot }) => {
              const active = selectedRole === role;
              return (
                <button
                  key={role}
                  type="button"
                  suppressHydrationWarning
                  onClick={() => setSelectedRole(active ? "" : role)}
                  className={`flex items-start gap-4 px-5 py-4 border text-left transition-all ${
                    active ? `${border} ${bg}` : "border-white/5 hover:border-white/15"
                  }`}
                >
                  <span className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${active ? dot : "bg-white/20"}`} />
                  <div>
                    <p className={`text-[10px] font-mono uppercase tracking-widest mb-0.5 ${active ? accent : "text-white/50"}`}>{label}</p>
                    <p className="text-white/30 font-light text-xs leading-relaxed">{desc}</p>
                  </div>
                  {active && <ArrowRight className={`w-3.5 h-3.5 shrink-0 ml-auto mt-1 ${accent}`} />}
                </button>
              );
            })}
          </div>
        </div>

        {/* ── RIGHT PANEL — Login Form ── */}
        <div className="flex-1 flex items-center justify-center px-8 lg:px-20 py-16">
          <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="w-full max-w-md">

            <div className="flex items-center gap-3 mb-16 lg:hidden">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand to-aurora flex items-center justify-center">
                <span className="text-white text-xs font-bold">N</span>
              </div>
              <span className="font-display font-medium text-white tracking-widest uppercase text-sm">Nexus Engine</span>
            </div>

            <motion.div variants={fadeSlideUp} className="mb-14">
              <div className="flex items-center gap-3 text-sm font-mono text-white/30 uppercase tracking-widest mb-6">
                <span className="w-8 h-[1px] bg-white/20" />
                Secure Access
              </div>
              <h2 className="text-4xl font-display text-white">Welcome back.</h2>
              {selectedRole && (() => {
                const m = ROLE_META[selectedRole];
                return m ? (
                  <div className={`mt-4 flex items-center gap-3 px-4 py-2.5 border ${m.color.includes("brand") ? "border-brand/30 bg-brand/5" : m.color.includes("insight") ? "border-insight/30 bg-insight/5" : m.color.includes("aurora") ? "border-aurora/30 bg-aurora/5" : "border-alert/30 bg-alert/5"}`}>
                    <span className={`text-[10px] font-mono uppercase tracking-widest ${m.color.split(" ")[0]}`}>
                      Signing in as {m.label}
                    </span>
                    <span className="text-white/30 text-[10px] font-light">— {m.desc}</span>
                  </div>
                ) : null;
              })()}
            </motion.div>

            {/* ── LOCKOUT STATE ── */}
            {locked ? (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col gap-6"
              >
                <div className="flex items-start gap-4 p-5 bg-alert/5 border border-alert/30">
                  <ShieldAlert className="w-5 h-5 text-alert shrink-0 mt-0.5" />
                  <div>
                    <p className="text-alert text-sm font-mono font-medium mb-1">Account locked</p>
                    <p className="text-white/60 text-sm font-light leading-relaxed">
                      Too many failed attempts. Failed sign-ins are capped at {MAX_ATTEMPTS} per session. Contact your administrator or use Forgot Password to unlock your account.
                    </p>
                  </div>
                </div>
                <div className="flex flex-col gap-3">
                  <Link href="/forgot-password"
                    className="flex items-center gap-3 px-8 py-4 bg-white text-black text-sm font-medium hover:bg-white/90 transition-colors">
                    Reset via Forgot Password <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </motion.div>
            ) : (
              <motion.form variants={staggerContainer} onSubmit={handleLogin} className="flex flex-col gap-0" noValidate suppressHydrationWarning={true}>

                {/* Department + AY */}
                <motion.div variants={fadeSlideUp} className="grid grid-cols-2 gap-6 pb-6 border-b border-white/10 mb-6">
                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-mono text-white/40 uppercase tracking-widest">Department</label>
                    <select
                      suppressHydrationWarning
                      value={dept}
                      onChange={e => {
                        setDept(e.target.value);
                        if (touched.dept) {
                          setFieldErrors(prev => ({ ...prev, dept: e.target.value ? "" : "Department is required" }));
                        }
                      }}
                      onBlur={() => {
                        setTouched(prev => ({ ...prev, dept: true }));
                        setFieldErrors(prev => ({ ...prev, dept: dept ? "" : "Department is required" }));
                      }}
                      className={`bg-transparent text-white text-sm outline-none font-light appearance-none w-full cursor-pointer border-b pb-1 ${
                        touched.dept && fieldErrors.dept ? "border-red-500" : "border-white/20"
                      }`}
                    >
                      <option value="" className="bg-[#0a0a0f]">Select</option>
                      {DEPARTMENTS.map(d => <option key={d} value={d} className="bg-[#0a0a0f]">{d}</option>)}
                    </select>
                    <AnimatePresence>
                      {touched.dept && fieldErrors.dept && (
                        <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                          className="text-red-400 text-xs font-mono mt-1">
                          {fieldErrors.dept}
                        </motion.p>
                      )}
                    </AnimatePresence>
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-mono text-white/40 uppercase tracking-widest">Academic Year</label>
                    <select value={ay} onChange={e => setAY(e.target.value)}
                      suppressHydrationWarning
                      className="bg-transparent text-white text-sm outline-none font-light border-none appearance-none w-full cursor-pointer">
                      {ACTIVE_AYS.map(a => <option key={a} value={a} className="bg-[#0a0a0f]">{a}</option>)}
                    </select>
                  </div>
                </motion.div>

                {/* Employee ID */}
                <motion.div variants={fadeSlideUp} className="flex flex-col gap-2 pb-8 mb-2">
                  <label className="text-xs font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
                    <Mail className="w-3 h-3" /> Employee ID
                  </label>
                  <input
                    suppressHydrationWarning
                    type="text"
                    value={email}
                    onChange={e => handleEmailChange(e.target.value)}
                    onBlur={() => { setTouched(t => ({ ...t, email: true })); setFieldErrors(e => ({ ...e, email: validateEmployeeId(email) })); }}
                    placeholder="FAC2024001 or you@nexus.edu"
                    className={`bg-transparent text-white text-xl placeholder-white/20 outline-none w-full font-light border-b pb-3 transition-colors ${
                      touched.email && fieldErrors.email ? "border-red-500" : "border-white/20 focus:border-white"
                    }`}
                  />
                  <AnimatePresence>
                    {touched.email && fieldErrors.email && (
                      <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                        className="text-red-400 text-xs font-mono mt-1">
                        {fieldErrors.email}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </motion.div>

                {/* Password */}
                <motion.div variants={fadeSlideUp} className="flex flex-col gap-2 pb-6 mb-2">
                  <label className="text-xs font-mono text-white/40 uppercase tracking-widest flex items-center gap-2">
                    <Lock className="w-3 h-3" /> Password
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      suppressHydrationWarning
                      type={showPass ? "text" : "password"}
                      value={password}
                      onChange={e => handlePasswordChange(e.target.value)}
                      onBlur={() => { setTouched(t => ({ ...t, password: true })); setFieldErrors(e => ({ ...e, password: validatePassword(password) })); }}
                      placeholder="••••••••••"
                      className={`bg-transparent text-white text-xl placeholder-white/20 outline-none flex-1 font-light border-b pb-3 transition-colors ${
                        touched.password && fieldErrors.password ? "border-red-500" : "border-white/20 focus:border-white"
                      }`}
                    />
                    <button suppressHydrationWarning type="button" onClick={() => setShowPass(s => !s)} className="text-white/20 hover:text-white/60 transition-colors shrink-0 pb-3">
                      {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  <AnimatePresence>
                    {touched.password && fieldErrors.password && (
                      <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                        className="text-red-400 text-xs font-mono mt-1">
                        {fieldErrors.password}
                      </motion.p>
                    )}
                  </AnimatePresence>
                  <div className="flex justify-end mt-1">
                    <Link href="/forgot-password" className="text-xs text-white/30 hover:text-white/60 transition-colors font-mono">
                      Forgot password?
                    </Link>
                  </div>
                </motion.div>

                {/* Remember me */}
                <motion.div variants={fadeSlideUp} className="flex items-center gap-2 mb-6 cursor-pointer group" onClick={() => setRememberMe(r => !r)}>
                  <div className={`w-4 h-4 border rounded-sm flex items-center justify-center transition-colors ${rememberMe ? "border-brand bg-brand/20" : "border-white/20 group-hover:border-brand"}`}>
                    {rememberMe && <div className="w-2 h-2 bg-brand" />}
                  </div>
                  <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest select-none">Remember this device for 7 days</span>
                </motion.div>

                {/* Wrong credentials banner */}
                <AnimatePresence>
                  {loginError && !locked && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="flex items-start gap-3 text-sm font-mono mb-6 p-4 bg-alert/5 border border-alert/30"
                    >
                      <AlertCircle className="w-4 h-4 text-alert shrink-0 mt-0.5" />
                      <div>
                        <p className="text-alert">Incorrect Employee ID or password.</p>
                        {remaining > 0 && remaining < MAX_ATTEMPTS && (
                          <p className="text-white/40 text-xs mt-1">
                            Failed attempts: {attempts}/{MAX_ATTEMPTS}. {remaining} attempt{remaining !== 1 ? "s" : ""} remaining before lockout.
                          </p>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Submit */}
                <motion.div variants={fadeSlideUp} className="flex items-center justify-between">
                  <button
                    suppressHydrationWarning
                    type="submit"
                    disabled={isLoading || !email.trim() || !password.trim() || !dept || !selectedRole}
                    className="flex items-center gap-3 px-8 py-4 bg-white text-black font-medium text-sm hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isLoading
                      ? <><Loader2 className="w-4 h-4 animate-spin" /> Authenticating</>
                      : <>Sign In as {selectedRole ? ROLE_META[selectedRole]?.label : "User"} <ArrowRight className="w-4 h-4" /></>}
                  </button>
                </motion.div>
              </motion.form>
            )}

            <motion.p variants={fadeSlideUp} className="mt-12 text-white/30 text-sm font-light">
              New to Nexus Engine?{" "}
              <Link href="/register" className="text-white/60 hover:text-white transition-colors underline-offset-4 hover:underline">Request access →</Link>
            </motion.p>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

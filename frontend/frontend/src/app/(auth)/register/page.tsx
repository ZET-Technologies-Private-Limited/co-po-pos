"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { ArrowRight, CheckCircle2, User, Mail, Lock, Building2, GraduationCap, ChevronRight, BookOpen, Loader2 } from "lucide-react";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";
import { useUIStore } from "@/lib/uiStore";
import { apiClient } from "@/lib/apiClient";
import { useAuthStore } from "@/lib/authStore";

// ── SYNC: Match login page constants ──
const DEPARTMENTS = ["Administration", "CSE", "ECE", "MECH", "CIVIL", "IT"];
const ACTIVE_AYS = ["2025-26", "2024-25", "2023-24", "2022-23"];

const ROLES = [
  { id: "faculty", label: "Faculty", icon: GraduationCap, desc: "Create courses, upload syllabi, generate COs" },
  { id: "subject_lead", label: "Subject Lead", icon: BookOpen, desc: "Coordinate specific courses, approve CO-PO maps" },
  { id: "hod", label: "Department Head", icon: Building2, desc: "Manage faculty, view analytics & reports" },
  { id: "admin", label: "Admin", icon: User, desc: "Full system access and user management" },
];

const STEPS = ["Account", "Department", "Role", "Security"];

// ── SYNC: Validation functions from login page ──
function validateFullName(val: string) {
  if (!val.trim()) return "Full name is required";
  return "";
}

function validateEmail(val: string) {
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!val) return "Email is required";
  if (!EMAIL_RE.test(val)) return "Enter a valid email";
  return "";
}

function validatePassword(val: string) {
  if (!val) return "Password is required";
  if (val.length < 8) return "Password must be at least 8 characters";
  return "";
}

const ROLE_HOME: Record<string, string> = {
  admin: "/admin/dashboard",
  hod: "/dashboard",
  subject_lead: "/dashboard",
  faculty: "/faculty/dashboard",
  student: "/student/dashboard",
};

export default function RegisterPage() {
  const router = useRouter();
  const { addToast } = useUIStore();
  const { setActiveRole, setActiveAY } = useAuthStore();
  
  const [step, setStep] = useState(0);
  const [role, setRole] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [form, setForm] = useState({
    name: "",
    email: "",
    department: "",
    academicYear: "2025-26",
    password: "",
    confirm: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const setField = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));
  
  const markTouched = (field: string) => {
    setTouched(t => ({ ...t, [field]: true }));
  };

  const validate = (forSubmit?: boolean) => {
    const e: Record<string, string> = {};
    
    // If submitting, validate all steps; otherwise validate current step
    const stepsToValidate = forSubmit ? [0, 1, 2, 3] : [step];
    
    for (const s of stepsToValidate) {
      if (s === 0) {
        const nameErr = validateFullName(form.name);
        const emailErr = validateEmail(form.email);
        if (nameErr) e.name = nameErr;
        if (emailErr) e.email = emailErr;
      }
      
      if (s === 1) {
        if (!form.department) e.department = "Department is required";
      }
      
      if (s === 2) {
        if (!role) e.role = "Please select a role";
      }
      
      if (s === 3) {
        const passErr = validatePassword(form.password);
        if (passErr) e.password = passErr;
        if (form.password !== form.confirm) e.confirm = "Passwords do not match";
      }
    }
    
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const next = () => {
    if (validate()) setStep(s => s + 1);
  };

  const prev = () => setStep(s => s - 1);

  const handleRegister = async () => {
    if (!validate(true)) return;
    setIsLoading(true);

    try {
      const response = await apiClient.register({
        username: form.email,
        email: form.email,
        password: form.password,
        full_name: form.name,
        role,
      });

      if (response) {
        addToast("Account created successfully! Welcome to Nexus Engine.", "success");
        // Hydrate store from the token returned by register
        const { user } = useAuthStore.getState();
        setActiveAY(form.academicYear);
        const resolvedRole = (user?.roles?.[0] as any) ?? role;
        if (resolvedRole) setActiveRole(resolvedRole);
        const destination = ROLE_HOME[resolvedRole] || ROLE_HOME[role] || "/dashboard";
        router.push(destination);
      }
    } catch (error: any) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      if (errorMsg.includes("already exists") || errorMsg.includes("409")) {
        addToast("Email already registered. Try logging in instead.", "error");
      } else if (errorMsg.includes("Failed to fetch") || errorMsg.includes("NetworkError") || errorMsg.includes("fetch")) {
        addToast("Cannot reach the server. Make sure the backend is running on port 8000.", "error");
      } else if (errorMsg.includes("Invalid or expired token")) {
        addToast("Session expired. Please log in again.", "error");
        router.push("/login?reason=session_expired");
      } else {
        addToast(errorMsg || "Registration failed. Please try again.", "error");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-cosmic flex items-center justify-center px-4 py-16">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="w-full max-w-lg">
        {/* Progress */}
        <motion.div variants={fadeSlideUp} className="flex items-center gap-0 mb-16">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center">
              <div className={`flex items-center gap-2 text-sm font-mono uppercase tracking-widest transition-colors ${i === step ? "text-white" : i < step ? "text-brand" : "text-white/30"}`}>
                {i < step ? <CheckCircle2 className="w-4 h-4" /> : <span className="w-4 h-4 rounded-full border border-current flex items-center justify-center text-[10px]">{i + 1}</span>}
                {s}
              </div>
              {i < STEPS.length - 1 && <div className={`w-16 h-[1px] mx-4 transition-colors ${i < step ? "bg-brand" : "bg-white/10"}`} />}
            </div>
          ))}
        </motion.div>

        {/* Step 0: Account Info */}
        <AnimatePresence mode="wait">
          {step === 0 && (
            <motion.div key="step0" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-8">
              <div>
                <h1 className="text-4xl font-display text-white mb-2">Create account</h1>
                <p className="text-white/50 font-light">Join the Nexus Engine academic platform.</p>
              </div>

              <div className="flex flex-col gap-6">
                {/* Full Name */}
                <label className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-white/50 uppercase tracking-widest flex items-center gap-2"><User className="w-3 h-3" /> Full Name</span>
                  <input
                    value={form.name}
                    onChange={e => setField("name", e.target.value)}
                    onBlur={() => markTouched("name")}
                    placeholder="Dr. John Smith"
                    className={`bg-transparent border-b py-3 text-white placeholder-white/30 outline-none transition-colors text-lg ${
                      touched.name && errors.name ? "border-alert" : "border-white/20 focus:border-white"
                    }`}
                  />
                  {touched.name && errors.name && <span className="text-alert text-sm font-mono">{errors.name}</span>}
                </label>

                {/* Email */}
                <label className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-white/50 uppercase tracking-widest flex items-center gap-2"><Mail className="w-3 h-3" /> Email</span>
                  <input
                    type="email"
                    value={form.email}
                    onChange={e => setField("email", e.target.value)}
                    onBlur={() => markTouched("email")}
                    placeholder="you@university.edu"
                    className={`bg-transparent border-b py-3 text-white placeholder-white/30 outline-none transition-colors text-lg ${
                      touched.email && errors.email ? "border-alert" : "border-white/20 focus:border-white"
                    }`}
                  />
                  {touched.email && errors.email && <span className="text-alert text-sm font-mono">{errors.email}</span>}
                </label>
              </div>

              <button onClick={next} className="flex items-center gap-3 text-white/80 hover:text-white group mt-4">
                Continue <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </motion.div>
          )}

          {/* Step 1: Department & Academic Year (SYNC WITH LOGIN) */}
          {step === 1 && (
            <motion.div key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-8">
              <div>
                <h1 className="text-4xl font-display text-white mb-2">Your context</h1>
                <p className="text-white/50 font-light">Select your department and academic year.</p>
              </div>

              <div className="grid grid-cols-2 gap-6">
                {/* Department Dropdown - SYNC with Login */}
                <label className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-white/40 uppercase tracking-widest">Department</span>
                  <select
                    value={form.department}
                    onChange={e => setField("department", e.target.value)}
                    onBlur={() => markTouched("department")}
                    className={`bg-transparent text-white text-sm outline-none font-light appearance-none w-full cursor-pointer border-b pb-1 ${
                      touched.department && errors.department ? "border-alert" : "border-white/20 focus:border-white"
                    }`}
                  >
                    <option value="" className="bg-[#0a0a0f]">Select</option>
                    {DEPARTMENTS.map(d => <option key={d} value={d} className="bg-[#0a0a0f]">{d}</option>)}
                  </select>
                  {touched.department && errors.department && <span className="text-alert text-xs font-mono">{errors.department}</span>}
                </label>

                {/* Academic Year - SYNC with Login */}
                <label className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-white/40 uppercase tracking-widest">Academic Year</span>
                  <select
                    value={form.academicYear}
                    onChange={e => setField("academicYear", e.target.value)}
                    className="bg-transparent text-white text-sm outline-none font-light border-none appearance-none w-full cursor-pointer border-b pb-1 border-white/20 focus:border-white"
                  >
                    {ACTIVE_AYS.map(a => <option key={a} value={a} className="bg-[#0a0a0f]">{a}</option>)}
                  </select>
                </label>
              </div>

              <div className="flex items-center gap-8">
                <button onClick={prev} className="text-white/40 hover:text-white transition-colors text-sm">← Back</button>
                <button onClick={next} className="flex items-center gap-3 text-white/80 hover:text-white group">
                  Continue <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </motion.div>
          )}

          {/* Step 2: Role Selection */}
          {step === 2 && (
            <motion.div key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-8">
              <div>
                <h1 className="text-4xl font-display text-white mb-2">Select your role</h1>
                <p className="text-white/50 font-light">This determines your access level and UI.</p>
              </div>

              <div className="flex flex-col gap-4">
                {ROLES.map(r => (
                  <button key={r.id} onClick={() => setRole(r.id)}
                    className={`flex items-center gap-6 p-6 border text-left transition-all ${role === r.id ? "border-brand text-white" : "border-white/10 text-white/60 hover:border-white/30 hover:text-white"}`}>
                    <r.icon className={`w-6 h-6 shrink-0 ${role === r.id ? "text-brand" : ""}`} />
                    <div>
                      <div className="font-medium text-lg">{r.label}</div>
                      <div className="text-sm opacity-70 mt-1">{r.desc}</div>
                    </div>
                    {role === r.id && <CheckCircle2 className="w-5 h-5 text-brand ml-auto" />}
                  </button>
                ))}
                {errors.role && <span className="text-alert text-sm font-mono">{errors.role}</span>}
              </div>

              <div className="flex items-center gap-8">
                <button onClick={prev} className="text-white/40 hover:text-white transition-colors text-sm">← Back</button>
                <button onClick={next} className="flex items-center gap-3 text-white/80 hover:text-white group">
                  Continue <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </motion.div>
          )}

          {/* Step 3: Password - SYNC with Login validation */}
          {step === 3 && (
            <motion.div key="step3" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-8">
              <div>
                <h1 className="text-4xl font-display text-white mb-2">Secure your account</h1>
                <p className="text-white/50 font-light">Set a strong password to protect your data.</p>
              </div>

              <div className="flex flex-col gap-6">
                <label className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-white/50 uppercase tracking-widest flex items-center gap-2"><Lock className="w-3 h-3" /> Password</span>
                  <input
                    type="password"
                    value={form.password}
                    onChange={e => setField("password", e.target.value)}
                    onBlur={() => markTouched("password")}
                    placeholder="Min. 8 characters"
                    className={`bg-transparent border-b py-3 text-white placeholder-white/30 outline-none transition-colors text-lg ${
                      touched.password && errors.password ? "border-alert" : "border-white/20 focus:border-white"
                    }`}
                  />
                  {touched.password && errors.password && <span className="text-alert text-sm font-mono">{errors.password}</span>}
                </label>

                <label className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-white/50 uppercase tracking-widest flex items-center gap-2"><Lock className="w-3 h-3" /> Confirm Password</span>
                  <input
                    type="password"
                    value={form.confirm}
                    onChange={e => setField("confirm", e.target.value)}
                    onBlur={() => markTouched("confirm")}
                    placeholder="Repeat password"
                    className={`bg-transparent border-b py-3 text-white placeholder-white/30 outline-none transition-colors text-lg ${
                      touched.confirm && errors.confirm ? "border-alert" : "border-white/20 focus:border-white"
                    }`}
                  />
                  {touched.confirm && errors.confirm && <span className="text-alert text-sm font-mono">{errors.confirm}</span>}
                </label>

                {/* Password strength hints */}
                <div className="flex gap-2 mt-2">
                  {[form.password.length >= 8, /[A-Z]/.test(form.password), /[0-9]/.test(form.password)].map((met, i) => (
                    <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${met ? "bg-brand" : "bg-white/10"}`} />
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-8">
                <button onClick={prev} className="text-white/40 hover:text-white transition-colors text-sm">← Back</button>
                <button
                  onClick={handleRegister}
                  disabled={isLoading}
                  className="flex items-center gap-3 px-8 py-4 bg-white text-black font-medium text-sm hover:bg-white/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      Create Account <ChevronRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <motion.p variants={fadeSlideUp} className="mt-16 text-white/40 text-sm">
          Already have an account? <Link href="/login" className="text-white hover:underline">Sign in →</Link>
        </motion.p>
      </motion.div>
    </div>
  );
}

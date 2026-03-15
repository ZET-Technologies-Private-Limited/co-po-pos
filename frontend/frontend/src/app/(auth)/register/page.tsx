"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { ArrowRight, CheckCircle2, User, Mail, Lock, Building2, GraduationCap, ChevronRight, BookOpen } from "lucide-react";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";

const ROLES = [
  { id: "faculty", label: "Faculty", icon: GraduationCap, desc: "Create courses, upload syllabi, generate COs" },
  { id: "subject_lead", label: "Subject Lead", icon: BookOpen, desc: "Coordinate specific courses, approve CO-PO maps" },
  { id: "department_head", label: "Department Head", icon: Building2, desc: "Manage faculty, view analytics & reports" },
  { id: "admin", label: "Admin", icon: User, desc: "Full system access and user management" },
];

const STEPS = ["Account", "Role", "Security"];

export default function RegisterPage() {
  const [step, setStep] = useState(0);
  const [role, setRole] = useState("");
  const [form, setForm] = useState({ name: "", email: "", department: "", password: "", confirm: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const setField = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  const validate = () => {
    const e: Record<string, string> = {};
    if (step === 0) {
      if (!form.name.trim()) e.name = "Full name is required";
      if (!form.email.includes("@")) e.email = "Valid email required";
    }
    if (step === 1 && !role) e.role = "Please select a role";
    if (step === 2) {
      if (form.password.length < 8) e.password = "Min. 8 characters required";
      if (form.password !== form.confirm) e.confirm = "Passwords do not match";
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const next = () => { if (validate()) setStep(s => s + 1); };

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
                <label className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-white/50 uppercase tracking-widest flex items-center gap-2"><User className="w-3 h-3" /> Full Name</span>
                  <input value={form.name} onChange={e => setField("name", e.target.value)} placeholder="Dr. John Smith" className="bg-transparent border-b border-white/20 focus:border-white py-3 text-white placeholder-white/30 outline-none transition-colors text-lg" />
                  {errors.name && <span className="text-alert text-sm font-mono">{errors.name}</span>}
                </label>
                <label className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-white/50 uppercase tracking-widest flex items-center gap-2"><Mail className="w-3 h-3" /> Email</span>
                  <input type="email" value={form.email} onChange={e => setField("email", e.target.value)} placeholder="you@university.edu" className="bg-transparent border-b border-white/20 focus:border-white py-3 text-white placeholder-white/30 outline-none transition-colors text-lg" />
                  {errors.email && <span className="text-alert text-sm font-mono">{errors.email}</span>}
                </label>
                <label className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-white/50 uppercase tracking-widest flex items-center gap-2"><Building2 className="w-3 h-3" /> Department</span>
                  <input value={form.department} onChange={e => setField("department", e.target.value)} placeholder="Computer Science & Engineering" className="bg-transparent border-b border-white/20 focus:border-white py-3 text-white placeholder-white/30 outline-none transition-colors text-lg" />
                </label>
              </div>

              <button onClick={next} className="flex items-center gap-3 text-white/80 hover:text-white group mt-4">
                Continue <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </motion.div>
          )}

          {/* Step 1: Role Selection */}
          {step === 1 && (
            <motion.div key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-8">
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
                <button onClick={() => setStep(0)} className="text-white/40 hover:text-white transition-colors text-sm">← Back</button>
                <button onClick={next} className="flex items-center gap-3 text-white/80 hover:text-white group">
                  Continue <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </motion.div>
          )}

          {/* Step 2: Password */}
          {step === 2 && (
            <motion.div key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-8">
              <div>
                <h1 className="text-4xl font-display text-white mb-2">Secure your account</h1>
                <p className="text-white/50 font-light">Set a strong password to protect your data.</p>
              </div>

              <div className="flex flex-col gap-6">
                <label className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-white/50 uppercase tracking-widest flex items-center gap-2"><Lock className="w-3 h-3" /> Password</span>
                  <input type="password" value={form.password} onChange={e => setField("password", e.target.value)} placeholder="Min. 8 characters" className="bg-transparent border-b border-white/20 focus:border-white py-3 text-white placeholder-white/30 outline-none transition-colors text-lg" />
                  {errors.password && <span className="text-alert text-sm font-mono">{errors.password}</span>}
                </label>
                <label className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-white/50 uppercase tracking-widest flex items-center gap-2"><Lock className="w-3 h-3" /> Confirm Password</span>
                  <input type="password" value={form.confirm} onChange={e => setField("confirm", e.target.value)} placeholder="Repeat password" className="bg-transparent border-b border-white/20 focus:border-white py-3 text-white placeholder-white/30 outline-none transition-colors text-lg" />
                  {errors.confirm && <span className="text-alert text-sm font-mono">{errors.confirm}</span>}
                </label>
                {/* Password strength hints */}
                <div className="flex gap-2 mt-2">
                  {[form.password.length >= 8, /[A-Z]/.test(form.password), /[0-9]/.test(form.password)].map((met, i) => (
                    <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${met ? "bg-brand" : "bg-white/10"}`} />
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-8">
                <button onClick={() => setStep(1)} className="text-white/40 hover:text-white transition-colors text-sm">← Back</button>
                <Link href="/dashboard" className="flex items-center gap-3 px-8 py-4 bg-white text-black font-medium text-sm">
                  Create Account <ChevronRight className="w-4 h-4" />
                </Link>
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

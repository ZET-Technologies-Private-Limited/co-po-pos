"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, ArrowRight, Check, Loader2, AlertCircle,
  BookOpen, GraduationCap, BarChart3, Settings2,
} from "lucide-react";
import Link from "next/link";
import { useAuthStore } from "@/lib/authStore";
import apiClient from "@/lib/apiClient";
import { AccessGate } from "@/components/auth/AccessGate";

// ─── Types ────────────────────────────────────────────────────────────────────
interface FormData {
  course_code: string;
  course_name: string;
  department: string;
  credits: number;
  semester: number;
  description: string;
  course_type: string;
  enrolled_students: number;
  fa_method: string;
  fa_best_n: number;
  fa_total_components: number;
  fa_weight: number;
  sa_weight: number;
}

// ─── Step definitions ─────────────────────────────────────────────────────────
const STEPS = [
  { id: 0, label: "Identity",    icon: BookOpen,      desc: "Course code, name & department" },
  { id: 1, label: "Structure",   icon: GraduationCap, desc: "Credits, semester & type" },
  { id: 2, label: "Assessment",  icon: BarChart3,      desc: "FA/SA weights & method" },
  { id: 3, label: "Description", icon: Settings2,      desc: "Optional course overview" },
];

// ─── Animations ───────────────────────────────────────────────────────────────
const slideVariants = {
  enter: (dir: number) => ({ x: dir > 0 ? 40 : -40, opacity: 0 }),
  center: { x: 0, opacity: 1, transition: { duration: 0.28, ease: [0.4, 0, 0.2, 1] } },
  exit:  (dir: number) => ({ x: dir > 0 ? -40 : 40, opacity: 0, transition: { duration: 0.2 } }),
};

// ─── Field component ──────────────────────────────────────────────────────────
function Field({
  label, hint, required, children,
}: { label: string; hint?: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <label className="text-[11px] font-mono uppercase tracking-widest text-white/40">
          {label}{required && <span className="text-brand ml-1">*</span>}
        </label>
        {hint && <span className="text-[10px] text-white/20 font-mono">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

const inputCls =
  "w-full bg-transparent border-b border-white/15 pb-2 text-white text-sm placeholder-white/20 " +
  "focus:outline-none focus:border-brand/60 transition-colors";

const selectCls =
  "w-full bg-transparent border-b border-white/15 pb-2 text-white text-sm " +
  "focus:outline-none focus:border-brand/60 transition-colors appearance-none cursor-pointer";

// ─── Live preview panel ───────────────────────────────────────────────────────
function PreviewPanel({ form, step }: { form: FormData; step: number }) {
  const faTotal = form.fa_weight + form.sa_weight;
  const faOk = Math.abs(faTotal - 100) < 0.01;

  return (
    <div className="flex flex-col h-full px-10 py-12 justify-between">
      {/* Brand mark */}
      <div>
        <Link
          href="/faculty/dashboard"
          className="flex items-center gap-2 text-[10px] font-mono text-white/25 hover:text-white/60 uppercase tracking-widest transition-colors mb-12"
        >
          <ArrowLeft className="w-3 h-3" /> Dashboard
        </Link>

        <p className="text-[10px] font-mono uppercase tracking-widest text-brand/60 mb-3">
          New Course
        </p>
        <h1 className="font-display text-4xl font-bold text-white leading-tight mb-2">
          {form.course_name || <span className="text-white/15">Course Name</span>}
        </h1>
        {form.course_code && (
          <p className="font-mono text-sm text-white/40">{form.course_code}</p>
        )}
      </div>

      {/* Live summary */}
      <div className="space-y-0 divide-y divide-white/5">
        {[
          { label: "Department",  value: form.department || "—" },
          { label: "Type",        value: form.course_type ? form.course_type.charAt(0).toUpperCase() + form.course_type.slice(1) : "—" },
          { label: "Semester",    value: form.semester ? `Semester ${form.semester}` : "—" },
          { label: "Credits",     value: form.credits ? `${form.credits} credits` : "—" },
          { label: "Students",    value: form.enrolled_students ? `${form.enrolled_students} enrolled` : "—" },
          { label: "FA / SA",     value: faOk ? `${form.fa_weight}% / ${form.sa_weight}%` : <span className="text-alert/70">{form.fa_weight}% + {form.sa_weight}% ≠ 100</span> },
          { label: "FA Method",   value: form.fa_method === "best_n_of_m" ? `Best ${form.fa_best_n} of ${form.fa_total_components}` : form.fa_method === "simple_avg" ? "Simple Average" : "Weighted" },
        ].map(({ label, value }) => (
          <div key={label} className="flex items-center justify-between py-3">
            <span className="text-[10px] font-mono uppercase tracking-widest text-white/25">{label}</span>
            <span className="text-xs text-white/60">{value}</span>
          </div>
        ))}
      </div>

      {/* Step progress */}
      <div className="space-y-3">
        <p className="text-[10px] font-mono uppercase tracking-widest text-white/20">Progress</p>
        <div className="flex gap-2">
          {STEPS.map((s) => (
            <div
              key={s.id}
              className={`h-0.5 flex-1 transition-all duration-500 ${
                s.id < step ? "bg-brand" : s.id === step ? "bg-brand/50" : "bg-white/10"
              }`}
            />
          ))}
        </div>
        <p className="text-[10px] font-mono text-white/25">
          Step {step + 1} of {STEPS.length} — {STEPS[step].desc}
        </p>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function CreateCoursePage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [step, setStep] = useState(0);
  const [dir, setDir] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState<FormData>({
    course_code: "",
    course_name: "",
    department: user?.department || "",
    credits: 3,
    semester: 1,
    description: "",
    course_type: "core",
    enrolled_students: 0,
    fa_method: "best_n_of_m",
    fa_best_n: 3,
    fa_total_components: 5,
    fa_weight: 40,
    sa_weight: 60,
  });

  // Sync department from user once loaded
  useEffect(() => {
    if (user?.department && !form.department) {
      setForm((p) => ({ ...p, department: user.department }));
    }
  }, [user]);

  const set = (name: keyof FormData, value: string | number) =>
    setForm((p) => ({ ...p, [name]: value }));

  const handleInput = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    const intFields = new Set(["credits", "semester", "enrolled_students", "fa_best_n", "fa_total_components"]);
    const floatFields = new Set(["fa_weight", "sa_weight"]);
    set(
      name as keyof FormData,
      intFields.has(name) ? parseInt(value) || 0 : floatFields.has(name) ? parseFloat(value) || 0 : value
    );
  };

  const validateStep = (): string | null => {
    if (step === 0) {
      if (!form.course_code.trim()) return "Course Code is required.";
      if (!form.course_name.trim()) return "Course Name is required.";
      if (!form.department.trim()) return "Department is required.";
    }
    if (step === 2) {
      if (form.fa_weight < 0 || form.sa_weight < 0) return "Weights cannot be negative.";
      if (Math.abs(form.fa_weight + form.sa_weight - 100) > 0.01) return "FA + SA weights must total 100%.";
      if (form.fa_best_n >= form.fa_total_components) return "Best N must be less than Total M.";
    }
    return null;
  };

  const next = () => {
    const err = validateStep();
    if (err) { setError(err); return; }
    setError(null);
    setDir(1);
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };

  const back = () => {
    setError(null);
    setDir(-1);
    setStep((s) => Math.max(s - 1, 0));
  };

  const handleSubmit = async () => {
    const err = validateStep();
    if (err) { setError(err); return; }
    setLoading(true);
    setError(null);
    try {
      const newCourse = await apiClient.createCourse({
        ...form,
        fa_weight: form.fa_weight / 100,
        sa_weight: form.sa_weight / 100,
      });
      router.push(`/faculty/course/${newCourse.id}`);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to create course.");
      setLoading(false);
    }
  };

  return (
    <AccessGate feature="dashboard" deny="lock">
      <div className="min-h-screen flex">
        {/* ── LEFT PANEL ── */}
        <div className="hidden lg:flex lg:w-[42%] xl:w-[38%] flex-col border-r border-white/5 bg-white/[0.02]">
          <PreviewPanel form={form} step={step} />
        </div>

        {/* ── RIGHT PANEL ── */}
        <div className="flex-1 flex flex-col">
          {/* Mobile back link */}
          <div className="lg:hidden px-8 pt-8">
            <Link
              href="/faculty/dashboard"
              className="flex items-center gap-2 text-[10px] font-mono text-white/30 hover:text-white uppercase tracking-widest transition-colors"
            >
              <ArrowLeft className="w-3 h-3" /> Dashboard
            </Link>
          </div>

          {/* Step tabs */}
          <div className="flex border-b border-white/5 px-8 lg:px-12 mt-8 lg:mt-0 pt-0 lg:pt-12">
            {STEPS.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => {
                  if (s.id < step) { setDir(-1); setStep(s.id); setError(null); }
                }}
                className={`flex items-center gap-2 px-4 py-4 text-[10px] font-mono uppercase tracking-widest border-b-2 transition-all ${
                  s.id === step
                    ? "text-white border-brand"
                    : s.id < step
                    ? "text-white/40 border-transparent hover:text-white/60 cursor-pointer"
                    : "text-white/15 border-transparent cursor-default"
                }`}
              >
                <s.icon className="w-3 h-3 shrink-0" />
                <span className="hidden sm:inline">{s.label}</span>
                {s.id < step && <Check className="w-2.5 h-2.5 text-brand" />}
              </button>
            ))}
          </div>

          {/* Form area */}
          <div className="flex-1 overflow-y-auto px-8 lg:px-12 py-10">
            {/* Error */}
            <AnimatePresence mode="wait">
              {error && (
                <motion.div
                  key="err"
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-2 text-red-400 text-xs mb-8 font-mono"
                >
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" /> {error}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Step content */}
            <AnimatePresence mode="wait" custom={dir}>
              <motion.div
                key={step}
                custom={dir}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                className="space-y-10 max-w-lg"
              >
                {/* ── STEP 0: Identity ── */}
                {step === 0 && (
                  <>
                    <div>
                      <h2 className="font-display text-2xl text-white mb-1">Course Identity</h2>
                      <p className="text-white/30 text-sm">The core identifiers for this course.</p>
                    </div>
                    <div className="space-y-8">
                      <Field label="Course Code" required hint="e.g. CS301">
                        <input
                          name="course_code"
                          value={form.course_code}
                          onChange={handleInput}
                          placeholder="CS301"
                          autoFocus
                          className={inputCls}
                        />
                      </Field>
                      <Field label="Course Name" required hint="Full title">
                        <input
                          name="course_name"
                          value={form.course_name}
                          onChange={handleInput}
                          placeholder="Data Structures & Algorithms"
                          className={inputCls}
                        />
                      </Field>
                      <Field label="Department" required>
                        <input
                          name="department"
                          value={form.department}
                          onChange={handleInput}
                          placeholder="Computer Science and Engineering"
                          className={inputCls}
                        />
                      </Field>
                    </div>
                  </>
                )}

                {/* ── STEP 1: Structure ── */}
                {step === 1 && (
                  <>
                    <div>
                      <h2 className="font-display text-2xl text-white mb-1">Course Structure</h2>
                      <p className="text-white/30 text-sm">Academic details and enrollment.</p>
                    </div>
                    <div className="space-y-8">
                      <Field label="Course Type">
                        <select name="course_type" value={form.course_type} onChange={handleInput} className={selectCls}>
                          <option value="core">Core</option>
                          <option value="elective">Elective</option>
                          <option value="lab">Lab</option>
                        </select>
                      </Field>
                      <Field label="Semester" hint="1 – 10">
                        <input
                          name="semester"
                          type="number"
                          min={1}
                          max={10}
                          value={form.semester}
                          onChange={handleInput}
                          className={inputCls}
                        />
                      </Field>
                      <Field label="Credits" hint="1 – 8">
                        <input
                          name="credits"
                          type="number"
                          min={1}
                          max={8}
                          value={form.credits}
                          onChange={handleInput}
                          className={inputCls}
                        />
                      </Field>
                      <Field label="Enrolled Students" hint="Approximate count">
                        <input
                          name="enrolled_students"
                          type="number"
                          min={0}
                          value={form.enrolled_students}
                          onChange={handleInput}
                          className={inputCls}
                        />
                      </Field>
                    </div>
                  </>
                )}

                {/* ── STEP 2: Assessment ── */}
                {step === 2 && (
                  <>
                    <div>
                      <h2 className="font-display text-2xl text-white mb-1">Assessment Config</h2>
                      <p className="text-white/30 text-sm">FA/SA split and formative method.</p>
                    </div>
                    <div className="space-y-8">
                      {/* Weight visualiser */}
                      <div className="space-y-3">
                        <div className="flex justify-between text-[10px] font-mono text-white/30 uppercase tracking-widest">
                          <span>FA {form.fa_weight}%</span>
                          <span>SA {form.sa_weight}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-white/5 overflow-hidden">
                          <div
                            className="h-full bg-brand transition-all duration-300"
                            style={{ width: `${Math.min(form.fa_weight, 100)}%` }}
                          />
                        </div>
                        {Math.abs(form.fa_weight + form.sa_weight - 100) > 0.01 && (
                          <p className="text-[10px] font-mono text-alert/70">
                            Total: {form.fa_weight + form.sa_weight}% — must equal 100%
                          </p>
                        )}
                      </div>

                      <Field label="FA Weight %" hint="Formative assessment">
                        <input
                          name="fa_weight"
                          type="number"
                          min={0}
                          max={100}
                          step={0.1}
                          value={form.fa_weight}
                          onChange={handleInput}
                          className={inputCls}
                        />
                      </Field>
                      <Field label="SA Weight %" hint="Summative assessment">
                        <input
                          name="sa_weight"
                          type="number"
                          min={0}
                          max={100}
                          step={0.1}
                          value={form.sa_weight}
                          onChange={handleInput}
                          className={inputCls}
                        />
                      </Field>
                      <Field label="FA Method">
                        <select name="fa_method" value={form.fa_method} onChange={handleInput} className={selectCls}>
                          <option value="best_n_of_m">Best N of M</option>
                          <option value="simple_avg">Simple Average</option>
                          <option value="weighted">Weighted</option>
                        </select>
                      </Field>
                      {form.fa_method === "best_n_of_m" && (
                        <div className="flex gap-8">
                          <Field label="Best N" hint="Top N counted">
                            <input
                              name="fa_best_n"
                              type="number"
                              min={1}
                              value={form.fa_best_n}
                              onChange={handleInput}
                              className={inputCls}
                            />
                          </Field>
                          <Field label="Total M" hint="Total components">
                            <input
                              name="fa_total_components"
                              type="number"
                              min={1}
                              value={form.fa_total_components}
                              onChange={handleInput}
                              className={inputCls}
                            />
                          </Field>
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* ── STEP 3: Description ── */}
                {step === 3 && (
                  <>
                    <div>
                      <h2 className="font-display text-2xl text-white mb-1">Course Description</h2>
                      <p className="text-white/30 text-sm">Optional — briefly describe objectives and scope.</p>
                    </div>
                    <div className="space-y-8">
                      <Field label="Description" hint="Optional">
                        <textarea
                          name="description"
                          rows={6}
                          placeholder="Describe the course objectives, topics covered, and expected outcomes..."
                          value={form.description}
                          onChange={handleInput}
                          className="w-full bg-transparent border border-white/10 p-4 text-white text-sm placeholder-white/15 focus:outline-none focus:border-white/25 resize-none transition-colors"
                        />
                      </Field>

                      {/* Final summary */}
                      <div className="border-t border-white/5 pt-8 space-y-0 divide-y divide-white/5">
                        <p className="text-[10px] font-mono uppercase tracking-widest text-white/25 pb-4">Review</p>
                        {[
                          ["Code",       form.course_code || "—"],
                          ["Name",       form.course_name || "—"],
                          ["Department", form.department || "—"],
                          ["Type",       form.course_type],
                          ["Semester",   `${form.semester}`],
                          ["Credits",    `${form.credits}`],
                          ["FA / SA",    `${form.fa_weight}% / ${form.sa_weight}%`],
                        ].map(([k, v]) => (
                          <div key={k} className="flex justify-between py-2.5">
                            <span className="text-[10px] font-mono uppercase tracking-widest text-white/25">{k}</span>
                            <span className="text-xs text-white/60">{v}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Navigation footer */}
          <div className="border-t border-white/5 px-8 lg:px-12 py-6 flex items-center justify-between">
            <button
              type="button"
              onClick={back}
              disabled={step === 0}
              className="flex items-center gap-2 text-xs font-mono text-white/30 hover:text-white disabled:opacity-0 disabled:pointer-events-none transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back
            </button>

            <div className="flex items-center gap-6">
              <Link
                href="/faculty/dashboard"
                className="text-[10px] font-mono text-white/20 hover:text-white/50 transition-colors uppercase tracking-widest"
              >
                Cancel
              </Link>

              {step < STEPS.length - 1 ? (
                <button
                  type="button"
                  onClick={next}
                  className="flex items-center gap-2 px-6 py-2.5 text-xs font-mono text-white border border-white/15 hover:border-brand/50 hover:text-brand transition-colors"
                >
                  Continue <ArrowRight className="w-3.5 h-3.5" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-2.5 text-xs font-mono text-white bg-brand/20 border border-brand/40 hover:bg-brand/30 hover:border-brand disabled:opacity-40 transition-colors"
                >
                  {loading ? (
                    <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Creating...</>
                  ) : (
                    <><Check className="w-3.5 h-3.5" /> Create Course</>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </AccessGate>
  );
}

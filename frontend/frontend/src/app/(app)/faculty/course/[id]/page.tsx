"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { AccessGate } from "@/components/auth/AccessGate";
import apiClient from "@/lib/apiClient";
import { CourseErrorDisplay } from "@/components/course/CourseErrorDisplay";
import {
  Sparkles, Settings, BrainCircuit, FileSpreadsheet, BarChart2,
  Bot, Target, FileText, ArrowRight, BookOpen, AlertCircle,
  Upload, Check, X, Loader2, ChevronDown, GitBranch,
} from "lucide-react";
import { fadeSlideUp, staggerContainer } from "@/lib/animations";

const WORKFLOWS = [
  { href: "co-generation", label: "CO Generation", icon: Sparkles, description: "AI-generate course outcomes from syllabus" },
  { href: "exam-config", label: "Exam Configuration", icon: Settings, description: "Configure exams and set up assessments" },
  { href: "question-analyser", label: "AI Question Analyser", icon: BrainCircuit, description: "Map questions to learning outcomes with AI" },
  { href: "marks", label: "Marks Upload", icon: FileSpreadsheet, description: "Upload and manage student marks" },
  { href: "co-attainment", label: "CO Attainment", icon: BarChart2, description: "View CO attainment analysis" },
  { href: "po-pso-attainment", label: "PO/PSO Attainment", icon: Target, description: "Program and program-specific outcome mapping" },
  { href: "correlations", label: "CO-PO Correlations", icon: GitBranch, description: "Manually set CO-PO and CO-PSO mappings" },
  { href: "chatbot", label: "OBE Chatbot", icon: Bot, description: "Ask questions about course outcomes" },
  { href: "reports", label: "Reports", icon: FileText, description: "Generate and export comprehensive reports" },
];

export default function CoursePage() {
  const { id } = useParams();
  const courseId = id as string;

  const [course, setCourse] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syllabusText, setSyllabusText] = useState("");
  const [syllabusLoading, setSyllabusLoading] = useState(false);
  const [syllabusError, setSyllabusError] = useState<string | null>(null);
  const [syllabusSuccess, setSyllabusSuccess] = useState(false);
  const [fileUploading, setFileUploading] = useState(false);
  const [showSyllabusForm, setShowSyllabusForm] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true); setError(null);
      try {
        const c = await apiClient.getCourse(courseId);
        if (!cancelled) { setCourse(c); setSyllabusText(c.syllabus || ""); }
      } catch (e: any) {
        if (!cancelled) { setError(typeof e?.message === "string" ? e.message : "Failed to load course."); }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [courseId]);

  const handleSyllabusUpdate = async () => {
    setSyllabusLoading(true); setSyllabusError(null); setSyllabusSuccess(false);
    try {
      await apiClient.updateSyllabus(courseId, syllabusText);
      setSyllabusSuccess(true);
      setTimeout(() => setSyllabusSuccess(false), 3000);
    } catch (e: any) {
      setSyllabusError(typeof e?.message === "string" ? e.message : "Failed to update syllabus.");
    } finally { setSyllabusLoading(false); }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const validTypes = [".pdf", ".docx", ".txt"];
    if (!validTypes.some((ext) => file.name.toLowerCase().endsWith(ext))) {
      setSyllabusError("Only PDF, DOCX, or TXT files are allowed."); return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setSyllabusError("File size must be less than 5 MB."); return;
    }
    setFileUploading(true); setSyllabusError(null); setSyllabusSuccess(false);
    try {
      await apiClient.uploadSyllabusFile(courseId, file);
      const c = await apiClient.getCourse(courseId);
      setCourse(c); setSyllabusText(c.syllabus || "");
      setSyllabusSuccess(true);
      setTimeout(() => setSyllabusSuccess(false), 3000);
    } catch (e: any) {
      setSyllabusError(typeof e?.message === "string" ? e.message : "Failed to upload file.");
    } finally { setFileUploading(false); e.target.value = ""; }
  };

  if (loading) {
    return (
      <AccessGate feature="dashboard" deny="lock">
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <BookOpen className="w-8 h-8 text-brand animate-pulse mx-auto mb-3" />
            <p className="text-white/50 text-sm">Loading course...</p>
          </div>
        </div>
      </AccessGate>
    );
  }

  if (error) {
    return (
      <AccessGate feature="dashboard" deny="lock">
        <CourseErrorDisplay
          title="Failed to Load Course"
          message={error}
          suggestion="The course data could not be retrieved. Please try again or go back to dashboard."
          onRetry={() => window.location.reload()}
        />
      </AccessGate>
    );
  }

  return (
    <AccessGate feature="dashboard" deny="lock">
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="w-full pb-32">
        {/* Course Header */}
        <motion.div variants={fadeSlideUp} className="border-b border-white/10 pb-8 mb-10">
          <div className="flex items-start gap-4">
            <BookOpen className="w-6 h-6 text-brand mt-1 shrink-0" />
            <div>
              <h1 className="text-4xl font-display text-white">{course?.course_code}</h1>
              <p className="text-xl text-white/60 font-light mt-1">{course?.course_name}</p>
              {course?.description && (
                <p className="text-white/30 mt-2 text-sm max-w-2xl">{course.description}</p>
              )}
              <div className="flex items-center gap-6 mt-4">
                {[
                  { label: "Credits", value: course?.credits ?? "—" },
                  { label: "Semester", value: course?.semester ?? "—" },
                  { label: "Department", value: course?.department ?? "—" },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-white/30 uppercase">{label}</span>
                    <span className="text-sm text-white/60 font-mono">{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Syllabus Management */}
        <motion.div variants={fadeSlideUp} className="border-b border-white/5 pb-10 mb-10">
          <button
            onClick={() => setShowSyllabusForm(!showSyllabusForm)}
            className="flex items-center justify-between w-full mb-2"
          >
            <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Syllabus Management</h2>
            <div className="flex items-center gap-2">
              {syllabusText ? (
                <span className="text-[9px] font-mono text-emerald-400 uppercase">
                  {syllabusText.length} chars uploaded
                </span>
              ) : (
                <span className="text-[9px] font-mono text-amber-400 uppercase">not uploaded</span>
              )}
              <ChevronDown className={`w-4 h-4 text-white/30 transition-transform ${showSyllabusForm ? "rotate-180" : ""}`} />
            </div>
          </button>

          {showSyllabusForm && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="overflow-hidden mt-6 space-y-4"
            >
              {syllabusError && (
                <div className="flex items-center gap-2 text-red-400 text-sm">
                  <X className="w-4 h-4 shrink-0" /> {syllabusError}
                </div>
              )}
              {syllabusSuccess && (
                <div className="flex items-center gap-2 text-emerald-400 text-sm">
                  <Check className="w-4 h-4 shrink-0" /> Syllabus updated successfully.
                </div>
              )}

              {/* File Upload */}
              <div className="border border-dashed border-white/20 p-6 text-center hover:border-brand/50 transition-colors">
                <label className="cursor-pointer">
                  <input type="file" accept=".pdf,.docx,.txt" onChange={handleFileUpload} disabled={fileUploading} className="hidden" />
                  <Upload className={`w-5 h-5 mx-auto mb-2 ${fileUploading ? "text-white/30 animate-pulse" : "text-brand"}`} />
                  <p className="text-white/50 text-sm">{fileUploading ? "Uploading..." : "Upload PDF, DOCX, or TXT (max 5 MB)"}</p>
                </label>
              </div>

              {/* Text Input */}
              <div>
                <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest block mb-2">
                  Or paste syllabus text
                </label>
                <textarea
                  value={syllabusText}
                  onChange={(e) => setSyllabusText(e.target.value)}
                  disabled={syllabusLoading}
                  placeholder="Paste your course syllabus content here..."
                  rows={8}
                  className="w-full bg-transparent border border-white/20 p-4 text-white text-sm placeholder-white/20 focus:outline-none focus:border-white/40 resize-none disabled:opacity-50"
                />
                <p className="text-white/20 text-xs mt-1 font-mono">{syllabusText.length} characters</p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => void handleSyllabusUpdate()}
                  disabled={syllabusLoading || !syllabusText.trim()}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-mono text-white border border-white/20 hover:border-white/50 disabled:opacity-40 transition-colors"
                >
                  {syllabusLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                  Save Syllabus
                </button>
                <button
                  onClick={() => { setShowSyllabusForm(false); setSyllabusError(null); setSyllabusText(course?.syllabus || ""); }}
                  className="px-4 py-2 text-xs font-mono text-white/40 hover:text-white transition-colors"
                >
                  Cancel
                </button>
              </div>
            </motion.div>
          )}
        </motion.div>

        {/* Workflows — card grid */}
        <motion.div variants={fadeSlideUp}>
          <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest mb-4">Course Workflows</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px bg-white/5">
            {WORKFLOWS.map((workflow) => {
              const Icon = workflow.icon;
              return (
                <Link key={workflow.href} href={`/faculty/course/${courseId}/${workflow.href}`}>
                  <div className="flex flex-col justify-between h-full bg-[#0a1628] px-5 py-5 hover:bg-white/[0.04] transition-colors group min-h-[100px]">
                    <div className="flex items-start justify-between gap-3">
                      <Icon className="w-4 h-4 text-brand shrink-0 mt-0.5" />
                      <ArrowRight className="w-3.5 h-3.5 text-white/15 group-hover:text-brand group-hover:translate-x-0.5 transition-all shrink-0" />
                    </div>
                    <div className="mt-4">
                      <p className="text-sm text-white group-hover:text-brand transition-colors font-medium">{workflow.label}</p>
                      <p className="text-[11px] text-white/35 mt-1 leading-relaxed">{workflow.description}</p>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </motion.div>

        {/* Getting Started hint */}
        {!syllabusText && (
          <motion.div variants={fadeSlideUp} className="mt-10 flex items-start gap-3 text-sm text-white/40">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <p>
              Start by uploading your course syllabus above, then use{" "}
              <span className="text-white/60">CO Generation</span> to generate course outcomes with AI.
            </p>
          </motion.div>
        )}
      </motion.div>
    </AccessGate>
  );
}

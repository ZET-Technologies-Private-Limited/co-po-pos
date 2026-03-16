"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { AccessGate } from "@/components/auth/AccessGate";
import { FileUploadSection } from "@/components/workflow/FileUploadSection";
import apiClient from "@/lib/apiClient";
import {
  AlertCircle,
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Download,
  FileText,
  History,
  Layers,
  ListChecks,
  Loader2,
  Lock,
  Pencil,
  RefreshCw,
  Sparkles,
  Trash2,
  Upload,
} from "lucide-react";

// ─── NBA Standard POs (fixed — never editable) ────────────────────────────────
const NBA_POS = [
  { code: "PO1",  name: "Engineering Knowledge",                         statement: "Apply knowledge of mathematics, science, engineering fundamentals and an engineering specialisation to the solution of complex engineering problems." },
  { code: "PO2",  name: "Problem Analysis",                               statement: "Identify, formulate, review research literature, and analyse complex engineering problems reaching substantiated conclusions using first principles of mathematics, natural sciences and engineering sciences." },
  { code: "PO3",  name: "Design/Development of Solutions",                statement: "Design solutions for complex engineering problems and design system components or processes that meet the specified needs with appropriate consideration for the public health and safety, and the cultural, societal, and environmental considerations." },
  { code: "PO4",  name: "Conduct Investigations of Complex Problems",      statement: "Use research-based knowledge and research methods including design of experiments, analysis and interpretation of data, and synthesis of the information to provide valid conclusions." },
  { code: "PO5",  name: "Modern Tool Usage",                              statement: "Create, select, and apply appropriate techniques, resources, and modern engineering and IT tools including prediction and modelling to complex engineering activities with an understanding of the limitations." },
  { code: "PO6",  name: "The Engineer and Society",                       statement: "Apply reasoning informed by the contextual knowledge to assess societal, health, safety, legal and cultural issues and the consequent responsibilities relevant to the professional engineering practice." },
  { code: "PO7",  name: "Environment and Sustainability",                 statement: "Understand the impact of the professional engineering solutions in societal and environmental contexts, and demonstrate the knowledge of, and need for sustainable development." },
  { code: "PO8",  name: "Ethics",                                         statement: "Apply ethical principles and commit to professional ethics and responsibilities and norms of the engineering practice." },
  { code: "PO9",  name: "Individual and Team Work",                       statement: "Function effectively as an individual, and as a member or leader in diverse teams, and in multidisciplinary settings." },
  { code: "PO10", name: "Communication",                                  statement: "Communicate effectively on complex engineering activities with the engineering community and with society at large." },
  { code: "PO11", name: "Project Management and Finance",                 statement: "Demonstrate knowledge and understanding of the engineering and management principles and apply these to one's own work, as a member and leader in a team, to manage projects and in multidisciplinary environments." },
  { code: "PO12", name: "Life-long Learning",                             statement: "Recognise the need for, and have the preparation and ability to engage in independent and life-long learning in the broadest context of technological change." },
];

const BLOOM_VERBS: Record<string, string[]> = {
  create:   ["design", "construct", "develop", "formulate", "produce", "synthesize", "compose"],
  evaluate: ["assess", "critique", "justify", "defend", "appraise", "evaluate", "judge"],
  analyze:  ["differentiate", "examine", "compare", "contrast", "investigate", "break down"],
  apply:    ["implement", "solve", "use", "demonstrate", "execute", "operate", "calculate"],
  understand: ["explain", "describe", "summarize", "classify", "interpret", "paraphrase"],
  remember: ["recall", "list", "identify", "define", "state", "name", "recognize"],
};

function bloomColor(level: string | undefined) {
  const l = (level || "").toLowerCase();
  if (l === "create" || l === "evaluate") return "text-purple-400";
  if (l === "analyze" || l === "analyse") return "text-blue-400";
  if (l === "apply") return "text-emerald-400";
  if (l === "understand") return "text-amber-400";
  return "text-white/40";
}

function formatWeightPercent(value: unknown, fallback: number) {
  const n = Number(value);
  if (!Number.isFinite(n)) return `${fallback}%`;
  const normalized = n <= 1.01 ? n * 100 : n;
  return `${Math.round(normalized)}%`;
}

function formatFaMethod(course: any) {
  const method = String(course?.fa_method || "best_n_of_m").toLowerCase();
  const bestN = Number(course?.fa_best_n ?? 3) || 3;
  const totalM = Number(course?.fa_total_components ?? 5) || 5;
  if (method === "best_n_of_m") return `Best ${bestN} of ${totalM}`;
  if (method === "weighted") return "Weighted average";
  return "Simple average";
}

function formatCourseType(value: unknown) {
  const t = String(value || "core").toLowerCase();
  if (t === "elective") return "Elective course";
  if (t === "lab") return "Lab course";
  return "Core course";
}

export default function FacultyCOGenerationPage() {
  const params = useParams();
  const courseId = params.id as string;

  const [course, setCourse] = useState<any>(null);
  const [outcomes, setOutcomes] = useState<any[]>([]);
  const [syllabus, setSyllabus] = useState("");
  const [numCos, setNumCos] = useState(5);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [generationSource, setGenerationSource] = useState<"llm" | "fallback" | null>(null);
  const [qualityWarnings, setQualityWarnings] = useState<string[]>([]);
  const [parsedUnits, setParsedUnits] = useState<{ unit: string; topics: string[] }[]>([]);
  const [coverage, setCoverage] = useState<any | null>(null);
  const [sessionSnapshot, setSessionSnapshot] = useState<any | null>(null);
  const [historySnapshots, setHistorySnapshots] = useState<any[]>([]);
  const [mappingJustifications, setMappingJustifications] = useState<Record<string, Record<string, string>>>({});
  const [validation, setValidation] = useState<{
    can_save: boolean;
    errors: string[];
    warnings: string[];
    matrix_density: number;
    nonzero_cells: number;
    total_cells: number;
  } | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [showUnits, setShowUnits] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [programOutcomes, setProgramOutcomes] = useState<any[]>([]);
  const [programSpecificOutcomes, setProgramSpecificOutcomes] = useState<any[]>([]);
  const [showVerbGuide, setShowVerbGuide] = useState(false);
  const [showPoPanel, setShowPoPanel] = useState(false);
  const [poTab, setPoTab] = useState<"po" | "pso">("po");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editStatement, setEditStatement] = useState("");
  const [editBloom, setEditBloom] = useState("understand");
  const [editSaving, setEditSaving] = useState(false);
  const [historyModal, setHistoryModal] = useState<{
    open: boolean;
    coId: string | null;
    coCode: string;
    loading: boolean;
    error: string | null;
    versions: any[];
  }>({ open: false, coId: null, coCode: "", loading: false, error: null, versions: [] });
  // Use NBA_POS as fallback when API returns nothing
  const displayPOs = programOutcomes.length > 0 ? programOutcomes : NBA_POS;

  const [justGenerated, setJustGenerated] = useState(false);
  const outcomesSectionRef = useRef<HTMLDivElement>(null);

  const hasSyllabus = syllabus.trim().length > 0;

  const syllabusWordCount = useMemo(() => {
    const trimmed = syllabus.trim();
    if (!trimmed) return 0;
    return trimmed.split(/\s+/).length;
  }, [syllabus]);

  const bloomBreakdown = useMemo(() => {
    const stats = {
      create: 0,
      evaluate: 0,
      analyze: 0,
      apply: 0,
      understand: 0,
      other: 0,
    };

    outcomes.forEach((co: any) => {
      const raw = (co?.bloom_level || "").toLowerCase().trim();
      if (raw === "create") stats.create += 1;
      else if (raw === "evaluate") stats.evaluate += 1;
      else if (raw === "analyze" || raw === "analyse") stats.analyze += 1;
      else if (raw === "apply") stats.apply += 1;
      else if (raw === "understand") stats.understand += 1;
      else stats.other += 1;
    });

    return stats;
  }, [outcomes]);

  // Quality checks on generated outcomes
  const qualityIssues = useMemo(() => {
    const issues: string[] = [];
    if (outcomes.length === 0) return issues;
    // Check for duplicate/overlapping statements
    const statements = outcomes.map((co: any) => (co.statement || "").toLowerCase());
    statements.forEach((s, i) => {
      statements.forEach((t, j) => {
        if (i >= j) return;
        const wordsS = new Set(s.split(/\s+/).filter((w: string) => w.length > 4));
        const wordsT = t.split(/\s+/).filter((w: string) => w.length > 4);
        const overlap = wordsT.filter((w: string) => wordsS.has(w)).length;
        if (overlap >= 6) issues.push(`CO${i + 1} and CO${j + 1} may overlap (${overlap} shared keywords)`);
      });
    });
    // Check for missing higher-order levels
    const hasHigher = outcomes.some((co: any) => ["create", "evaluate", "analyze"].includes((co.bloom_level || "").toLowerCase()));
    if (!hasHigher) issues.push("No higher-order BT levels (Analyze/Evaluate/Create) — NBA expects cognitive progression");
    // Check for all same level
    const levels = new Set(outcomes.map((co: any) => (co.bloom_level || "").toLowerCase()));
    if (levels.size === 1) issues.push("All COs are at the same Bloom's level — add variety for NBA compliance");
    return issues;
  }, [outcomes]);

  async function load(options?: { preserveCoverage?: boolean }) {
    setLoading(true); setError(null);
    try {
      const [c, cos, sessionInfo, historyInfo] = await Promise.all([
        apiClient.getCourse(courseId),
        apiClient.getCourseOutcomes(courseId),
        apiClient.getCOSession(courseId).catch(() => null),
        apiClient.getCOHistory(courseId).catch(() => ({ versions: [] })),
      ]);
      setCourse(c);
      setSyllabus(c?.syllabus || "");
      const safeOutcomes = Array.isArray(cos) ? cos : [];
      setOutcomes(safeOutcomes);
      setSessionSnapshot(sessionInfo);
      setHistorySnapshots(Array.isArray(historyInfo?.versions) ? historyInfo.versions : []);

      if (safeOutcomes.length > 0 && !options?.preserveCoverage) {
        const cov = await apiClient.getCOCoverage(courseId).catch(() => null);
        setCoverage(cov);
      } else if (safeOutcomes.length === 0) {
        setCoverage(null);
      }

      const programId = String(c?.program_id || c?.programId || "");
      const dept = String(c?.department || "");

      const nbaPOs = await apiClient.getNBAPOs();
      if (Array.isArray(nbaPOs) && nbaPOs.length > 0) {
        setProgramOutcomes(nbaPOs);
      } else if (programId) {
        const pos = await apiClient.getProgramOutcomes(programId);
        setProgramOutcomes(Array.isArray(pos) ? pos : []);
      } else {
        setProgramOutcomes(NBA_POS);
      }

      const deptPSOs = dept ? await apiClient.getDepartmentPSOs(dept) : [];
      if (Array.isArray(deptPSOs) && deptPSOs.length > 0) {
        setProgramSpecificOutcomes(deptPSOs);
      } else if (programId) {
        const psos = await apiClient.getPSOs(programId);
        setProgramSpecificOutcomes(Array.isArray(psos) ? psos : []);
      } else {
        setProgramSpecificOutcomes([]);
      }
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to load CO generation data.");
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [courseId]);

  async function saveSyllabus() {
    setSaving(true); setError(null); setMessage(null);
    try {
      await apiClient.updateSyllabus(courseId, syllabus);
      setMessage("Syllabus saved.");
      setTimeout(() => setMessage(null), 3000);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to save syllabus.");
    } finally { setSaving(false); }
  }

  async function generate() {
    if (!syllabus.trim()) { setError("Syllabus is required for AI CO generation."); return; }
    setGenerating(true); setError(null); setMessage(null); setGenerationSource(null); setQualityWarnings([]);
    setValidation(null); setConfirmed(false); setParsedUnits([]); setMappingJustifications({});
    try {
      const result = await apiClient.generateCourseOutcomes(courseId, {
        syllabus,
        num_cos: numCos,
        program_outcomes: programOutcomes.map((po: any) => ({
          code: po.code ?? po.id,
          statement: po.statement ?? po.name ?? po.description ?? "",
        })),
        program_specific_outcomes: programSpecificOutcomes.map((pso: any) => ({
          code: pso.code ?? pso.id,
          statement: pso.statement ?? pso.name ?? pso.description ?? "",
        })),
      });
      const warnings: string[] = Array.isArray(result?.quality_warnings) ? result.quality_warnings : [];
      const isFallback = warnings.some((w: string) => w.includes("domain default") || w.includes("LLM unavailable"));
      setGenerationSource(isFallback ? "fallback" : "llm");
      setQualityWarnings(warnings);
      if (Array.isArray(result?.units) && result.units.length > 0) {
        setParsedUnits(result.units);
        setShowUnits(true);
      }
      if (result?.coverage) setCoverage(result.coverage);
      if (result?.mapping_justifications && typeof result.mapping_justifications === "object") {
        setMappingJustifications(result.mapping_justifications);
      }
      if (result?.validation) setValidation(result.validation);
      const domain = result?.domain ? ` [${result.domain.toUpperCase()} domain]` : "";
      const src = isFallback ? " (domain defaults — LLM unavailable)" : " via AI";
      setMessage(`${result?.total_cos ?? numCos} course outcomes generated${src}${domain}.`);
      await load({ preserveCoverage: Boolean(result?.coverage) });
          setJustGenerated(true);
          setTimeout(() => {
            outcomesSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
          }, 400);
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "CO generation failed.");
    } finally { setGenerating(false); }
  }

  async function regenerate(coId: string) {
    setRegeneratingId(coId); setError(null);
    try {
      await apiClient.regenerateSingleCO(courseId, coId);
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "CO regeneration failed.");
    } finally { setRegeneratingId(null); }
  }

  async function deleteCO(coId: string) {
    if (!confirm("Delete this course outcome?")) return;
    setDeletingId(coId); setError(null);
    try {
      await apiClient.deleteCourseOutcome(courseId, coId);
      await load();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to delete CO.");
    } finally { setDeletingId(null); }
  }

  function startInlineEdit(co: any) {
    setEditingId(String(co.id));
    setEditStatement(String(co.statement || co.co_statement || ""));
    const bloom = String(co.bloom_level || "understand").toLowerCase();
    setEditBloom(bloom === "analyse" ? "analyze" : bloom);
  }

  function cancelInlineEdit() {
    setEditingId(null);
    setEditStatement("");
    setEditBloom("understand");
  }

  async function saveInlineEdit() {
    if (!editingId) return;
    setEditSaving(true);
    setError(null);
    try {
      const updated = await apiClient.updateCOStatement(courseId, editingId, {
        statement: editStatement,
        bloom_level: editBloom,
      });
      const warnings = Array.isArray(updated?.warnings) ? updated.warnings : [];
      if (warnings.length > 0) {
        setQualityWarnings((prev) => [...warnings, ...prev].slice(0, 10));
        setMessage(`CO updated with ${warnings.length} warning(s).`);
      } else {
        setMessage("CO statement updated.");
      }
      await load();
      cancelInlineEdit();
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "Failed to update CO statement.");
    } finally {
      setEditSaving(false);
    }
  }

  async function refreshCoverage() {
    try {
      const cov = await apiClient.getCOCoverage(courseId);
      setCoverage(cov);
    } catch {
      // Keep existing coverage if refresh fails.
    }
  }

  async function openItemHistory(co: any) {
    const coId = String(co?.id || "");
    const coCode = String(co?.code || co?.co_code || "");
    if (!coId) return;
    setHistoryModal({ open: true, coId, coCode, loading: true, error: null, versions: [] });
    try {
      const res = await apiClient.getCOItemHistory(courseId, coId);
      const versions = Array.isArray(res?.versions) ? res.versions : [];
      setHistoryModal((p) => ({ ...p, loading: false, versions }));
    } catch (e: any) {
      setHistoryModal((p) => ({ ...p, loading: false, error: e?.message || "Failed to load CO history" }));
    }
  }

  async function rollbackToVersion(versionIndex: number) {
    if (!historyModal.coId) return;
    setHistoryModal((p) => ({ ...p, loading: true, error: null }));
    try {
      await apiClient.rollbackCO(courseId, historyModal.coId, versionIndex);
      await load();
      const res = await apiClient.getCOItemHistory(courseId, historyModal.coId);
      const versions = Array.isArray(res?.versions) ? res.versions : [];
      setHistoryModal((p) => ({ ...p, loading: false, versions }));
      setMessage(`Rolled back ${historyModal.coCode} to version ${versionIndex}.`);
      setTimeout(() => setMessage(null), 3000);
    } catch (e: any) {
      setHistoryModal((p) => ({ ...p, loading: false, error: e?.message || "Rollback failed" }));
    }
  }

  async function downloadNBASAR() {
    setError(null);
    try {
      const blob = await apiClient.exportNBASAR(courseId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `NBA_SAR_${course?.course_code || courseId}.csv`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setMessage("NBA SAR CSV downloaded.");
    } catch (e: any) {
      setError(typeof e?.message === "string" ? e.message : "NBA SAR export failed.");
    }
  }

  const coverageUnits: any[] = Array.isArray(coverage?.units)
    ? coverage.units
    : Array.isArray(coverage?.unit_details)
    ? coverage.unit_details
    : [];
  const coveredUnitsRaw = coverage?.covered_units ?? coverage?.covered_count;
  const coveredUnitsCount = Array.isArray(coveredUnitsRaw)
    ? coveredUnitsRaw.length
    : Number.isFinite(Number(coveredUnitsRaw))
    ? Number(coveredUnitsRaw)
    : coverageUnits.filter((u: any) => Boolean(u?.is_covered ?? u?.covered)).length;
  const totalUnitsRaw = coverage?.total_units;
  const totalUnitsCount = Number.isFinite(Number(totalUnitsRaw))
    ? Number(totalUnitsRaw)
    : coverageUnits.length;
  const coveragePct = Number(
    coverage?.coverage_pct ??
    (totalUnitsCount > 0 ? (coveredUnitsCount / totalUnitsCount) * 100 : 0),
  );

  return (
    <AccessGate feature="co_generation" deny="lock">
      <div className="w-full pb-24 space-y-8">
        {historyModal.open && (
          <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center px-4">
            <div className="w-full max-w-2xl border border-white/10 bg-[#0a1628]">
              <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                <div>
                  <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Per-CO History</p>
                  <p className="text-sm text-white">{historyModal.coCode || "CO"}</p>
                </div>
                <button
                  onClick={() => setHistoryModal({ open: false, coId: null, coCode: "", loading: false, error: null, versions: [] })}
                  className="text-white/40 hover:text-white text-xs font-mono uppercase tracking-widest"
                >
                  Close
                </button>
              </div>
              <div className="px-4 py-4 space-y-3">
                {historyModal.error && (
                  <p className="text-xs text-red-400">{historyModal.error}</p>
                )}
                {historyModal.loading && (
                  <p className="text-xs text-white/40">Loading…</p>
                )}
                {!historyModal.loading && historyModal.versions.length === 0 && !historyModal.error && (
                  <p className="text-xs text-white/40">No versions found yet (history is recorded when you edit/regenerate).</p>
                )}
                {!historyModal.loading && historyModal.versions.length > 0 && (
                  <div className="divide-y divide-white/10 border border-white/10">
                    {historyModal.versions.slice(0, 10).map((v: any, idx: number) => (
                      <div key={idx} className="px-3 py-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-[10px] font-mono text-white/30 uppercase tracking-widest">
                              v{idx} · {v?.timestamp ? new Date(v.timestamp).toLocaleString() : "Unknown time"} · {String(v?.source || "change")}
                            </p>
                            <p className="text-xs text-white/70 mt-1 leading-relaxed">{String(v?.statement || "")}</p>
                            {v?.bloom_level && (
                              <p className="text-[10px] text-white/35 mt-1 font-mono">BT: {String(v.bloom_level)}</p>
                            )}
                          </div>
                          <button
                            onClick={() => void rollbackToVersion(idx)}
                            disabled={historyModal.loading}
                            className="shrink-0 text-[10px] font-mono uppercase tracking-widest text-attain border border-attain/40 px-2 py-1 hover:border-attain disabled:opacity-40"
                            title="Rollback to this version"
                          >
                            Rollback
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
        {/* Header */}
        <section className="border border-white/10 bg-gradient-to-r from-white/[0.04] to-white/[0.01] px-6 py-6">
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-5">
            <div>
              <h1 className="text-3xl text-white font-display">Course Outcome Generation</h1>
              <p className="text-white/40 text-sm mt-1 font-mono">
                {course?.course_name || "Loading..."}
                {course?.course_code ? ` (${course.course_code})` : ""}
              </p>
              <p className="text-xs text-white/35 mt-3">
                Upload or refine syllabus, generate COs with AI, then move to exam configuration.
              </p>
            </div>

            {outcomes.length > 0 && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => void downloadNBASAR()}
                  className="inline-flex items-center gap-2 px-4 py-2 border border-white/15 text-white/60 hover:text-white hover:border-white/40 transition-colors text-xs font-mono uppercase tracking-widest"
                >
                  <Download className="w-3.5 h-3.5" /> NBA SAR CSV
                </button>
                <Link
                  href={`/faculty/course/${courseId}/exam-config`}
                  className="inline-flex items-center gap-2 px-4 py-2 border border-brand/40 text-brand hover:text-white hover:border-white/40 transition-colors text-xs font-mono uppercase tracking-widest"
                >
                  Continue to Exam Config <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mt-6 border-t border-white/5 pt-5">
            {[
              ["Syllabus",         hasSyllabus ? "Ready" : "Missing",                    hasSyllabus ? "text-attain" : "text-amber-400"],
              ["Word Count",       String(syllabusWordCount),                             "text-white"],
              ["Generated COs",    String(outcomes.length),                               "text-brand"],
              ["Alignment Inputs", `${programOutcomes.length} POs · ${programSpecificOutcomes.length} PSOs`, "text-white/70"],
            ].map(([label, value, color]) => (
              <div key={label} className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-white/25 uppercase tracking-widest">{label}</span>
                <span className={`text-xs font-mono ${color}`}>{value}</span>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-4 text-[10px] font-mono uppercase tracking-widest">
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 border ${hasSyllabus ? "border-attain/40 text-attain" : "border-white/10 text-white/30"}`}>
              {hasSyllabus ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />} 1. Syllabus
            </span>
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 border ${outcomes.length > 0 ? "border-attain/40 text-attain" : "border-white/10 text-white/30"}`}>
              {outcomes.length > 0 ? <CheckCircle2 className="w-3 h-3" /> : <ListChecks className="w-3 h-3" />} 2. Generate COs
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 border border-white/10 text-white/30">
              <ArrowRight className="w-3 h-3" /> 3. Configure Exams
            </span>
          </div>
        </section>

        {/* ── Course Details ── */}
        <section className="border border-white/10 bg-white/[0.015]">
          <div className="flex items-start gap-3 px-5 pt-5 pb-4">
            <Layers className="w-4 h-4 text-brand mt-0.5 shrink-0" />
            <div>
              <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Course Details</h2>
              <p className="text-xs text-white/35 mt-1">Used as context for AI CO generation and NBA compliance validation.</p>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-px bg-white/5 border-t border-white/5">
            {[
              ["Course",      `${course?.course_name || "—"}`, `${course?.course_code || ""} · Sem ${course?.semester ?? "—"}`,  "course-details-course"],
              ["Department",  course?.department || "—",        "Academic unit",                                                   "course-details-department"],
              ["Credits",     String(course?.credits ?? "—"),   formatCourseType(course?.course_type),                             "course-details-credits"],
              ["Students",    String(course?.enrolled_students ?? 0), "Enrolled",                                                  "course-details-students"],
              ["FA Method",   formatFaMethod(course),           "NBA recommended",                                                 "course-details-fa-method"],
              ["FA / SA",     `${formatWeightPercent(course?.fa_weight, 40)} / ${formatWeightPercent(course?.sa_weight, 60)}`, "Formative / Summative split", "course-details-fa-sa"],
            ].map(([label, value, sub, drid]) => (
              <div key={label} data-testid={drid} className="flex flex-col justify-between bg-[#0a1628] px-5 py-4">
                <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest">{label}</span>
                <div className="mt-3">
                  <span data-testid={`${drid}-value`} className="text-sm text-white font-medium">{value}</span>
                  {sub && <p data-testid={`${drid}-sub`} className="text-[10px] text-white/30 mt-0.5">{sub}</p>}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── NBA Program Outcomes (PO1–PO12) + PSOs ── */}
        <section className="border border-white/10">
          <button
            onClick={() => setShowPoPanel(v => !v)}
            className="w-full flex items-center justify-between px-5 py-4 hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-center gap-3">
              <Lock className="w-3.5 h-3.5 text-brand/60 shrink-0" />
              <div className="text-left">
                <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest">
                  NBA Program Outcomes &amp; PSOs — Pre-loaded
                </p>
                <p className="text-[10px] text-white/20 mt-0.5 font-mono">
                  {displayPOs.length} POs (NBA Standard 12) · {programSpecificOutcomes.length} PSOs · Read-only for faculty
                </p>
              </div>
            </div>
            {showPoPanel
              ? <ChevronDown className="w-3.5 h-3.5 text-white/30 shrink-0" />
              : <ChevronRight className="w-3.5 h-3.5 text-white/30 shrink-0" />}
          </button>

          {showPoPanel && (
            <div className="border-t border-white/5">
              {/* NBA rule notice */}
              <div className="flex items-start gap-2 px-5 py-3 border-b border-white/5">
                <AlertCircle className="w-3.5 h-3.5 text-brand/50 mt-0.5 shrink-0" />
                <p className="text-[11px] text-white/35 leading-relaxed">
                  PO1–PO12 are permanently fixed by NBA and identical across all engineering colleges.
                  PSO1–PSO2 are fixed per department — editable only by HOD.
                  These are auto-loaded and sent to the AI during CO generation.
                </p>
              </div>

              {/* Tab switcher */}
              <div className="flex border-b border-white/5">
                {(["po", "pso"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setPoTab(t)}
                    className={`px-5 py-3 text-[10px] font-mono uppercase tracking-widest border-b-2 transition-colors ${
                      poTab === t ? "text-white border-brand" : "text-white/30 border-transparent hover:text-white/60"
                    }`}
                  >
                    {t === "po" ? `PO1–PO12 (${displayPOs.length})` : `PSOs (${programSpecificOutcomes.length})`}
                  </button>
                ))}
              </div>

              {/* PO table */}
              {poTab === "po" && (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-white/10 bg-white/[0.02]">
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 px-5 text-left w-16">Code</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 px-5 text-left">Program Outcome</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 px-5 text-right w-20">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {displayPOs.map((po: any) => (
                        <tr key={po.code} className="border-b border-white/5 hover:bg-white/[0.015] transition-colors">
                          <td className="py-3 px-5 font-mono text-xs text-brand/80 align-top">{po.code}</td>
                          <td className="py-3 px-5 text-xs text-white/60 leading-relaxed align-top">
                            {po.statement || po.name || po.description}
                          </td>
                          <td className="py-3 px-5 text-right align-top">
                            <span className="inline-flex items-center gap-1 text-[9px] font-mono text-white/20 uppercase tracking-widest">
                              <Lock className="w-2.5 h-2.5" /> Fixed
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* PSO table */}
              {poTab === "pso" && (
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-white/10 bg-white/[0.02]">
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 px-5 text-left w-16">Code</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 px-5 text-left">Program Specific Outcome</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 px-5 text-right w-28">Managed by</th>
                      </tr>
                    </thead>
                    <tbody>
                      {programSpecificOutcomes.map((pso: any) => (
                        <tr key={pso.code} className="border-b border-white/5 hover:bg-white/[0.015] transition-colors">
                          <td className="py-3 px-5 font-mono text-xs text-aurora/70 align-top">{pso.code}</td>
                          <td className="py-3 px-5 text-xs leading-relaxed align-top text-white/60">
                            {pso.statement || pso.description}
                          </td>
                          <td className="py-3 px-5 text-right align-top">
                            <span className="text-[9px] font-mono text-white/25 uppercase tracking-widest">HOD</span>
                          </td>
                        </tr>
                      ))}
                      {programSpecificOutcomes.length === 0 && (
                        <tr className="border-b border-white/5">
                          <td colSpan={3} className="py-4 px-5 text-xs text-white/35 italic">
                            No department PSOs configured yet. Ask HOD to add PSOs for this department.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                  <p className="px-5 py-3 text-[10px] text-white/20 font-mono border-t border-white/5">
                    PSOs are department-level definitions. Contact your HOD to update them.
                  </p>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Bloom's Verb Guide */}
        <section className="border border-white/10">
          <button
            onClick={() => setShowVerbGuide(v => !v)}
            className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/[0.02] transition-colors"
          >
            <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest">
              Bloom&apos;s Taxonomy Verb Guide (NBA CO Writing Reference)
            </span>
            {showVerbGuide ? <ChevronDown className="w-3.5 h-3.5 text-white/30" /> : <ChevronRight className="w-3.5 h-3.5 text-white/30" />}
          </button>
          {showVerbGuide && (
            <div className="px-4 pb-4 border-t border-white/5">
              <div className="divide-y divide-white/5 border border-white/5 mt-3">
                {Object.entries(BLOOM_VERBS).map(([level, verbs]) => {
                  const color = level === "create" || level === "evaluate" ? "text-purple-400"
                    : level === "analyze" ? "text-blue-400"
                    : level === "apply" ? "text-emerald-400"
                    : level === "understand" ? "text-amber-400" : "text-white/40";
                  return (
                    <div key={level} className="flex items-start gap-4 px-4 py-3">
                      <span className={`text-[10px] font-mono uppercase tracking-widest w-20 shrink-0 mt-0.5 ${color}`}>{level}</span>
                      <span className="text-[11px] text-white/45 leading-relaxed">{verbs.join(", ")}</span>
                    </div>
                  );
                })}
              </div>
              <p className="text-[10px] text-white/30 mt-3">NBA expects COs to span multiple Bloom&apos;s levels with at least 1–2 higher-order outcomes (Analyze/Evaluate/Create).</p>
            </div>
          )}
        </section>

        {loading && <p className="text-white/50 text-sm py-8">Loading course data...</p>}
        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm border border-red-500/30 bg-red-500/5 px-4 py-3">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}
        {message && (
          <div className="flex items-center gap-2 text-emerald-400 text-sm border border-emerald-500/30 bg-emerald-500/5 px-4 py-3">
            <CheckCircle2 className="w-4 h-4 shrink-0" /> {message}
          </div>
        )}

        {!loading && (
          <>
            {/* Syllabus File Upload */}
            <section className="border border-white/10 bg-white/[0.015] p-5">
              <div className="flex items-start gap-3 mb-4">
                <Upload className="w-4 h-4 text-brand mt-0.5" />
                <div>
                  <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Upload Syllabus File</h2>
                  <p className="text-xs text-white/35 mt-1">Upload once to auto-fill the syllabus editor below.</p>
                </div>
              </div>
              <FileUploadSection
                title="Upload Syllabus"
                description="PDF, DOCX, or TXT — content will be extracted automatically"
                acceptedFormats={[".pdf", ".docx", ".txt"]}
                maxSizeMB={10}
                onFileSelect={async (file) => {
                  const result = await apiClient.uploadSyllabusFile(courseId, file);
                  const updated = await apiClient.getCourse(courseId);
                  setSyllabus(updated.syllabus || "");
                  return result;
                }}
                onSuccess={() => void load()}
              />
            </section>

            {/* Syllabus Text */}
            <section className="border border-white/10 bg-white/[0.015] p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-start gap-3">
                  <FileText className="w-4 h-4 text-brand mt-0.5" />
                  <div>
                    <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Course Syllabus</h2>
                    <p className="text-xs text-white/35 mt-1">Keep units, outcomes, and assessment scope explicit for better AI generation.</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-mono text-white/20">{syllabus.length} chars · {syllabusWordCount} words</span>
                  <button
                    onClick={() => void saveSyllabus()}
                    disabled={saving || !syllabus.trim()}
                    className="flex items-center gap-1.5 text-xs font-mono text-white/40 hover:text-white disabled:opacity-40 transition-colors"
                  >
                    {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
                    Save
                  </button>
                </div>
              </div>
              <textarea
                value={syllabus}
                onChange={(e) => setSyllabus(e.target.value)}
                rows={10}
                placeholder="Paste your course syllabus here, or upload a file above..."
                className="w-full bg-transparent border border-white/20 p-4 text-white text-sm placeholder-white/20 focus:outline-none focus:border-white/40 resize-none font-mono leading-relaxed"
              />
              <p className="text-[11px] text-white/30 mt-3">
                Tip: Include unit-wise topics and expected competencies so CO suggestions are accurate and measurable.
              </p>
            </section>

            {/* ── Generation Controls ── */}
            <section className="border border-white/10 bg-white/[0.015]">
              <div className="flex items-start gap-3 px-5 pt-5 pb-4">
                <Sparkles className="w-4 h-4 text-brand mt-0.5 shrink-0" />
                <div>
                  <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Generate with AI</h2>
                  <p className="text-xs text-white/35 mt-1">
                    AI uses your syllabus + the pre-loaded 12 POs and department PSOs to generate aligned COs.
                  </p>
                </div>
              </div>

              <div className="divide-y divide-white/5 border-t border-white/5">
                {/* Number of COs */}
                <div className="flex items-center justify-between px-5 py-3">
                  <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest">
                    Number of COs
                  </label>
                  <select
                    value={numCos}
                    onChange={(e) => setNumCos(Number(e.target.value))}
                    className="bg-transparent border-b border-white/20 pb-1 text-white text-xs font-mono focus:outline-none focus:border-white/40 appearance-none cursor-pointer"
                  >
                    {[3, 4, 5, 6, 7].map((n) => (
                      <option key={n} value={n} className="bg-[#0F172A]">{n} outcomes</option>
                    ))}
                  </select>
                </div>

                {/* PO/PSO alignment status */}
                <div className="flex items-center justify-between px-5 py-3">
                  <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest">PO / PSO Alignment</span>
                  <span className="flex items-center gap-1.5 text-[10px] font-mono text-attain">
                    <CheckCircle2 className="w-3 h-3" />
                    {displayPOs.length} POs · {programSpecificOutcomes.length} PSOs auto-loaded
                  </span>
                </div>

                {/* Syllabus status */}
                <div className="flex items-center justify-between px-5 py-3">
                  <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest">Syllabus</span>
                  <span className={`text-[10px] font-mono flex items-center gap-1.5 ${
                    syllabus.trim() ? "text-attain" : "text-amber-400"
                  }`}>
                    {syllabus.trim()
                      ? <><CheckCircle2 className="w-3 h-3" /> {syllabusWordCount} words ready</>
                      : <><AlertCircle className="w-3 h-3" /> Missing — add above</>}
                  </span>
                </div>
              </div>

              <div className="px-5 py-4 border-t border-white/5">
                <button
                  onClick={() => void generate()}
                  disabled={generating || !syllabus.trim()}
                  className="flex items-center gap-2 px-5 py-2.5 text-xs font-mono text-white border border-brand/40 hover:border-brand text-brand/80 hover:text-brand disabled:opacity-40 transition-colors"
                >
                  {generating ? (
                    <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</>
                  ) : (
                    <><Sparkles className="w-3.5 h-3.5" /> Generate Course Outcomes</>
                  )}
                </button>
              </div>
            </section>

            {/* ── Parsed Units Panel ── */}
            {parsedUnits.length > 0 && (
              <section className="border border-white/10">
                <button
                  onClick={() => setShowUnits(v => !v)}
                  className="w-full flex items-center justify-between px-5 py-4 hover:bg-white/[0.02] transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Layers className="w-3.5 h-3.5 text-brand/60 shrink-0" />
                    <div className="text-left">
                      <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest">Syllabus Units Detected</p>
                      <p className="text-[10px] text-white/20 mt-0.5 font-mono">{parsedUnits.length} units parsed from syllabus — used for CO coverage mapping</p>
                    </div>
                  </div>
                  {showUnits
                    ? <ChevronDown className="w-3.5 h-3.5 text-white/30 shrink-0" />
                    : <ChevronRight className="w-3.5 h-3.5 text-white/30 shrink-0" />}
                </button>
                {showUnits && (
                  <div className="border-t border-white/5 divide-y divide-white/5">
                    {parsedUnits.map((u, i) => (
                      <div key={i} className="px-5 py-3">
                        <p className="text-[10px] font-mono text-brand/70 uppercase tracking-widest">{u.unit}</p>
                        {u.topics.length > 0 && (
                          <p className="text-[11px] text-white/35 mt-1 leading-relaxed">
                            {u.topics.slice(0, 4).join(" · ")}{u.topics.length > 4 ? ` · +${u.topics.length - 4} more` : ""}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* ── Session Memory Snapshot ── */}
            {sessionSnapshot?.last_generated_at && (
              <section className="border border-white/10 bg-white/[0.01] px-5 py-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest">Last Generation Session</p>
                    <p className="text-xs text-white/55 mt-1">
                      {new Date(sessionSnapshot.last_generated_at).toLocaleString()} · Domain {String(sessionSnapshot.domain || "unknown").toUpperCase()} · {sessionSnapshot.num_cos || outcomes.length} COs
                    </p>
                  </div>
                  <History className="w-4 h-4 text-white/35 shrink-0" />
                </div>
                {sessionSnapshot?.syllabus_snippet && (
                  <p className="text-[11px] text-white/35 mt-3 leading-relaxed">
                    {String(sessionSnapshot.syllabus_snippet)}
                  </p>
                )}
              </section>
            )}

            {/* ── CO Version History ── */}
            {historySnapshots.length > 0 && (
              <section className="border border-white/10">
                <button
                  onClick={() => setShowHistory((v) => !v)}
                  className="w-full flex items-center justify-between px-5 py-4 hover:bg-white/[0.02] transition-colors"
                >
                  <div className="text-left">
                    <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest">CO Version History</p>
                    <p className="text-[10px] text-white/20 mt-0.5 font-mono">{historySnapshots.length} snapshot(s) saved before overwrite</p>
                  </div>
                  {showHistory
                    ? <ChevronDown className="w-3.5 h-3.5 text-white/30 shrink-0" />
                    : <ChevronRight className="w-3.5 h-3.5 text-white/30 shrink-0" />}
                </button>
                {showHistory && (
                  <div className="border-t border-white/5 divide-y divide-white/5">
                    {historySnapshots.slice(0, 5).map((snap: any, i: number) => (
                      <div key={`${snap.timestamp || i}`} className="px-5 py-3">
                        <p className="text-[10px] font-mono text-brand/70 uppercase tracking-widest">
                          Snapshot {i + 1} · {snap?.timestamp ? new Date(snap.timestamp).toLocaleString() : "Unknown time"}
                        </p>
                        <p className="text-[11px] text-white/40 mt-1">
                          Domain {String(snap?.domain || "unknown").toUpperCase()} · {Array.isArray(snap?.cos) ? snap.cos.length : 0} COs
                        </p>
                        {snap?.syllabus_snippet && (
                          <p className="text-[11px] text-white/30 mt-1 leading-relaxed">{String(snap.syllabus_snippet)}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* ── Unit Coverage Summary ── */}
            {coverage && coverageUnits.length > 0 && (
              <section className={`border ${coveragePct >= 80 ? "border-attain/30 bg-attain/5" : "border-amber-500/30 bg-amber-500/5"}`}>
                <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between gap-4">
                  <div>
                    <p className="text-[10px] font-mono text-white/50 uppercase tracking-widest">Unit Coverage Check</p>
                    <p className="text-xs text-white/60 mt-1">
                      {coveredUnitsCount}/{totalUnitsCount} units covered · {coveragePct.toFixed(1)}%
                    </p>
                  </div>
                  <button
                    onClick={() => void refreshCoverage()}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-white/15 text-white/45 hover:text-white hover:border-white/35 text-[10px] font-mono uppercase tracking-widest transition-colors"
                  >
                    <RefreshCw className="w-3 h-3" /> Refresh
                  </button>
                </div>
                <div className="divide-y divide-white/5">
                  {coverageUnits.slice(0, 8).map((item: any, i: number) => {
                    const name = String(item?.unit || item?.name || `Unit ${i + 1}`);
                    const ok = Boolean(item?.is_covered ?? item?.covered);
                    const coveredBy = Array.isArray(item?.covered_by) ? item.covered_by : [];
                    return (
                      <div key={`${name}-${i}`} className="px-5 py-3">
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-[11px] text-white/65 leading-relaxed">{name}</p>
                          <span className={`text-[10px] font-mono uppercase tracking-widest ${ok ? "text-attain" : "text-amber-400"}`}>
                            {ok ? "Covered" : "Needs CO"}
                          </span>
                        </div>
                        {coveredBy.length > 0 && (
                          <p className="text-[10px] text-white/30 mt-1 font-mono">By {coveredBy.join(", ")}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* ── LLM Mapping Justifications ── */}
            {Object.keys(mappingJustifications).length > 0 && (
              <section className="border border-white/10 bg-white/[0.01] px-5 py-4">
                <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest mb-2">LLM Mapping Justifications</p>
                <div className="space-y-3">
                  {Object.entries(mappingJustifications).map(([coCode, reasons]) => (
                    <div key={coCode} className="border border-white/10 bg-white/[0.01] px-3 py-2">
                      <p className="text-[10px] font-mono text-brand/70 uppercase tracking-widest mb-1">{coCode}</p>
                      <div className="space-y-1">
                        {Object.entries(reasons || {}).slice(0, 6).map(([k, v]) => (
                          <p key={`${coCode}-${k}`} className="text-[11px] text-white/45 leading-relaxed">
                            <span className="text-white/65 font-mono mr-1">{k}:</span>
                            {String(v)}
                          </p>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* ── Matrix Validation Panel ── */}
            {validation && (
              <section className={`border ${
                validation.errors.length > 0
                  ? "border-red-500/30 bg-red-500/5"
                  : validation.warnings.length > 0
                  ? "border-amber-500/30 bg-amber-500/5"
                  : "border-attain/30 bg-attain/5"
              }`}>
                <div className="px-5 py-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      {validation.errors.length > 0
                        ? <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                        : validation.warnings.length > 0
                        ? <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                        : <CheckCircle2 className="w-4 h-4 text-attain shrink-0" />}
                      <span className="text-[10px] font-mono uppercase tracking-widest text-white/50">CO–PO Matrix Validation</span>
                    </div>
                    <div className="flex items-center gap-4 text-[10px] font-mono">
                      <span className="text-white/30">Density</span>
                      <span className={`${
                        validation.matrix_density < 0.30 || validation.matrix_density > 0.60
                          ? "text-amber-400" : "text-attain"
                      }`}>
                        {(validation.matrix_density * 100).toFixed(0)}%
                        <span className="text-white/20 ml-1">(target 30–60%)</span>
                      </span>
                      <span className="text-white/30">{validation.nonzero_cells}/{validation.total_cells} cells mapped</span>
                    </div>
                  </div>

                  {validation.errors.length > 0 && (
                    <div className="space-y-1 mb-3">
                      {validation.errors.map((e, i) => (
                        <p key={i} className="text-xs text-red-400 flex items-center gap-1.5">
                          <AlertCircle className="w-3 h-3 shrink-0" /> {e}
                        </p>
                      ))}
                    </div>
                  )}
                  {validation.warnings.length > 0 && (
                    <div className="space-y-1">
                      {validation.warnings.map((w, i) => (
                        <p key={i} className="text-xs text-amber-400/80 flex items-center gap-1.5">
                          <AlertCircle className="w-3 h-3 shrink-0" /> {w}
                        </p>
                      ))}
                    </div>
                  )}
                  {validation.errors.length === 0 && validation.warnings.length === 0 && (
                    <p className="text-xs text-attain">All NBA matrix rules passed. COs are well-distributed across POs.</p>
                  )}
                </div>
              </section>
            )}

            {/* ── Faculty Confirmation Gate ── */}
            {outcomes.length > 0 && validation && !confirmed && (
              <section className="border border-brand/30 bg-brand/5 px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-[10px] font-mono text-white/40 uppercase tracking-widest mb-1">Review &amp; Confirm</p>
                    <p className="text-xs text-white/60 leading-relaxed">
                      {outcomes.length} COs generated and saved.
                      {validation.errors.length > 0
                        ? " Fix the matrix errors above before confirming."
                        : validation.warnings.length > 0
                        ? " Warnings found — review above, then confirm to proceed."
                        : " Matrix validation passed. Confirm to proceed to exam configuration."}
                    </p>
                  </div>
                  <button
                    onClick={() => setConfirmed(true)}
                    disabled={validation.errors.length > 0}
                    className="shrink-0 flex items-center gap-2 px-4 py-2 border border-attain/40 text-attain hover:border-attain text-xs font-mono uppercase tracking-widest disabled:opacity-40 transition-colors"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" /> Confirm COs
                  </button>
                </div>
              </section>
            )}

            {confirmed && (
              <div className="flex items-center justify-between gap-4 border border-attain/30 bg-attain/5 px-4 py-3">
                <div className="flex items-center gap-2 text-attain text-xs font-mono">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  COs confirmed. Next: set up CO-PO matrix.
                </div>
                <Link
                  href={`/faculty/course/${courseId}/correlations`}
                  className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 border border-attain/60 text-attain hover:border-attain hover:bg-attain/10 text-xs font-mono uppercase tracking-widest transition-colors"
                >
                  CO-PO Matrix <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            )}

            {/* ── Next Step Banner (shows right after generation) ── */}
            {justGenerated && outcomes.length > 0 && (
              <section
                ref={outcomesSectionRef}
                className="border border-brand/40 bg-gradient-to-r from-brand/10 to-brand/5 px-5 py-5 animate-pulse-once"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <CheckCircle2 className="w-4 h-4 text-brand" />
                      <span className="text-[10px] font-mono text-brand uppercase tracking-widest">
                        {outcomes.length} Course Outcomes Generated
                      </span>
                    </div>
                    <p className="text-xs text-white/50 leading-relaxed">
                      Review the COs below. Once satisfied, proceed to build the CO–PO correlation matrix.
                    </p>
                  </div>
                  <Link
                    href={`/faculty/course/${courseId}/correlations`}
                    className="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 bg-brand/20 border border-brand text-brand hover:bg-brand hover:text-white transition-all text-xs font-mono uppercase tracking-widest"
                  >
                    Next Step: CO-PO Matrix <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </section>
            )}

            {/* Generated Outcomes */}
            <section className={`border p-5 transition-colors ${justGenerated && outcomes.length > 0 ? "border-brand/30 bg-white/[0.02]" : "border-white/10 bg-white/[0.015]"}`}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-start gap-3">
                  <BookOpenCheck className="w-4 h-4 text-brand mt-0.5" />
                  <div>
                    <h2 className="text-[10px] font-mono text-white/30 uppercase tracking-widest">
                      Generated Course Outcomes ({outcomes.length})
                    </h2>
                    <p className="text-xs text-white/35 mt-1">Use regenerate for quick improvements or delete low-quality COs before proceeding.</p>
                  </div>
                </div>
              </div>

              {qualityIssues.length > 0 && (
                <div className="border border-amber-500/30 bg-amber-500/5 px-3 py-2 space-y-1 mb-4">
                  {qualityIssues.map((issue, i) => (
                    <p key={i} className="text-xs text-amber-400 flex items-center gap-1.5">
                      <AlertCircle className="w-3 h-3 shrink-0" /> {issue}
                    </p>
                  ))}
                </div>
              )}

              {outcomes.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 mb-4 text-[10px] font-mono uppercase tracking-widest">
                  {([
                    ["create", bloomBreakdown.create],
                    ["evaluate", bloomBreakdown.evaluate],
                    ["analyze", bloomBreakdown.analyze],
                    ["apply", bloomBreakdown.apply],
                    ["understand", bloomBreakdown.understand],
                    ["other", bloomBreakdown.other],
                  ] as [string, number][]).map(([level, count]) => (
                    <span key={level} className={`px-2.5 py-1 border border-white/10 ${bloomColor(level)}`}>
                      {level.charAt(0).toUpperCase() + level.slice(1)} {count}
                    </span>
                  ))}
                </div>
              )}

              {/* Backend quality warnings (LLM fallback notice, overlap, etc.) */}
              {qualityWarnings.length > 0 && (
                <div className="border border-amber-500/20 bg-amber-500/5 px-3 py-2 space-y-1 mb-4">
                  <p className="text-[10px] font-mono text-amber-400/60 uppercase tracking-widest mb-1">Backend Quality Warnings</p>
                  {qualityWarnings.map((w, i) => (
                    <p key={i} className="text-xs text-amber-400/80 flex items-center gap-1.5">
                      <AlertCircle className="w-3 h-3 shrink-0" /> {w}
                    </p>
                  ))}
                </div>
              )}

              {/* LLM vs fallback source indicator */}
              {generationSource && (
                <div className={`flex items-center gap-2 text-xs font-mono px-3 py-2 mb-4 border ${
                  generationSource === "llm"
                    ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400"
                    : "border-amber-500/20 bg-amber-500/5 text-amber-400"
                }`}>
                  {generationSource === "llm"
                    ? <><CheckCircle2 className="w-3.5 h-3.5" /> Generated by AI (LLM) — statements are course-specific</>
                    : <><AlertCircle className="w-3.5 h-3.5" /> Generated from domain defaults (LLM unavailable) — configure API key for AI generation</>}
                </div>
              )}

              {outcomes.length === 0 ? (
                <div className="py-12 text-center">
                  <Sparkles className="w-8 h-8 text-white/10 mx-auto mb-3" />
                  <p className="text-white/30 text-sm italic">
                    No course outcomes yet. Add a syllabus and click Generate.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto border border-white/10">
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-white/10 bg-white/[0.02]">
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-left w-20 px-3">Code</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-left px-3">Statement</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-center w-32 px-3">Bloom Level</th>
                        <th className="text-[10px] font-mono text-white/30 uppercase tracking-widest py-3 text-right w-28 px-3">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {outcomes.map((co: any, index: number) => (
                        <tr key={co.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                          <td className="py-4 px-3 font-mono text-sm text-brand font-medium align-top">
                            {co.code || co.co_code || `CO${index + 1}`}
                          </td>
                          <td className="py-4 px-3 text-white/80 pr-6 leading-relaxed align-top">
                            {editingId === String(co.id) ? (
                              <div className="space-y-2">
                                <textarea
                                  value={editStatement}
                                  onChange={(e) => setEditStatement(e.target.value)}
                                  rows={3}
                                  className="w-full bg-transparent border border-white/20 p-2 text-white text-xs placeholder-white/20 focus:outline-none focus:border-white/40 resize-y"
                                />
                                <div className="flex items-center gap-2">
                                  <span className="text-[10px] font-mono text-white/35 uppercase tracking-widest">Bloom</span>
                                  <select
                                    value={editBloom}
                                    onChange={(e) => setEditBloom(e.target.value)}
                                    className="bg-transparent border border-white/20 px-2 py-1 text-xs text-white focus:outline-none"
                                  >
                                    {["remember", "understand", "apply", "analyze", "evaluate", "create"].map((level) => (
                                      <option key={level} value={level} className="bg-[#0F172A]">{level}</option>
                                    ))}
                                  </select>
                                </div>
                              </div>
                            ) : (
                              <>{co.statement || co.co_statement || co.description || "—"}</>
                            )}
                          </td>
                          <td className="py-4 px-3 text-center align-top">
                            <span className={`inline-flex items-center justify-center px-2 py-1 border text-xs font-mono capitalize ${bloomColor(co.bloom_level)}`}>
                              {editingId === String(co.id) ? editBloom : (co.bloom_level || "—")}
                            </span>
                          </td>
                          <td className="py-4 px-3 text-right align-top">
                            <div className="flex items-center justify-end gap-3">
                              {editingId === String(co.id) ? (
                                <>
                                  <button
                                    onClick={() => void saveInlineEdit()}
                                    disabled={editSaving || !editStatement.trim()}
                                    title="Save CO statement"
                                    className="text-attain hover:text-attain/80 transition-colors disabled:opacity-40 text-[10px] font-mono uppercase tracking-widest"
                                  >
                                    {editSaving ? "Saving..." : "Save"}
                                  </button>
                                  <button
                                    onClick={() => cancelInlineEdit()}
                                    disabled={editSaving}
                                    title="Cancel edit"
                                    className="text-white/35 hover:text-white transition-colors disabled:opacity-40 text-[10px] font-mono uppercase tracking-widest"
                                  >
                                    Cancel
                                  </button>
                                </>
                              ) : (
                                <button
                                  onClick={() => startInlineEdit(co)}
                                  title="Edit statement"
                                  className="text-white/30 hover:text-white transition-colors"
                                >
                                  <Pencil className="w-3.5 h-3.5" />
                                </button>
                              )}
                              <button
                                onClick={() => void openItemHistory(co)}
                                disabled={editingId === String(co.id)}
                                title="Per-CO version history / rollback"
                                className="text-white/30 hover:text-white transition-colors disabled:opacity-40"
                              >
                                <History className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => void regenerate(String(co.id))}
                                disabled={regeneratingId === String(co.id) || editingId === String(co.id)}
                                title="Regenerate this CO"
                                className="text-white/30 hover:text-white transition-colors disabled:opacity-40"
                              >
                                {regeneratingId === String(co.id)
                                  ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                  : <RefreshCw className="w-3.5 h-3.5" />
                                }
                              </button>
                              <button
                                onClick={() => void deleteCO(String(co.id))}
                                disabled={deletingId === String(co.id) || editingId === String(co.id)}
                                title="Delete this CO"
                                className="text-red-400/40 hover:text-red-400 transition-colors disabled:opacity-40"
                              >
                                {deletingId === String(co.id)
                                  ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                  : <Trash2 className="w-3.5 h-3.5" />
                                }
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {outcomes.length > 0 && (
                <div className="mt-4 flex items-center justify-between gap-3">
                  <p className="text-xs text-white/35 inline-flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5" /> Map each CO to POs and PSOs after finalising outcomes.
                  </p>
                  <Link
                    href={`/faculty/course/${courseId}/correlations`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-brand/40 text-brand hover:border-brand hover:text-white text-xs font-mono uppercase tracking-widest transition-colors"
                  >
                    Set up CO-PO Matrix <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </AccessGate>
  );
}

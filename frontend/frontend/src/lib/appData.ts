// ============================================================
// OBE AI System — Central Data Store (Spec v2.1 compliant)
// All logic runs in browser, no backend needed.
// ============================================================

// ─── COURSES ────────────────────────────────────────────────
export const COURSES = [
  { id: "cs301", code: "CS301", name: "Database Management Systems", dept: "Computer Science", semester: 5, credits: 4, students: 60, examType: "Theory" },
  { id: "cs401", code: "CS401", name: "Machine Learning", dept: "Computer Science", semester: 7, credits: 4, students: 48, examType: "Theory" },
  { id: "ec201", code: "EC201", name: "Digital Signal Processing", dept: "Electronics", semester: 4, credits: 3, students: 55, examType: "Theory + Practical" },
  { id: "me301", code: "ME301", name: "Thermodynamics", dept: "Mechanical", semester: 5, credits: 4, students: 71, examType: "Theory" },
  { id: "cs501", code: "CS501", name: "Compiler Design", dept: "Computer Science", semester: 6, credits: 3, students: 43, examType: "Theory" },
];

// ─── EXAM TYPES (Spec Section 3.1) ──────────────────────────
export const EXAM_TYPES = [
  { code: "T1", name: "Unit Test 1",    maxMarks: 20,  weightage: "CIE", group: "CIE", scaledMax: 20 },
  { code: "T2", name: "Unit Test 2",    maxMarks: 20,  weightage: "CIE", group: "CIE", scaledMax: 20 },
  { code: "T3", name: "Assignment",     maxMarks: 10,  weightage: "CIE", group: "CIE", scaledMax: 10 },
  { code: "T4", name: "Quiz / Viva",    maxMarks: 10,  weightage: "CIE", group: "CIE", scaledMax: 10 },
  { code: "T5", name: "Model Exam",     maxMarks: 100, weightage: "CIE", group: "CIE", scaledMax: 20 },
  { code: "SEE", name: "End Semester",  maxMarks: 100, weightage: "SEE", group: "SEE", scaledMax: 100 },
];
export const CIE_WEIGHT = 0.40;
export const SEE_WEIGHT = 0.60;

// ─── BLOOM'S TAXONOMY (Spec Section 4.2 — Full Verb List) ───
export const BLOOMS_LEVELS = [
  {
    level: 1, code: "L1", name: "Remember", color: "text-white/50",
    verbs: ["define","list","name","recall","state","identify","recognise","label","memorise"],
  },
  {
    level: 2, code: "L2", name: "Understand", color: "text-brand",
    verbs: ["explain","describe","summarise","interpret","classify","paraphrase","illustrate","compare"],
  },
  {
    level: 3, code: "L3", name: "Apply", color: "text-aurora",
    verbs: ["apply","use","solve","implement","compute","calculate","demonstrate","execute","construct"],
  },
  {
    level: 4, code: "L4", name: "Analyse", color: "text-insight",
    verbs: ["analyse","analyze","differentiate","examine","break down","categorise","contrast","investigate"],
  },
  {
    level: 5, code: "L5", name: "Evaluate", color: "text-alert",
    verbs: ["evaluate","judge","justify","critique","assess","defend","recommend","prioritise"],
  },
  {
    level: 6, code: "L6", name: "Create", color: "text-attain",
    verbs: ["design","develop","formulate","plan","generate","produce","invent","compose"],
  },
];

export function detectBloomsLevel(questionText: string): { level: number; code: string; name: string; verb: string } {
  const lower = questionText.toLowerCase();
  // Check from highest to lowest priority
  for (const bl of [...BLOOMS_LEVELS].reverse()) {
    for (const verb of bl.verbs) {
      if (lower.includes(verb)) {
        return { level: bl.level, code: bl.code, name: bl.name, verb };
      }
    }
  }
  return { level: 2, code: "L2", name: "Understand", verb: "explain" };
}

// ─── COURSE OUTCOMES ─────────────────────────────────────────
// Each CO stores CIE%, SEE%, and computed final% per spec formula
export type CO = {
  co: string;
  desc: string;
  bloom: string;
  bloomCode: string;
  ciePct: number;   // CIE CO Attainment %
  seePct: number;   // SEE CO Attainment %
  pct: number;      // Final = CIE*0.4 + SEE*0.6
};

function finalPct(cie: number, see: number) {
  return Math.round(cie * CIE_WEIGHT + see * SEE_WEIGHT);
}

export const COURSE_COS: Record<string, CO[]> = {
  cs301: [
    { co: "CO1", desc: "Design ER diagrams and relational schemas",            bloom: "Create",   bloomCode: "L6", ciePct: 70, seePct: 63, pct: finalPct(70,63) },
    { co: "CO2", desc: "Apply normalization to eliminate data redundancy",      bloom: "Apply",    bloomCode: "L3", ciePct: 75, seePct: 70, pct: finalPct(75,70) },
    { co: "CO3", desc: "Formulate SQL queries using relational algebra",        bloom: "Apply",    bloomCode: "L3", ciePct: 55, seePct: 50, pct: finalPct(55,50) },
    { co: "CO4", desc: "Analyze indexing strategies and query optimization",    bloom: "Analyse",  bloomCode: "L4", ciePct: 65, seePct: 60, pct: finalPct(65,60) },
    { co: "CO5", desc: "Implement transaction management and ACID properties",  bloom: "Apply",    bloomCode: "L3", ciePct: 45, seePct: 40, pct: finalPct(45,40) },
    { co: "CO6", desc: "Evaluate concurrency control and recovery mechanisms",  bloom: "Evaluate", bloomCode: "L5", ciePct: 68, seePct: 62, pct: finalPct(68,62) },
  ],
  cs401: [
    { co: "CO1", desc: "Understand ML algorithms and mathematical foundations", bloom: "Understand", bloomCode: "L2", ciePct: 85, seePct: 80, pct: finalPct(85,80) },
    { co: "CO2", desc: "Apply supervised learning algorithms",                  bloom: "Apply",      bloomCode: "L3", ciePct: 80, seePct: 75, pct: finalPct(80,75) },
    { co: "CO3", desc: "Analyse model performance and apply regularization",    bloom: "Analyse",    bloomCode: "L4", ciePct: 70, seePct: 65, pct: finalPct(70,65) },
    { co: "CO4", desc: "Implement neural networks for classification tasks",    bloom: "Create",     bloomCode: "L6", ciePct: 62, seePct: 58, pct: finalPct(62,58) },
    { co: "CO5", desc: "Evaluate ensemble methods and boosting techniques",     bloom: "Evaluate",   bloomCode: "L5", ciePct: 72, seePct: 68, pct: finalPct(72,68) },
  ],
  ec201: [
    { co: "CO1", desc: "Recall fundamental DSP concepts and transforms",        bloom: "Remember", bloomCode: "L1", ciePct: 68, seePct: 63, pct: finalPct(68,63) },
    { co: "CO2", desc: "Apply DFT and FFT for signal processing",               bloom: "Apply",    bloomCode: "L3", ciePct: 62, seePct: 55, pct: finalPct(62,55) },
    { co: "CO3", desc: "Design FIR and IIR digital filters",                    bloom: "Create",   bloomCode: "L6", ciePct: 55, seePct: 50, pct: finalPct(55,50) },
    { co: "CO4", desc: "Analyse spectral characteristics of signals",           bloom: "Analyse",  bloomCode: "L4", ciePct: 64, seePct: 60, pct: finalPct(64,60) },
    { co: "CO5", desc: "Implement real-time DSP systems",                       bloom: "Apply",    bloomCode: "L3", ciePct: 70, seePct: 65, pct: finalPct(70,65) },
    { co: "CO6", desc: "Evaluate filter design techniques comparatively",       bloom: "Evaluate", bloomCode: "L5", ciePct: 61, seePct: 56, pct: finalPct(61,56) },
  ],
};

// ─── AY HISTORY (Spec Section 8) ─────────────────────────────
export const AY_HISTORY: Record<string, { ay: string; locked: boolean; cos: Record<string, number> }[]> = {
  cs301: [
    { ay: "2022-23", locked: true,  cos: { CO1: 58, CO2: 68, CO3: 48, CO4: 60, CO5: 38, CO6: 55 } },
    { ay: "2023-24", locked: true,  cos: { CO1: 62, CO2: 70, CO3: 50, CO4: 64, CO5: 40, CO6: 60 } },
    { ay: "2024-25", locked: false, cos: { CO1: 65, CO2: 72, CO3: 52, CO4: 62, CO5: 42, CO6: 64 } },
  ],
};

export function getTrend(current: number, prev: number): { arrow: string; label: string; color: string } {
  const diff = current - prev;
  if (diff >= 3) return { arrow: "↑", label: "Improving",  color: "text-attain" };
  if (diff <= -3) return { arrow: "↓", label: "Declining",  color: "text-alert"  };
  return              { arrow: "→", label: "Stable",      color: "text-white/50" };
}

// A CO is a "Curricular Gap" if it was Level 1 or Level 2 in two or more AYs
export function getCurricularGaps(courseId: string): string[] {
  const history = AY_HISTORY[courseId];
  if (!history || history.length < 2) return [];
  const gaps: string[] = [];
  const coKeys = Object.keys(history[0].cos);
  coKeys.forEach(co => {
    const lowCount = history.filter(h => h.cos[co] < 60).length;
    if (lowCount >= 2) gaps.push(co);
  });
  return gaps;
}

// ─── PROGRAM OUTCOMES ────────────────────────────────────────
export const PROGRAM_OUTCOMES = [
  { id: "PO1",  name: "Engineering Knowledge" },
  { id: "PO2",  name: "Problem Analysis" },
  { id: "PO3",  name: "Design / Dev of Solutions" },
  { id: "PO4",  name: "Conduct Investigations" },
  { id: "PO5",  name: "Modern Tool Usage" },
  { id: "PO6",  name: "Engineer & Society" },
  { id: "PO7",  name: "Ethics" },
  { id: "PO8",  name: "Communication" },
  { id: "PO9",  name: "Individual & Teamwork" },
  { id: "PO10", name: "Project Management" },
  { id: "PO11", name: "Lifelong Learning" },
  { id: "PO12", name: "Environment & Sustainability" },
];

export const PROGRAM_SPECIFIC_OUTCOMES = [
  { id: "PSO1", name: "Algorithm Design" },
  { id: "PSO2", name: "Software Development" },
  { id: "PSO3", name: "Professional Practice" },
];

// ─── CO–PO–PSO CORRELATION MATRIX (Spec 2.3) ─────────────────
// Values: 1=Low, 2=Medium, 3=High, absent=no correlation
export const CO_PO_MAPPING: Record<string, Record<string, number>> = {
  CO1: { PO1: 3, PO2: 2, PSO2: 3 },
  CO2: { PO1: 3, PO2: 3, PO3: 2, PSO1: 3, PSO2: 1 },
  CO3: { PO1: 2, PO2: 3, PO3: 3, PO4: 2, PSO1: 3, PSO2: 2 },
  CO4: { PO2: 2, PO3: 3, PO4: 3, PO5: 2, PSO1: 2, PSO2: 3 },
  CO5: { PO3: 2, PO4: 3, PO5: 3, PSO1: 1, PSO2: 3 },
  CO6: { PO2: 3, PO4: 2, PO7: 1, PSO3: 2 },
};

// ─── ATTAINMENT LEVEL — SPEC CORRECT (Section 3.3) ──────────
// Level 3: ≥ 60% | Level 2: 40–59% | Level 1: < 40%
export function getAttainmentLevel(pct: number): { level: number; label: string; color: string; bg: string } {
  if (pct >= 60) return { level: 3, label: "Level 3", color: "text-attain", bg: "bg-attain/10" };
  if (pct >= 40) return { level: 2, label: "Level 2", color: "text-brand",  bg: "bg-brand/10"  };
  return               { level: 1, label: "Level 1", color: "text-alert",  bg: "bg-alert/10"  };
}

// ─── PO/PSO ATTAINMENT (Spec 7.1) ────────────────────────────
export function computePOAttainment(
  cos: Array<{ co: string; pct: number }>,
  mapping: Record<string, Record<string, number>> = CO_PO_MAPPING
): Record<string, { pct: number; contributions: { co: string; weight: number; coAtt: number }[] }> {
  const weightedSum: Record<string, number> = {};
  const totalWeights: Record<string, number> = {};
  const contributions: Record<string, { co: string; weight: number; coAtt: number }[]> = {};

  cos.forEach(({ co, pct }) => {
    const mappings = mapping[co] || {};
    Object.entries(mappings).forEach(([po, weight]) => {
      weightedSum[po] = (weightedSum[po] || 0) + pct * weight;
      totalWeights[po] = (totalWeights[po] || 0) + weight;
      if (!contributions[po]) contributions[po] = [];
      contributions[po].push({ co, weight, coAtt: pct });
    });
  });

  const result: Record<string, { pct: number; contributions: { co: string; weight: number; coAtt: number }[] }> = {};
  Object.keys(weightedSum).forEach(po => {
    result[po] = {
      pct: Math.round(weightedSum[po] / totalWeights[po]),
      contributions: contributions[po] || [],
    };
  });
  return result;
}

// ─── COURSE HEALTH ───────────────────────────────────────────
export function getCourseHealth(cos: Array<{ pct: number }>): number {
  if (!cos.length) return 0;
  return Math.round(cos.reduce((a, c) => a + c.pct, 0) / cos.length);
}

// ─── EXAM INSTANCES ──────────────────────────────────────────
export const EXAM_INSTANCES: Record<string, Array<{ id: string; name: string; maxMarks: number; questions: number; type: string; group: string }>> = {
  cs301: [
    { id: "t1",  name: "T1 — Unit Test 1", maxMarks: 20,  questions: 4, type: "Formative", group: "CIE" },
    { id: "t2",  name: "T2 — Unit Test 2", maxMarks: 20,  questions: 4, type: "Formative", group: "CIE" },
    { id: "t3",  name: "T3 — Assignment",  maxMarks: 10,  questions: 2, type: "Formative", group: "CIE" },
    { id: "t4",  name: "T4 — Quiz/Viva",   maxMarks: 10,  questions: 5, type: "Formative", group: "CIE" },
    { id: "t5",  name: "T5 — Model Exam",  maxMarks: 100, questions: 10, type: "Formative", group: "CIE" },
    { id: "see", name: "SEE — End Sem",    maxMarks: 100, questions: 10, type: "Summative", group: "SEE" },
  ],
};

// ─── STUDENT MARKS ───────────────────────────────────────────
export type StudentMark = {
  name: string;
  roll: string;
  marks: Record<string, number | "">;
  eitherOrChoices?: Record<string, "a" | "b">; // e.g. { "Q3": "a", "Q4": "b" }
};

export const STUDENT_MARKS: Record<string, StudentMark[]> = {
  cs301: [
    { name: "Aarav Sharma",  roll: "21CS001", marks: { T1: 16, T2: 18, T3: 8, T4: 7, T5: 75, SEE: 63 }, eitherOrChoices: { "Q3": "a", "Q4": "a" } },
    { name: "Priya Verma",   roll: "21CS002", marks: { T1: 14, T2: 16, T3: 9, T4: 8, T5: 70, SEE: 71 }, eitherOrChoices: { "Q3": "b", "Q4": "a" } },
    { name: "Rahul Nair",    roll: "21CS003", marks: { T1: 10, T2: 12, T3: 6, T4: 5, T5: 55, SEE: 55 }, eitherOrChoices: { "Q3": "a", "Q4": "b" } },
    { name: "Sneha Patel",   roll: "21CS004", marks: { T1: 18, T2: 19, T3: 10, T4: 9, T5: 88, SEE: 91 }, eitherOrChoices: { "Q3": "a", "Q4": "a" } },
    { name: "Karan Mehta",   roll: "21CS005", marks: { T1: 13, T2: 15, T3: 7, T4: 6, T5: 67, SEE: 69 }, eitherOrChoices: { "Q3": "b", "Q4": "b" } },
    { name: "Divya Rao",     roll: "21CS006", marks: { T1: 12, T2: 14, T3: 8, T4: 7, T5: 60, SEE: 58 }, eitherOrChoices: { "Q3": "a", "Q4": "a" } },
    { name: "Arjun Singh",   roll: "21CS007", marks: { T1:  8, T2: 10, T3: 5, T4: 4, T5: 45, SEE: 48 }, eitherOrChoices: { "Q3": "b", "Q4": "b" } },
    { name: "Neha Gupta",    roll: "21CS008", marks: { T1: 15, T2: 17, T3: 9, T4: 8, T5: 72, SEE: 74 }, eitherOrChoices: { "Q3": "a", "Q4": "a" } },
    { name: "Vikram Iyer",   roll: "21CS009", marks: { T1: 11, T2: 13, T3: 7, T4: 6, T5: 58, SEE: 60 }, eitherOrChoices: { "Q3": "b", "Q4": "a" } },
    { name: "Pooja Desai",   roll: "21CS010", marks: { T1: 17, T2: 18, T3: 9, T4: 8, T5: 80, SEE: 78 }, eitherOrChoices: { "Q3": "a", "Q4": "b" } },
  ],
};

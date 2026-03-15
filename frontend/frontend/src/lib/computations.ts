// ============================================================
// OBE AI System — Pure Computation Engine (No side effects)
// All attainment calculations per the Spec formula
// ============================================================

export const CIE_WEIGHT = 0.40;
export const SEE_WEIGHT = 0.60;

// ─── ATTAINMENT LEVEL THRESHOLDS ────────────────────────────
export type AttainmentThresholds = {
  level3: number; // e.g. 60 → ≥60% is Level 3
  level2: number; // e.g. 40 → ≥40% is Level 2
};

export const DEFAULT_THRESHOLDS: AttainmentThresholds = {
  level3: 60,
  level2: 40,
};

export function getAttainmentLevel(pct: number, thresholds = DEFAULT_THRESHOLDS) {
  if (pct >= thresholds.level3) return { level: 3, label: "Level 3", color: "text-attain", bg: "bg-attain/10", badgeColor: "border-attain/30 text-attain bg-attain/10" };
  if (pct >= thresholds.level2) return { level: 2, label: "Level 2", color: "text-brand",  bg: "bg-brand/10",  badgeColor: "border-brand/30 text-brand bg-brand/10"   };
  return                               { level: 1, label: "Level 1", color: "text-alert",  bg: "bg-alert/10",  badgeColor: "border-alert/30 text-alert bg-alert/10"   };
}

// ─── BLOOM'S DETECTION ──────────────────────────────────────
export const BLOOMS_LEVELS = [
  { level: 1, code: "L1", name: "Remember",  verbs: ["define","list","name","recall","state","identify","recognise","label","memorise","enumerate","repeat","record"] },
  { level: 2, code: "L2", name: "Understand", verbs: ["explain","describe","summarise","interpret","classify","paraphrase","illustrate","compare","discuss","review","translate"] },
  { level: 3, code: "L3", name: "Apply",      verbs: ["apply","use","solve","implement","compute","calculate","demonstrate","execute","construct","operate","manipulate","practice"] },
  { level: 4, code: "L4", name: "Analyse",    verbs: ["analyse","analyze","differentiate","examine","break down","categorise","contrast","investigate","dissect","distinguish","inspect"] },
  { level: 5, code: "L5", name: "Evaluate",   verbs: ["evaluate","judge","justify","critique","assess","defend","recommend","prioritise","argue","decide","select","value"] },
  { level: 6, code: "L6", name: "Create",     verbs: ["design","develop","formulate","plan","generate","produce","invent","compose","synthesize","construct","devise","compile"] },
];

export function detectBloomsLevel(text: string) {
  const lower = text.toLowerCase();
  for (const bl of [...BLOOMS_LEVELS].reverse()) {
    for (const verb of bl.verbs) {
      if (lower.includes(verb)) return { level: bl.level, code: bl.code, name: bl.name, verb };
    }
  }
  return { level: 2, code: "L2", name: "Understand", verb: "explain" };
}

// ─── CO ATTAINMENT FROM MARKS ────────────────────────────────
// Spec: students who score >= target% of max marks in questions
// mapped to a CO counts as "attained" for that CO

export type QuestionMapping = {
  qno: string;
  co: string;       // e.g. "CO1"
  maxMarks: number;
  isEitherOr?: boolean;
  eitherOrGroup?: string; // e.g. "Q3" — both Q3a/Q3b share a group
};

export type StudentMarkRow = {
  roll: string;
  name: string;
  marks: Record<string, number | "">; // qno → mark
  eitherOrChoices?: Record<string, "a" | "b">;
};

export function computeCOAttainmentFromMarks(
  students: StudentMarkRow[],
  questions: QuestionMapping[],
  targetPct: number = 50, // threshold: student must score >=50% of a q's max to "attain" that CO
  thresholds: AttainmentThresholds = DEFAULT_THRESHOLDS
): Record<string, { attained: number; total: number; pct: number }> {
  // Group questions by CO
  const coQuestions: Record<string, QuestionMapping[]> = {};
  for (const q of questions) {
    if (!coQuestions[q.co]) coQuestions[q.co] = [];
    coQuestions[q.co].push(q);
  }

  const result: Record<string, { attained: number; total: number; pct: number }> = {};

  for (const [co, qs] of Object.entries(coQuestions)) {
    let attained = 0;
    for (const student of students) {
      // For each student, check if they attained all questions mapped to this CO
      let studentAttainsCO = true;
      for (const q of qs) {
        const mark = student.marks[q.qno];
        if (mark === "" || mark === undefined) { studentAttainsCO = false; break; }
        const pct = (Number(mark) / q.maxMarks) * 100;
        if (pct < targetPct) { studentAttainsCO = false; break; }
      }
      if (studentAttainsCO) attained++;
    }
    const total = students.length;
    result[co] = { attained, total, pct: total > 0 ? Math.round((attained / total) * 100) : 0 };
  }

  return result;
}

// ─── CIE TOTAL CALCULATION ────────────────────────────────────
// T1(20) + T2(20) + T3(10) + T4(10) + T5(100→20 scaled) = 80 max
// Then CIE best-of-two T1/T2 logic is simplified here
export function computeCIETotal(marks: Record<string, number | "">): number {
  const t1 = Number(marks.T1 || 0);
  const t2 = Number(marks.T2 || 0);
  const t3 = Number(marks.T3 || 0);
  const t4 = Number(marks.T4 || 0);
  const t5Raw = Number(marks.T5 || 0);
  const t5 = Math.round((t5Raw / 100) * 20); // Scale T5 100→20
  // Best of T1, T2 (spec: only best 2 of T tests count toward CIE)
  const scores = [t1, t2].sort((a, b) => b - a);
  return scores[0] + scores[1] + t3 + t4 + t5; // max = 20+20+10+10+20 = 80
}

export function computeSEEScaled(seeMark: number): number {
  return Math.round((seeMark / 100) * 100); // SEE is out of 100
}

export function computeFinalAttainment(ciePct: number, seePct: number): number {
  return Math.round(ciePct * CIE_WEIGHT + seePct * SEE_WEIGHT);
}

// ─── PO/PSO ATTAINMENT ────────────────────────────────────────
export function computePOAttainment(
  cos: Array<{ co: string; pct: number }>,
  mapping: Record<string, Record<string, number>>
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

export function getTrend(current: number, prev: number) {
  const diff = current - prev;
  if (diff >= 3) return { arrow: "↑", label: "Improving", color: "text-attain" };
  if (diff <= -3) return { arrow: "↓", label: "Declining", color: "text-alert" };
  return              { arrow: "→", label: "Stable",     color: "text-white/50" };
}

export function getCourseHealth(cos: Array<{ pct: number }>): number {
  if (!cos.length) return 0;
  return Math.round(cos.reduce((a, c) => a + c.pct, 0) / cos.length);
}

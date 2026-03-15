// ============================================================
// OBE AI System — Master Data Store (Frontend-only, persisted)
// Uses Zustand + localStorage. No backend needed.
// ============================================================
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Role } from './authStore';

// ─── TYPE DEFINITIONS ────────────────────────────────────────

export type CourseRecord = {
  id: string;
  code: string;
  name: string;
  dept: string;
  semester: number;
  credits: number;
  students: number;
  studentRolls?: string[];
  examType: string;
  facultyId: string;
  leadId?: string;
  section?: string;     // A/B/C for multi-section courses
  mappings?: Record<string, Record<string, number>>;
};

export type CODefinition = {
  co: string;            // "CO1", "CO2"…
  desc: string;
  bloom: string;         // "Apply"
  bloomCode: string;     // "L3"
};

export type QuestionDef = {
  qno: string;           // "Q1", "Q3a"
  co: string;
  maxMarks: number;
  text?: string;
  bloomCode?: string;
  isEitherOr?: boolean;
  eitherOrGroup?: string;
  type?: "compulsory" | "either-or" | "optional";
  pairId?: string;
};

export type StudentMarkRow = {
  roll: string;
  name: string;
  marks: Record<string, number | "">;           // qno → mark
  eitherOrChoices?: Record<string, "a" | "b">;  // group → choice
};

export type ExamConfig = {
  id: string;   // "t1", "t2", "see"
  name: string;
  maxMarks: number;
  date?: string;
  weightage?: number;
  group: "CIE" | "SEE";
  questions: QuestionDef[];
  status: "draft" | "locked";
};

export type ExamQuestion = QuestionDef;
export type StudentMark = StudentMarkRow;

export type MarksSubmission = {
  courseId: string;
  examId: string;
  students: StudentMark[];
  status: "draft" | "pending" | "approved" | "returned";
  submittedAt?: string;
  approvedBy?: string;
  approvedAt?: string;   // ISO timestamp when lead approved — used for grievance deadline
  returnReason?: string;
  leadComment?: string;
  overrideReason?: string;
  history?: {
    id: string;
    action: "submitted" | "approved" | "returned" | "override";
    by: string;
    role: string;
    at: string;
    comment?: string;
  }[];
};

export type UserRecord = {
  id: string;
  name: string;
  email: string;
  password: string;
  employeeId: string;
  roles: Role[];
  dept: string;
  designation: string;
  status: "active" | "inactive";
  joinedAt: string;
  lastLogin?: string;   // ISO timestamp
  firstLogin?: boolean;
  phone?: string;
  alsoLead?: boolean;   // dual-role: faculty who is also a lead
};

export type AYConfig = {
  ay: string;           // "2024-25"
  status: "active" | "locked" | "archived";
  startDate: string;
  endDate: string;
  marksDeadline: string;
  coLockDeadline: string;
  poDeadline: string;
  lockedBy?: string;
  lockedOn?: string;
};

export type AYHistoryRecord = AYConfig;

export type ThresholdConfig = {
  level3: number;      // ≥ this → Level 3
  level2: number;      // ≥ this → Level 2
  level1: number;      // < level2 → Level 1
  targetPassPct: number;
  cieWeight: number;
  seeWeight: number;
  absentPolicy: "include" | "exclude";
  minCOs: number;
  maxCOs: number;
};

export type COLibrarySet = {
  id: string;
  name: string;
  dept: string;
  courseCode: string;
  regulation: string;
  bloomCode: string;
  cos: { co: string; desc: string; bloomCode: string; poMaps?: string }[];
  version: number;
  status: "active" | "archived";
  createdAt: string;
  updatedAt: string;
};

export type PODefinition = {
  id: string;       // "PO1"…"PO12"
  name: string;
  statement: string;
  category: "Technical" | "Professional" | "Social";
  regulation: string;
  version: number;
};

export type PSODefinition = {
  id: string;       // "PSO1"…
  dept: string;
  name: string;
  statement: string;
  regulation: string;
  version: number;
};

export type FacultyNotification = {
  id: string;
  type: "critical" | "success" | "reminder" | "system";
  title: string;
  message: string;
  timestamp: string;
  link: string;
  read: boolean;
  userId: string;
};

export type AuditEntry = {
  id: string;
  type: "login" | "login_fail" | "co_generate" | "marks" | "approval" | "override" | "system" | "user" | "ay_lock" | "error";
  userId: string;
  role: string;
  action: string;
  ip: string;
  timestamp: string;
  result?: "success" | "failure";
  errorType?: string;
};

export type Grievance = {
  id: string;
  studentRoll: string;
  courseId: string;
  examId: string;
  qno: string;
  text: string;
  status: "pending" | "under_review" | "resolved_unchanged" | "resolved_updated" | "rejected";
  submittedAt: string;
  resolution?: string;
  evidenceFileName?: string;
  updatedMarks?: number;
};

// ─── DEFAULT SEED DATA ────────────────────────────────────────

const DEFAULT_AY_HISTORY: AYHistoryRecord[] = [];

const DEFAULT_SEED_AUDIT: AuditEntry[] = [];

const DEFAULT_USERS: UserRecord[] = [];

const DEFAULT_COURSES: CourseRecord[] = [];

const DEFAULT_COS: Record<string, CODefinition[]> = {};

const DEFAULT_EXAM_CONFIGS: Record<string, ExamConfig[]> = {};

const DEFAULT_MARKS: Record<string, MarksSubmission[]> = {};

const DEFAULT_AY: AYConfig = {
  ay: "2024-25",
  status: "active",
  startDate: "2024-07-15",
  endDate: "2025-04-30",
  marksDeadline: "2024-11-30",
  coLockDeadline: "2024-12-10",
  poDeadline: "2024-12-20",
};

const DEFAULT_THRESHOLDS: ThresholdConfig = {
  level3: 60,
  level2: 40,
  level1: 0,
  targetPassPct: 50,
  cieWeight: 40,
  seeWeight: 60,
  absentPolicy: "include",
  minCOs: 4,
  maxCOs: 6,
};

const DEFAULT_CO_LIBRARY: COLibrarySet[] = [];

const DEFAULT_PO_DEFINITIONS: PODefinition[] = [
  { id: "PO1",  name: "Engineering Knowledge",        regulation: "R21", version: 1, category: "Technical",     statement: "Apply the knowledge of mathematics, science, engineering fundamentals, and an engineering specialization to the solution of complex engineering problems." },
  { id: "PO2",  name: "Problem Analysis",             regulation: "R21", version: 1, category: "Technical",     statement: "Identify, formulate, review research literature, and analyze complex engineering problems reaching substantiated conclusions using first principles of mathematics, natural sciences, and engineering sciences." },
  { id: "PO3",  name: "Design/Development of Solutions", regulation: "R21", version: 1, category: "Technical", statement: "Design solutions for complex engineering problems and design system components or processes that meet the specified needs with appropriate consideration for the public health and safety, and the cultural, societal, and environmental considerations." },
  { id: "PO4",  name: "Conduct Investigations",       regulation: "R21", version: 1, category: "Technical",     statement: "Use research-based knowledge and research methods including design of experiments, analysis and interpretation of data, and synthesis of the information to provide valid conclusions." },
  { id: "PO5",  name: "Modern Tool Usage",            regulation: "R21", version: 1, category: "Technical",     statement: "Create, select, and apply appropriate techniques, resources, and modern engineering and IT tools including prediction and modeling to complex engineering activities with an understanding of the limitations." },
  { id: "PO6",  name: "Engineer & Society",           regulation: "R21", version: 1, category: "Social",        statement: "Apply reasoning informed by the contextual knowledge to assess societal, health, safety, legal and cultural issues and the consequent responsibilities relevant to the professional engineering practice." },
  { id: "PO7",  name: "Environment & Sustainability", regulation: "R21", version: 1, category: "Social",        statement: "Understand the impact of the professional engineering solutions in societal and environmental contexts, and demonstrate the knowledge of, and need for sustainable development." },
  { id: "PO8",  name: "Ethics",                       regulation: "R21", version: 1, category: "Professional",  statement: "Apply ethical principles and commit to professional ethics and responsibilities and norms of the engineering practice." },
  { id: "PO9",  name: "Individual & Teamwork",        regulation: "R21", version: 1, category: "Professional",  statement: "Function effectively as an individual, and as a member or leader in diverse teams, and in multidisciplinary settings." },
  { id: "PO10", name: "Communication",                regulation: "R21", version: 1, category: "Professional",  statement: "Communicate effectively on complex engineering activities with the engineering community and with society at large, such as, being able to comprehend and write effective reports and design documentation." },
  { id: "PO11", name: "Project Management",           regulation: "R21", version: 1, category: "Professional",  statement: "Demonstrate knowledge and understanding of the engineering and management principles and apply these to one's own work, as a member and leader in a team, to manage projects and in multidisciplinary environments." },
  { id: "PO12", name: "Lifelong Learning",            regulation: "R21", version: 1, category: "Professional",  statement: "Recognize the need for, and have the preparation and ability to engage in independent and life-long learning in the broadest context of technological change." },
];

const DEFAULT_PSO_DEFINITIONS: PSODefinition[] = [
  { id: "PSO1", dept: "CSE", name: "Algorithm Design",      regulation: "R21", version: 1, statement: "Specify, design, develop, test and maintain usable software systems using modern software engineering principles." },
  { id: "PSO2", dept: "CSE", name: "Software Development",  regulation: "R21", version: 1, statement: "Use modern network and security engineering techniques for business-scale IT infrastructure and AI/ML solutions." },
  { id: "PSO3", dept: "CSE", name: "Professional Practice", regulation: "R21", version: 1, statement: "Apply professional ethics and contribute to society through computing innovations and research." },
];

export const CO_PO_MAPPING: Record<string, Record<string, number>> = {};

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

// ─── STORE INTERFACE ─────────────────────────────────────────

interface DataState {
  // Data
  users: UserRecord[];
  courses: CourseRecord[];
  cos: Record<string, CODefinition[]>;           // courseId → CO[]
  coPOMappings: Record<string, Record<string, Record<string, number>>>; // courseId → CO → PO/PSO → weight
  examConfigs: Record<string, ExamConfig[]>;     // courseId → ExamConfig[]
  submissions: Record<string, MarksSubmission[]>;// courseId → MarksSubmission[]
  ay: AYConfig;
  thresholds: ThresholdConfig;
  coLibrary: COLibrarySet[];
  auditLog: AuditEntry[];
  ayHistory: AYHistoryRecord[];
  grievances: Grievance[];
  remedialActions: Record<string, Record<string, string>>;
  facultyNotifications: FacultyNotification[];
  poDefinitions: PODefinition[];
  psoDefinitions: PSODefinition[];

  // Optional: CO attainment overrides per course/CO (used by faculty view)
  coOverrides?: Record<
    string,
    Record<
      string,
      {
        original: number;
        overridden: number;
        by: string;
        at: string;
      }
    >
  >;

  // User CRUD
  addUser: (user: Omit<UserRecord, "id" | "joinedAt">) => void;
  updateUser: (id: string, patch: Partial<UserRecord>) => void;
  deleteUser: (id: string) => void;

  // Course CRUD
  addCourse: (course: Omit<CourseRecord, "id">) => void;
  updateCourse: (id: string, patch: Partial<CourseRecord>) => void;

  // CO Management
  setCOs: (courseId: string, cos: CODefinition[]) => void;
  addCO: (courseId: string, co: CODefinition) => void;
  updateCO: (courseId: string, coId: string, patch: Partial<CODefinition>) => void;
  deleteCO: (courseId: string, coId: string) => void;
  setCOPOMapping: (courseId: string, mapping: Record<string, Record<string, number>>) => void;
  setCOOverride: (
    courseId: string,
    coId: string,
    override: { original: number; overridden: number; by: string; at: string; reason?: string },
  ) => void;

  // Exam Config
  addExamConfig: (courseId: string, exam: ExamConfig) => void;
  setExamConfig: (courseId: string, examId: string, patch: Partial<ExamConfig>) => void;
  setQuestions: (courseId: string, examId: string, questions: QuestionDef[]) => void;
  deleteExamConfig: (courseId: string, examId: string) => void;

  // Marks
  setSubmission: (courseId: string, submission: MarksSubmission) => void;
  saveSubmission: (submission: MarksSubmission) => void;
  approveSubmission: (courseId: string, examId: string, approvedBy: string) => void;
  returnSubmission: (courseId: string, examId: string, reason: string) => void;
  getSubmission: (courseId: string, examId: string) => MarksSubmission | undefined;

  // AY Config
  setAY: (config: Partial<AYConfig>) => void;
  lockAY: (signedBy: string) => void;
  addAYHistory: (record: AYHistoryRecord) => void;

  // Thresholds
  setThresholds: (t: Partial<ThresholdConfig>) => void;

  // CO Library
  addCOLibrarySet: (set: Omit<COLibrarySet, "id" | "createdAt" | "updatedAt">) => void;
  updateCOLibrarySet: (id: string, patch: Partial<COLibrarySet>) => void;
  archiveCOLibrarySet: (id: string) => void;
  restoreCOLibrarySet: (id: string) => void;

  // PO/PSO Master actions
  updatePODefinition: (id: string, patch: Partial<PODefinition>) => void;
  addPSODefinition: (pso: Omit<PSODefinition, "version">) => void;
  updatePSODefinition: (id: string, patch: Partial<PSODefinition>) => void;
  deletePSODefinition: (id: string) => void;

  // Audit
  addAuditEntry: (entry: Omit<AuditEntry, "id" | "timestamp">) => void;

  // Grievances
  addGrievance: (g: Omit<Grievance, "id" | "submittedAt">) => void;
  resolveGrievance: (id: string, resolution: string) => void;
  updateGrievanceStatus: (id: string, status: Grievance["status"], resolution?: string, updatedMarks?: number) => void;

  // Remedial Actions
  saveRemedialAction: (courseId: string, coId: string, action: string) => void;

  // Submission status update (used by lead approval)
  updateSubmissionStatus: (
    courseId: string,
    examId: string,
    status: MarksSubmission["status"],
    meta?: { by?: string; comment?: string; returnReason?: string; overrideReason?: string; students?: StudentMark[] }
  ) => void;

  // Faculty Notifications
  addFacultyNotification: (n: Omit<FacultyNotification, "id" | "timestamp" | "read">) => void;
  markFacultyNotifRead: (id: string) => void;
  deleteFacultyNotif: (id: string) => void;
  markAllFacultyNotifsRead: (userId: string) => void;
}

function uid() {
  return Math.random().toString(36).substr(2, 9);
}

function now() {
  return new Date().toISOString().replace("T", " ").substring(0, 19);
}

// ─── STORE ───────────────────────────────────────────────────

export const useDataStore = create<DataState>()(
  persist(
    (set, get) => ({
      users: DEFAULT_USERS,
      courses: DEFAULT_COURSES,
      cos: DEFAULT_COS,
      coPOMappings: {},
      examConfigs: DEFAULT_EXAM_CONFIGS,
      submissions: DEFAULT_MARKS,
      coOverrides: {},
      ay: DEFAULT_AY,
      thresholds: DEFAULT_THRESHOLDS,
      coLibrary: DEFAULT_CO_LIBRARY,
      poDefinitions: DEFAULT_PO_DEFINITIONS,
      psoDefinitions: DEFAULT_PSO_DEFINITIONS,
      auditLog: DEFAULT_SEED_AUDIT,
      ayHistory: DEFAULT_AY_HISTORY,
      grievances: [],
      remedialActions: {},
      facultyNotifications: [],

      // ── User CRUD ──
      addUser: (user) => {
        const newUser: UserRecord = { ...user, id: uid(), joinedAt: now().split(" ")[0] };
        set(s => ({ users: [...s.users, newUser] }));
        get().addAuditEntry({ type: "user", userId: "system", role: "admin", action: `Provisioned new user: ${user.name} (${user.employeeId})`, ip: "127.0.0.1" });
      },
      updateUser: (id, patch) =>
        set(s => ({ users: s.users.map(u => u.id === id ? { ...u, ...patch } : u) })),
      deleteUser: (id) =>
        set(s => ({ users: s.users.filter(u => u.id !== id) })),

      // ── Course CRUD ──
      addCourse: (course) =>
        set(s => ({ courses: [...s.courses, { ...course, id: uid() }] })),
      updateCourse: (id, patch) =>
        set(s => ({ courses: s.courses.map(c => c.id === id ? { ...c, ...patch } : c) })),

      // ── CO Management ──
      setCOs: (courseId, cos) =>
        set(s => ({ cos: { ...s.cos, [courseId]: cos } })),
      addCO: (courseId, co) =>
        set(s => ({ cos: { ...s.cos, [courseId]: [...(s.cos[courseId] || []), co] } })),
      updateCO: (courseId, coId, patch) =>
        set(s => ({
          cos: { ...s.cos, [courseId]: (s.cos[courseId] || []).map(c => c.co === coId ? { ...c, ...patch } : c) }
        })),
      deleteCO: (courseId, coId) =>
        set(s => ({ cos: { ...s.cos, [courseId]: (s.cos[courseId] || []).filter(c => c.co !== coId) } })),
      setCOPOMapping: (courseId, mapping) =>
        set(s => ({ coPOMappings: { ...s.coPOMappings, [courseId]: mapping } })),
      setCOOverride: (courseId, coId, override) =>
        set(s => ({
          coOverrides: {
            ...(s.coOverrides || {}),
            [courseId]: {
              ...((s.coOverrides || {})[courseId] || {}),
              [coId]: override,
            },
          },
        })),

      // ── Exam Config ──
      addExamConfig: (courseId, exam) =>
        set(s => ({
          examConfigs: {
            ...s.examConfigs,
            [courseId]: [...(s.examConfigs[courseId] || []), exam]
          }
        })),
      setExamConfig: (courseId, examId, patch) =>
        set(s => ({
          examConfigs: {
            ...s.examConfigs,
            [courseId]: (s.examConfigs[courseId] || []).map(e => e.id === examId ? { ...e, ...patch } : e)
          }
        })),
      setQuestions: (courseId, examId, questions) =>
        set(s => ({
          examConfigs: {
            ...s.examConfigs,
            [courseId]: (s.examConfigs[courseId] || []).map(e => e.id === examId ? { ...e, questions } : e)
          }
        })),
      deleteExamConfig: (courseId, examId) =>
        set(s => ({
          examConfigs: {
            ...s.examConfigs,
            [courseId]: (s.examConfigs[courseId] || []).filter(e => e.id !== examId)
          }
        })),

      // ── Marks ──
      setSubmission: (courseId: string, submission: MarksSubmission) =>
        set(s => ({
          submissions: {
            ...s.submissions,
            [courseId]: [
              ...(s.submissions[courseId] || []).filter(m => m.examId !== submission.examId),
              submission
            ]
          }
        })),
      saveSubmission: (submission) =>
        set(s => {
          const existing = s.submissions[submission.courseId] || [];
          const idx = existing.findIndex(m => m.examId === submission.examId);
          const updated = idx >= 0
            ? existing.map((m, i) => i === idx ? submission : m)
            : [...existing, submission];
          return { submissions: { ...s.submissions, [submission.courseId]: updated } };
        }),
      approveSubmission: (courseId, examId, approvedBy) => {
        const approvedAt = new Date().toISOString();
        set(s => ({
          submissions: {
            ...s.submissions,
            [courseId]: (s.submissions[courseId] || []).map(m =>
              m.examId === examId ? { ...m, status: "approved", approvedBy, approvedAt } : m
            )
          }
        }));
        get().addAuditEntry({ type: "approval", userId: approvedBy, role: "subject_lead", action: `Approved marks for ${courseId.toUpperCase()} — ${examId.toUpperCase()}`, ip: "192.168.1.1" });
      },
      returnSubmission: (courseId, examId, reason) =>
        set(s => ({
          submissions: {
            ...s.submissions,
            [courseId]: (s.submissions[courseId] || []).map(m =>
              m.examId === examId ? { ...m, status: "returned", returnReason: reason } : m
            )
          }
        })),
      getSubmission: (courseId, examId) =>
        get().submissions[courseId]?.find(m => m.examId === examId),

      // ── AY Config ──
      setAY: (config) => set(s => ({ ay: { ...s.ay, ...config } })),
      lockAY: (signedBy) => {
        set(s => ({ ay: { ...s.ay, status: "locked", lockedBy: signedBy, lockedOn: now().split(" ")[0] } }));
        get().addAuditEntry({ type: "ay_lock", userId: signedBy, role: "department_head", action: `Academic Year ${get().ay.ay} locked and archived by ${signedBy}`, ip: "192.168.1.1" });
      },
      addAYHistory: (record) =>
        set(s => ({ ayHistory: [...s.ayHistory.filter(h => h.ay !== record.ay), record] })),

      // ── Thresholds ──
      setThresholds: (t) => set(s => ({ thresholds: { ...s.thresholds, ...t } })),

      // ── CO Library ──
      addCOLibrarySet: (set_) =>
        set(s => ({ coLibrary: [...s.coLibrary, { ...set_, id: uid(), createdAt: now().split(" ")[0], updatedAt: now().split(" ")[0] }] })),
      updateCOLibrarySet: (id, patch) =>
        set(s => ({ coLibrary: s.coLibrary.map(l => l.id === id ? { ...l, ...patch, updatedAt: now().split(" ")[0], version: (l.version || 1) + 1 } : l) })),
      archiveCOLibrarySet: (id) =>
        set(s => ({ coLibrary: s.coLibrary.map(l => l.id === id ? { ...l, status: "archived", updatedAt: now().split(" ")[0] } : l) })),
      restoreCOLibrarySet: (id) =>
        set(s => ({ coLibrary: s.coLibrary.map(l => l.id === id ? { ...l, status: "active", updatedAt: now().split(" ")[0] } : l) })),

      // ── PO/PSO Master ──
      updatePODefinition: (id, patch) =>
        set(s => ({ poDefinitions: s.poDefinitions.map(p => p.id === id ? { ...p, ...patch, version: p.version + 1 } : p) })),
      addPSODefinition: (pso) =>
        set(s => ({ psoDefinitions: [...s.psoDefinitions, { ...pso, version: 1 }] })),
      updatePSODefinition: (id, patch) =>
        set(s => ({ psoDefinitions: s.psoDefinitions.map(p => p.id === id ? { ...p, ...patch, version: p.version + 1 } : p) })),
      deletePSODefinition: (id) =>
        set(s => ({ psoDefinitions: s.psoDefinitions.filter(p => p.id !== id) })),

      // ── Audit ──
      addAuditEntry: (entry) =>
        set(s => ({
          auditLog: [
            { ...entry, id: uid(), timestamp: now() },
            ...s.auditLog.slice(0, 499), // keep last 500
          ]
        })),

      // ── Grievances ──
      addGrievance: (g) =>
        set(s => ({ grievances: [...s.grievances, { ...g, id: uid(), submittedAt: now(), status: "pending" }] })),
      resolveGrievance: (id, resolution) =>
        set(s => ({ grievances: s.grievances.map(g => g.id === id ? { ...g, status: "resolved_unchanged", resolution } : g) })),
      updateGrievanceStatus: (id, status, resolution, updatedMarks) =>
        set(s => ({ grievances: s.grievances.map(g => g.id === id ? { ...g, status, ...(resolution ? { resolution } : {}), ...(updatedMarks !== undefined ? { updatedMarks } : {}) } : g) })),

      // ── Submission Status ──
      updateSubmissionStatus: (courseId, examId, status, meta) =>
        set(s => ({
          submissions: {
            ...s.submissions,
            [courseId]: (s.submissions[courseId] || []).map(m =>
              m.examId === examId
                ? {
                    ...m,
                    status,
                    ...(status === "approved" ? { approvedAt: new Date().toISOString(), approvedBy: meta?.by } : {}),
                    ...(status === "returned" ? { returnReason: meta?.returnReason || m.returnReason } : {}),
                    ...(meta?.comment ? { leadComment: meta.comment } : {}),
                    ...(meta?.overrideReason ? { overrideReason: meta.overrideReason } : {}),
                    ...(meta?.students ? { students: meta.students } : {}),
                    history: [
                      ...(m.history || []),
                      {
                        id: uid(),
                        action: status === "approved" ? "approved" : status === "returned" ? "returned" : "submitted",
                        by: meta?.by || "system",
                        role: "subject_lead",
                        at: now(),
                        comment: meta?.comment || meta?.returnReason || meta?.overrideReason,
                      },
                    ],
                  }
                : m
            )
          }
        })),

      // ── Faculty Notifications ──
      addFacultyNotification: (n) =>
        set(s => ({ facultyNotifications: [{ ...n, id: uid(), timestamp: "Just now", read: false }, ...s.facultyNotifications] })),
      markFacultyNotifRead: (id) =>
        set(s => ({ facultyNotifications: s.facultyNotifications.map(n => n.id === id ? { ...n, read: true } : n) })),
      deleteFacultyNotif: (id) =>
        set(s => ({ facultyNotifications: s.facultyNotifications.filter(n => n.id !== id) })),
      markAllFacultyNotifsRead: (userId) =>
        set(s => ({ facultyNotifications: s.facultyNotifications.map(n => n.userId === userId ? { ...n, read: true } : n) })),

      // ── Remedial Actions ──
      saveRemedialAction: (courseId, coId, action) =>
        set(s => ({
          remedialActions: {
            ...s.remedialActions,
            [courseId]: {
              ...(s.remedialActions[courseId] || {}),
              [coId]: action
            }
          }
        })),
    }),
    {
      name: "obe-ai-data-store",
      version: 4,
    }
  )
);

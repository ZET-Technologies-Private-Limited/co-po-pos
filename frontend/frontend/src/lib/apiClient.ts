// ============================================================
// API Client — Real Backend Integration
// ============================================================
import { useAuthStore } from './authStore';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

// In the browser, use relative /api/v1 so requests go through the Next.js proxy.
// On the server, use the full backend URL.
const getBaseURL = () =>
  typeof window !== 'undefined' ? '' : (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000');

// Types matching backend schemas
export interface LoginRequest {
  email?: string;
  employee_id?: string;
  password: string;
  department?: string;
  academic_year?: string;
  remember_me?: boolean;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name: string;
  role?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  role: string;
}

export interface Course {
  id: string;
  course_code: string;
  course_name: string;
  credits: number;
  semester: number;
  description?: string;
  course_type?: string;
  enrolled_students?: number;
  fa_method?: string;
  fa_best_n?: number;
  fa_total_components?: number;
  fa_weight?: number;
  sa_weight?: number;
  department?: string;
  syllabus?: string;
  program_id?: string;
  programId?: string;
}

export interface CourseOutcome {
  id: string;
  course_id: string;
  code: string;
  statement: string;
  bloom_level: string;
  description?: string;
}

export interface Exam {
  id: string;
  course_id: string;
  exam_name: string;
  exam_type: string;
  total_marks: number;
  duration_minutes?: number;
  question_count?: number;
  assessment_code?: string;
  weightage_pct?: number;
  units_covered?: string[];
  number_of_questions?: number;
}

export interface Question {
  id: string;
  exam_id: string;
  question_number: number;
  question_text: string;
  marks: number;
  question_type: string;
  bloom_level: string;
  bloom_confidence?: number;
  mapped_cos?: Array<{ co_id: string; co_code: string }>;
}

export interface AttainmentResult {
  co_code: string;
  attainment_percentage: number;
  attainment_level: string;
  students_cleared: number;
  total_students: number;
}

class ApiClient {
  private baseURL: string;
  private token: string | null = null;
  private readonly nbaPoFallback = [
    { code: "PO1",  name: "Engineering Knowledge",                         statement: "Apply knowledge of mathematics, science, engineering fundamentals and an engineering specialisation to the solution of complex engineering problems.", editable: false },
    { code: "PO2",  name: "Problem Analysis",                               statement: "Identify, formulate, review research literature, and analyse complex engineering problems reaching substantiated conclusions using first principles of mathematics, natural sciences and engineering sciences.", editable: false },
    { code: "PO3",  name: "Design/Development of Solutions",                statement: "Design solutions for complex engineering problems and design system components or processes that meet the specified needs with appropriate consideration for the public health and safety, and the cultural, societal, and environmental considerations.", editable: false },
    { code: "PO4",  name: "Conduct Investigations of Complex Problems",      statement: "Use research-based knowledge and research methods including design of experiments, analysis and interpretation of data, and synthesis of the information to provide valid conclusions.", editable: false },
    { code: "PO5",  name: "Modern Tool Usage",                              statement: "Create, select, and apply appropriate techniques, resources, and modern engineering and IT tools including prediction and modelling to complex engineering activities with an understanding of the limitations.", editable: false },
    { code: "PO6",  name: "The Engineer and Society",                       statement: "Apply reasoning informed by the contextual knowledge to assess societal, health, safety, legal and cultural issues and the consequent responsibilities relevant to the professional engineering practice.", editable: false },
    { code: "PO7",  name: "Environment and Sustainability",                 statement: "Understand the impact of the professional engineering solutions in societal and environmental contexts, and demonstrate the knowledge of, and need for sustainable development.", editable: false },
    { code: "PO8",  name: "Ethics",                                         statement: "Apply ethical principles and commit to professional ethics and responsibilities and norms of the engineering practice.", editable: false },
    { code: "PO9",  name: "Individual and Team Work",                       statement: "Function effectively as an individual, and as a member or leader in diverse teams, and in multidisciplinary settings.", editable: false },
    { code: "PO10", name: "Communication",                                  statement: "Communicate effectively on complex engineering activities with the engineering community and with society at large.", editable: false },
    { code: "PO11", name: "Project Management and Finance",                 statement: "Demonstrate knowledge and understanding of the engineering and management principles and apply these to one's own work, as a member and leader in a team, to manage projects and in multidisciplinary environments.", editable: false },
    { code: "PO12", name: "Life-long Learning",                             statement: "Recognise the need for, and have the preparation and ability to engage in independent and life-long learning in the broadest context of technological change.", editable: false },
  ];

  constructor() {
    this.baseURL = API_BASE_URL;
  }

  private isTokenExpired(token: string): boolean {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return true;
      const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
      if (!payload?.exp) return true;
      const now = Math.floor(Date.now() / 1000);
      return payload.exp <= now;
    } catch {
      return true;
    }
  }

  private clearAuthSession(): void {
    this.token = null;
    try {
      if (typeof window !== 'undefined') localStorage.removeItem('auth_token');
    } catch {
      // noop
    }
    useAuthStore.setState({
      user: null,
      activeRole: null,
      isAuthenticated: false,
      loginError: 'Session expired. Please log in again.',
      accessToken: null,
    });
  }

  private getAuthHeader(): Record<string, string> {
    const stored = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    const token = this.token || stored;
    if (!token) return {};

    if (this.isTokenExpired(token)) {
      this.clearAuthSession();
      return {};
    }

    return { Authorization: `Bearer ${token}` };
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    opts: { suppressErrorLog?: boolean } = {}
  ): Promise<T> {
    const base = getBaseURL();
    const url = `${base}/api/v1${endpoint}`;
    const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
    const baseHeaders: Record<string, string> = {
      ...this.getAuthHeader(),
      ...(options.headers as Record<string, string> | undefined),
    };
    if (!isFormData) {
      baseHeaders['Content-Type'] = 'application/json';
    }

    const config: RequestInit = {
      ...options,
      headers: baseHeaders,
    };

    try {
      let response = await fetch(url, config);

      // Dev resilience: if Next proxy fails with 5xx, retry GET directly to backend.
      if (
        typeof window !== 'undefined' &&
        base === '' &&
        (config.method ?? 'GET').toUpperCase() === 'GET' &&
        [500, 502, 503, 504].includes(response.status)
      ) {
        const directUrl = `${this.baseURL}/api/v1${endpoint}`;
        try {
          const retried = await fetch(directUrl, config);
          response = retried;
        } catch {
          // Keep original response handling below.
        }
      }

      if (!response.ok) {
        const rawError = await response.text().catch(() => '');
        let errorData: any = {};
        try {
          errorData = rawError ? JSON.parse(rawError) : {};
        } catch {
          errorData = {};
        }

        const deriveErrorMessage = (): string => {
          if (typeof errorData?.detail === 'string' && errorData.detail.trim()) {
            return errorData.detail;
          }

          if (Array.isArray(errorData?.detail) && errorData.detail.length > 0) {
            const items = errorData.detail
              .map((d: any) => {
                if (typeof d === 'string') return d;
                if (typeof d?.msg === 'string') {
                  const loc = Array.isArray(d?.loc) ? d.loc.join('.') : '';
                  return loc ? `${loc}: ${d.msg}` : d.msg;
                }
                return '';
              })
              .filter(Boolean);
            if (items.length > 0) return items.join('; ');
          }

          if (typeof errorData?.message === 'string' && errorData.message.trim()) {
            return errorData.message;
          }

          if (typeof rawError === 'string' && rawError.trim()) {
            const rawTrimmed = rawError.trim();
            if (/^<!doctype html>|^<html/i.test(rawTrimmed)) {
              return `HTTP ${response.status}`;
            }
            return rawTrimmed;
          }

          return `HTTP ${response.status}`;
        };

        if (response.status === 401) {
          const path = typeof window !== 'undefined' ? window.location.pathname : '';
          const isAuthPage = /\/(login|register|forgot-password|student-login)/.test(path);
          if (!isAuthPage) {
            this.clearAuthSession();
            if (typeof window !== 'undefined') {
              window.location.href = '/login?reason=session_expired';
            }
          }
          throw new Error('Invalid or expired token. Please log in again.');
        }
        if (opts.suppressErrorLog) {
          throw new Error(`HTTP ${response.status}`);
        }
        throw new Error(deriveErrorMessage());
      }

      return await response.json();
    } catch (error) {
      const message = error instanceof Error ? error.message : '';
      if (/Invalid or expired token/i.test(message)) throw error;
      if (
        message === 'Failed to fetch' ||
        message.includes('NetworkError') ||
        message.includes('ERR_CONNECTION_REFUSED') ||
        message.includes('net::ERR')
      ) {
        throw new Error('Cannot reach the server. Make sure the backend is running on http://127.0.0.1:8000.');
      }
      if (!opts.suppressErrorLog) {
        console.error(`API Error [${endpoint}]:`, error);
      }
      throw error;
    }
  }

  // ============================================================
  // AUTHENTICATION
  // ============================================================
  
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    
    this.token = response.access_token;
    if (typeof window !== 'undefined') localStorage.setItem('auth_token', response.access_token);
    
    return response;
  }

  async register(userData: RegisterRequest): Promise<TokenResponse> {
    const response = await this.request<TokenResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
    this.token = response.access_token;
    if (typeof window !== 'undefined') localStorage.setItem('auth_token', response.access_token);
    return response;
  }

  /** Admin create user (does not overwrite current auth token). */
  async createUser(data: { username: string; email: string; password: string; full_name: string; role?: string; department?: string }): Promise<any> {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        username: data.username,
        email: data.email,
        password: data.password,
        full_name: data.full_name,
        role: data.role || 'faculty',
        department: data.department,
      }),
    });
  }

  async getRoleOptions(): Promise<{ primary_role: string; available_roles: string[] }> {
    return this.request('/auth/role-options');
  }

  async forgotPassword(data: { employee_id: string; email: string }): Promise<any> {
    return this.request('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async resendOtp(data: { employee_id: string; email: string }): Promise<any> {
    return this.request('/auth/resend-otp', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async verifyOtp(data: { employee_id: string; email: string; otp: string }): Promise<any> {
    return this.request('/auth/verify-otp', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async resetPassword(data: { 
    employee_id: string; 
    email: string; 
    otp: string; 
    new_password: string; 
    confirm_password: string 
  }): Promise<any> {
    return this.request('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /** Change password for authenticated user (first-login or profile). */
  async changePassword(data: { old_password: string; new_password: string; confirm_password: string }): Promise<{ status: string; message: string }> {
    return this.request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ============================================================
  // COURSES
  // ============================================================
  
  async createCourse(courseData: Omit<Course, 'id'>): Promise<Course> {
    return this.request('/courses', {
      method: 'POST',
      body: JSON.stringify(courseData),
    });
  }

  async getCourses(semester?: number): Promise<Course[]> {
    const params = semester ? `?semester=${semester}` : '';
    return this.request(`/courses${params}`);
  }

  async getCourse(courseId: string): Promise<Course> {
    return this.request(`/courses/${courseId}`);
  }

  async updateCourse(courseId: string, updates: Partial<Course>): Promise<Course> {
    return this.request(`/courses/${courseId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async deleteCourse(courseId: string): Promise<{ status: string }> {
    return this.request(`/courses/${courseId}`, {
      method: 'DELETE',
    });
  }

  async updateSyllabus(courseId: string, syllabus: string): Promise<any> {
    return this.request(`/courses/${courseId}/syllabus`, {
      method: 'POST',
      body: JSON.stringify({ syllabus }),
    });
  }

  async uploadSyllabusFile(courseId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    
    return this.request(`/courses/${courseId}/syllabus/upload`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeader(),
      },
      body: formData,
    });
  }

  // ============================================================
  // COURSE OUTCOMES
  // ============================================================
  
  async createCourseOutcome(courseId: string, coData: {
    co_code: string;
    co_statement: string;
    bloom_level: string;
    description?: string;
  }): Promise<CourseOutcome> {
    return this.request(`/courses/${courseId}/outcomes`, {
      method: 'POST',
      body: JSON.stringify(coData),
    });
  }

  async getCourseOutcomes(courseId: string): Promise<CourseOutcome[]> {
    return this.request(`/courses/${courseId}/outcomes`);
  }

  async getCourseOutcomesDetail(courseId: string): Promise<any[]> {
    return this.request(`/courses/${courseId}/outcomes/detail`);
  }

  async updateCourseOutcome(courseId: string, coId: string, updates: Partial<CourseOutcome>): Promise<CourseOutcome> {
    return this.request(`/courses/${courseId}/outcomes/${coId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async deleteCourseOutcome(courseId: string, coId: string): Promise<{ status: string }> {
    return this.request(`/courses/${courseId}/outcomes/${coId}`, {
      method: 'DELETE',
    });
  }

  async generateCourseOutcomes(courseId: string, data: {
    syllabus: string;
    program_outcomes: any[];
    program_specific_outcomes: any[];
    num_cos?: number;
  }): Promise<any> {
    return this.request(`/courses/${courseId}/generate-co`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async regenerateSingleCO(courseId: string, coId: string): Promise<CourseOutcome> {
    return this.request(`/courses/${courseId}/outcomes/${coId}/regenerate`, {
      method: 'POST',
    });
  }

  async updateCOMappings(courseId: string, coId: string, data: {
    po_codes?: string[];
    pso_codes?: string[];
    po_levels?: Record<string, number>;
    pso_levels?: Record<string, number>;
    program_id?: string;
  }): Promise<any> {
    return this.request(`/courses/${courseId}/outcomes/${coId}/mappings`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getBloomDistribution(courseId: string): Promise<any> {
    return this.request(`/courses/${courseId}/outcomes/bloom-distribution`);
  }

  async getCOCoverage(courseId: string): Promise<any> {
    return this.request(`/courses/${courseId}/co-coverage`);
  }

  async updateCOStatement(courseId: string, coId: string, data: { statement: string; bloom_level?: string }): Promise<any> {
    return this.request(`/courses/${courseId}/outcomes/${coId}/statement`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getCOHistory(courseId: string): Promise<any> {
    return this.request(`/courses/${courseId}/co-history`, {}, { suppressErrorLog: true });
  }

  async getCOSession(courseId: string): Promise<any> {
    return this.request(`/courses/${courseId}/co-session`, {}, { suppressErrorLog: true });
  }

  async exportNBASAR(courseId: string): Promise<Blob> {
    const base = getBaseURL();
    const response = await fetch(`${base}/api/v1/courses/${courseId}/outcomes/export/nba-sar`, {
      headers: this.getAuthHeader(),
    });
    if (!response.ok) throw new Error(`NBA SAR export failed: ${response.statusText}`);
    return response.blob();
  }

  async exportCourseOutcomes(courseId: string, format: 'pdf' | 'csv'): Promise<Blob> {
    const base = getBaseURL();
    const response = await fetch(`${base}/api/v1/courses/${courseId}/outcomes/export?format=${format}`, {
      headers: this.getAuthHeader(),
    });
    
    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }
    
    return response.blob();
  }

  async getCOItemHistory(courseId: string, coId: string): Promise<any> {
    return this.request(`/courses/${courseId}/outcomes/${coId}/history`);
  }

  async rollbackCO(courseId: string, coId: string, versionIndex: number = 0): Promise<any> {
    return this.request(`/courses/${courseId}/outcomes/${coId}/rollback`, {
      method: 'POST',
      body: JSON.stringify({ version_index: versionIndex }),
    });
  }

  // ============================================================
  // EXAMS
  // ============================================================
  
  async createExam(courseId: string, examData: {
    exam_name: string;
    exam_type: string;
    total_marks: number;
    duration_minutes?: number;
    exam_date?: string;
    assessment_code?: string;
    weightage_pct?: number;
    units_covered?: string[];
    number_of_questions?: number;
  }): Promise<Exam> {
    return this.request(`/courses/${courseId}/exams`, {
      method: 'POST',
      body: JSON.stringify(examData),
    });
  }

  async getExams(courseId: string): Promise<Exam[]> {
    return this.request(`/courses/${courseId}/exams`);
  }

  async updateExam(courseId: string, examId: string, updates: Partial<Exam>): Promise<Exam> {
    return this.request(`/courses/${courseId}/exams/${examId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async deleteExam(courseId: string, examId: string): Promise<{ status: string }> {
    return this.request(`/courses/${courseId}/exams/${examId}`, {
      method: 'DELETE',
    });
  }

  // ============================================================
  // QUESTIONS
  // ============================================================
  
  async addQuestions(examId: string, questions: any[]): Promise<any> {
    return this.request(`/exams/${examId}/questions`, {
      method: 'POST',
      body: JSON.stringify({ questions }),
    });
  }

  async uploadQuestionsFile(examId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    return this.request(`/exams/${examId}/questions/upload-bulk`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeader(),
      },
      body: formData,
    });
  }

  async getQuestions(examId: string): Promise<{ questions: Question[]; total: number }> {
    return this.request(`/exams/${examId}/questions`);
  }

  async updateQuestion(examId: string, questionId: string, updates: Partial<Question>): Promise<Question> {
    return this.request(`/exams/${examId}/questions/${questionId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async deleteQuestion(examId: string, questionId: string): Promise<{ status: string }> {
    return this.request(`/exams/${examId}/questions/${questionId}`, {
      method: 'DELETE',
    });
  }

  async mapQuestionToCO(examId: string, questionId: string, coIds: string[]): Promise<any> {
    return this.request(`/exams/${examId}/questions/${questionId}/map-co`, {
      method: 'POST',
      body: JSON.stringify(coIds),
    });
  }

  async analyzeQuestions(examId: string): Promise<any> {
    return this.request(`/exams/${examId}/analyze-questions`, {
      method: 'POST',
    });
  }

  async detectBloomLevels(examId: string): Promise<any> {
    return this.request(`/exams/${examId}/detect-bloom-levels`, {
      method: 'POST',
    });
  }

  // ============================================================
  // MARKS
  // ============================================================
  
  async submitMarks(examId: string, marksData: {
    rows: Array<{ student_id: string; marks: Record<string, number> }>;
  }): Promise<any> {
    return this.request(`/exams/${examId}/marks`, {
      method: 'POST',
      body: JSON.stringify(marksData),
    });
  }

  async uploadMarksFile(examId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    
    return this.request(`/exams/${examId}/upload-marks`, {
      method: 'POST',
      headers: {
        ...this.getAuthHeader(),
      },
      body: formData,
    });
  }

  async getMarks(examId: string): Promise<any> {
    return this.request(`/exams/${examId}/marks`);
  }

  async getMarksPreview(examId: string, thresholdPct: number = 0.6): Promise<any> {
    return this.request(`/marks/${examId}/preview?threshold_pct=${thresholdPct}`);
  }

  async submitMarksForApproval(examId: string): Promise<any> {
    return this.request(`/marks/${examId}/submit`, {
      method: 'POST',
    });
  }

  async approveMarks(examId: string, programId: string, thresholdPct: number = 0.6): Promise<any> {
    return this.request(`/marks/${examId}/approve?program_id=${programId}&threshold_pct=${thresholdPct}`, {
      method: 'POST',
    });
  }

  async unlockMarks(examId: string): Promise<any> {
    return this.request(`/marks/${examId}/unlock`, {
      method: 'POST',
    });
  }

  // ============================================================
  // ATTAINMENT
  // ============================================================
  
  async calculateCOAttainment(courseId: string, examId: string, thresholdPct: number = 0.6): Promise<{
    attainments: AttainmentResult[];
  }> {
    return this.request(`/attainment/calculate-co?course_id=${courseId}&exam_id=${examId}&threshold_pct=${thresholdPct}`, {
      method: 'POST',
    });
  }

  async getWeightedCOAttainment(courseId: string, thresholdPct: number = 0.6): Promise<any> {
    return this.request(`/attainment/weighted/${courseId}?threshold_pct=${thresholdPct}`);
  }

  async calculatePOAttainment(courseId: string, programId?: string): Promise<any> {
    const params = new URLSearchParams({ course_id: courseId });
    if (programId) params.set('program_id', programId);
    return this.request(`/attainment/calculate-po?${params.toString()}`, {
      method: 'POST',
    });
  }

  async calculatePSOAttainment(courseId: string, programId?: string): Promise<any> {
    const params = new URLSearchParams({ course_id: courseId });
    if (programId) params.set('program_id', programId);
    return this.request(`/attainment/calculate-pso?${params.toString()}`, {
      method: 'POST',
    });
  }

  async runFullAttainmentPipeline(courseId: string, programId: string | undefined, thresholdPct: number = 0.6): Promise<any> {
    const params = new URLSearchParams({ course_id: courseId, threshold_pct: String(thresholdPct) });
    if (programId) params.set('program_id', programId);
    return this.request(`/attainment/full-pipeline?${params.toString()}`, {
      method: 'POST',
    });
  }

  async queueAttainmentPipeline(courseId: string, programId: string | undefined, thresholdPct: number = 0.6): Promise<any> {
    const params = new URLSearchParams({ course_id: courseId, threshold_pct: String(thresholdPct) });
    if (programId) params.set('program_id', programId);
    return this.request(`/attainment/full-pipeline/async?${params.toString()}`, {
      method: 'POST',
    });
  }

  async getCourseAttainment(courseId: string): Promise<any> {
    return this.request(`/attainment/course/${courseId}`);
  }

  async getCOPOMatrix(courseId: string): Promise<any> {
    return this.request(`/attainment/matrix/${courseId}`);
  }

  async getStudentPerformance(courseId: string, examId?: string): Promise<any> {
    const params = examId ? `?exam_id=${examId}` : '';
    return this.request(`/attainment/students/${courseId}${params}`);
  }

  async setIndirectAttainment(courseId: string, coId: string, surveyAvg: number, scale: number = 5.0): Promise<any> {
    return this.request(`/attainment/indirect?course_id=${courseId}&co_id=${coId}&survey_avg=${surveyAvg}&scale=${scale}`, {
      method: 'POST',
    });
  }

  async getIndirectAttainments(courseId: string): Promise<any> {
    return this.request(`/attainment/indirect/${courseId}`);
  }

  async getGapAnalysis(courseId: string, thresholdPct: number = 0.4): Promise<any> {
    return this.request(`/attainment/gap-analysis/${courseId}?threshold_pct=${thresholdPct}`);
  }

  async getOBEWorkflow(courseId: string, params?: {
    threshold_pct?: number;
    fa_method?: 'best_n_of_m' | 'simple_avg' | 'weighted';
    fa_best_n?: number;
    fa_weight?: number;
    sa_weight?: number;
    direct_weight?: number;
    indirect_weight?: number;
  }): Promise<any> {
    const q = new URLSearchParams();
    if (params?.threshold_pct != null) q.append('threshold_pct', String(params.threshold_pct));
    if (params?.fa_method) q.append('fa_method', params.fa_method);
    if (params?.fa_best_n != null) q.append('fa_best_n', String(params.fa_best_n));
    if (params?.fa_weight != null) q.append('fa_weight', String(params.fa_weight));
    if (params?.sa_weight != null) q.append('sa_weight', String(params.sa_weight));
    if (params?.direct_weight != null) q.append('direct_weight', String(params.direct_weight));
    if (params?.indirect_weight != null) q.append('indirect_weight', String(params.indirect_weight));
    const qs = q.toString();
    try {
      return await this.request(`/courses/${courseId}/obe-workflow${qs ? `?${qs}` : ''}`, {}, { suppressErrorLog: true });
    } catch (error: any) {
      const msg = String(error?.message || '');
      if (/not found|http 404/i.test(msg)) {
        try {
          return await this.request(`/attainment/course/${courseId}`, {}, { suppressErrorLog: true });
        } catch (fallbackError: any) {
          const fallbackMsg = String(fallbackError?.message || '');
          if (/not found|http 404/i.test(fallbackMsg)) {
            return {
              co_attainments: [],
              po_attainments: [],
              config: {},
              nba_formulas: {},
              summary: {
                total_cos: 0,
                cos_attained: 0,
                cos_gap: 0,
                avg_final_attainment: 0,
                overall_level: 'Level 1',
              },
            };
          }
          throw fallbackError;
        }
      }
      throw error;
    }
  }

  // ============================================================
  // PROGRAM OUTCOMES
  // ============================================================
  
  async createProgramOutcome(programId: string, data: {
    code: string;
    statement: string;
    description?: string;
  }): Promise<any> {
    return this.request(`/programs/${programId}/outcomes`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // NBA fixed POs — returned from backend seed endpoint
  async getNBAPOs(): Promise<any[]> {
    try {
      return await this.request('/nba/pos', {}, { suppressErrorLog: true });
    } catch {
      return this.nbaPoFallback;
    }
  }

  // Department PSOs — HOD-managed
  async getDepartmentPSOs(department: string): Promise<any[]> {
    const cleanedDepartment = String(department || '').trim();
    if (!cleanedDepartment) return [];
    try {
      return await this.request(`/nba/psos/${encodeURIComponent(cleanedDepartment)}`, {}, { suppressErrorLog: true });
    } catch {
      try {
        const deptProgram = `DEPT:${cleanedDepartment.toUpperCase()}`;
        return await this.request(`/programs/${encodeURIComponent(deptProgram)}/pso`, {}, { suppressErrorLog: true });
      } catch {
        return [];
      }
    }
  }

  async getProgramOutcomes(programId: string): Promise<any[]> {
    return this.request(`/programs/${programId}/outcomes`);
  }

  async updateProgramOutcome(programId: string, poId: string, data: {
    code: string;
    statement: string;
    description?: string;
  }): Promise<any> {
    return this.request(`/programs/${programId}/outcomes/${poId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteProgramOutcome(programId: string, poId: string): Promise<any> {
    return this.request(`/programs/${programId}/outcomes/${poId}`, {
      method: 'DELETE',
    });
  }

  async createPSO(programId: string, data: {
    code: string;
    statement: string;
    description?: string;
  }): Promise<any> {
    return this.request(`/programs/${programId}/pso`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getPSOs(programId: string): Promise<any[]> {
    return this.request(`/programs/${programId}/pso`);
  }

  async updatePSO(programId: string, psoId: string, data: { code?: string; statement?: string; description?: string }): Promise<any> {
    return this.request(`/programs/${programId}/pso/${psoId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deletePSO(programId: string, psoId: string): Promise<any> {
    return this.request(`/programs/${programId}/pso/${psoId}`, {
      method: 'DELETE',
    });
  }

  // ============================================================
  // MAPPING
  // ============================================================
  
  async mapCOToPO(courseId: string, programId: string | undefined, threshold: number = 0.3): Promise<any> {
    const params = new URLSearchParams({ course_id: courseId, threshold: String(threshold) });
    if (programId) params.set('program_id', programId);
    return this.request(`/map-co-po?${params.toString()}`, {
      method: 'POST',
    });
  }

  /** LLM-powered CO-PO mapping: uses Gemini/OpenAI to reason about alignment levels */
  async mapCOToPOWithLLM(courseId: string, programId?: string): Promise<any> {
    const params = new URLSearchParams({ course_id: courseId });
    if (programId) params.set('program_id', programId);
    return this.request(`/map-co-po/llm?${params.toString()}`, {
      method: 'POST',
    });
  }

  async mapCOToPSO(courseId: string, programId: string | undefined, threshold: number = 0.3): Promise<any> {
    const params = new URLSearchParams({ course_id: courseId, threshold: String(threshold) });
    if (programId) params.set('program_id', programId);
    return this.request(`/map-co-pso?${params.toString()}`, {
      method: 'POST',
    });
  }

  // ============================================================
  // REPORTS
  // ============================================================
  
  async generateReport(courseId: string, reportType: string): Promise<any> {
    return this.request(`/reports/generate?course_id=${courseId}&report_type=${reportType}`, {
      method: 'POST',
    });
  }

  async downloadReport(courseId: string, format: 'pdf' | 'excel' | 'nba'): Promise<Blob> {
    const base = getBaseURL();
    const response = await fetch(`${base}/api/v1/reports/${courseId}/download?format=${format}`, {
      headers: this.getAuthHeader(),
    });
    
    if (!response.ok) {
      throw new Error(`Report download failed: ${response.statusText}`);
    }
    
    return response.blob();
  }

  async getTaskStatus(taskId: string): Promise<any> {
    return this.request(`/tasks/${taskId}`);
  }

  // ============================================================
  // VISUALIZATION
  // ============================================================
  
  async getVisualizationData(courseId: string): Promise<any> {
    return this.request(`/visualization/${courseId}`);
  }

  // ============================================================
  // CHATBOT
  // ============================================================
  
  async sendChatMessage(data: {
    message: string;
    course_id?: string;
    session_id?: string;
    message_number?: 1 | 2 | 3;
    text?: string;
  }): Promise<any> {
    return this.request('/chatbot/message', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getChatbotState(courseId: string): Promise<any> {
    return this.request(`/chatbot/sessions/${courseId}/state`);
  }

  async updateChatbotState(courseId: string, step: string, sessionData: any): Promise<any> {
    return this.request(`/chatbot/sessions/${courseId}/state?step=${step}`, {
      method: 'POST',
      body: JSON.stringify(sessionData),
    });
  }

  async resetChatbotSession(courseId: string): Promise<any> {
    return this.request(`/chatbot/sessions/${courseId}/reset`, {
      method: 'POST',
    });
  }

  // ============================================================
  // FACULTY DASHBOARD
  // ============================================================
  
  async getFacultyDashboard(params?: {
    ay_code?: string;
    search?: string;
    sort_by?: string;
    sort_dir?: string;
    show_completed?: boolean;
  }): Promise<any> {
    const searchParams = new URLSearchParams();
    if (params?.ay_code) searchParams.append('ay_code', params.ay_code);
    if (params?.search) searchParams.append('search', params.search);
    if (params?.sort_by) searchParams.append('sort_by', params.sort_by);
    if (params?.sort_dir) searchParams.append('sort_dir', params.sort_dir);
    if (params?.show_completed) searchParams.append('show_completed', 'true');
    
    const queryString = searchParams.toString();
    return this.request(`/faculty/dashboard${queryString ? `?${queryString}` : ''}`);
  }

  async getFacultyActivityLog(limit: number = 100): Promise<any> {
    return this.request(`/faculty/activity-log?limit=${limit}`);
  }

  async getNotifications(): Promise<any> {
    return this.request('/faculty/notifications');
  }

  async markNotificationsRead(notificationIds: string[]): Promise<any> {
    return this.request('/faculty/notifications/mark-read', {
      method: 'POST',
      body: JSON.stringify({ notification_ids: notificationIds }),
    });
  }

  // ============================================================
  // COURSE LEAD DASHBOARD
  // ============================================================
  
  async getCourseLeadDashboard(department: string, academicYear: string): Promise<any> {
    return this.request(`/lead/dashboard?department=${department}&academic_year=${academicYear}`);
  }

  async approveSubmission(approvalId: string, comments?: string): Promise<any> {
    const params = comments ? `?comments=${encodeURIComponent(comments)}` : '';
    return this.request(`/lead/approve/${approvalId}${params}`, {
      method: 'POST',
    });
  }

  async getCOHealthAnalysis(department: string, academicYear: string): Promise<any> {
    return this.request(`/lead/co-health/${department}?academic_year=${academicYear}`);
  }

  async getPOTargets(department: string, academicYear: string): Promise<any> {
    return this.request(`/lead/po-targets/${department}?academic_year=${academicYear}`);
  }

  async getLeadMarksApproval(submissionId: string): Promise<any> {
    return this.request(`/lead/marks-approval/${submissionId}`);
  }

  async approveLeadMarksApproval(submissionId: string, comments?: string): Promise<any> {
    return this.request(`/lead/marks-approval/${submissionId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ comments }),
    });
  }

  async returnLeadMarksApproval(submissionId: string, reason: string): Promise<any> {
    return this.request(`/lead/marks-approval/${submissionId}/return`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  async overrideLeadMarksApproval(submissionId: string, reason: string): Promise<any> {
    return this.request(`/lead/marks-approval/${submissionId}/override`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  async getLeadCOAttainment(params?: { department?: string; course_id?: string; academic_year?: string }): Promise<any> {
    const searchParams = new URLSearchParams();
    if (params?.department) searchParams.append('department', params.department);
    if (params?.course_id) searchParams.append('course_id', params.course_id);
    if (params?.academic_year) searchParams.append('academic_year', params.academic_year);
    const queryString = searchParams.toString();
    return this.request(`/lead/co-attainment${queryString ? `?${queryString}` : ''}`);
  }

  async overrideLeadCOAttainment(payload: {
    course_id: string;
    co_code: string;
    override_pct: number;
    reason: string;
  }): Promise<any> {
    return this.request('/lead/co-attainment/override', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getLeadPOAttainment(params?: { department?: string; academic_year?: string }): Promise<any> {
    const searchParams = new URLSearchParams();
    if (params?.department) searchParams.append('department', params.department);
    if (params?.academic_year) searchParams.append('academic_year', params.academic_year);
    const queryString = searchParams.toString();
    return this.request(`/lead/po-attainment${queryString ? `?${queryString}` : ''}`);
  }

  async getLeadAYComparison(params?: { course_id?: string; department?: string; years?: number }): Promise<any> {
    const searchParams = new URLSearchParams();
    // Backend requires course_id; department+years are fallback for HOD view
    if (params?.course_id) searchParams.append('course_id', params.course_id);
    if (params?.department) searchParams.append('department', params.department);
    if (params?.years) searchParams.append('years', String(params.years));
    const queryString = searchParams.toString();
    return this.request(`/lead/ay-comparison${queryString ? `?${queryString}` : ''}`);
  }

  async getLeadReports(params?: { department?: string; academic_year?: string }): Promise<any> {
    const searchParams = new URLSearchParams();
    if (params?.department) searchParams.append('department', params.department);
    if (params?.academic_year) searchParams.append('academic_year', params.academic_year);
    const queryString = searchParams.toString();
    return this.request(`/lead/reports${queryString ? `?${queryString}` : ''}`);
  }

  async generateLeadReport(payload: Record<string, any>): Promise<any> {
    const searchParams = new URLSearchParams();
    Object.entries(payload || {}).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return;
      searchParams.append(key, String(value));
    });
    const queryString = searchParams.toString();
    return this.request(`/lead/reports/generate${queryString ? `?${queryString}` : ''}`, {
      method: 'POST',
    });
  }

  async downloadLeadReport(params?: { format?: 'pdf' | 'excel' | 'nba'; report_type?: string; course_id?: string }): Promise<any> {
    const searchParams = new URLSearchParams();
    if (params?.format) searchParams.append('format', params.format);
    if (params?.report_type) searchParams.append('report_type', params.report_type);
    if (params?.course_id) searchParams.append('course_id', params.course_id);
    const queryString = searchParams.toString();
    return this.request(`/lead/reports/download${queryString ? `?${queryString}` : ''}`);
  }

  async getLeadReportHistory(limit: number = 50, department?: string): Promise<any> {
    const params = new URLSearchParams();
    if (department) params.append('department', department);
    params.append('limit', String(limit));
    return this.request(`/lead/reports/history?${params.toString()}`);
  }

  // ============================================================
  // ACADEMIC YEARS
  // ============================================================
  
  async getAcademicYears(): Promise<any> {
    return this.request('/academic-years');
  }

  async getCurrentAcademicYear(): Promise<any> {
    return this.request('/academic-years/current');
  }

  async createAcademicYear(data: {
    code: string;
    name: string;
    start_date: string;
    end_date: string;
    is_active: boolean;
  }): Promise<any> {
    return this.request('/academic-years', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async lockAcademicYear(ayCode: string): Promise<any> {
    return this.request(`/academic-years/${ayCode}/lock`, {
      method: 'POST',
    });
  }

  async getUsers(): Promise<any[]> {
    return this.request('/users');
  }

  async updateUser(userId: string, data: { role?: string; department?: string; full_name?: string; is_active?: boolean }): Promise<any> {
    return this.request(`/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getPrograms(): Promise<{ id: string; code: string; name: string; description?: string }[]> {
    return this.request('/programs');
  }

  async getAuditLog(limit: number = 200): Promise<any[]> {
    return this.request(`/audit-log?limit=${limit}`);
  }

  async getThresholds(): Promise<{ level2: number; level3: number; pass_threshold: number }> {
    return this.request('/settings/thresholds');
  }

  async setThresholds(data: { level2?: number; level3?: number; pass_threshold?: number }): Promise<any> {
    return this.request('/settings/thresholds', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // ============================================================
  // UTILITIES
  // ============================================================
  
  async getBloomVerbs(level?: string): Promise<any> {
    const params = level ? `?level=${level}` : '';
    return this.request(`/outcomes/bt-verbs${params}`);
  }

  async searchQuestions(query: string, size: number = 10): Promise<any> {
    return this.request('/search/questions', {
      method: 'POST',
      body: JSON.stringify({ query, size }),
    });
  }

  async uploadFile(file: File, bucket: string = 'obe-uploads', folder: string = 'uploads'): Promise<any> {
    const base = getBaseURL();
    const formData = new FormData();
    formData.append('file', file);
    return this.request(`/files/upload?bucket=${bucket}&folder=${folder}`, {
      method: 'POST',
      headers: { ...this.getAuthHeader() },
      body: formData,
    });
  }

  async healthCheck(): Promise<any> {
    return this.request('/health');
  }

  // ============================================================
  // LOGOUT
  // ============================================================
  
  logout(): void {
    this.token = null;
    if (typeof window !== 'undefined') localStorage.removeItem('auth_token');
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
export default apiClient;
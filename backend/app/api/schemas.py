from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserLogin(BaseModel):
    email: Optional[EmailStr] = None
    employee_id: Optional[str] = None
    password: str
    department: Optional[str] = None
    academic_year: Optional[str] = None
    remember_me: bool = False


# Alias for backwards compatibility
UserLoginRequest = UserLogin


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    role: Optional[str] = "faculty"
    department: Optional[str] = None


# Alias for backwards compatibility
UserRegisterRequest = UserRegister


class ForgotPasswordRequest(BaseModel):
    employee_id: str
    email: EmailStr


class ResendOtpRequest(BaseModel):
    employee_id: str
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    employee_id: str
    email: EmailStr
    otp: str


class ResetPasswordRequest(BaseModel):
    employee_id: str
    email: EmailStr
    otp: str
    new_password: str
    confirm_password: str


class ChangePasswordRequest(BaseModel):
    """Authenticated user change password (e.g. first-login or profile)."""
    old_password: str
    new_password: str
    confirm_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    role: str


class UserResponse(BaseModel):
    """User response schema (non-sensitive fields only)"""
    id: str
    username: str
    email: str
    full_name: str  
    role: str
    department: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    course_code: str
    course_name: str
    credits: int
    semester: int
    description: Optional[str] = None
    department: Optional[str] = None
    course_type: Optional[str] = "core"
    enrolled_students: Optional[int] = 0
    fa_method: Optional[str] = "best_n_of_m"
    fa_best_n: Optional[int] = 3
    fa_total_components: Optional[int] = 5
    fa_weight: Optional[float] = 0.40
    sa_weight: Optional[float] = 0.60


class CourseResponse(BaseModel):
    id: str
    course_code: str
    course_name: str
    credits: Optional[int] = None
    semester: Optional[int] = None
    description: Optional[str] = None
    department: Optional[str] = None
    course_type: Optional[str] = None
    enrolled_students: Optional[int] = None
    fa_method: Optional[str] = None
    fa_best_n: Optional[int] = None
    fa_total_components: Optional[int] = None
    fa_weight: Optional[float] = None
    sa_weight: Optional[float] = None
    syllabus: Optional[str] = None
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class COCreate(BaseModel):
    co_code: str
    co_statement: str
    bloom_level: str
    description: Optional[str] = None


class COResponse(BaseModel):
    id: str
    course_id: str
    code: str
    statement: str
    bloom_level: str
    description: Optional[str]
    
    class Config:
        from_attributes = True


class ExamCreate(BaseModel):
    assessment_code: Optional[str] = None
    exam_name: str
    exam_type: str
    total_marks: int
    duration_minutes: Optional[int] = 120
    weightage_pct: Optional[float] = None
    exam_date: Optional[datetime] = None
    units_covered: Optional[List[str]] = None
    number_of_questions: Optional[int] = None


class ExamResponse(BaseModel):
    id: str
    course_id: str
    exam_name: str
    exam_type: str
    total_marks: int
    duration_minutes: int
    
    class Config:
        from_attributes = True


class MarksUpload(BaseModel):
    student_id: str
    question_id: str
    marks_obtained: float


class AttainmentResponse(BaseModel):
    co_id: str
    co_code: str
    attainment_percentage: float
    attainment_level: str
    total_marks: int
    total_obtained: float
    students: int


class ReportResponse(BaseModel):
    id: str
    report_type: str
    title: str
    course_id: Optional[str]
    generated_by: str
    generated_at: datetime
    file_format: str
    
    class Config:
        from_attributes = True


# ─── New Schemas for OBE Chatbot System ───────────────────────────────────────

class ProgramOutcomeInput(BaseModel):
    """PO or PSO for use in CO generation"""
    code: str
    statement: str


class COGenerateRequest(BaseModel):
    """Request to generate COs from syllabus with PO/PSO alignment"""
    syllabus: Optional[str] = None
    program_outcomes: List[ProgramOutcomeInput] = Field(default_factory=list)
    program_specific_outcomes: List[ProgramOutcomeInput] = Field(default_factory=list)
    num_cos: int = 5


class COGenerateResponse(BaseModel):
    """Response with generated COs and their PO/PSO mappings"""
    course_outcomes: List[Dict[str, Any]]
    co_po_mappings: List[Dict[str, Any]]
    co_pso_mappings: List[Dict[str, Any]]
    total_cos: int


class SyllabusUpdate(BaseModel):
    """Update course syllabus"""
    syllabus: str


class QuestionCreate(BaseModel):
    """A single exam question with marks"""
    question_number: int
    question_text: str
    marks: float
    question_type: str = "long_answer"
    bloom_level: Optional[str] = None
    part_label: Optional[str] = None
    either_or_pair: Optional[str] = None
    co_mapped: Optional[List[str]] = None
    co_ids: Optional[List[str]] = None
    co_code: Optional[str] = None
    co_codes: Optional[List[str]] = None
    override_reason: Optional[str] = None


class QuestionsAddRequest(BaseModel):
    """Add multiple questions to an exam"""
    questions: List[QuestionCreate]


class BulkMarksRow(BaseModel):
    """A single student's marks row – question numbers as string keys"""
    student_id: str
    marks: Dict[str, float]   # {"1": 8.0, "2": 7.0, "3": 12.0, ...}


class BulkMarksRequest(BaseModel):
    """Spreadsheet-style marks upload: one row per student"""
    rows: List[BulkMarksRow]


class ChatMessage(BaseModel):
    """Chatbot conversation message"""
    message: Optional[str] = None
    text: Optional[str] = None
    course_id: Optional[str] = None
    session_id: Optional[str] = None
    message_number: Optional[int] = None


class ChatResponse(BaseModel):
    """Chatbot response"""
    reply: str
    intent: Optional[str] = None
    nlu_confidence: Optional[float] = None
    nlu_source: Optional[str] = None   # "rasa" | "keyword"
    data: Optional[Dict[str, Any]] = None
    session_id: str


class COAttainmentDetail(BaseModel):
    co_id: str
    co_code: str
    co_statement: str
    attainment_percentage: float
    attainment_level: str
    total_marks: int
    total_obtained: float
    students: int


class POAttainmentDetail(BaseModel):
    po_id: str
    po_code: str
    po_statement: str
    attainment_percentage: float
    attainment_level: str
    mapped_cos: int


class PSOMappingRequest(BaseModel):
    """Request for PSO attainment calculation"""
    course_id: str
    program_id: str
    pso_id: Optional[str] = None  # None = calculate all PSOs


class QuestionSearchRequest(BaseModel):
    query: str
    size: int = 20


class PresignRequest(BaseModel):
    bucket: str
    key: str
    expires_in: Optional[int] = None


class NotificationMarkReadRequest(BaseModel):
    notification_ids: List[str]


class AcademicYearConfig(BaseModel):
    code: str
    is_active: bool = True
    is_locked: bool = False
    read_only: bool = False
    lock_date: Optional[datetime] = None


class COMappingsUpdate(BaseModel):
    """Update PO and PSO code mappings for a CO (inline multi-select in CO table)"""
    po_codes: List[str] = []
    pso_codes: List[str] = []
    # correlation weights: {"PO1": 3, "PO2": 2, ...}  — 1/2/3 scale
    po_levels: Dict[str, int] = {}
    pso_levels: Dict[str, int] = {}
    program_id: Optional[str] = None


# ─── Course Lead Dashboard Schemas ────────────────────────────────────────────

class ApprovalQueueItem(BaseModel):
    """Single item in the approval queue"""
    id: str
    course: str
    faculty: str
    exam: str
    submitted: str
    wait_time: str
    wait_time_hours: float
    urgency: str
    urgency_color: str
    action_link: str


class COHealthItem(BaseModel):
    """CO health status for a single CO"""
    code: str
    level: str
    percentage: Optional[float]
    color: str
    bold: bool


class CourseHealthRow(BaseModel):
    """CO health row for a single course"""
    course: str
    course_id: str
    cos: List[COHealthItem]
    faculty: str


class POSummaryItem(BaseModel):
    """PO summary with target tracking"""
    code: str
    attainment_pct: float
    target_pct: float
    level: str
    target_met: str
    status_color: str


class RecentActionItem(BaseModel):
    """Recent action item"""
    index: int
    action: str
    timestamp: str


class CourseLeadDashboardResponse(BaseModel):
    """Complete Course Lead Dashboard response"""
    header: Dict[str, str]
    approval_queue: List[ApprovalQueueItem]
    co_health_table: List[CourseHealthRow]
    po_summary: List[POSummaryItem]
    pso_summary: str
    recent_actions: List[RecentActionItem]
    statistics: Dict[str, int]


class ApprovalRequest(BaseModel):
    """Request to approve a submission"""
    comments: Optional[str] = None


class Level1COItem(BaseModel):
    """Level 1 CO requiring remedial action"""
    course_code: str
    course_name: str
    co_code: str
    co_statement: str
    attainment_percentage: float
    calculated_at: str
    urgency: str
    recommended_action: str


class COHealthAnalysisResponse(BaseModel):
    """Detailed CO health analysis response"""
    department: str
    academic_year: str
    total_courses: int
    level1_cos: List[Level1COItem]
    level1_count: int
    critical_count: int


class POTargetItem(BaseModel):
    """PO target tracking item"""
    code: str
    statement: str
    current_percentage: float
    target_percentage: float
    gap: float
    status: str
    level: str
    course_count: int
    color: str


class POTargetsResponse(BaseModel):
    """PO targets tracking response"""
    department: str
    academic_year: str
    po_targets: List[POTargetItem]
    summary: Dict[str, Any]


# ─── L2 - Marks Approval Page Schemas ─────────────────────────────────────────

class MarksApprovalHeader(BaseModel):
    """L2-01: Submission header"""
    title: str

class QuestionHeader(BaseModel):
    """Question header for marks table"""
    question_text: str
    max_marks: float
    co_code: str

class MarksTableData(BaseModel):
    """L2-02: Read-only marks table data"""
    headers: Dict[int, QuestionHeader]
    data: Dict[str, Dict[int, Dict[str, float]]]
    readonly: bool

class AnomalyData(BaseModel):
    """L2-03/L2-04: Anomaly detection data"""
    zero_total: List[str]
    full_marks: List[str]
    summary: str

class COPreview(BaseModel):
    """L2-05: CO preview panel"""
    title: str
    co_previews: List[Dict[str, Any]]

class PreviousComparison(BaseModel):
    """L2-06: Previous exam comparison"""
    comparisons: List[str]

class SubmissionHistory(BaseModel):
    """L2-12: Submission history"""
    date: str
    status: str
    comment: str

class MarksApprovalResponse(BaseModel):
    """Complete L2 marks approval page response"""
    submission_id: str
    exam_id: str
    header: MarksApprovalHeader
    marks_table: MarksTableData
    anomalies: AnomalyData
    co_preview: COPreview
    previous_comparison: PreviousComparison
    submission_history: List[SubmissionHistory]
    can_override: bool
    status: str


# ─── L3 - CO Attainment Page Schemas ──────────────────────────────────────────

class COData(BaseModel):
    """Individual CO data for L3-04"""
    co_code: str
    statement: str
    cie_percentage: float
    see_percentage: float
    final_percentage: float
    level: str
    remedial_status: str
    can_override: bool

class CourseRow(BaseModel):
    """L3-02/L3-03: Course row with expandable COs"""
    course_id: str
    course_code: str
    course_name: str
    faculty: str
    cos_generated: int
    overall_avg_level: str
    marks_status: str
    cos_data: List[COData]
    expanded: bool

class COAttainmentFilters(BaseModel):
    """L3-01: Filter controls"""
    course_filter: Optional[str]
    semester_filter: Optional[int]
    status_filter: str

class COAttainmentResponse(BaseModel):
    """Complete L3 CO attainment page response"""
    department: str
    academic_year: str
    filters: COAttainmentFilters
    course_rows: List[CourseRow]
    total_courses: int

class COOverrideRequest(BaseModel):
    """L3-05: CO override request"""
    new_level: str
    justification: str

class CourseComparisonResponse(BaseModel):
    """L3-08: Side comparison response"""
    comparison_type: str
    course1: Dict[str, Any]
    course2: Dict[str, Any]


# ─── L4 - PO & PSO Attainment Page Schemas ────────────────────────────────────

class COContribution(BaseModel):
    """L4-03: CO contribution to PO"""
    co_code: str
    correlation_weight: float
    co_attainment: float
    weighted_contribution: float

class POTableItem(BaseModel):
    """L4-01: PO table item with gap analysis"""
    po_id: str
    po_code: str
    statement: str
    mapped_cos: int
    weighted_attainment: float
    level: str
    target: float
    gap: float
    gap_color: str
    co_contributions: List[COContribution]
    expanded: bool

class PSOTableItem(BaseModel):
    """L4-05: PSO table item"""
    pso_id: str
    pso_code: str
    statement: str
    mapped_cos: int
    weighted_attainment: float
    level: str
    target: float
    gap: float
    gap_color: str

class POChartData(BaseModel):
    """L4-04: PO bar chart data"""
    labels: List[str]
    attainments: List[float]
    threshold: float
    colors: List[str]

class FormulaReference(BaseModel):
    """L4-06: Formula reference"""
    po_formula: str
    pso_formula: str
    worked_example: Dict[str, str]

class POPSOAttainmentResponse(BaseModel):
    """Complete L4 PO & PSO attainment page response"""
    department: str
    academic_year: str
    po_table: List[POTableItem]
    pso_table: List[PSOTableItem]
    po_chart_data: POChartData
    formula_reference: FormulaReference


# ─── L5 - Academic Year Comparison Page Schemas ───────────────────────────────

class ComparisonRow(BaseModel):
    """L5-02: Comparison table row"""
    co_code: str
    co_statement: str
    ay_2022_23: float
    ay_2023_24: float
    ay_2024_25: float
    trend_direction: str
    trend_percentage: float
    persistent_low: bool
    row_color: str

class ChartDataset(BaseModel):
    """L5-05: Chart dataset for trend analysis"""
    label: str
    data: List[float]
    borderColor: str
    backgroundColor: str

class TrendChartData(BaseModel):
    """L5-05: Trend chart data"""
    labels: List[str]
    datasets: List[ChartDataset]

class ComparisonSummary(BaseModel):
    """Comparison summary statistics"""
    total_cos: int
    improving_cos: int
    declining_cos: int
    persistent_low_cos: int

class AYComparisonResponse(BaseModel):
    """Complete L5 academic year comparison response"""
    course_id: str
    course_code: str
    course_name: str
    academic_years: List[str]
    comparison_table: List[ComparisonRow]
    chart_data: TrendChartData
    summary: ComparisonSummary


# ─── L6 - Lead Reports Page Schemas ───────────────────────────────────────────

class ReportType(BaseModel):
    """L6-01: Report type option"""
    value: str
    label: str
    description: str

class FilterOption(BaseModel):
    """L6-02: Filter option"""
    value: str
    label: str

class ReportFilters(BaseModel):
    """L6-02: Report filter controls"""
    course_options: List[FilterOption]
    exam_options: List[FilterOption]
    selected_course: Optional[str]
    selected_exam: Optional[str]

class ReportPreview(BaseModel):
    """Report preview data"""
    report_type: str
    estimated_pages: int
    estimated_size: str
    contains: List[str]

class LeadReportsPageResponse(BaseModel):
    """Complete L6 lead reports page response"""
    department: str
    academic_year: str
    report_types: List[ReportType]
    current_report_type: str
    filters: ReportFilters
    recent_reports: ReportPreview
    can_generate: bool

class GenerateReportRequest(BaseModel):
    """L6-03: Generate report request"""
    department: str
    academic_year: str
    report_type: str
    course_filter: Optional[str] = None
    exam_filter: Optional[str] = None

class DownloadLinks(BaseModel):
    """L6-04/L6-05: Download links"""
    pdf: str
    excel: str
    nba: Optional[str]

class GenerateReportResponse(BaseModel):
    """L6-03: Generate report response"""
    report_id: str
    status: str
    title: str
    generated_at: str
    pdf_preview_base64: str
    download_links: DownloadLinks

class ReportHistoryItem(BaseModel):
    """L6-06: Report history item"""
    report_id: str
    title: str
    report_type: str
    generated_at: str
    generated_by: str
    file_format: str
    download_links: Dict[str, str]
    is_archived: bool

class ReportHistoryResponse(BaseModel):
    """L6-06: Report history response"""
    department: str
    total_reports: int
    reports: List[ReportHistoryItem]


# ─── General Course Lead Schemas ──────────────────────────────────────────────

class ApprovalActionRequest(BaseModel):
    """Request for approval actions"""
    comments: Optional[str] = None
    reason: Optional[str] = None

class OverrideRequest(BaseModel):
    """HOD override request"""
    marks_data: Dict[str, Any]
    override_reason: str


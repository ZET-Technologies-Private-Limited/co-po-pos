"""
SQLAlchemy ORM models for all database entities
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, DECIMAL, Index, UniqueConstraint,
    JSON, Table, TypeDecorator, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from app.core.config.constants import (
    UserRole, BloomTaxonomyLevel, OutcomeType, ExamType, QuestionType
)


# TypeDecorator to handle ENUM/String conversion for PostgreSQL compatibility
class EnumString(TypeDecorator):
    """A type that can store both ENUM and String values"""
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # Convert enum to string value
        if hasattr(value, 'value'):
            return value.value
        return str(value)
    
    def process_result_value(self, value, dialect):
        return value

Base = declarative_base()

# Association tables for many-to-many relationships
co_po_mapping_table = Table(
    'co_po_mapping',
    Base.metadata,
    Column('course_outcome_id', String(36), ForeignKey('course_outcomes.id')),
    Column('program_outcome_id', String(36), ForeignKey('program_outcomes.id')),
    Column('similarity_score', Float, default=0.0),
)

co_pso_mapping_table = Table(
    'co_pso_mapping',
    Base.metadata,
    Column('course_outcome_id', String(36), ForeignKey('course_outcomes.id')),
    Column('program_specific_outcome_id', String(36), ForeignKey('program_specific_outcomes.id')),
    Column('similarity_score', Float, default=0.0),
)

question_co_mapping_table = Table(
    'question_co_mapping',
    Base.metadata,
    Column('question_id', String(36), ForeignKey('exam_questions.id')),
    Column('course_outcome_id', String(36), ForeignKey('course_outcomes.id')),
    Column('similarity_score', Float, default=0.0),
    Column('confidence_score', Float, default=0.0),
)


class User(Base):
    """User accounts with authentication"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, native_enum=True), default=UserRole.VIEWER, nullable=False)
    department = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (Index('idx_user_email', 'email'),)


class Course(Base):
    """Academic courses"""
    __tablename__ = "courses"
    
    id = Column(String(36), primary_key=True)
    course_code = Column(String(50), unique=True, nullable=False, index=True)
    course_name = Column(String(255), nullable=False)
    description = Column(Text)
    credits = Column(Integer, default=3)
    semester = Column(Integer)
    course_type = Column(String(20), default="core")
    enrolled_students = Column(Integer, default=0)
    fa_method = Column(String(50), default="best_n_of_m")
    fa_best_n = Column(Integer, default=3)
    fa_total_components = Column(Integer, default=5)
    fa_weight = Column(Float, default=0.40)
    sa_weight = Column(Float, default=0.60)
    department = Column(String(255))
    syllabus = Column(Text)
    syllabus_embedding_id = Column(String(255))  # Pinecone vector ID
    created_by = Column(String(36), ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    course_outcomes = relationship("CourseOutcome", back_populates="course")
    exams = relationship("Exam", back_populates="course")


class CourseOutcome(Base):
    """Course Outcomes (CO) - Learning outcomes for courses"""
    __tablename__ = "course_outcomes"
    
    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False)
    code = Column(String(50), nullable=False)
    statement = Column(Text, nullable=False)
    bloom_level = Column(Enum(BloomTaxonomyLevel, native_enum=True), nullable=False)
    description = Column(Text)
    embedding_id = Column(String(255))  # Pinecone vector ID
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    course = relationship("Course", back_populates="course_outcomes")
    program_outcomes = relationship(
        "ProgramOutcome",
        secondary=co_po_mapping_table,
        back_populates="course_outcomes"
    )
    program_specific_outcomes = relationship(
        "ProgramSpecificOutcome",
        secondary=co_pso_mapping_table,
        back_populates="course_outcomes"
    )
    
    __table_args__ = (
        UniqueConstraint('course_id', 'code', name='uq_course_id_code'),
    )


class ProgramOutcome(Base):
    """Program Outcomes (PO)"""
    __tablename__ = "program_outcomes"
    
    id = Column(String(36), primary_key=True)
    code = Column(String(50), nullable=False)
    statement = Column(Text, nullable=False)
    description = Column(Text)
    program = Column(String(255), nullable=False)
    embedding_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    course_outcomes = relationship(
        "CourseOutcome",
        secondary=co_po_mapping_table,
        back_populates="program_outcomes"
    )

    __table_args__ = (
        UniqueConstraint('program', 'code', name='uq_program_outcome_program_code'),
    )


class ProgramSpecificOutcome(Base):
    """Program Specific Outcomes (PSO)"""
    __tablename__ = "program_specific_outcomes"
    
    id = Column(String(36), primary_key=True)
    code = Column(String(50), nullable=False)
    statement = Column(Text, nullable=False)
    description = Column(Text)
    program = Column(String(255), nullable=False)
    embedding_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    course_outcomes = relationship(
        "CourseOutcome",
        secondary=co_pso_mapping_table,
        back_populates="program_specific_outcomes"
    )

    __table_args__ = (
        UniqueConstraint('program', 'code', name='uq_program_specific_outcome_program_code'),
    )


class Exam(Base):
    """Exam configurations"""
    __tablename__ = "exams"
    
    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False)
    exam_name = Column(String(255), nullable=False)
    exam_type = Column(Enum(ExamType, native_enum=True), nullable=False)
    total_marks = Column(Integer, nullable=False)
    duration_minutes = Column(Integer)
    exam_date = Column(DateTime)
    question_count = Column(Integer, default=0)
    created_by = Column(String(36), ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    course = relationship("Course", back_populates="exams")
    questions = relationship("ExamQuestion", back_populates="exam")
    marks = relationship("StudentMarks", back_populates="exam")


class ExamQuestion(Base):
    """Exam questions with Bloom's Taxonomy mapping"""
    __tablename__ = "exam_questions"
    
    id = Column(String(36), primary_key=True)
    exam_id = Column(String(36), ForeignKey('exams.id'), nullable=False)
    question_number = Column(Integer)
    question_text = Column(Text, nullable=False)
    marks = Column(Integer, nullable=False)
    question_type = Column(Enum(QuestionType, native_enum=True), nullable=False)
    bloom_level = Column(Enum(BloomTaxonomyLevel, native_enum=True))
    bloom_confidence = Column(Float, default=0.0)
    embedding_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    exam = relationship("Exam", back_populates="questions")
    course_outcomes = relationship(
        "CourseOutcome",
        secondary=question_co_mapping_table,
        lazy="joined"
    )


class StudentMarks(Base):
    """Student marks for exam questions"""
    __tablename__ = "student_marks"
    
    id = Column(String(36), primary_key=True)
    exam_id = Column(String(36), ForeignKey('exams.id'), nullable=False)
    student_id = Column(String(255), nullable=False)  # External student ID
    question_id = Column(String(36), ForeignKey('exam_questions.id'))
    marks_obtained = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    exam = relationship("Exam", back_populates="marks")
    
    __table_args__ = (
        UniqueConstraint('exam_id', 'student_id', 'question_id', 
                        name='uq_exam_student_question'),
    )


class COAttainment(Base):
    """Course Outcome attainment calculations"""
    __tablename__ = "co_attainments"
    
    id = Column(String(36), primary_key=True)
    course_outcome_id = Column(String(36), ForeignKey('course_outcomes.id'))
    exam_id = Column(String(36), ForeignKey('exams.id'))
    total_students = Column(Integer, default=0)
    total_marks = Column(Integer)
    marks_obtained = Column(DECIMAL(10, 2))
    attainment_percentage = Column(Float, default=0.0)
    attainment_level = Column(String(20))
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('course_outcome_id', 'exam_id', 
                        name='uq_co_exam_attainment'),
    )


class POAttainment(Base):
    """Program Outcome attainment calculations"""
    __tablename__ = "po_attainments"
    
    id = Column(String(36), primary_key=True)
    program_outcome_id = Column(String(36), ForeignKey('program_outcomes.id'))
    course_id = Column(String(36), ForeignKey('courses.id'))
    attainment_percentage = Column(Float, default=0.0)
    attainment_level = Column(String(20))
    co_count = Column(Integer, default=0)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('program_outcome_id', 'course_id', 
                        name='uq_po_course_attainment'),
    )


class Department(Base):
    """Academic departments"""
    __tablename__ = "departments"
    
    id = Column(String(36), primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    head_id = Column(String(36), ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Program(Base):
    """Academic programs/degrees"""
    __tablename__ = "programs"
    
    id = Column(String(36), primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    department_id = Column(String(36), ForeignKey('departments.id'), nullable=False)
    duration_years = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Student(Base):
    """Student records"""
    __tablename__ = "students"
    
    id = Column(String(36), primary_key=True)
    roll_number = Column(String(50), unique=True, nullable=False, index=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255))
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20))
    program_id = Column(String(36), ForeignKey('programs.id'), nullable=False)
    enrollment_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StudentEnrollment(Base):
    """Student course enrollments"""
    __tablename__ = "student_enrollments"
    
    id = Column(String(36), primary_key=True)
    student_id = Column(String(36), ForeignKey('students.id'), nullable=False)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False)
    semester = Column(Integer, nullable=False)
    academic_year = Column(String(10), nullable=False)
    enrollment_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='active')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('student_id', 'course_id', 'semester', 'academic_year',
                        name='uq_student_course_enrollment'),
    )


class ExamTypeRecord(Base):
    """Types of exams (midterm, final, quiz, etc.)"""
    __tablename__ = "exam_types"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    weight = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ExamStructure(Base):
    """Exam structure configurations"""
    __tablename__ = "exam_structures"
    
    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False)
    exam_type_id = Column(String(36), ForeignKey('exam_types.id'), nullable=False)
    total_questions = Column(Integer)
    total_marks = Column(Integer, nullable=False)
    duration_minutes = Column(Integer)
    passing_percentage = Column(Float, default=40.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('course_id', 'exam_type_id', name='uq_course_exam_type'),
    )


class CourseSyllabus(Base):
    """Detailed course syllabus and content"""
    __tablename__ = "course_syllabi"
    
    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    learning_resources = Column(Text)
    assessment_strategy = Column(Text)
    embedding_id = Column(String(255))
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExamResult(Base):
    """Student exam results summary"""
    __tablename__ = "exam_results"
    
    id = Column(String(36), primary_key=True)
    exam_id = Column(String(36), ForeignKey('exams.id'), nullable=False)
    student_id = Column(String(36), ForeignKey('students.id'), nullable=False)
    total_marks_obtained = Column(DECIMAL(10, 2), nullable=False)
    percentage = Column(Float)
    grade = Column(String(5))
    status = Column(String(50), default='completed')
    exam_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('exam_id', 'student_id', name='uq_exam_student_result'),
        Index('idx_exam_result_exam', 'exam_id'),
        Index('idx_exam_result_student', 'student_id'),
    )


class QuestionBloomLevel(Base):
    """Bloom's taxonomy level for each question"""
    __tablename__ = "question_bloom_levels"
    
    id = Column(String(36), primary_key=True)
    question_id = Column(String(36), ForeignKey('exam_questions.id'), nullable=False)
    bloom_level = Column(Enum(BloomTaxonomyLevel, native_enum=True), nullable=False)
    confidence_score = Column(Float, default=0.0)
    detection_method = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('question_id', name='uq_question_bloom'),
    )


class PSO_Attainment(Base):
    """Program Specific Outcome attainment calculations"""
    __tablename__ = "pso_attainments"
    
    id = Column(String(36), primary_key=True)
    pso_id = Column(String(36), ForeignKey('program_specific_outcomes.id'), nullable=False)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False)
    attainment_percentage = Column(Float, default=0.0)
    attainment_level = Column(String(20))
    co_count = Column(Integer, default=0)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('pso_id', 'course_id', name='uq_pso_course_attainment'),
    )


class Report(Base):
    """Generated reports and analytics"""
    __tablename__ = "reports"
    
    id = Column(String(36), primary_key=True)
    report_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    course_id = Column(String(36), ForeignKey('courses.id'))
    program_id = Column(String(36), ForeignKey('programs.id'))
    generated_by = Column(String(36), ForeignKey('users.id'))
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    file_path = Column(String(500))
    file_format = Column(String(50))
    data = Column(JSON)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AIRequest(Base):
    """Tracks AI processing requests"""
    __tablename__ = "ai_requests"
    
    id = Column(String(36), primary_key=True)
    request_type = Column(String(100), nullable=False)
    user_id = Column(String(36), ForeignKey('users.id'))
    input_data = Column(JSON, nullable=False)
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_ai_request_status', 'status'),
        Index('idx_ai_request_user', 'user_id'),
    )


class AIResponse(Base):
    """Stores AI processing responses"""
    __tablename__ = "ai_responses"
    
    id = Column(String(36), primary_key=True)
    request_id = Column(String(36), ForeignKey('ai_requests.id'), nullable=False)
    response_data = Column(JSON, nullable=False)
    confidence_score = Column(Float)
    model_used = Column(String(255))
    tokens_used = Column(Integer)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EmbeddingMetadata(Base):
    """Metadata for vector embeddings"""
    __tablename__ = "embedding_metadata"
    
    id = Column(String(36), primary_key=True)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(36), nullable=False)
    embedding_id = Column(String(255), nullable=False)
    vector_dimension = Column(Integer)
    embedding_model = Column(String(255))
    similarity_scores = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', name='uq_embedding_entity'),
        Index('idx_embedding_entity', 'entity_type', 'entity_id'),
    )


class ApprovalQueue(Base):
    """Course Lead approval queue for marks and CO submissions"""
    __tablename__ = "approval_queue"
    
    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False)
    faculty_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    exam_id = Column(String(36), ForeignKey('exams.id'))
    submission_type = Column(String(50), nullable=False)  # 'marks', 'co_generation', 'exam_config'
    status = Column(String(50), default='pending', nullable=False)  # 'pending', 'approved', 'rejected', 'returned'
    priority = Column(String(20), default='normal')  # 'low', 'normal', 'high', 'critical'
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime)
    reviewed_by = Column(String(36), ForeignKey('users.id'))
    review_comments = Column(Text)
    data = Column(JSON)  # Submission data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_approval_status', 'status'),
        Index('idx_approval_submitted', 'submitted_at'),
        Index('idx_approval_course', 'course_id'),
    )


class RemedialAction(Base):
    """Remedial actions for Level 1 CO attainments"""
    __tablename__ = "remedial_actions"
    
    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False)
    course_outcome_id = Column(String(36), ForeignKey('course_outcomes.id'), nullable=False)
    attainment_percentage = Column(Float, nullable=False)
    action_plan = Column(Text, nullable=False)
    target_percentage = Column(Float, nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(String(50), default='pending')  # 'pending', 'in_progress', 'completed', 'overdue'
    assigned_to = Column(String(36), ForeignKey('users.id'), nullable=False)
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_remedial_status', 'status'),
        Index('idx_remedial_due', 'due_date'),
        Index('idx_remedial_course', 'course_id'),
    )


class POTarget(Base):
    """PO attainment targets and tracking"""
    __tablename__ = "po_targets"
    
    id = Column(String(36), primary_key=True)
    program_outcome_id = Column(String(36), ForeignKey('program_outcomes.id'), nullable=False)
    department = Column(String(255), nullable=False)
    academic_year = Column(String(10), nullable=False)
    target_percentage = Column(Float, nullable=False, default=70.0)
    current_percentage = Column(Float, default=0.0)
    status = Column(String(20), default='not_met')  # 'met', 'partial', 'not_met'
    courses_mapped = Column(Integer, default=0)
    last_calculated = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('program_outcome_id', 'department', 'academic_year', 
                        name='uq_po_target_dept_year'),
        Index('idx_po_target_status', 'status'),
    )


class PSOTarget(Base):
    """PSO attainment targets and tracking"""
    __tablename__ = "pso_targets"
    
    id = Column(String(36), primary_key=True)
    pso_id = Column(String(36), ForeignKey('program_specific_outcomes.id'), nullable=False)
    department = Column(String(255), nullable=False)
    academic_year = Column(String(10), nullable=False)
    target_percentage = Column(Float, nullable=False, default=70.0)
    current_percentage = Column(Float, default=0.0)
    status = Column(String(20), default='not_met')  # 'met', 'partial', 'not_met'
    courses_mapped = Column(Integer, default=0)
    last_calculated = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('pso_id', 'department', 'academic_year', 
                        name='uq_pso_target_dept_year'),
        Index('idx_pso_target_status', 'status'),
    )


class AuditLog(Base):
    """System audit log for tracking changes"""
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'))
    action = Column(String(255), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(String(36))
    changes = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (Index('idx_audit_timestamp', 'timestamp'),
                      Index('idx_audit_user', 'user_id'))

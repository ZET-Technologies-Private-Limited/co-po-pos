-- Complete CO-PO-PSO Mapping Database Schema
-- Highly normalized PostgreSQL schema for academic outcome assessment

-- 1. USER MANAGEMENT TABLES
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    department VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_email (email),
    INDEX idx_user_username (username)
);

-- 2. ACADEMIC STRUCTURE TABLES
CREATE TABLE IF NOT EXISTS departments (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    head_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (head_id) REFERENCES users(id),
    INDEX idx_dept_code (code)
);

CREATE TABLE IF NOT EXISTS programs (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    department_id VARCHAR(36) NOT NULL,
    duration_years INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id),
    INDEX idx_program_code (code),
    INDEX idx_program_dept (department_id)
);

CREATE TABLE IF NOT EXISTS students (
    id VARCHAR(36) PRIMARY KEY,
    roll_number VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    program_id VARCHAR(36) NOT NULL,
    enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (program_id) REFERENCES programs(id),
    INDEX idx_student_roll (roll_number),
    INDEX idx_student_email (email),
    INDEX idx_student_program (program_id)
);

CREATE TABLE IF NOT EXISTS courses (
    id VARCHAR(36) PRIMARY KEY,
    course_code VARCHAR(50) UNIQUE NOT NULL,
    course_name VARCHAR(255) NOT NULL,
    description TEXT,
    credits INTEGER DEFAULT 3,
    semester INTEGER,
    department VARCHAR(255),
    syllabus TEXT,
    syllabus_embedding_id VARCHAR(255),
    created_by VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_course_code (course_code),
    INDEX idx_course_semester (semester)
);

CREATE TABLE IF NOT EXISTS course_syllabi (
    id VARCHAR(36) PRIMARY KEY,
    course_id VARCHAR(36) UNIQUE NOT NULL,
    content LONGTEXT NOT NULL,
    learning_resources TEXT,
    assessment_strategy TEXT,
    embedding_id VARCHAR(255),
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id),
    INDEX idx_syllabus_course (course_id)
);

CREATE TABLE IF NOT EXISTS student_enrollments (
    id VARCHAR(36) PRIMARY KEY,
    student_id VARCHAR(36) NOT NULL,
    course_id VARCHAR(36) NOT NULL,
    semester INTEGER NOT NULL,
    academic_year VARCHAR(10) NOT NULL,
    enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    UNIQUE KEY uq_student_course_enrollment (student_id, course_id, semester, academic_year),
    INDEX idx_enrollment_student (student_id),
    INDEX idx_enrollment_course (course_id)
);

-- 3. OUTCOME DEFINITION TABLES
CREATE TABLE IF NOT EXISTS course_outcomes (
    id VARCHAR(36) PRIMARY KEY,
    course_id VARCHAR(36) NOT NULL,
    code VARCHAR(50) NOT NULL,
    statement LONGTEXT NOT NULL,
    bloom_level VARCHAR(50) NOT NULL,
    description TEXT,
    embedding_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id),
    UNIQUE KEY uq_course_id_code (course_id, code),
    INDEX idx_co_course (course_id),
    INDEX idx_co_bloom (bloom_level)
);

CREATE TABLE IF NOT EXISTS program_outcomes (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    statement LONGTEXT NOT NULL,
    description TEXT,
    program VARCHAR(255) NOT NULL,
    embedding_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_po_code (code),
    INDEX idx_po_program (program)
);

CREATE TABLE IF NOT EXISTS program_specific_outcomes (
    id VARCHAR(36) PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    statement LONGTEXT NOT NULL,
    description TEXT,
    program VARCHAR(255) NOT NULL,
    embedding_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pso_code (code),
    INDEX idx_pso_program (program)
);

-- 4. OUTCOME MAPPING TABLES
CREATE TABLE IF NOT EXISTS co_po_mapping (
    course_outcome_id VARCHAR(36) NOT NULL,
    program_outcome_id VARCHAR(36) NOT NULL,
    similarity_score FLOAT DEFAULT 0.0,
    PRIMARY KEY (course_outcome_id, program_outcome_id),
    FOREIGN KEY (course_outcome_id) REFERENCES course_outcomes(id),
    FOREIGN KEY (program_outcome_id) REFERENCES program_outcomes(id),
    INDEX idx_co_po_score (similarity_score)
);

CREATE TABLE IF NOT EXISTS co_pso_mapping (
    course_outcome_id VARCHAR(36) NOT NULL,
    program_specific_outcome_id VARCHAR(36) NOT NULL,
    similarity_score FLOAT DEFAULT 0.0,
    PRIMARY KEY (course_outcome_id, program_specific_outcome_id),
    FOREIGN KEY (course_outcome_id) REFERENCES course_outcomes(id),
    FOREIGN KEY (program_specific_outcome_id) REFERENCES program_specific_outcomes(id),
    INDEX idx_co_pso_score (similarity_score)
);

-- 5. EXAM MANAGEMENT TABLES
CREATE TABLE IF NOT EXISTS exam_types (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_exam_type_code (code)
);

CREATE TABLE IF NOT EXISTS exam_structures (
    id VARCHAR(36) PRIMARY KEY,
    course_id VARCHAR(36) NOT NULL,
    exam_type_id VARCHAR(36) NOT NULL,
    total_questions INTEGER,
    total_marks INTEGER NOT NULL,
    duration_minutes INTEGER,
    passing_percentage FLOAT DEFAULT 40.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id),
    FOREIGN KEY (exam_type_id) REFERENCES exam_types(id),
    UNIQUE KEY uq_course_exam_type (course_id, exam_type_id),
    INDEX idx_exam_struct_course (course_id)
);

CREATE TABLE IF NOT EXISTS exams (
    id VARCHAR(36) PRIMARY KEY,
    course_id VARCHAR(36) NOT NULL,
    exam_name VARCHAR(255) NOT NULL,
    exam_type VARCHAR(50) NOT NULL,
    total_marks INTEGER NOT NULL,
    duration_minutes INTEGER,
    exam_date TIMESTAMP,
    question_count INTEGER DEFAULT 0,
    created_by VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_exam_course (course_id),
    INDEX idx_exam_date (exam_date)
);

CREATE TABLE IF NOT EXISTS exam_questions (
    id VARCHAR(36) PRIMARY KEY,
    exam_id VARCHAR(36) NOT NULL,
    question_number INTEGER,
    question_text LONGTEXT NOT NULL,
    marks INTEGER NOT NULL,
    question_type VARCHAR(50) NOT NULL,
    bloom_level VARCHAR(50),
    bloom_confidence FLOAT DEFAULT 0.0,
    embedding_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exam_id) REFERENCES exams(id),
    INDEX idx_question_exam (exam_id),
    INDEX idx_question_bloom (bloom_level)
);

CREATE TABLE IF NOT EXISTS question_bloom_levels (
    id VARCHAR(36) PRIMARY KEY,
    question_id VARCHAR(36) NOT NULL,
    bloom_level VARCHAR(50) NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    detection_method VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES exam_questions(id),
    UNIQUE KEY uq_question_bloom (question_id),
    INDEX idx_qbl_question (question_id)
);

CREATE TABLE IF NOT EXISTS question_co_mapping (
    question_id VARCHAR(36) NOT NULL,
    course_outcome_id VARCHAR(36) NOT NULL,
    similarity_score FLOAT DEFAULT 0.0,
    confidence_score FLOAT DEFAULT 0.0,
    PRIMARY KEY (question_id, course_outcome_id),
    FOREIGN KEY (question_id) REFERENCES exam_questions(id),
    FOREIGN KEY (course_outcome_id) REFERENCES course_outcomes(id),
    INDEX idx_q_co_score (similarity_score)
);

-- 6. STUDENT MARKS TABLES
CREATE TABLE IF NOT EXISTS student_marks (
    id VARCHAR(36) PRIMARY KEY,
    exam_id VARCHAR(36) NOT NULL,
    student_id VARCHAR(36) NOT NULL,
    question_id VARCHAR(36),
    marks_obtained DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exam_id) REFERENCES exams(id),
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (question_id) REFERENCES exam_questions(id),
    UNIQUE KEY uq_exam_student_question (exam_id, student_id, question_id),
    INDEX idx_marks_exam (exam_id),
    INDEX idx_marks_student (student_id)
);

CREATE TABLE IF NOT EXISTS exam_results (
    id VARCHAR(36) PRIMARY KEY,
    exam_id VARCHAR(36) NOT NULL,
    student_id VARCHAR(36) NOT NULL,
    total_marks_obtained DECIMAL(10, 2) NOT NULL,
    percentage FLOAT,
    grade VARCHAR(5),
    status VARCHAR(50) DEFAULT 'completed',
    exam_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exam_id) REFERENCES exams(id),
    FOREIGN KEY (student_id) REFERENCES students(id),
    UNIQUE KEY uq_exam_student_result (exam_id, student_id),
    INDEX idx_exam_result_exam (exam_id),
    INDEX idx_exam_result_student (student_id)
);

-- 7. ATTAINMENT ANALYTICS TABLES
CREATE TABLE IF NOT EXISTS co_attainments (
    id VARCHAR(36) PRIMARY KEY,
    course_outcome_id VARCHAR(36),
    exam_id VARCHAR(36),
    total_students INTEGER DEFAULT 0,
    total_marks INTEGER,
    marks_obtained DECIMAL(10, 2),
    attainment_percentage FLOAT DEFAULT 0.0,
    attainment_level VARCHAR(20),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_outcome_id) REFERENCES course_outcomes(id),
    FOREIGN KEY (exam_id) REFERENCES exams(id),
    UNIQUE KEY uq_co_exam_attainment (course_outcome_id, exam_id),
    INDEX idx_co_attain_co (course_outcome_id),
    INDEX idx_co_attain_exam (exam_id)
);

CREATE TABLE IF NOT EXISTS po_attainments (
    id VARCHAR(36) PRIMARY KEY,
    program_outcome_id VARCHAR(36),
    course_id VARCHAR(36),
    attainment_percentage FLOAT DEFAULT 0.0,
    attainment_level VARCHAR(20),
    co_count INTEGER DEFAULT 0,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (program_outcome_id) REFERENCES program_outcomes(id),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    UNIQUE KEY uq_po_course_attainment (program_outcome_id, course_id),
    INDEX idx_po_attain_po (program_outcome_id),
    INDEX idx_po_attain_course (course_id)
);

CREATE TABLE IF NOT EXISTS pso_attainments (
    id VARCHAR(36) PRIMARY KEY,
    pso_id VARCHAR(36),
    course_id VARCHAR(36),
    attainment_percentage FLOAT DEFAULT 0.0,
    attainment_level VARCHAR(20),
    co_count INTEGER DEFAULT 0,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pso_id) REFERENCES program_specific_outcomes(id),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    UNIQUE KEY uq_pso_course_attainment (pso_id, course_id),
    INDEX idx_pso_attain_pso (pso_id),
    INDEX idx_pso_attain_course (course_id)
);

-- 8. REPORTING TABLES
CREATE TABLE IF NOT EXISTS reports (
    id VARCHAR(36) PRIMARY KEY,
    report_type VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    course_id VARCHAR(36),
    program_id VARCHAR(36),
    generated_by VARCHAR(36),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path VARCHAR(500),
    file_format VARCHAR(50),
    data JSON,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id),
    FOREIGN KEY (program_id) REFERENCES programs(id),
    FOREIGN KEY (generated_by) REFERENCES users(id),
    INDEX idx_report_type (report_type),
    INDEX idx_report_date (generated_at)
);

-- 9. AI PROCESSING TABLES
CREATE TABLE IF NOT EXISTS ai_requests (
    id VARCHAR(36) PRIMARY KEY,
    request_type VARCHAR(100) NOT NULL,
    user_id VARCHAR(36),
    input_data JSON NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_ai_request_status (status),
    INDEX idx_ai_request_user (user_id),
    INDEX idx_ai_request_type (request_type)
);

CREATE TABLE IF NOT EXISTS ai_responses (
    id VARCHAR(36) PRIMARY KEY,
    request_id VARCHAR(36) NOT NULL,
    response_data JSON NOT NULL,
    confidence_score FLOAT,
    model_used VARCHAR(255),
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES ai_requests(id),
    INDEX idx_ai_response_request (request_id)
);

CREATE TABLE IF NOT EXISTS embedding_metadata (
    id VARCHAR(36) PRIMARY KEY,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(36) NOT NULL,
    embedding_id VARCHAR(255) NOT NULL,
    vector_dimension INTEGER,
    embedding_model VARCHAR(255),
    similarity_scores JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_embedding_entity (entity_type, entity_id),
    INDEX idx_embedding_entity (entity_type, entity_id)
);

-- 10. AUDIT LOGGING TABLES
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    action VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100),
    entity_id VARCHAR(36),
    changes JSON,
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_audit_timestamp (timestamp),
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_action (action)
);

-- Add foreign key constraints for relationships
ALTER TABLE courses ADD CONSTRAINT fk_course_created_by FOREIGN KEY (created_by) REFERENCES users(id);

-- Create composite indexes for common queries
CREATE INDEX idx_student_course_semester ON student_enrollments(student_id, course_id, semester);
CREATE INDEX idx_marks_exam_student ON student_marks(exam_id, student_id);
CREATE INDEX idx_exam_result_percentage ON exam_results(percentage);
CREATE INDEX idx_attainment_level ON co_attainments(attainment_level);

COMMIT;

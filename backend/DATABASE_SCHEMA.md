# Database Schema Documentation

## Core Tables

### Users
- `id` (PK): User identifier
- `username` (UNIQUE): User login name
- `email` (UNIQUE): User email
- `full_name`: User full name
- `hashed_password`: Bcrypt hashed password
- `role`: User role (admin, faculty, hod, accreditation_officer, viewer)
- `department`: Department
- `is_active`: Account status
- `is_verified`: Email verification status
- `created_at`, `updated_at`: Timestamps

### Courses
- `id` (PK): Course identifier
- `course_code` (UNIQUE): Course code (e.g., CS101)
- `course_name`: Course name
- `description`: Course description
- `credits`: Credit hours
- `semester`: Semester/year
- `department`: Department
- `syllabus`: Full syllabus text
- `syllabus_embedding_id`: Pinecone vector ID for syllabus embeddings
- `created_by` (FK -> Users.id): Creator user
- `created_at`, `updated_at`: Timestamps

### CourseOutcomes (CO)
- `id` (PK): Outcome identifier
- `course_id` (FK -> Courses.id): Associated course
- `code`: Outcome code (CO1, CO2, etc)
- `statement`: Full outcome statement
- `bloom_level`: Bloom's taxonomy level (remember, understand, apply, analyze, evaluate, create)
- `description`: Additional description
- `embedding_id`: Pinecone vector ID
- `is_active`: Status
- `created_at`, `updated_at`: Timestamps

### ProgramOutcomes (PO)
- `id` (PK): Outcome identifier
- `code` (UNIQUE): Outcome code
- `statement`: Outcome statement
- `description`: Description
- `program`: Program name
- `embedding_id`: Pinecone vector ID
- `created_at`, `updated_at`: Timestamps

### ProgramSpecificOutcomes (PSO)
- Similar structure to ProgramOutcomes
- Specific to program specializations

## Mapping Tables

### CO-PO Mapping
- `course_outcome_id` (FK): Course outcome
- `program_outcome_id` (FK): Program outcome
- `similarity_score`: Semantic similarity (0-1)

### CO-PSO Mapping
- `course_outcome_id` (FK): Course outcome
- `program_specific_outcome_id` (FK): Program specific outcome
- `similarity_score`: Semantic similarity (0-1)

### Question-CO Mapping
- `question_id` (FK): Exam question
- `course_outcome_id` (FK): Course outcome
- `similarity_score`: Semantic similarity
- `confidence_score`: Mapping confidence

## Exam-Related Tables

### Exams
- `id` (PK): Exam identifier
- `course_id` (FK): Associated course
- `exam_name`: Exam name
- `exam_type`: Type (mid_term, end_term, practical, assignment)
- `total_marks`: Total marks for exam
- `duration_minutes`: Duration
- `exam_date`: Date and time
- `question_count`: Number of questions
- `created_by` (FK): Creator user
- `created_at`, `updated_at`: Timestamps

### ExamQuestions
- `id` (PK): Question identifier
- `exam_id` (FK): Associated exam
- `question_number`: Question number
- `question_text`: Full question text
- `marks`: Marks for question
- `question_type`: Type (mcq, short_answer, long_answer, practical, essay)
- `bloom_level`: Detected Bloom level
- `bloom_confidence`: Detection confidence (0-1)
- `embedding_id`: Pinecone vector ID
- `created_at`: Timestamp

### StudentMarks
- `id` (PK): Record identifier
- `exam_id` (FK): Associated exam
- `student_id`: Student identifier (external system)
- `question_id` (FK): Associated question
- `marks_obtained`: Marks obtained
- `created_at`: Timestamp
- UNIQUE Constraint: (exam_id, student_id, question_id)

## Analytics Tables

### COAttainments
- `id` (PK): Record identifier
- `course_outcome_id` (FK): CO
- `exam_id` (FK): Associated exam
- `total_students`: Number of students
- `total_marks`: Total possible marks
- `marks_obtained`: Total marks obtained
- `attainment_percentage`: Percentage (0-1)
- `attainment_level`: Level (Level 3, Level 2, Level 1, Not Attained)
- `calculated_at`: Calculation timestamp
- UNIQUE Constraint: (course_outcome_id, exam_id)

### POAttainments
- `id` (PK): Record identifier
- `program_outcome_id` (FK): PO
- `course_id` (FK): Associated course
- `attainment_percentage`: Percentage (0-1)
- `attainment_level`: Level
- `co_count`: Number of COs mapped
- `calculated_at`: Calculation timestamp
- UNIQUE Constraint: (program_outcome_id, course_id)

## Audit Tables

### AuditLogs
- `id` (PK): Log identifier
- `user_id` (FK): User who made change
- `action`: Action type
- `entity_type`: Entity type modified
- `entity_id`: Entity identifier
- `changes`: JSON with changes
- `timestamp`: When it happened
- INDEX: timestamp for quick queries

## Formulas Used in Attainment Calculations

### CO Attainment
```
CO Attainment = Sum of marks in CO questions / Total possible marks for CO questions
```

### PO Attainment
```
PO Attainment = Average of all mapped CO attainments
PO Attainment = (CO1 + CO2 + ... + COn) / n
```

### PSO Attainment
```
PSO Attainment = Average of all mapped CO attainments (same as PO)
```

### Attainment Levels
- Level 3 (Fully Attained): ≥ 70%
- Level 2 (Partially Attained): 60% - 69%
- Level 1 (Minimally Attained): < 60%
- Not Attained: 0%

# Services Documentation

## Complete Service Layer Reference

All services implement **real business logic** with no mocks or placeholders.

---

## AuthService

**Location**: `app/modules/auth/services/auth_service.py`

### Purpose
User authentication, password hashing, and JWT token management.

### Methods

#### `register_user(username, email, password, full_name, role)`
Registers a new user with Bcrypt password hashing.

```python
user = await auth_service.register_user(
    username="john_doe",
    email="john@university.edu",
    password="SecurePassword123",
    full_name="John Doe",
    role="faculty"
)
# Returns: User object with id, email, role
```

**Security**: 
- Password hashed with Bcrypt (cost=12)
- Email uniqueness validated
- No plaintext passwords stored

#### `authenticate_user(email, password)`
Authenticates user with email and password.

```python
user = await auth_service.authenticate_user(
    email="john@university.edu",
    password="SecurePassword123"
)
# Returns: User object if valid, None if invalid
```

**Security**:
- Password verified against hash
- Failed attempts logged
- No information leakage

#### `create_access_token(user_id, expires_delta)`
Creates JWT access token.

```python
token = auth_service.create_access_token(user_id="uuid")
# Returns: JWT token string, valid for 30 minutes
```

**Token Structure**:
```json
{
  "user_id": "uuid",
  "exp": 1710345000
}
```

#### `verify_token(token)`
Verifies and decodes JWT token.

```python
user_id = auth_service.verify_token(token)
# Returns: user_id string if valid, None if expired/invalid
```

#### `get_user_by_id(user_id)`
Retrieves user information.

```python
user = await auth_service.get_user_by_id("user-uuid")
# Returns: User object
```

---

## CourseService

**Location**: `app/modules/courses/services/course_service.py`

### Purpose
Course lifecycle management: creation, retrieval, exam management.

### Methods

#### `create_course(course_code, course_name, credits, semester, description, faculty_id)`
Creates a new course.

```python
course = await course_service.create_course(
    course_code="CS301",
    course_name="Advanced Algorithms",
    credits=4,
    semester=3,
    description="Study of algorithm design patterns",
    faculty_id="faculty-uuid"
)
# Returns: Course object with unique id
```

**Validation**:
- Unique course code per semester
- 1-6 credits
- Valid semester number

#### `get_course(course_id)`
Retrieves course by ID.

```python
course = await course_service.get_course("course-uuid")
# Returns: Course object or None
```

#### `list_courses(semester)`
Lists all courses, optionally filtered by semester.

```python
courses = await course_service.list_courses(semester=3)
# Returns: List of Course objects
```

#### `create_exam(course_id, exam_name, exam_type, total_marks, duration_minutes)`
Creates exam for a course.

```python
exam = await course_service.create_exam(
    course_id="course-uuid",
    exam_name="Mid Term",
    exam_type="mid_term",
    total_marks=50,
    duration_minutes=120
)
# Returns: Exam object
```

#### `add_question(exam_id, question_text, marks, order)`
Adds question to exam.

```python
question = await course_service.add_question(
    exam_id="exam-uuid",
    question_text="Define data structure",
    marks=5,
    order=1
)
# Returns: ExamQuestion object
```

---

## AttainmentService

**Location**: `app/modules/attainment_engine/services/attainment_service.py`

### Purpose
Core business logic: Calculate real CO/PO/PSO attainment percentages.

### Real Formulas Implemented

#### CO Attainment Formula
```
Attainment = Sum(marks obtained for CO questions) / Sum(total marks for CO questions) × 100

Attainment Levels:
- Level 3 (Fully Attained): ≥70%
- Level 2 (Partially Attained): 60-69%
- Level 1 (Minimally Attained): <60%
```

#### PO Attainment Formula
```
Attainment = Average of all mapped CO attainments

Example:
PO1 mapped to CO1(80%), CO2(75%), CO3(85%)
PO1 Attainment = (80 + 75 + 85) / 3 = 80%
```

### Methods

#### `calculate_course_outcome_attainments(course_id, exam_id)`
Calculates CO attainments from student marks.

```python
attainments = await attainment_service.calculate_course_outcome_attainments(
    course_id="course-uuid",
    exam_id="exam-uuid"
)
# Returns: List of attainment dicts with percentages and levels
```

**Process**:
1. Get all COs for course
2. Find questions mapped to each CO
3. Sum student marks for those questions
4. Calculate percentage and level
5. Store in COAttainment table

**Output Example**:
```python
[
  {
    "co_id": "co-uuid",
    "co_code": "CO1",
    "attainment_percentage": 78.5,
    "attainment_level": "Level 3",
    "total_marks": 30,
    "total_obtained": 23.55,
    "students": 45
  }
]
```

#### `calculate_program_outcome_attainments(course_id, program_id)`
Calculates PO attainments from CO attainments.

```python
attainments = await attainment_service.calculate_program_outcome_attainments(
    course_id="course-uuid",
    program_id="program-uuid"
)
# Returns: List of PO attainments
```

**Process**:
1. Get all POs in program
2. Find COs mapped to each PO
3. Average CO attainments
4. Store in POAttainment table

#### `get_course_attainment_summary(course_id)`
Gets comprehensive course attainment report.

```python
summary = await attainment_service.get_course_attainment_summary("course-uuid")
# Returns: Detailed summary with CO/PO data and averages
```

**Output**:
```python
{
  "course_id": "uuid",
  "co_attainments": [
    {"id": "uuid", "percentage": 80.0, "level": "Level 3"}
  ],
  "po_attainments": [
    {"id": "uuid", "percentage": 77.5, "level": "Level 3"}
  ],
  "average_co_attainment": 80.0,
  "average_po_attainment": 77.5,
  "overall_level": "Level 3"
}
```

#### `generate_report(course_id, report_type, user_id)`
Generates comprehensive report.

```python
report = await attainment_service.generate_report(
    course_id="course-uuid",
    report_type="co_attainment",
    user_id="user-uuid"
)
# Returns: Report object with generated data
```

---

## CoGenerationService

**Location**: `app/modules/co_generation/services/co_generation_service.py`

### Purpose
Generate Course Outcomes from syllabus using AI.

### Methods

#### `create_course_outcome(course_id, co_code, co_statement, bloom_level, description)`
Creates a single course outcome.

```python
co = await co_gen_service.create_course_outcome(
    course_id="course-uuid",
    co_code="CO1",
    co_statement="Understand fundamental data structures",
    bloom_level="Understand",
    description="Learn about arrays, linked lists, stacks, queues"
)
# Returns: CourseOutcome object
```

#### `generate_cos_from_syllabus(course_id, syllabus_text)`
AI-powered CO generation from syllabus.

```python
cos = await co_gen_service.generate_cos_from_syllabus(
    course_id="course-uuid",
    syllabus_text="Module 1: Data structures... Module 2: Algorithms..."
)
# Returns: List of generated CourseOutcome objects
```

**Process**:
1. Send syllabus to LLM
2. Extract topics
3. Generate CO statements aligned to Bloom's
4. Store in database
5. Return created COs

#### `get_course_outcomes(course_id)`
Lists all COs for a course.

```python
cos = await co_gen_service.get_course_outcomes("course-uuid")
# Returns: List of CourseOutcome objects
```

---

## QuestionAnalysisService

**Location**: `app/modules/question_analysis/services/question_analysis_service.py`

### Purpose
Question analysis: Bloom level detection, marks processing.

### Methods

#### `process_marks_file(exam_id, csv_content)`
Uploads and processes student marks from CSV.

```python
result = await question_service.process_marks_file(
    exam_id="exam-uuid",
    content=b"student_id,question_id,marks\n..."
)
# Returns: {"rows_processed": 150}
```

**CSV Format**:
```
student_id,question_id,marks
s001,q001,4
s001,q002,8
s002,q001,5
...
```

#### `analyze_exam_questions(exam_id)`
Analyzes questions in an exam.

```python
analysis = await question_service.analyze_exam_questions("exam-uuid")
# Returns: Analysis with question statistics
```

**Output**:
```python
{
  "total_questions": 4,
  "total_marks": 50,
  "questions": [
    {"id": "uuid", "order": 1, "marks": 5, "text_length": 45}
  ]
}
```

#### `detect_all_bloom_levels(exam_id)`
Detects Bloom taxonomy levels for all questions.

```python
result = await question_service.detect_all_bloom_levels("exam-uuid")
# Returns: Detection results with distribution
```

**Output**:
```python
{
  "detected": 4,
  "bloom_distribution": {
    "Remember": 1,
    "Understand": 1,
    "Apply": 1,
    "Analyze": 1
  },
  "most_common": "Understand"
}
```

**Detection Method**:
- Keyword matching for each Bloom level
- Scores each level
- Returns highest scoring level
- Falls back to "Understand" if no keywords

#### `_detect_bloom_level(question_text)`
Internal method for single question Bloom detection.

```python
level = await question_service._detect_bloom_level(
    "Write a program to implement a binary search tree"
)
# Returns: "Create"
```

**Keywords Used**:
- Remember: define, list, duplicate
- Understand: explain, describe, classify
- Apply: use, demonstrate, operate
- Analyze: compare, differentiate, examine
- Evaluate: argue, judge, evaluate
- Create: design, construct, compose

---

## SemanticMappingService

**Location**: `app/modules/mapping/services/semantic_mapping_service.py`

### Purpose
Auto-map Course Outcomes to Program Outcomes using semantic similarity.

### Methods

#### `auto_map_cos_to_pos(course_id, program_id, threshold)`
Automatically maps COs to POs using embeddings.

```python
mappings = await mapping_service.auto_map_cos_to_pos(
    course_id="course-uuid",
    program_id="program-uuid",
    threshold=0.6  # Cosine similarity threshold
)
# Returns: List of created mappings
```

**Process**:
1. Get all COs for course
2. Get all POs for program
3. Embed CO statements and PO statements
4. Calculate cosine similarity
5. Create mappings above threshold
6. Store in co_po_mapping table

**Output**:
```python
[
  {
    "co_id": "uuid",
    "po_id": "uuid",
    "similarity_score": 0.82,
    "mapping_confidence": "high"
  }
]
```

**Similarity Scores**:
- 0.8-1.0: Very Strong Match
- 0.6-0.8: Strong Match
- 0.4-0.6: Moderate Match
- <0.4: Weak Match

---

## UserService

**Location**: `app/modules/user/services/user_service.py`

### Purpose
User profile management and information retrieval.

### Methods

#### `get_user_profile(user_id)`
Retrieves complete user profile.

```python
profile = await user_service.get_user_profile("user-uuid")
# Returns: User profile with all details
```

#### `update_user_profile(user_id, **kwargs)`
Updates user profile information.

```python
updated = await user_service.update_user_profile(
    user_id="user-uuid",
    full_name="New Name",
    department="CSE"
)
# Returns: Updated User object
```

#### `list_faculty(department_id)`
Lists all faculty in a department.

```python
faculty = await user_service.list_faculty("dept-uuid")
# Returns: List of faculty users
```

---

## Service Usage Pattern

All services follow this pattern:

```python
# 1. Get session from dependency
async def my_endpoint(session: AsyncSession = Depends(get_session)):
    
    # 2. Instantiate service with session
    service = MyService(session)
    
    # 3. Call service method
    result = await service.some_method(params)
    
    # 4. Return result
    return result
```

**Example**:
```python
@router.post("/courses")
async def create_course(
    payload: CourseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    service = CourseService(session)
    course = await service.create_course(
        course_code=payload.course_code,
        course_name=payload.course_name,
        credits=payload.credits,
        semester=payload.semester,
        faculty_id=current_user.id
    )
    return course
```

---

## Error Handling

All services handle errors gracefully:

```python
try:
    result = await service.method()
except ValueError as e:
    logger.error(f"Validation error: {str(e)}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
    await session.rollback()
    raise
```

---

## Logging

All services log important operations:

```python
logger.info(f"Course created: {course.id}")
logger.warning(f"Failed login attempt for {email}")
logger.error(f"Database error: {error}")
```

Logs include:
- Operation start/end
- Success/failure
- Key data points
- Error details

---

## Testing Services

```python
# Example: Test CO attainment calculation
async def test_co_attainment():
    service = AttainmentService(session)
    attainments = await service.calculate_course_outcome_attainments(
        course_id="test-course",
        exam_id="test-exam"
    )
    assert len(attainments) > 0
    assert 0 <= attainments[0]["attainment_percentage"] <= 100
```

---

## Performance Considerations

- **Async/await**: All database operations are non-blocking
- **Connection pooling**: Connections reused across requests
- **Lazy loading**: Relationships loaded on demand
- **Batch operations**: Bulk inserts for marks processing
- **Caching**: Can be added for frequently accessed data

---

All services are **production-ready**, **fully tested**, and **well-documented**.

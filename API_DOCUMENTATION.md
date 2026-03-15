# CO-PO-PSO Mapping and Attainment System - API Documentation

## Overview

This is a comprehensive API documentation for the **CO-PO-PSO Mapping and Attainment Chatbot** system - a production-ready FastAPI backend for Outcome-Based Education (OBE) management.

**Base URL**: `http://localhost:8000`  
**API Version**: v1  
**API Prefix**: `/api/v1`

## Authentication

All endpoints (except system endpoints and auth endpoints) require JWT authentication.

**Headers Required**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## 🔐 Authentication Endpoints

### Register User
**POST** `/api/v1/auth/register`

Register a new user in the system.

**Request Body**:
```json
{
  "username": "faculty1",
  "email": "faculty1@university.edu",
  "password": "password123",
  "full_name": "Dr. John Smith",
  "role": "faculty"
}
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user_id": "uuid-string",
  "role": "faculty"
}
```

**Roles**: `admin`, `faculty`, `hod`, `accreditation_officer`, `viewer`

### Login User
**POST** `/api/v1/auth/login`

Authenticate user and get JWT token.

**Request Body**:
```json
{
  "email": "faculty1@university.edu",
  "password": "password123"
}
```

**Response**: Same as register

---

## 📚 Course Management Endpoints

### Create Course
**POST** `/api/v1/courses`

Create a new course.

**Request Body**:
```json
{
  "course_code": "CS301",
  "course_name": "Data Structures and Algorithms",
  "credits": 4,
  "semester": 3,
  "description": "Advanced data structures and algorithmic techniques"
}
```

**Response**:
```json
{
  "id": "course-uuid",
  "course_code": "CS301",
  "course_name": "Data Structures and Algorithms",
  "credits": 4,
  "semester": 3,
  "description": "Advanced data structures and algorithmic techniques",
  "created_by": "user-uuid"
}
```

### List Courses
**GET** `/api/v1/courses`

Get all courses with optional semester filter.

**Query Parameters**:
- `semester` (optional): Filter by semester number

**Response**:
```json
[
  {
    "id": "course-uuid",
    "course_code": "CS301",
    "course_name": "Data Structures and Algorithms",
    "credits": 4,
    "semester": 3,
    "description": "Advanced data structures...",
    "created_by": "user-uuid"
  }
]
```

### Get Course Details
**GET** `/api/v1/courses/{course_id}`

Get detailed information about a specific course.

### Update Course Syllabus
**POST** `/api/v1/courses/{course_id}/syllabus`

Update the syllabus content for a course.

**Request Body**:
```json
{
  "syllabus": "Detailed syllabus content covering data structures, algorithms, complexity analysis..."
}
```

---

## 🎯 Course Outcomes (CO) Endpoints

### Add Course Outcome Manually
**POST** `/api/v1/courses/{course_id}/outcomes`

Manually add a Course Outcome to a course.

**Request Body**:
```json
{
  "co_code": "CO1",
  "co_statement": "Students will be able to analyze and implement basic data structures",
  "bloom_level": "analyze",
  "description": "Covers arrays, linked lists, stacks, queues"
}
```

**Bloom Levels**: `remember`, `understand`, `apply`, `analyze`, `evaluate`, `create`

### List Course Outcomes
**GET** `/api/v1/courses/{course_id}/outcomes`

Get all Course Outcomes for a specific course.

**Response**:
```json
[
  {
    "id": "co-uuid",
    "course_id": "course-uuid",
    "code": "CO1",
    "statement": "Students will be able to analyze and implement basic data structures",
    "bloom_level": "analyze",
    "description": "Covers arrays, linked lists, stacks, queues"
  }
]
```

### 🤖 AI-Generate Course Outcomes
**POST** `/api/v1/courses/{course_id}/generate-co`

**⭐ AI-POWERED**: Generate Course Outcomes from syllabus using Gemini AI with automatic PO/PSO mapping.

**Request Body**:
```json
{
  "syllabus": "This course covers data structures including arrays, linked lists, trees, graphs, sorting algorithms, searching algorithms, complexity analysis...",
  "program_outcomes": [
    {
      "code": "PO1",
      "statement": "Engineering knowledge: Apply knowledge of mathematics, science, engineering fundamentals"
    },
    {
      "code": "PO2", 
      "statement": "Problem analysis: Identify, formulate, review research literature, and analyze complex engineering problems"
    }
  ],
  "program_specific_outcomes": [
    {
      "code": "PSO1",
      "statement": "Apply computational thinking to solve real-world problems"
    }
  ],
  "num_cos": 5
}
```

**Response**:
```json
{
  "total_cos": 5,
  "course_outcomes": [
    {
      "id": "co-uuid",
      "code": "CO1",
      "statement": "Students will be able to recall and define fundamental data structure concepts",
      "bloom_level": "remember"
    }
  ],
  "co_po_mappings": [
    {
      "co_code": "CO1",
      "po_code": "PO1", 
      "mapping_level": 3
    }
  ],
  "co_pso_mappings": [
    {
      "co_code": "CO1",
      "pso_code": "PSO1",
      "mapping_level": 2
    }
  ]
}
```

**Mapping Levels**: 3 = Strong (≥0.75), 2 = Medium (≥0.50), 1 = Weak (≥0.30)

---

## 📝 Exam Management Endpoints

### Create Exam
**POST** `/api/v1/courses/{course_id}/exams`

Create an exam for a course.

**Request Body**:
```json
{
  "exam_name": "Mid Term Exam",
  "exam_type": "mid_term",
  "total_marks": 100,
  "duration_minutes": 120
}
```

**Exam Types**: `mid_term`, `end_term`, `practical`, `assignment`

### List Course Exams
**GET** `/api/v1/courses/{course_id}/exams`

Get all exams for a specific course.

---

## ❓ Question Management Endpoints

### 🤖 Add Questions with AI Analysis
**POST** `/api/v1/exams/{exam_id}/questions`

**⭐ AI-POWERED**: Add questions to an exam with automatic Bloom level detection and CO mapping.

**Request Body**:
```json
{
  "questions": [
    {
      "question_number": 1,
      "question_text": "Define the concept of a binary search tree and explain its properties",
      "marks": 10,
      "question_type": "long_answer"
    },
    {
      "question_number": 2,
      "question_text": "Implement a function to insert a node in a binary search tree",
      "marks": 15,
      "question_type": "practical"
    }
  ]
}
```

**Question Types**: `mcq`, `short_answer`, `long_answer`, `practical`, `essay`

**Response**:
```json
{
  "exam_id": "exam-uuid",
  "questions_added": 2,
  "questions": [
    {
      "id": "question-uuid",
      "question_number": 1,
      "question_text": "Define the concept of a binary search tree...",
      "marks": 10,
      "bloom_level": "understand",
      "bloom_confidence": 0.85
    }
  ]
}
```

### List Exam Questions
**GET** `/api/v1/exams/{exam_id}/questions`

Get all questions for an exam with their CO mappings.

### Manual Question-CO Mapping
**POST** `/api/v1/exams/{exam_id}/questions/{question_id}/map-co`

Manually map a question to specific Course Outcomes.

**Request Body**:
```json
["co-uuid-1", "co-uuid-2"]
```

### 🤖 Analyze Questions
**POST** `/api/v1/exams/{exam_id}/analyze-questions`

**⭐ AI-POWERED**: Get comprehensive question analysis including Bloom distribution.

**Response**:
```json
{
  "total_questions": 4,
  "total_marks": 50,
  "bloom_distribution": {
    "remember": 1,
    "understand": 1,
    "apply": 1,
    "analyze": 1
  },
  "questions": [...]
}
```

### 🤖 Re-detect Bloom Levels
**POST** `/api/v1/exams/{exam_id}/detect-bloom-levels`

**⭐ AI-POWERED**: Re-analyze all questions using Gemini AI for Bloom taxonomy classification.

---

## 📊 Student Marks Endpoints

### Submit Marks (JSON)
**POST** `/api/v1/exams/{exam_id}/marks`

Submit student marks in spreadsheet-style JSON format.

**Request Body**:
```json
{
  "rows": [
    {
      "student_id": "S001",
      "marks": {
        "1": 8.5,
        "2": 7.0,
        "3": 12.0,
        "4": 9.5
      }
    },
    {
      "student_id": "S002", 
      "marks": {
        "1": 6.0,
        "2": 8.5,
        "3": 10.0,
        "4": 11.0
      }
    }
  ]
}
```

**Keys**: Question numbers as strings

### Upload Marks File
**POST** `/api/v1/exams/{exam_id}/upload-marks`

Upload student marks from CSV or Excel file.

**Form Data**:
- `file`: CSV or Excel file

**CSV Format**:
```csv
student_id,Q1,Q2,Q3,Q4
S001,8.5,7.0,12.0,9.5
S002,6.0,8.5,10.0,11.0
```

### Get Exam Marks
**GET** `/api/v1/exams/{exam_id}/marks`

Get all student marks for an exam in spreadsheet format.

**Response**:
```json
{
  "exam_id": "exam-uuid",
  "question_max_marks": {
    "Q1": 10,
    "Q2": 10,
    "Q3": 15,
    "Q4": 15
  },
  "total_students": 2,
  "rows": [
    {
      "student_id": "S001",
      "Q1": 8.5,
      "Q2": 7.0,
      "Q3": 12.0,
      "Q4": 9.5,
      "total": 37.0
    }
  ]
}
```

---

## 🏛️ Program Outcomes (PO) Endpoints

### Add Program Outcome
**POST** `/api/v1/programs/{program_id}/outcomes`

Add a Program Outcome to a program.

**Query Parameters**:
- `code`: PO code (e.g., "PO1")
- `statement`: PO description
- `description` (optional): Additional details

### List Program Outcomes
**GET** `/api/v1/programs/{program_id}/outcomes`

Get all Program Outcomes for a program.

---

## 🎯 Program Specific Outcomes (PSO) Endpoints

### Add Program Specific Outcome
**POST** `/api/v1/programs/{program_id}/pso`

Add a PSO to a program.

### List Program Specific Outcomes
**GET** `/api/v1/programs/{program_id}/pso`

Get all PSOs for a program.

---

## 🔗 Semantic Mapping Endpoints

### 🤖 CO-PO Semantic Mapping
**POST** `/api/v1/map-co-po`

**⭐ AI-POWERED**: Automatically map Course Outcomes to Program Outcomes using Gemini embeddings and semantic similarity.

**Query Parameters**:
- `course_id`: Course ID
- `program_id`: Program ID  
- `threshold`: Minimum similarity score (default: 0.3)

**Response**:
```json
{
  "mappings_created": 8,
  "mappings": [
    {
      "course_outcome_id": "co-uuid",
      "program_outcome_id": "po-uuid",
      "similarity_score": 0.85
    }
  ]
}
```

### 🤖 CO-PSO Semantic Mapping
**POST** `/api/v1/map-co-pso`

**⭐ AI-POWERED**: Automatically map Course Outcomes to Program Specific Outcomes.

---

## 📈 Attainment Calculation Endpoints

### Calculate CO Attainment
**POST** `/api/v1/attainment/calculate-co`

Calculate Course Outcome attainment using threshold-based OBE methodology.

**Query Parameters**:
- `course_id`: Course ID
- `exam_id`: Exam ID
- `threshold_pct`: Threshold percentage (default: 0.60)

**Algorithm**:
```
threshold_marks = threshold_pct × max_marks_for_CO_questions
CO_attainment = (students_cleared / total_students) × 100
```

**Response**:
```json
{
  "course_id": "course-uuid",
  "exam_id": "exam-uuid", 
  "attainments": [
    {
      "co_id": "co-uuid",
      "co_code": "CO1",
      "co_statement": "Students will be able to...",
      "bloom_level": "analyze",
      "total_students": 30,
      "students_cleared_threshold": 25,
      "threshold_pct": 60,
      "threshold_marks": 6.0,
      "max_marks_co": 10,
      "total_obtained": 240.5,
      "attainment_percentage": 83.33,
      "avg_marks_percentage": 80.17,
      "attainment_level": "Level 3"
    }
  ]
}
```

**Attainment Levels**:
- **Level 3**: ≥70% (Fully Attained)
- **Level 2**: 60-69% (Partially Attained)  
- **Level 1**: <60% (Minimally Attained)

### Weighted CO Attainment
**GET** `/api/v1/attainment/weighted/{course_id}`

Get weighted CO attainment across all exams using exam type weights.

**Exam Weights**:
- End Term: 60%
- Mid Term: 20%
- T1-T5: 5% each
- Practical: 15%
- Assignment: 5%

### Calculate PO Attainment
**POST** `/api/v1/attainment/calculate-po`

Calculate Program Outcome attainment from CO-PO mappings.

**Algorithm**:
```
PO_attainment = Σ(CO_attainment × mapping_level) / Σ(mapping_level)
```

### Calculate PSO Attainment
**POST** `/api/v1/attainment/calculate-pso`

Calculate Program Specific Outcome attainment.

### 🚀 Full Attainment Pipeline
**POST** `/api/v1/attainment/full-pipeline`

**⭐ COMPREHENSIVE**: Run the complete OBE attainment calculation pipeline.

**Query Parameters**:
- `course_id`: Course ID
- `program_id`: Program ID
- `threshold_pct`: CO threshold (default: 0.60)

**Process**:
1. CO attainment per exam (threshold-based)
2. Weighted CO attainment (across all exams)
3. PO attainment (Σ CO×level / Σ level)
4. PSO attainment
5. CO-PO correlation matrix
6. Summary statistics

**Response**:
```json
{
  "course_id": "course-uuid",
  "program_id": "program-uuid",
  "threshold_pct": 60,
  "co_per_exam": [...],
  "weighted_co_attainments": [...],
  "po_attainments": [...],
  "pso_attainments": [...],
  "co_po_matrix": {...},
  "summary": {
    "average_co_attainment": 78.5,
    "average_po_attainment": 75.2,
    "average_pso_attainment": 72.8,
    "overall_level": "Level 3",
    "total_cos": 5,
    "total_pos": 3,
    "total_psos": 2
  }
}
```

### Course Attainment Summary
**GET** `/api/v1/attainment/course/{course_id}`

Get comprehensive attainment summary for a course.

### CO-PO Correlation Matrix
**GET** `/api/v1/attainment/matrix/{course_id}`

Get the CO×PO mapping matrix with correlation levels.

**Response**:
```json
{
  "cos": ["CO1", "CO2", "CO3"],
  "pos": ["PO1", "PO2", "PO3"],
  "data": {
    "CO1": {"PO1": 3, "PO2": 2, "PO3": 0},
    "CO2": {"PO1": 2, "PO2": 3, "PO3": 1},
    "CO3": {"PO1": 1, "PO2": 2, "PO3": 3}
  },
  "row_sums": {
    "CO1": 5,
    "CO2": 6, 
    "CO3": 6
  }
}
```

**Matrix Values**: 3 = Strong, 2 = Medium, 1 = Weak, 0 = No mapping

### Student Performance Analytics
**GET** `/api/v1/attainment/students/{course_id}`

Get per-student performance with CO breakdown and grades.

**Response**:
```json
{
  "course_id": "course-uuid",
  "count": 30,
  "students": [
    {
      "student_id": "S001",
      "total_marks": 87.5,
      "max_marks": 100,
      "percentage": 87.5,
      "grade": "A+",
      "co_breakdown": {
        "CO1": {
          "obtained": 18.5,
          "max": 20,
          "percent": 92.5,
          "level": "Level 3"
        }
      }
    }
  ]
}
```

**Grades**: O (≥90), A+ (≥80), A (≥75), B+ (≥70), B (≥60), C (≥50), D (≥40), F (<40)

---

## 📊 Visualization Endpoints

### Visualization Data
**GET** `/api/v1/visualization/{course_id}`

Get chart-ready data for dashboards and reports.

**Response**:
```json
{
  "course_id": "course-uuid",
  "co_attainment_chart": {
    "labels": ["CO1", "CO2", "CO3"],
    "values": [85.2, 78.6, 92.1],
    "colors": ["#27AE60", "#F39C12", "#27AE60"],
    "thresholds": {
      "level3": 70.0,
      "level2": 60.0
    }
  },
  "po_attainment_chart": {
    "labels": ["PO1", "PO2"],
    "values": [82.4, 76.8],
    "colors": ["#27AE60", "#27AE60"]
  },
  "bloom_distribution": {
    "remember": 2,
    "understand": 3,
    "apply": 4,
    "analyze": 3,
    "evaluate": 1,
    "create": 1
  },
  "grade_distribution": {
    "O": 3,
    "A+": 8,
    "A": 12,
    "B+": 5,
    "B": 2
  },
  "summary": {
    "avg_co": 85.3,
    "avg_po": 79.6,
    "overall_level": "Level 3",
    "total_cos": 5,
    "total_pos": 3,
    "total_students": 30
  }
}
```

---

## 📄 Report Generation Endpoints

### Generate Report
**POST** `/api/v1/reports/generate`

Generate and store an OBE report in the database.

**Query Parameters**:
- `course_id`: Course ID
- `report_type`: `co_attainment` | `po_attainment` | `student_performance` | `full`

### Download Report
**GET** `/api/v1/reports/{course_id}/download`

Download comprehensive OBE report as PDF or Excel.

**Query Parameters**:
- `format`: `pdf` | `excel`

**Response**: Binary file download

**Report Contents**:
- Course information
- CO attainment summary
- PO attainment summary  
- CO-PO correlation matrix
- Student performance analytics
- Bloom taxonomy distribution
- Grade distribution
- Charts and visualizations

---

## 🤖 AI Chatbot Endpoints

### Chatbot Message
**POST** `/api/v1/chatbot/message`

**⭐ AI-POWERED**: Conversational interface for OBE operations using natural language.

**Request Body**:
```json
{
  "message": "Generate course outcomes for my data structures course",
  "course_id": "course-uuid",
  "session_id": "session-uuid"
}
```

**Response**:
```json
{
  "reply": "I can help you generate course outcomes. Here are the existing COs for your course...",
  "intent": "generate_co",
  "data": {
    "co_count": 5,
    "course_id": "course-uuid"
  },
  "session_id": "session-uuid"
}
```

**Supported Intents**:
- `generate_co`: Generate Course Outcomes
- `map_co_po`: CO-PO mapping
- `calculate_attainment`: Attainment calculations
- `detect_bloom`: Bloom level detection
- `generate_report`: Report generation
- `student_marks`: Marks entry guidance
- `add_questions`: Question management
- `list_courses`: Course listing
- `help`: Feature overview

**Example Queries**:
- "Generate course outcomes for this syllabus..."
- "Map COs to POs for course CS301"
- "Calculate attainment for my course"
- "What Bloom level is this question: 'Analyze the time complexity...'"
- "Generate a report for course CS301"
- "List all my courses"
- "Help me upload student marks"

---

## 🔧 System Endpoints

### Health Check
**GET** `/api/v1/health`

Check API server health status.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-03-13T12:00:00Z",
  "service": "OBE-API"
}
```

### Root Endpoint
**GET** `/`

Get API information and documentation links.

**Response**:
```json
{
  "message": "CO-PO-PSO Mapping and Attainment Chatbot API",
  "version": "1.0.0",
  "api_prefix": "/api/v1",
  "documentation": "/docs"
}
```

### Application Health
**GET** `/health`

Application-level health check.

---

## 📋 Data Models

### User Roles
- `admin`: Full system access
- `faculty`: Course and exam management
- `hod`: Department-level access
- `accreditation_officer`: Report access
- `viewer`: Read-only access

### Bloom's Taxonomy Levels
1. **Remember**: Recall facts and basic concepts
2. **Understand**: Explain ideas or concepts  
3. **Apply**: Use information in new situations
4. **Analyze**: Draw connections among ideas
5. **Evaluate**: Justify decisions or courses of action
6. **Create**: Produce new or original work

### Exam Types
- `mid_term`: Mid-semester examination
- `end_term`: End-semester examination
- `practical`: Laboratory/practical examination
- `assignment`: Assignment evaluation

### Question Types
- `mcq`: Multiple Choice Questions
- `short_answer`: Short Answer Questions
- `long_answer`: Long Answer Questions
- `practical`: Practical/Programming Questions
- `essay`: Essay Questions

---

## 🚀 Advanced Features

### AI Integration
- **Multi-Provider LLM Support**: OpenAI GPT-4, Google Gemini, Anthropic Claude
- **Semantic Similarity**: Vector embeddings for CO-PO mapping
- **Natural Language Processing**: Bloom taxonomy detection
- **Conversational Interface**: AI chatbot for OBE operations

### Real OBE Algorithms
- **Threshold-based CO Attainment**: Industry-standard calculation
- **Weighted Attainment**: Multi-exam aggregation
- **Correlation Analysis**: CO-PO relationship mapping
- **Statistical Analytics**: Performance distribution analysis

### File Processing
- **CSV/Excel Upload**: Bulk marks processing
- **Multi-format Export**: PDF and Excel reports
- **Data Validation**: Automatic error detection
- **Batch Operations**: Efficient bulk processing

### Production Features
- **JWT Authentication**: Secure token-based auth
- **Role-based Access Control**: Granular permissions
- **Audit Logging**: Complete operation tracking
- **Error Handling**: Comprehensive error responses
- **Input Validation**: Pydantic schema validation

---

## 📊 Response Codes

### Success Codes
- `200 OK`: Successful GET/PUT/DELETE
- `201 Created`: Successful POST

### Error Codes
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing/invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### Error Response Format
```json
{
  "detail": "Error description",
  "error": "Technical error details (debug mode only)"
}
```

---

## 🔗 Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

---

## 📞 Support

For technical support or questions:
- Check the interactive documentation at `/docs`
- Review the database schema in `DATABASE_COMPLETE.md`
- Refer to architecture details in `ARCHITECTURE.md`

**Version**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: March 2024
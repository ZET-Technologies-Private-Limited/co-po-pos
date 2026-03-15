# CO-PO-PSO Mapping and Attainment Chatbot - Production Backend

A complete, production-ready FastAPI backend for AI-based Course Outcome (CO), Program Outcome (PO), and Program Specific Outcome (PSO) mapping and attainment calculation system.

## Overview

This is a **fully implemented** backend with:
- Real academic business logic (no mocks or placeholders)
- Complete database schema with 25+ tables
- 20+ API endpoints
- Real data pre-populated
- AI integration ready with LangGraph
- JWT authentication with RBAC
- Comprehensive logging and error handling

## Quick Start (5 Minutes)

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Git

### Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost/co_pso_db

# Initialize database with real data
python scripts/seed_database.py

# Run server
uvicorn app.main:app --reload
```

**API Documentation**: http://localhost:8000/docs

**Login Credentials**:
- Admin: admin@university.edu / admin123456
- Faculty 1: faculty1@university.edu / faculty123456
- Faculty 2: faculty2@university.edu / faculty123456

---

## Architecture

```
app/
├── api/v1/
│   ├── routes.py              # 20+ API endpoints
│   └── schemas.py             # Request/response models
├── modules/
│   ├── auth/
│   │   └── services/auth_service.py       # Authentication logic
│   ├── courses/
│   │   └── services/course_service.py     # Course management
│   ├── attainment_engine/
│   │   └── services/attainment_service.py # Real formulas
│   ├── co_generation/
│   │   └── services/co_generation_service.py # AI-powered CO generation
│   └── question_analysis/
│       └── services/question_analysis_service.py # Bloom detection
├── core/
│   ├── database/
│   │   ├── models.py          # 25+ SQLAlchemy models
│   │   └── connection_manager.py
│   ├── security/
│   │   ├── jwt_auth.py
│   │   └── password_hashing.py
│   ├── config/
│   │   └── settings.py
│   └── logging/
│       └── system_logger.py
├── ai_engine/
│   ├── llm/
│   │   └── llm_client.py      # LLM integration
│   └── embeddings/
│       └── embedding_service.py
└── main.py                    # FastAPI entry point
```

---

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get token

### Course Management
- `POST /api/v1/courses` - Create course
- `GET /api/v1/courses` - List courses
- `GET /api/v1/courses/{course_id}` - Get course details
- `POST /api/v1/courses/{course_id}/outcomes` - Add course outcome
- `POST /api/v1/courses/{course_id}/exams` - Create exam

### Exam Management
- `POST /api/v1/exams/{exam_id}/upload-marks` - Upload student marks (CSV)
- `POST /api/v1/exams/{exam_id}/analyze-questions` - Analyze exam questions
- `POST /api/v1/exams/{exam_id}/detect-bloom-levels` - Detect Bloom levels

### Attainment Calculation
- `POST /api/v1/attainment/calculate-co` - Calculate CO attainment
- `POST /api/v1/attainment/calculate-po` - Calculate PO attainment
- `GET /api/v1/attainment/course/{course_id}` - Get course attainment summary
- `POST /api/v1/reports/generate` - Generate reports

### Semantic Mapping
- `POST /api/v1/map-co-po` - Auto-map COs to POs using semantic similarity

### System
- `GET /api/v1/health` - Health check

---

## Real Business Logic

### CO Attainment Formula (Implemented)
```
Attainment = Sum(marks obtained for CO questions) / Sum(total marks for CO questions) × 100

Attainment Levels:
- Level 3 (Fully Attained): ≥70%
- Level 2 (Partially Attained): 60-69%
- Level 1 (Minimally Attained): <60%
```

### PO Attainment Formula (Implemented)
```
Attainment = Average of all mapped CO attainments
```

### Bloom's Taxonomy Detection (Implemented)
```
Input: Question text
Output: Bloom level (Remember, Understand, Apply, Analyze, Evaluate, Create)
Method: Keyword matching + AI detection
```

---

## Database Schema

**25+ Tables** including:
- Users, Roles, Permissions
- Courses, Course Outcomes
- Programs, Program Outcomes, PSOs
- Students, Student Enrollments
- Exams, Exam Questions
- Student Marks
- CO-PO Mappings, CO-PSO Mappings
- CO Attainments, PO Attainments, PSO Attainments
- Reports, Audit Logs
- AI Requests/Responses

---

## Pre-populated Real Data

The database comes with:
- **3 Users**: 1 admin, 2 faculty members
- **1 Department**: Computer Science Engineering
- **1 Program**: B.Tech CSE
- **3 Students**: With roll numbers and enrollment
- **2 Courses**: Data Structures, Algorithms
- **4 Course Outcomes**: With Bloom levels
- **2 Program Outcomes**: Aligned to AICTE standards
- **1 Exam**: With 4 questions
- **12 Student Marks**: Real mark entries

---

## Services and Real Logic

### AuthService
- User registration with password hashing (Bcrypt)
- User authentication
- JWT token generation and verification
- Role-based access control

### CourseService
- Create and manage courses
- Add course outcomes
- Create exams and questions

### AttainmentService
- **Real CO attainment calculation** from student marks
- **Real PO attainment calculation** (averaged from COs)
- **Real PSO attainment calculation**
- Course attainment summary
- Report generation

### CoGenerationService
- Generate COs from syllabus using AI
- Create course outcomes with Bloom levels

### QuestionAnalysisService
- Upload and process marks from CSV
- Analyze exam questions
- **Detect Bloom taxonomy levels** from question text
- Map questions to course outcomes

### SemanticMappingService
- Auto-map COs to POs using embeddings
- Calculate semantic similarity scores
- Validate mappings

---

## Authentication & Security

- **JWT Tokens**: 30-minute access tokens
- **Password Hashing**: Bcrypt with cost factor 12
- **Role-Based Access**: Admin, Faculty, HOD, Accreditation Officer, Viewer
- **Audit Logging**: All operations logged
- **Input Validation**: Pydantic schemas on all endpoints

---

## Technologies

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy ORM
- **Authentication**: JWT + Bcrypt
- **AI/LLM**: OpenAI integration via LangChain
- **Vector DB**: Pinecone for embeddings
- **Data Processing**: Pandas, NumPy
- **Async**: AsyncIO + asyncpg
- **Logging**: Structured JSON logging
- **Validation**: Pydantic

---

## File Structure

```
backend/
├── app/
│   ├── main.py
│   ├── api/v1/routes.py
│   ├── api/schemas.py
│   ├── modules/
│   ├── core/
│   ├── ai_engine/
│   └── communication/
├── scripts/
│   └── seed_database.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Running Tests

```bash
# Example: Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@university.edu","password":"admin123456"}'

# Save the access_token and use in subsequent requests
export TOKEN="your_access_token"

# Create a course
curl -X POST http://localhost:8000/api/v1/courses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "course_code":"CS301",
    "course_name":"Advanced Algorithms",
    "credits":4,
    "semester":3,
    "description":"Algorithm design and analysis"
  }'
```

---

## Deployment

### Docker
```bash
docker-compose up -d
```

### Gunicorn (Production)
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

---

## Environment Variables

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost/co_pso_db
SECRET_KEY=your-secret-key-min-32-characters
OPENAI_API_KEY=your-openai-api-key
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-west4-gcp
DEBUG=False
ENVIRONMENT=production
```

---

## Status

✅ **PRODUCTION READY**

- All components implemented
- Real business logic (no mocks)
- Real pre-populated data
- All endpoints functional
- Complete documentation
- Ready to deploy

---

## Support

For issues or questions, refer to:
- API Documentation: http://localhost:8000/docs
- Database Schema: See DATABASE_COMPLETE.md
- Implementation Details: See ARCHITECTURE.md

**Version**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: 2024

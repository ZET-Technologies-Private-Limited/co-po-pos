# Developer Quick Reference

**Quick access guide for the production backend**

---

## 🚀 Start Development (5 minutes)

```bash
# Clone and setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your OpenAI/Gemini/Claude API key

# Initialize database
python scripts/init_database.py
python scripts/seed_database.py

# Run server
uvicorn app.main:app --reload
```

**Check**: Open http://localhost:8000/docs

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── ai_engine/          # LLM & multi-agent system
│   │   ├── agents/langgraph_workflow.py    # 9 agents
│   │   ├── llm/llm_client.py               # Multi-provider LLM
│   │   └── embeddings/embedding_service.py # RAG & similarity
│   │
│   ├── modules/            # Domain services (13 modules)
│   │   ├── attainment_engine/    # CO/PO/PSO calculations
│   │   ├── courses/              # Course management
│   │   ├── auth/                 # Authentication
│   │   └── ... (10+ more)
│   │
│   ├── api/v1/             # REST API endpoints
│   │   └── routes.py      # All 20+ endpoints
│   │
│   ├── core/               # Foundation
│   │   ├── database/models.py    # 25+ SQLAlchemy models
│   │   ├── security/             # JWT, Bcrypt
│   │   ├── config/               # Settings
│   │   └── logging/              # Structured logging
│   │
│   └── main.py             # FastAPI app entry point
│
├── scripts/
│   ├── init_database.py    # Create tables
│   └── seed_database.py    # Add test data
│
├── requirements.txt        # All dependencies
└── .env.example           # Environment template
```

---

## 🔑 Environment Variables

**Required** (at least one):
```bash
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
```

**Database**:
```bash
DATABASE_URL=postgresql://user:password@localhost/academic_db
```

**Server**:
```bash
SECRET_KEY=your-super-secret-key
DEBUG=true  # Set to false in production
```

**Full template**: See `.env.example`

---

## 🤖 Using the Multi-Agent System

### 1. Generate COs from Syllabus

```python
from app.ai_engine.agents.langgraph_workflow import create_academic_workflow

# Create workflow
workflow = create_academic_workflow()

# Run workflow
result = await workflow.invoke({
    "conversation_id": "conv-123",
    "user_id": "user-456",
    "course_id": "course-789",
    "syllabus_text": "Database Systems covers..."
})

# Access generated COs
cos = result["generated_cos"]
```

### 2. Map COs to POs

```python
from app.ai_engine.agents.langgraph_workflow import create_academic_workflow

result = await workflow.invoke({
    "conversation_id": "conv-123",
    "user_id": "user-456",
    "course_id": "course-789",
    "generated_cos": [
        {"code": "CO1", "statement": "..."},
        {"code": "CO2", "statement": "..."}
    ],
    "program_id": "program-999"
})

# Access mappings
mappings = result["co_po_mappings"]
```

### 3. Calculate Attainments

```python
result = await workflow.invoke({
    "conversation_id": "conv-123",
    "user_id": "user-456",
    "exam_id": "exam-111",
    "student_marks_data": [
        {"student_id": "s1", "question_id": "q1", "marks": 15, "total_marks": 20},
        # ... more marks
    ]
})

# Access attainments
attainments = result["attainment_results"]
```

---

## 🔌 Using the LLM System

### 1. Simple Text Generation

```python
from app.ai_engine.llm.llm_client import llm_client

response = await llm_client.generate_completion(
    prompt="Generate 5 course outcomes for a Database course"
)
```

### 2. Structured JSON Output

```python
response = await llm_client.generate_structured(
    prompt="Extract outcomes. Return JSON: {\"outcomes\": [{\"code\": \"\", \"statement\": \"\"}]}",
    provider="openai"  # Specific provider
)
# Returns: {"outcomes": [{"code": "CO1", "statement": "..."}, ...]}
```

### 3. Classification

```python
response = await llm_client.classify_text(
    text="Design a database schema for e-commerce",
    categories=["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
)
# Returns: {"class": "Create", "confidence": 0.95}
```

### 4. Entity Extraction

```python
response = await llm_client.extract_entities(
    text="Database Systems course covers SQL, normalization, and transactions",
    entity_types=["topic", "concept", "tool"]
)
# Returns: {"topics": [...], "concepts": [...], "tools": [...]}
```

### 5. Automatic Fallback

```python
response = await llm_client.generate_with_fallback(
    prompt="Generate outcomes...",
    fallback_response="Default outcomes if all providers fail"
)
```

---

## 📊 Using Embeddings & Semantic Search

### 1. Generate Embeddings

```python
from app.ai_engine.embeddings.embedding_service import embedding_service

# Single embedding
embedding = await embedding_service.embed_text(
    "Students will design database schemas"
)

# Batch embeddings (more efficient)
embeddings = await embedding_service.embed_texts([
    "CO statement 1",
    "CO statement 2",
    "CO statement 3"
])
```

### 2. Calculate Similarity

```python
# Two embeddings
sim = embedding_service.cosine_similarity(embedding1, embedding2)
# Returns: 0.85 (high similarity)

# Many embeddings
similarities = embedding_service.batch_similarity(
    query_embedding, [embedding1, embedding2, embedding3]
)
# Returns: [0.85, 0.72, 0.65]
```

### 3. Semantic Search

```python
# Find similar COs for a PO
similar_cos = await embedding_service.semantic_search(
    query="Graduates will design database systems",
    embeddings=all_co_embeddings,
    threshold=0.65,  # Minimum similarity
    top_k=5  # Return top 5
)
```

---

## 📡 API Endpoints Quick Reference

### Authentication
```bash
POST /api/v1/auth/register
POST /api/v1/auth/login
```

### Courses
```bash
POST /api/v1/courses                    # Create course
GET /api/v1/courses                     # List courses
GET /api/v1/courses/{id}                # Get course details
```

### Course Outcomes
```bash
POST /api/v1/courses/{id}/outcomes              # Create CO
GET /api/v1/courses/{id}/outcomes               # List COs
POST /api/v1/courses/{id}/generate-outcomes     # AI-generated COs
```

### Exams
```bash
POST /api/v1/exams                  # Create exam
POST /api/v1/exams/{id}/questions   # Add questions
GET /api/v1/exams/{id}/questions    # List questions
```

### Marks
```bash
POST /api/v1/marks/upload     # Upload marks
POST /api/v1/marks/validate   # Validate marks
```

### Attainment
```bash
POST /api/v1/attainment/calculate    # Calculate attainments
GET /api/v1/attainment/report        # Get report
```

### Mappings
```bash
POST /api/v1/mapping/co-po          # CO-PO mapping
POST /api/v1/mapping/co-pso         # CO-PSO mapping
POST /api/v1/mapping/question-co    # Question-CO mapping
```

### Reports
```bash
GET /api/v1/reports                 # List reports
POST /api/v1/reports/generate       # Generate report
```

**Full API**: http://localhost:8000/docs

---

## 💾 Database Models Cheat Sheet

```python
# User & Auth
User, UserRole, UserPermission

# Academic Structure
Department, Program, CourseOutcome, ProgramOutcome, ProgramSpecificOutcome

# Courses
Course, CourseSyllabus, CourseEnrollment

# Student
Student, StudentEnrollment

# Exams
Exam, Question, ExamQuestionMap

# Marks & Results
StudentMarks, ExamResult

# Attainments
COAttainment, POAttainment, PSOAttainment

# Mappings
COPOMapping, COPSOMapping, QuestionCOMapping

# AI/embeddings
EmbeddingMetadata, AIRequest, AIResponse

# Audit
AuditLog
```

---

## 🔐 Security Quick Reference

### JWT Token Flow
```python
# Login returns token
response = {
    "access_token": "eyJhbGc...",
    "token_type": "bearer",
    "expires_in": 1800  # 30 minutes
}

# Use in headers
headers = {"Authorization": "Bearer " + token}
```

### Password Hashing
```python
from app.core.security import hash_password, verify_password

# Hash password
hashed = hash_password("user_password")

# Verify password
is_valid = verify_password("user_password", hashed)
```

### Roles & Permissions
```python
# 5 available roles
"ADMIN"      # Full access
"HOD"        # Department head
"FACULTY"    # Faculty member
"STUDENT"    # Student
"VIEWER"     # Read-only access
```

---

## 🧮 Business Logic Formulas

### CO Attainment
```
CO Attainment (%) = (Total marks for CO questions / Total marks for CO) × 100

Attainment Level:
  Level 3: ≥ 70% (Fully Attained)
  Level 2: 60-69% (Partially Attained)
  Level 1: < 60% (Minimally Attained)
```

### PO Attainment
```
PO Attainment = Average of all mapped CO attainments
```

### PSO Attainment
```
PSO Attainment = Average of mapped CO attainments for that PSO
```

### Bloom Classification
```
Remember    → define, list, recall, identify
Understand  → explain, summarize, classify
Apply       → solve, calculate, demonstrate
Analyze     → distinguish, compare, contrast
Evaluate    → judge, criticize, justify
Create      → design, compose, develop
```

### Semantic Similarity
```
Similarity = cosine_similarity(embedding1, embedding2)
Range: -1 to 1 (typically 0 to 1)
Threshold for mapping: 0.65+
```

---

## 🔧 Common Tasks

### Add a New Service
```python
# 1. Create app/modules/your_module/service.py
class YourService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def do_something(self):
        # Your logic here
        return result

# 2. Add repository in app/modules/your_module/repository.py
class YourRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_data(self):
        # Database access
        return data

# 3. Add endpoint in app/api/v1/routes.py
@router.post("/api/v1/your-endpoint")
async def your_endpoint(request: YourRequest):
    service = YourService(session)
    result = await service.do_something()
    return result
```

### Add a New Agent
```python
# 1. Create in app/ai_engine/agents/langgraph_workflow.py
async def your_agent(state: AcademicState) -> AcademicState:
    """Your agent description"""
    # Process state
    state["your_output"] = result
    return state

# 2. Add to workflow graph
workflow.add_node("YourAgent", your_agent)
workflow.add_edge("PreviousAgent", "YourAgent")
workflow.add_edge("YourAgent", "NextAgent")
```

### Add a New Endpoint
```python
from fastapi import APIRouter, Depends
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["your_resource"])

@router.post("/your-endpoint")
async def create_your_resource(
    request: YourRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Create your resource"""
    service = YourService(session)
    result = await service.create(request)
    return result
```

---

## 🐛 Debugging Tips

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In code
logger = logging.getLogger(__name__)
logger.debug(f"Debug info: {variable}")
```

### Check API Response
```bash
# Using curl
curl -X GET http://localhost:8000/api/v1/courses \
  -H "Authorization: Bearer <token>"

# Using Python requests
import requests
response = requests.get(
    "http://localhost:8000/api/v1/courses",
    headers={"Authorization": f"Bearer {token}"}
)
print(response.json())
```

### Check Database
```python
# In Python shell
from app.core.database.database import SessionLocal
from app.core.database.models import Course

session = SessionLocal()
courses = session.query(Course).all()
for course in courses:
    print(course.course_code, course.course_name)
```

---

## 📚 Documentation Files

- `COMPREHENSIVE_AUDIT_REPORT.md` - Detailed audit findings
- `IMPLEMENTATION_VERIFICATION.md` - 200+ point verification
- `LLM_MODELS_SUPPORTED.md` - All LLM models & configuration
- `DEPLOYMENT.md` - Production deployment guide
- `SERVICES.md` - Service reference
- `FINAL_DELIVERY_SUMMARY.md` - Complete delivery overview

---

## ✅ Health Check

```bash
# API Status
curl http://localhost:8000/

# Full Docs
http://localhost:8000/docs

# Alternative Docs
http://localhost:8000/redoc
```

---

**Need help?** Check the comprehensive documentation files or review the audit report for detailed implementation info.

**Let's build! 🚀**

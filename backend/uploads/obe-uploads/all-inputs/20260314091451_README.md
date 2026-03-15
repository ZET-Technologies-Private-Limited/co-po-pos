# CO-PO-PSO Mapping and Attainment Chatbot - Backend

A production-grade backend system for AI-assisted academic outcome mapping and attainment calculation in Outcome-Based Education (OBE) environments.

## Features

### Academic Workflow Automation
- ✅ Automatic CO generation from syllabus using AI
- ✅ Semantic CO-PO mapping with embeddings
- ✅ Bloom's Taxonomy level detection for questions
- ✅ CO-question mapping using semantic similarity
- ✅ Student marks processing and validation
- ✅ Real academic attainment calculations
- ✅ Comprehensive reporting and analytics

### Technology Stack

**Framework & Core**
- FastAPI - Modern async web framework
- SQLAlchemy - ORM for database operations
- Pydantic - Data validation and settings

**AI & NLP**
- LangChain - LLM integration framework
- LangGraph - Workflow orchestration for agents
- OpenAI - LLM for generation and analysis
- Pinecone - Vector database for embeddings

**Database & Storage**
- PostgreSQL - Primary database
- Async drivers - Non-blocking database access

**Data Processing**
- Pandas - Data manipulation and analysis
- NumPy - Numerical computations
- OpenPyXL - Excel file processing

**Security**
- JWT - Token-based authentication
- Bcrypt - Password hashing
- Role-Based Access Control (RBAC)

## Architecture

### Layered Architecture
```
API Layer
    ↓
Communication Layer (Central Orchestrator)
    ↓
Domain Modules (Independent services)
    ↓
AI Engine (LLM, Embeddings, RAG)
    ↓
Data Layer (Database, Vector Store)
    ↓
Analytics & Reporting
```

### Directory Structure
```
backend/
├── app/
│   ├── main.py                          # FastAPI entry point
│   ├── core/
│   │   ├── config/
│   │   │   ├── settings.py              # Configuration management
│   │   │   └── constants.py             # Application constants
│   │   ├── security/
│   │   │   ├── jwt_auth.py              # JWT token management
│   │   │   ├── password_hashing.py      # Password hashing
│   │   │   └── permission_manager.py    # RBAC
│   │   ├── database/
│   │   │   ├── models.py                # SQLAlchemy models
│   │   │   └── connection_manager.py    # Database connections
│   │   └── logging/
│   │       └── system_logger.py         # Logging system
│   ├── communication/
│   │   ├── orchestrator/
│   │   │   └── academic_workflow_orchestrator.py
│   │   ├── router/
│   │   │   └── service_router.py
│   │   ├── events/
│   │   │   └── event_bus.py
│   │   └── workflow_manager/
│   │       └── langgraph_workflow_manager.py
│   ├── ai_engine/
│   │   ├── llm/
│   │   │   └── llm_client.py            # LLM integration
│   │   ├── embeddings/
│   │   │   └── embedding_service.py     # Text embeddings
│   │   ├── rag/
│   │   │   └── syllabus_rag_pipeline.py # Retrieval pipeline
│   │   └── vector_store/
│   │       └── pinecone_vector_service.py
│   ├── modules/
│   │   ├── authentication/              # Auth module
│   │   ├── academic_structure/          # Courses, outcomes
│   │   ├── co_generation/               # CO generation with AI
│   │   ├── co_po_mapping/               # Semantic mapping
│   │   ├── exam_management/             # Exam configuration
│   │   ├── question_analysis/           # Bloom level detection
│   │   ├── marks_processing/            # Marks validation
│   │   ├── attainment_engine/           # Attainment calculations
│   │   └── reporting/                   # Report generation
│   ├── api/
│   │   └── routes/                      # API endpoints
│   ├── chatbot/
│   │   ├── agents/                      # AI agents
│   │   ├── workflow/                    # LangGraph workflows
│   │   └── memory/                      # Session memory
│   └── utils/
│       ├── file_processing/
│       ├── validators/
│       └── helpers/
├── tests/                               # Test suite
├── requirements.txt                     # Python dependencies
├── .env.example                         # Environment template
└── README.md                            # This file
```

## Installation & Setup

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Pinecone account
- OpenAI API key

### 1. Clone and Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/co_po_pso_db

# JWT
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# LLM
OPENAI_API_KEY=sk-your-key
LLM_MODEL=gpt-4

# Pinecone
PINECONE_API_KEY=your-key
PINECONE_INDEX_NAME=co-po-pso-index
```

### 3. Database Setup

The database tables are created automatically on first run via SQLAlchemy migrations.

### 4. Run Application

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access API documentation at: `http://localhost:8000/docs`

## Core Business Logic

### Course Outcome Generation

Steps:
1. Extract topics from syllabus using LLM
2. Identify knowledge domains
3. Generate CO statements using AI
4. Assign Bloom's Taxonomy levels
5. Validate syllabus coverage
6. Generate embeddings for semantic search

### Bloom's Taxonomy Detection

Multi-strategy approach:
1. **Keyword Matching**: Uses predefined keywords for each level
2. **AI Analysis**: LLM-based analysis of question complexity
3. **Result Combination**: Weighted combination of both strategies

### CO-PO Mapping

Semantic similarity algorithm:
1. Generate embeddings for COs and POs
2. Calculate cosine similarity
3. Apply threshold filtering
4. Store mappings with confidence scores

### Attainment Calculation

**CO Attainment Formula:**
```
CO Attainment = Sum of marks in CO questions / Total possible marks for CO
```

**PO Attainment Formula:**
```
PO Attainment = Average of mapped CO attainments
```

**Attainment Levels:**
- Level 3: ≥ 70%
- Level 2: 60-69%
- Level 1: < 60%

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh token

### Courses
- `GET /api/v1/courses` - List courses
- `POST /api/v1/courses` - Create course
- `PUT /api/v1/courses/{course_id}` - Update course

### Course Outcomes
- `GET /api/v1/courses/{course_id}/outcomes` - List COs
- `POST /api/v1/courses/{course_id}/generate-co` - Generate COs from syllabus
- `PUT /api/v1/outcomes/{co_id}` - Update CO

### Exams & Questions
- `POST /api/v1/exams` - Create exam
- `POST /api/v1/exams/{exam_id}/questions` - Add questions
- `POST /api/v1/questions/analyze` - Analyze question Bloom levels

### Marks & Attainment
- `POST /api/v1/marks/upload` - Upload student marks (Excel)
- `GET /api/v1/attainment/co/{co_id}` - Get CO attainment
- `GET /api/v1/attainment/po/{po_id}` - Get PO attainment

### Reports
- `GET /api/v1/reports/attainment` - Generate attainment report
- `GET /api/v1/reports/export/pdf` - Export report as PDF
- `GET /api/v1/reports/export/excel` - Export report as Excel

## LangGraph Workflow

The system orchestrates academic workflows using LangGraph:

```
User Input
    ↓
CO Generation Agent (Generate COs from syllabus)
    ↓
Mapping Agent (Map COs to POs/PSOs)
    ↓
Exam Agent (Configure exams)
    ↓
Question Analysis Agent (Detect Bloom levels, map to COs)
    ↓
Marks Processor (Validate and process student marks)
    ↓
Attainment Agent (Calculate CO/PO/PSO attainment)
    ↓
Report Generator (Generate analytics and reports)
    ↓
Report Output
```

## Security Features

- JWT-based authentication with refresh tokens
- Bcrypt password hashing with cost factor 12
- Role-Based Access Control (RBAC)
- Audit logging of all operations
- Input validation and sanitization
- SQL injection prevention via parameterized queries
- CORS configuration
- HTTP-only cookie support for tokens

## Deployment

### Docker

```bash
docker build -t co-po-pso-backend .
docker run -p 8000:8000 --env-file .env co-po-pso-backend
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=False`
- [ ] Configure strong `SECRET_KEY`
- [ ] Setup PostgreSQL with backups
- [ ] Configure Pinecone production index
- [ ] Setup monitoring and logging
- [ ] Configure CORS allowed origins
- [ ] Setup SSL/TLS certificates
- [ ] Configure email notifications
- [ ] Setup rate limiting

## Development

### Testing

```bash
pytest tests/ -v --cov=app
```

### Code Quality

```bash
black app/
flake8 app/
isort app/
mypy app/
```

### Database Migrations

Migrations are handled automatically by SQLAlchemy on startup.

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Ensure user has correct permissions

### LLM Integration Issues
- Verify OPENAI_API_KEY is set
- Check API rate limits
- Monitor token usage

### Pinecone Vector Store Issues
- Verify PINECONE_API_KEY and environment
- Check index dimensions match embeddings
- Ensure index is active

## Performance Optimization

- Database connection pooling (20 connections)
- Async/await throughout
- Query optimization with indexes
- Vector search caching
- Response caching with TTL
- Batch processing for bulk operations

## Support & Documentation

- API Docs: http://localhost:8000/docs
- Database Schema: See DATABASE_SCHEMA.md
- Architecture Details: See inline code comments
- Academic Formulas: See DATABASE_SCHEMA.md

## License

Proprietary - Outcome-Based Education System

## Contact

For issues, feature requests, or support, please contact the development team.

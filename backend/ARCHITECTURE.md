# Backend Architecture Documentation

## System Architecture Overview

The system follows an advanced layered architecture with a central communication hub that orchestrates all academic workflows.

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│  REST Endpoints | Authentication | Input Validation         │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│            Communication Layer (Central Hub)                 │
│  ┌──────────────────┬──────────────────┬──────────────────┐  │
│  │  Orchestrator    │  Service Router  │   Event Bus      │  │
│  │  (Workflow Mgmt) │  (Request Route) │  (Async Comms)   │  │
│  └──────────────────┴──────────────────┴──────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐│
│  │    LangGraph Workflow Manager (AI Orchestration)        ││
│  └──────────────────────────────────────────────────────────┘│
└────────────────┬──────────────────────────────────┬──────────┘
                 │                                  │
┌────────────────▼──────────────┐  ┌───────────────▼────────────┐
│    Domain Modules             │  │   AI Engine                │
│  ┌──────────────────────────┐ │  │ ┌────────────────────────┐ │
│  │ Authentication           │ │  │ │ LLM Client (OpenAI)    │ │
│  │ Course Management        │ │  │ │ Embeddings Service     │ │
│  │ Academic Structure       │ │  │ │ RAG Pipelines          │ │
│  │ CO Generation (AI)       │ │  │ │ Semantic Search        │ │
│  │ CO-PO Mapping           │ │  │ │ Vector Store (Pinecone)│ │
│  │ Exam Management         │ │  │ └────────────────────────┘ │
│  │ Question Analysis       │ │  │ ┌────────────────────────┐ │
│  │ Marks Processing        │ │  │ │ Chatbot Agents         │ │
│  │ Attainment Engine       │ │  │ │ - CO Generation Agent  │ │
│  │ Reporting               │ │  │ │ - Mapping Agent        │ │
│  └──────────────────────────┘ │  │ │ - Question Agent       │ │
└────────────────┬───────────────┘  │ │ - Attainment Agent     │ │
                 │                   │ └────────────────────────┘ │
                 │                   └───────────────────────────┘
┌────────────────▼────────────────────────────────────────────────┐
│                    Data Layer                                    │
│  ┌─────────────────────┐         ┌─────────────────────────┐    │
│  │   PostgreSQL DB     │         │  Pinecone Vector DB     │    │
│  │  - Users            │         │  - CO Embeddings        │    │
│  │  - Courses          │         │  - PO Embeddings        │    │
│  │  - Outcomes         │         │  - Question Embeddings  │    │
│  │  - Exams            │         │  - Syllabus Vectors     │    │
│  │  - Questions        │         │  - Semantic Search      │    │
│  │  - Marks            │         └─────────────────────────┘    │
│  │  - Attainments      │                                         │
│  │  - Audit Logs       │                                         │
│  └─────────────────────┘                                         │
└──────────────────────────────────────────────────────────────────┘
```

## Module Communication Flow

### 1. Authentication Module
**Purpose**: User authentication and authorization

**Components**:
- JWT Token Management
- Password Hashing (Bcrypt)
- Role-Based Access Control

**Flow**:
```
User Login → JWT Manager → Token Generation → Session Storage
   ↓
Token Verification → Permission Check → Access Granted/Denied
```

### 2. Course & Academic Structure Modules
**Purpose**: Manage courses, outcomes, and academic metadata

**Components**:
- Course Repository
- Outcome Repository
- Validation & Constraints

**Data Flow**:
```
Course Input → Validation → Database Storage → Embedding Generation
     ↓
Vector Store (Pinecone) → Indexed for semantic search
```

### 3. CO Generation Module
**Purpose**: Automatically generate Course Outcomes from syllabus

**Advanced Logic**:
1. **Syllabus Parsing**: Extract topics using LLM
2. **Topic Analysis**: Identify knowledge domains
3. **CO Statement Generation**: AI-driven creation
4. **Bloom's Taxonomy Assignment**: Level detection
5. **Coverage Validation**: Ensure complete coverage
6. **Embedding Generation**: Create semantic vectors

**AI Pipeline**:
```
Syllabus Text
    ↓
RAG Pipeline (Retrieval-Augmented Generation)
    ↓
LLM Processing
    ↓
CO Statements with Bloom Levels
    ↓
Embedding Generation
    ↓
Vector Storage in Pinecone
```

### 4. CO-PO Mapping Module
**Purpose**: Create semantic links between COs and POs

**Algorithm**:
```
CO Embeddings → Cosine Similarity Calculation → PO Embeddings
    ↓
Similarity Scores → Threshold Filtering → Mapped COs & POs
    ↓
Confidence Scores → Database Storage
```

### 5. Exam & Question Analysis Module
**Purpose**: Process exams and analyze questions

**Question Analysis Process**:
1. **Bloom Level Detection**:
   - Keyword matching
   - AI-based analysis
   - Result combination

2. **CO Mapping**:
   - Semantic similarity matching
   - Confidence scoring

**Formula**:
```
Question Text
    ↓
Embedding Generation
    ↓
Similarity Comparison with CO Embeddings
    ↓
Matching Score Calculation
    ↓
CO Assignment
```

### 6. Marks Processing Module
**Purpose**: Upload and validate student marks

**Validation Pipeline**:
```
Excel Upload
    ↓
Format Validation
    ↓
Range Checking (marks ≤ total_marks)
    ↓
Duplicate Detection
    ↓
Outlier Detection
    ↓
Database Storage
```

### 7. Attainment Engine
**Purpose**: Calculate CO, PO, and PSO attainment

**Calculation Formulas**:

**CO Attainment** (Real academic formula):
```
CO Attainment = Σ(marks for CO questions) / Σ(total marks for CO)

Example:
CO1 has 3 questions (Q1, Q2, Q3) with 10 marks each
Students obtained: Q1: 70, Q2: 60, Q3: 75
CO1 Attainment = (70+60+75) / (10+10+10) = 205/30 = 0.683 (68.3%)
Attainment Level = Level 2 (60-69%)
```

**PO Attainment** (Averaging formula):
```
PO Attainment = Σ(CO Attainments) / Number of Mapped COs

Example:
PO1 mapped to: CO1 (68.3%), CO2 (75%), CO3 (62%)
PO1 Attainment = (0.683 + 0.75 + 0.62) / 3 = 0.684 (68.4%)
Attainment Level = Level 2
```

**PSO Attainment**:
Same as PO attainment (average of mapped CO attainments)

**Attainment Levels**:
- Level 3 (Fully Attained): ≥ 70%
- Level 2 (Partially Attained): 60-69%
- Level 1 (Minimally Attained): < 60%
- Not Attained: 0%

### 8. Reporting Module
**Purpose**: Generate comprehensive reports

**Report Types**:
- CO Attainment Report
- PO Attainment Report
- Class Statistics
- Trend Analysis
- Export Formats: PDF, Excel

## LangGraph Workflow Orchestration

The system uses LangGraph for sophisticated multi-agent workflows:

```
┌──────────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow State Machine              │
└──────────────────────────────────────────────────────────────────┘

Input State
    ↓
┌─────────────────────────────────┐
│  CO Generation Agent            │
│  - Parse syllabus               │
│  - Extract topics               │
│  - Generate COs with Bloom      │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  Mapping Agent                  │
│  - Create embeddings            │
│  - Map COs to POs/PSOs          │
│  - Store mappings               │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  Exam Configuration Agent       │
│  - Configure exam structure     │
│  - Set mark distribution        │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  Question Analysis Agent        │
│  - Detect Bloom levels          │
│  - Map to COs                   │
│  - Calculate confidence         │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  Marks Processing Agent         │
│  - Validate marks               │
│  - Process Excel files          │
│  - Detect outliers              │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  Attainment Calculation Agent   │
│  - Calculate CO attainment      │
│  - Calculate PO attainment      │
│  - Determine levels             │
└────────────┬────────────────────┘
             ↓
┌─────────────────────────────────┐
│  Report Generation Agent        │
│  - Create analytics             │
│  - Generate reports             │
│  - Export formats               │
└────────────┬────────────────────┘
             ↓
Output Report & Analytics
```

## Event-Driven Communication

The Event Bus enables asynchronous communication:

```
Module A                Event Bus              Module B
   │                       │                     │
   ├──→ PublishEvent(X) ──→│                     │
   │                       ├──→ Route Event X──→ │
   │                       │                     │
   │                    │                     │
   │                    │                     │
   │                 Register Handlers        │
   │ (Subscribers listen for events)          │
   │                    │                     │
```

**Event Types**:
- CO_GENERATED
- CO_MAPPED
- EXAM_CREATED
- QUESTIONS_ANALYZED
- MARKS_PROCESSED
- ATTAINMENT_CALCULATED
- REPORT_GENERATED
- ERROR_OCCURRED

## Security Architecture

### Authentication Flow
```
1. Credentials → Hash Check → Success?
2. Success → Generate JWT (access + refresh)
3. Store tokens → Client keeps access token
4. Each request → Verify token signature & expiry
5. Invalid? → Return 401 Unauthorized
```

### Authorization Flow
```
Token → Extract User & Role → Check Permissions → Allow/Deny
```

### Password Security
```
User Password → Bcrypt (cost=12) → Hash Storage
Login → Bcrypt Verify → Match?
```

## Database Transaction Management

**ACID Compliance**:
- **Atomicity**: All-or-nothing operations
- **Consistency**: Data integrity constraints
- **Isolation**: Concurrent request handling
- **Durability**: PostgreSQL durability

**Transaction Patterns**:
```python
async with session.begin():
    # All operations succeed or all fail
    user = await create_user(session, data)
    await create_audit_log(session, user, "created")
    # Auto-commit on success, auto-rollback on error
```

## Performance Optimization Strategies

### 1. Database
- Connection pooling (20 connections)
- Query optimization with indexes
- Lazy loading relationships
- Batch operations for bulk inserts

### 2. Caching
- Vector embeddings cache
- Short TTL: 5 minutes
- Medium TTL: 30 minutes
- Long TTL: 1 day

### 3. Async Processing
- Non-blocking database access
- Concurrent request handling
- Event-driven updates

### 4. AI Engine
- LLM response caching
- Embedding reuse
- Batch processing

## Deployment Topology

### Development
```
Single Container with hot-reload
SQLite optional for quick testing
```

### Production
```
┌─────────────────────┐
│  Load Balancer      │
│  (Nginx)            │
└────────┬────────────┘
         │
    ┌────┴────┬────────┬────────┐
    │          │        │        │
┌───▼──┐ ┌───▼──┐ ┌───▼──┐ ┌──▼───┐
│ App  │ │ App  │ │ App  │ │ App  │
│ Pod1 │ │ Pod2 │ │ Pod3 │ │ Pod4 │
└───┬──┘ └───┬──┘ └───┬──┘ └──┬───┘
    │         │        │       │
    └─────────┼────────┼───────┘
              │        │
         ┌────▼────┐   │
         │ Database│   │
         │ Cluster │   │
         └─────────┘   │
                       │
                  ┌────▼────┐
                  │ Pinecone │
                  │ (SaaS)   │
                  └──────────┘
```

## Scalability Considerations

1. **Horizontal Scaling**: Multiple app instances behind load balancer
2. **Database Scaling**: PostgreSQL read replicas for analytics
3. **Vector DB**: Pinecone handles scaling automatically
4. **Caching Layer**: Redis for distributed caching
5. **Task Queue**: Celery for long-running operations

## Monitoring & Observability

- Structured JSON logging
- Audit logs for compliance
- Performance metrics
- Error tracking
- Request tracing

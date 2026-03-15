# Deployment Guide - CO-PO-PSO Mapping System

## Overview
Complete production-ready CO-PO-PSO Mapping and Attainment Chatbot with multi-agent AI orchestration.

## Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Git
- Docker (optional)

## Local Development Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd backend
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql+asyncpg://user:password@localhost/co_pso_db
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-key
PINECONE_API_KEY=your-pinecone-key
```

### 5. Initialize Database
```bash
cd backend
python scripts/init_database.py
```

### 6. Run Application
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access API at: http://localhost:8000/docs

## API Endpoints Overview

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/change-password` - Change password

### Courses
- `POST /api/v1/courses` - Create course
- `GET /api/v1/courses/{course_id}` - Get course details
- `POST /api/v1/courses/{course_id}/generate-cos` - Generate COs from syllabus
- `GET /api/v1/courses/{course_id}/outcomes` - Get course outcomes

### CO-PO Mapping
- `POST /api/v1/courses/{course_id}/outcomes/{co_id}/map-to-pos` - Map CO to POs

### Exams
- `POST /api/v1/courses/{course_id}/exams` - Create exam
- `POST /api/v1/exams/{exam_id}/questions` - Add question
- `POST /api/v1/exams/{exam_id}/marks` - Submit marks

### Attainment
- `POST /api/v1/exams/{exam_id}/calculate-attainments` - Calculate attainments
- `GET /api/v1/courses/{course_id}/attainment-report` - Get report

### Multi-Agent System
- `POST /api/v1/conversations` - Start conversation
- `POST /api/v1/conversations/{conversation_id}/message` - Send message

## Docker Deployment

### 1. Build Image
```bash
docker build -t co-pso-api:latest -f Dockerfile .
```

### 2. Run Container
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:password@host/db \
  -e OPENAI_API_KEY=your-key \
  -e PINECONE_API_KEY=your-key \
  co-pso-api:latest
```

### 3. Docker Compose
```bash
docker-compose up -d
```

## Production Deployment

### Environment Variables
```bash
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:password@prod-db/co_pso_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
SECRET_KEY=<strong-secret-key>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
OPENAI_API_KEY=<your-api-key>
PINECONE_API_KEY=<your-api-key>
LOG_LEVEL=INFO
```

### Database Setup
```bash
# Create database
createdb co_pso_db

# Run migrations
alembic upgrade head

# Initialize data
python scripts/init_database.py
```

### Run with Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker app.main:app
```

### Nginx Configuration
```nginx
upstream app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Testing

### Unit Tests
```bash
pytest tests/ -v --cov=app
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### Load Testing
```bash
locust -f tests/load/locustfile.py
```

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Logs
```bash
tail -f logs/app.log
```

### Database Backups
```bash
pg_dump co_pso_db > backup_$(date +%Y%m%d).sql
```

## Troubleshooting

### Database Connection Issues
```bash
# Test connection
psql -h localhost -U user -d co_pso_db

# Check logs
tail -f logs/app.log
```

### LLM API Issues
- Verify OPENAI_API_KEY is set correctly
- Check rate limits on OpenAI dashboard
- Ensure network connectivity

### Pinecone Issues
- Verify PINECONE_API_KEY
- Check index status in Pinecone console
- Validate namespace configuration

## System Architecture

### Layered Architecture
1. **API Layer** - FastAPI routes and schemas
2. **Service Layer** - Business logic (attainment, mapping, etc.)
3. **Repository Layer** - Data access (CRUD operations)
4. **Agent Layer** - LangGraph multi-agent orchestration
5. **AI Engine** - LLM and embedding services
6. **Database Layer** - SQLAlchemy ORM with PostgreSQL

### Multi-Agent System
- **CO Generation Agent** - Generate outcomes from syllabus
- **Bloom Taxonomy Agent** - Detect question difficulty levels
- **Semantic Mapping Agent** - Map COs to POs/PSOs
- **Attainment Agent** - Calculate attainment metrics
- **Reporting Agent** - Generate comprehensive reports

## Real Business Logic

### Attainment Formula
```
CO Attainment = Sum(marks for CO questions) / Sum(total marks for CO) * 100
PO Attainment = Average of mapped CO attainments
PSO Attainment = Average of mapped CO attainments
```

### Attainment Levels
- Level 3: ≥ 70% (Fully Attained)
- Level 2: 60-69% (Partially Attained)
- Level 1: <60% (Minimally Attained)

### Semantic Similarity
Uses cosine similarity with embeddings:
- High threshold: ≥0.8
- Medium threshold: ≥0.6
- Low threshold: ≥0.4

## Performance Optimization

### Database
- Connection pooling (pool_size=20)
- Query optimization with proper indexing
- Async operations throughout

### Caching
- Short TTL: 5 minutes
- Medium TTL: 30 minutes
- Long TTL: 1 day

### API
- Response compression (GZIP)
- Request validation
- Rate limiting (can be added)

## Security

### Authentication
- JWT with refresh tokens
- Password hashing with bcrypt (cost=12)
- Role-based access control (RBAC)

### Data Protection
- SQL parameterized queries
- Input validation
- CORS configuration
- HTTPS in production

### Audit
- Comprehensive audit logging
- User action tracking
- Database transaction logging

## Maintenance

### Regular Tasks
- Monitor API logs
- Check database size
- Verify backups
- Update dependencies
- Monitor API performance

### Updates
```bash
pip install --upgrade -r requirements.txt
python scripts/init_database.py
```

## Support & Documentation

- API Documentation: http://localhost:8000/docs
- Code Documentation: See inline comments
- Architecture Guide: ARCHITECTURE.md
- Implementation Guide: IMPLEMENTATION_GUIDE.md

## License
Internal Use Only

## Contact
Support: support@university.edu

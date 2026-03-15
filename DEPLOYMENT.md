# Deployment Guide - Production Backend

## Local Development (5 minutes)

### Step 1: Setup Environment
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Configure Database
```bash
cp .env.example .env
```

Edit `.env`:
```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/co_pso_db
SECRET_KEY=your-secret-key-change-this-in-production
OPENAI_API_KEY=sk-...
DEBUG=True
ENVIRONMENT=development
```

### Step 3: Initialize Database
```bash
python scripts/seed_database.py
```

Expected output:
```
Seeding database with real data...
Database seeded successfully with real data!
- 3 users (admin, 2 faculty)
- 1 department and 1 program
- 3 students
- 2 courses with 4 course outcomes
- 2 program outcomes
- 1 exam with 4 questions
- 12 student marks records
```

### Step 4: Start Server
```bash
uvicorn app.main:app --reload
```

Server runs on: http://localhost:8000

API Documentation: http://localhost:8000/docs

---

## Docker Deployment

### Build Docker Image
```bash
docker build -t co-pso-backend:latest .
```

### Run with Docker Compose
```bash
docker-compose up -d
```

This will:
- Start PostgreSQL container
- Run backend on port 8000
- Initialize database automatically
- Seed real data

**Access**: http://localhost:8000

---

## Production Deployment (AWS/Heroku/DigitalOcean)

### Prerequisites
- PostgreSQL database (RDS, Heroku Postgres, DigitalOcean Managed)
- Python 3.9+ runtime
- Environment variables configured

### Step 1: Prepare Code
```bash
# Clone repository
git clone <repo-url>
cd backend

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment
Set environment variables on your hosting platform:
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
SECRET_KEY=your-production-secret-key-min-32-chars
OPENAI_API_KEY=sk-...
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO
```

### Step 3: Initialize Database
```bash
# Run migrations (one-time)
python scripts/seed_database.py
```

### Step 4: Run Server
```bash
# Using Gunicorn (recommended for production)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 60 \
  app.main:app
```

Or with Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Heroku Deployment

### Create Heroku App
```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:standard-0
```

### Set Environment Variables
```bash
heroku config:set SECRET_KEY=your-secret-key
heroku config:set OPENAI_API_KEY=sk-...
heroku config:set ENVIRONMENT=production
```

### Deploy
```bash
git push heroku main
heroku run "python scripts/seed_database.py"
```

---

## AWS Elastic Beanstalk

### Create Application
```bash
eb init -p python-3.9 co-pso-backend
eb create production-env
```

### Configure Environment
```bash
eb setenv DATABASE_URL=postgresql+asyncpg://...
eb setenv SECRET_KEY=your-key
eb setenv OPENAI_API_KEY=sk-...
```

### Deploy
```bash
eb deploy
eb ssh
# Then run: python scripts/seed_database.py
```

---

## DigitalOcean App Platform

### Create app.yaml
```yaml
name: co-pso-backend
services:
  - name: api
    github:
      repo: your-username/repo
      branch: main
    build_command: pip install -r requirements.txt
    run_command: gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
    envs:
      - key: DATABASE_URL
        scope: RUN_AND_BUILD_TIME
        value: ${db.connection_string}
    http_port: 8000

databases:
  - name: db
    engine: PG
    version: "12"
    production: true
```

### Deploy
```bash
doctl apps create --spec app.yaml
```

---

## Production Checklist

- [ ] Set `DEBUG=False` in environment
- [ ] Change `SECRET_KEY` to random string (≥32 chars)
- [ ] Configure production database (AWS RDS/managed)
- [ ] Set up environment variables on hosting platform
- [ ] Run database initialization script once
- [ ] Test all API endpoints
- [ ] Enable HTTPS/SSL
- [ ] Set up monitoring and logging
- [ ] Configure CORS for frontend domain
- [ ] Set up database backups
- [ ] Configure CI/CD pipeline
- [ ] Load test the application
- [ ] Set up error tracking (Sentry)
- [ ] Configure email for notifications

---

## Monitoring & Logging

### Application Logs
The backend logs all operations to stdout with JSON format:
```json
{"timestamp": "2024-03-13T10:30:45", "level": "INFO", "logger": "api_routes", "message": "User authenticated: user_id"}
```

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{"status": "healthy", "timestamp": "2024-03-13T10:30:45"}
```

### Performance Monitoring
- Connection pool: 20 connections
- Query timeout: 30 seconds
- Request timeout: 60 seconds
- Memory limit: 512MB (recommended minimum)

---

## Troubleshooting

### Issue: Database connection failed
```
Error: could not translate host name "localhost" to address
```
**Solution**: Verify DATABASE_URL in .env matches your database setup

### Issue: Port 8000 already in use
```bash
# Find process using port
lsof -i :8000

# Use different port
uvicorn app.main:app --port 8001
```

### Issue: CORS errors from frontend
**Solution**: Update CORS origins in `.env`:
```
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Issue: Slow queries
**Solution**: Check database indexes:
```sql
-- List all indexes
SELECT * FROM pg_indexes WHERE tablename = 'courses';
```

---

## Scaling

### Horizontal Scaling
Use load balancer (Nginx, AWS ALB) to distribute requests across multiple API instances:
```
API1 → Load Balancer → Database
API2 → Load Balancer → Database
API3 → Load Balancer → Database
```

### Database Scaling
For high load:
1. Read replicas for GET endpoints
2. Separate write database for POST/PUT/DELETE
3. Redis cache for frequently accessed data

### Caching Strategy
Add Redis for:
- Course outcomes (30min TTL)
- Program outcomes (1hr TTL)
- Attainment calculations (5min TTL)

---

## Backup & Recovery

### Automated Backups
```bash
# PostgreSQL backup
pg_dump -U postgres co_pso_db > backup_$(date +%Y%m%d).sql

# Restore from backup
psql -U postgres co_pso_db < backup_20240313.sql
```

### Point-in-Time Recovery
Enable WAL (Write-Ahead Logging) in PostgreSQL for point-in-time recovery.

---

## Version Upgrades

### Update Dependencies
```bash
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt
git commit -m "Update dependencies"
git push
# Deploy to hosting platform
```

### Database Migrations
When adding new tables:
```bash
# Edit models.py
# Then run:
python scripts/migrate_database.py
```

---

## Support & Maintenance

- Check logs regularly
- Monitor database performance
- Review error tracking (Sentry)
- Keep dependencies updated
- Test new deployments in staging first
- Document configuration changes

---

## Quick Reference

```bash
# Local development
uvicorn app.main:app --reload

# Production (Gunicorn)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app

# Docker
docker-compose up -d

# Database initialization
python scripts/seed_database.py

# Health check
curl http://localhost:8000/api/v1/health

# API documentation
http://localhost:8000/docs
```

---

**Ready for deployment!** 🚀

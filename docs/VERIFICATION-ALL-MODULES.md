# Frontend & Backend Modules Verification

## Backend verification

### Status
- **Server**: FastAPI (Uvicorn) runs on `http://localhost:8000`
- **Health**: `GET /health` — returns status, environment, dependencies (postgres, redis, neo4j)
- **API prefix**: `/api/v1`
- **Docs**: `http://localhost:8000/docs`

### Core API modules (all under `/api/v1`)

| Module | Endpoints | Purpose |
|--------|-----------|---------|
| **Auth** | POST /auth/register, /auth/login, /auth/change-password, /auth/forgot-password, /auth/reset-password, /auth/verify-otp | Registration, login, password flows |
| **Users** | GET /users, PUT /users/{user_id} | Admin user list & update |
| **Programs** | GET /programs | List programs |
| **Settings** | GET/PUT /settings/thresholds | Attainment thresholds |
| **Audit** | GET /audit-log | Admin/HOD audit log |
| **Academic years** | GET/POST /academic-years, GET /academic-years/current, POST /academic-years/{code}/lock | AY config |
| **Faculty** | GET /faculty/dashboard, /faculty/notifications, /faculty/activity-log | Faculty dashboard & activity |
| **Lead** | GET /lead/dashboard, /lead/co-health/{dept}, /lead/po-targets/{dept}, POST /lead/approve, marks-approval, reports | Course lead & HOD |
| **Courses** | GET/POST/PUT/DELETE /courses, /courses/{id}/outcomes, /courses/{id}/exams, generate-co, outcomes/detail, mappings | Courses, COs, exams |
| **Exams** | POST /exams/{id}/questions, /exams/{id}/marks, GET exam questions | Exam config & marks |
| **PO/PSO** | GET/POST/PUT/DELETE /programs/{id}/outcomes, /programs/{id}/pso | PO & PSO master |
| **Chatbot** | POST /chatbot/message | AI chat |
| **Reports** | POST /reports/generate, GET download | Report generation |

### How to test backend
```powershell
# Health
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get

# API root
Invoke-RestMethod -Uri "http://localhost:8000/" -Method Get

# Login (get token first for protected routes)
$body = '{"email":"admin@test.com","password":"yourpassword"}'  # or employee_id
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method Post -Body $body -ContentType "application/json"
```

---

## Frontend verification

### Status
- **Dev server**: Next.js 16 (Turbopack) on `http://localhost:3000`
- **Build**: Run `npm run build` from `frontend/frontend` (fixed unicode ellipsis in loading messages for Turbopack parse)

### App routes (all under `(app)` or `(auth)`)

| Area | Routes | Backend integration |
|------|--------|--------------------|
| **Auth** | /login, /register, /student-login, /forgot-password, /reset-password | auth/login, register, change-password, forgot/reset |
| **Dashboard** | /dashboard, /faculty/dashboard, /lead/dashboard, /hod/dashboard, /admin/dashboard | faculty/dashboard, lead/dashboard, getCourses |
| **Faculty** | /faculty/course/[id]/co-generation, exam-config, question-mapping, marks, co-attainment, reports, chatbot | courses, outcomes, exams, marks, attainment, chatbot/message |
| **Lead** | /lead/co-attainment, marks-approval, po-attainment, reports, ay-comparison, remedial-actions | lead/* |
| **HOD** | /hod/dashboard, co-attainment, year-end-lock, thresholds | lead/dashboard, academic-years lock |
| **Admin** | /admin/users, thresholds, audit-log, academic-year, po-pso-master, co-library, users/course-assignment, student-bulk-enrolment | /users, /settings/thresholds, /audit-log, /programs, /courses |
| **Shared** | /chatbot, /co-library, /co-po-matrix, /reports, /audit-trail, /low-co-alerts, /settings | getCourses, getCourseOutcomesDetail, updateCOMappings, getFacultyActivityLog, getCourseLeadDashboard |
| **Student** | /student/dashboard, courses, marks, course/[id]/co-attainment | (student-facing APIs) |

### Fix applied
- Replaced Unicode ellipsis (`…`) with ASCII `...` in loading messages (admin co-library, users, thresholds, audit-log, po-pso-master, student-bulk-enrolment, course-assignment) to avoid Turbopack parse errors.

---

## Quick checklist

- [x] Backend starts (Uvicorn, DB init, Redis optional)
- [x] Backend /health and / exist
- [x] Frontend dev server runs (Next.js)
- [x] Frontend build parse error fixed (co-library + ellipsis in other admin pages)
- [ ] Manual: Open http://localhost:3000 and log in; hit dashboard, faculty course, admin users, chatbot
- [ ] Manual: Open http://localhost:8000/docs and try protected endpoints with JWT

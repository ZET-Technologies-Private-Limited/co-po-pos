# OBE Backend Spec Compliance Audit

Date: 2026-03-14
Scope: Existing backend project structure under backend/app against provided architecture specification.

## 1) Microservice Architecture Coverage

| Spec Service | Status | Evidence |
|---|---|---|
| api-gateway (Nginx/Kong) | Missing | No gateway config in backend project.
| auth-service (separate) | Partial | Auth endpoints exist in monolith routes; not split as dedicated service.
| rasa-server | Partial | Rasa configs and training assets exist under backend/rasa; external runtime not bundled as service process in app.
| action-server (Rasa SDK) | Missing | No dedicated Rasa SDK action server package/module detected.
| langgraph-engine (separate) | Partial | LangGraph workflow exists in app/agents; not deployed as separate microservice.
| fastapi-core | Implemented | Primary API layer in app/main.py + app/api/v1/routes.py.
| attainment-service (separate) | Partial | Attainment engine and Celery task exist; no separate deployable service boundary.
| report-service (separate) | Partial | Report generation exists in FastAPI service + exporter module; no separate deployable.
| file-service (separate) | Partial | Implemented upload/presign APIs, but still hosted in monolith route set.
| notification-service (separate) | Missing | No dedicated notification microservice with SMTP flow.

## 2) Core Technology Coverage

| Technology | Status | Notes |
|---|---|---|
| Rasa NLU | Partial | Present with trained model flow; not fully microservice-isolated action pipeline.
| LangGraph | Implemented | Workflow nodes and routing used by chatbot service.
| FastAPI REST | Implemented | Full API backbone active.
| PostgreSQL | Implemented | Async SQLAlchemy models and connection manager active.
| Neo4j | Partial | Client + graph mapping service implemented; requires env/config + running Neo4j.
| Redis | Implemented | Health-check integration, cache helpers, marks locks, pub/sub + streams event bus.
| Celery | Partial | App + attainment task + queue/status APIs implemented; worker process orchestration still required in deployment.
| MinIO/S3 | Partial | Real upload and presigned URL APIs implemented; requires credentials and endpoint setup.
| Elasticsearch | Partial | Real index/search client and search API implemented; requires ES endpoint setup.

## 3) Endpoint Parity Summary

### Implemented from requested matrix
- Auth: login/register present (refresh/logout/reset-password/set-password/me not fully present as specified).
- Course/CO CRUD and generation flows present.
- Exam/question CRUD + analysis present.
- Attainment compute + pipeline + matrix + course/student analytics present.
- Report generation + direct download present.
- Chatbot message endpoint present.
- Added now:
  - POST /api/v1/marks/{exam_id}/submit
  - POST /api/v1/marks/{exam_id}/approve
  - POST /api/v1/marks/{exam_id}/unlock
  - GET /api/v1/marks/{exam_id}/preview
  - POST /api/v1/files/upload
  - POST /api/v1/files/presigned
  - POST /api/v1/search/questions
  - GET /api/v1/reports/status/{job_id}
  - GET /api/v1/reports/download/{job_id}

### Still missing from requested matrix
- Full auth lifecycle endpoints: refresh/logout/password reset OTP/me profile.
- Marks workflow endpoints with exact path contract and return/approval comments semantics.
- Full admin suite (users bulk import, AY lock/signoff, thresholds CRUD, full audit API).
- Dedicated notification endpoints/service.

## 4) Data Model Parity

- Implemented core entities: users, courses, outcomes, exams, questions, marks, CO/PO/PSO attainments, reports.
- Partial/mismatch versus requested schema:
  - Current models are simplified compared to requested AY, dept, role-assignment, and override/audit richness.
  - No first-class upload_log table or report job table for full async file lifecycle.
  - No explicit JWT blacklist/session tables in DB (Redis-based behavior only).

## 5) Critical Gaps Remaining for Full Spec Parity

1. Service decomposition into actual independently deployable microservices (gateway/auth/action/langgraph/attainment/report/file/notification).
2. Rasa action-server separation and endpoint wiring via endpoints.yml.
3. Notification system with SMTP and event subscribers.
4. Full academic-year lock/signoff and role-scoped middleware semantics at requested strictness.
5. Complete admin and audit APIs + data model enrichment.
6. Full file-service async job flow with persistent upload logs and status polling contract.
7. Elastic question indexing trigger coverage beyond question creation path.

## 6) Verified Runtime Signals (this pass)

- Health endpoint includes dependency state and currently reports Postgres and Redis healthy.
- Marks submit/unlock endpoints verified with JWT auth.
- Marks preview and approve endpoints verified, including Celery task ID return.
- File-service endpoint verified to return explicit 503 when object storage credentials are not configured.
- Search endpoint verified to return explicit 503 when Elasticsearch URL is not configured.

## 7) Rasa Intent List Coverage (requested complete list)

- Implemented all requested intents in Rasa domain and NLU training data:
  - greet, goodbye, start_co_generation, provide_syllabus, confirm_po_pso, request_co_count,
    approve_cos, edit_co, regenerate_cos, regenerate_single_co, explain_co_bt, setup_exam,
    provide_exam_type, provide_max_marks, analyse_question, map_question_co, upload_marks_intent,
    explain_attainment, ask_po_attainment, ask_ay_history, ask_low_co, affirm, deny, out_of_scope.
- Added corresponding stories/rules and response handlers.
- Linked newly added intents to existing LangGraph nodes for backend actionability.
- Trained model artifact:
  - rasa/models/20260314-134654-big-warp.tar.gz
- Real parse checks on Rasa API (port 5006) confirmed correct recognition for the new intent set,
  including out_of_scope classification for unrelated message samples.

### Final tuned parse benchmark (post-disambiguation)

- Generate COs for my course -> start_co_generation (0.9882)
- Here is my syllabus unit 1 arrays -> provide_syllabus (0.9858)
- Yes use defaults -> confirm_po_pso (0.9535)
- Generate 5 COs -> request_co_count (0.8424)
- Change CO3 -> edit_co (0.9625)
- Redo CO3 only -> regenerate_single_co (0.9533)
- Why is CO3 L4 -> explain_co_bt (0.9150)
- Configure T1 -> setup_exam (0.9575)
- 20 marks -> provide_max_marks (0.8944)
- Analyse this question -> analyse_question (0.9591)
- Upload marks sheet -> upload_marks_intent (0.9620)
- Explain CO3 52% -> explain_attainment (0.9648)
- PO1 attainment -> ask_po_attainment (0.9061)
- Show 3 year trend -> ask_ay_history (0.9294)
- Level 1 COs -> ask_low_co (0.7549)
- Anything unrelated to courses -> out_of_scope (0.9788)

## 8) Conclusion

Current project now has strong monolithic feature coverage with real integrations for Redis, Celery, and Neo4j/MinIO/Elasticsearch client paths.
It is not yet fully compliant with the provided microservice-level architecture and full endpoint/data-contract matrix.

## 9) Latest Live Verification (Neo4j re-check)

Backend instance verified on port 8012 with authenticated E2E checks:

- auth_register: PASS
- course_outcomes_fetch: PASS (count=5)
- map_co_po: PASS (mappings=15)
- map_co_pso: PASS (mappings=10)
- calculate_co: PASS (rows=0)
- calculate_po: PASS (rows=3)
- marks_preview: PASS (source=redis,count=0)
- marks_approve: PASS (task queued)
- chatbot_po_attainment: PASS (intent resolved via rasa)
- graph_po_impact: FAIL with detail Neo4j is not configured

Runtime diagnosis in current shell/session:

- NEO4J_URI is empty
- NEO4J_USER is empty
- NEO4J_PASSWORD is not set

Result: Neo4j code path is implemented, but runtime configuration is not loaded in the active backend process.
To enable graph endpoint success, set Neo4j env vars for the backend runtime and restart FastAPI.

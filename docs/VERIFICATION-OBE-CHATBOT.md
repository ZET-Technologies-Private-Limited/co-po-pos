# Verification: AI-Based CO-PO-PSO Mapping and Attainment Chatbot

This document verifies that the implementation matches the problem statement **with real logic, dynamic algorithms, and no mocks or hardcoded data** on both frontend and backend.

---

## 1. Course Outcome Generation

| Requirement | Backend | Frontend | Mocks / Hardcoded |
|-------------|---------|----------|-------------------|
| Inputs: syllabus, POs, PSOs | `POST /api/v1/courses/{id}/generate-co` — `CoGenerationService.generate_cos_from_syllabus()` uses **LLMClient** (Gemini/Ollama) and DB for Course, PO, PSO | `faculty/course/[id]/co-generation` — `apiClient.getCourse`, `getProgramOutcomes`, `getPSOs`, `generateCourseOutcomes()` | **None** |
| Generate 4–6 COs, Bloom’s Taxonomy | Service generates COs via LLM; Bloom levels validated; num_cos configurable (default 5) | User sets syllabus, num COs; PO/PSO from API | **None** |
| Align COs with syllabus; map CO→PO/PSO | LLM prompt includes syllabus + PO/PSO; mappings stored in `co_po_mapping_table`, `co_pso_mapping_table` | Displays generated COs and mappings from API response | **None** |

**Backend:** `app/modules/co_generation/services/co_generation_service.py`, `app/api/v1/routes.py` (generate_course_outcomes).  
**Frontend:** `app/(app)/faculty/course/[id]/co-generation/page.tsx` — **apiClient only**, no useDataStore.

---

## 2. Examination Configuration

| Requirement | Backend | Frontend | Mocks / Hardcoded |
|-------------|---------|----------|-------------------|
| Exam type (Formative T1–T5, Summative) | `POST /api/v1/courses/{id}/exams` — ExamCreate (exam_name, exam_type, total_marks, etc.) stored in DB | `faculty/course/[id]/exam-config` — `apiClient.getCourse`, `getExams`, `createExam`, `deleteExam`, `addQuestions` | **None** |
| Question paper structure, marks distribution | `POST /api/v1/exams/{id}/questions` — questions with marks, question_number; AI Bloom + CO mapping in `QuestionAnalysisService` | Same page: add questions with marks; data from/to API | **None** |

**Backend:** `app/api/v1/routes.py` (create_exam, add_exam_questions), `app/modules/question_analysis/services/question_analysis_service.py`.  
**Frontend:** `app/(app)/faculty/course/[id]/exam-config/page.tsx` — **apiClient only**.

---

## 3. Question–CO Mapping

| Requirement | Backend | Frontend | Mocks / Hardcoded |
|-------------|---------|----------|-------------------|
| Analyze question statements | `POST /api/v1/exams/{id}/analyze-questions` — `QuestionAnalysisService` (stats, Bloom distribution) | `faculty/course/[id]/question-analyser` — `apiClient.analyzeQuestions(examId)` | **None** |
| Identify Bloom’s level | `POST /api/v1/exams/{id}/detect-bloom-levels` — **LLMClient** for Bloom detection; `add_questions` uses `_batch_bloom_detect_llm` and `_map_question_to_co_llm` | `apiClient.detectBloomLevels(examId)`, `addQuestions` with CO mapping | **None** |
| Map each question to CO | `question_co_mapping_table` populated by service; `POST .../questions/{id}/map-co` for manual override | Question analyser shows CO suggestions; add/edit questions with `co_mapped` | **None** |

**Backend:** `QuestionAnalysisService` (LLM + DB).  
**Frontend:** `app/(app)/faculty/course/[id]/question-analyser/page.tsx` — **apiClient only**.

---

## 4. Student Marks Input

| Requirement | Backend | Frontend | Mocks / Hardcoded |
|-------------|---------|----------|-------------------|
| Enter/upload marks per question per exam | `POST /api/v1/exams/{id}/marks` (BulkMarksRequest), `POST .../upload-marks` (CSV/Excel) — `QuestionAnalysisService.process_marks_json` / `process_marks_file` → **StudentMarks** in DB | `faculty/course/[id]/marks/[examCode]` — `apiClient.getQuestions`, `getMarks`, `submitMarks`, `submitMarksForApproval`, `uploadMarksFile` | **None** |

**Backend:** `app/modules/question_analysis/services/question_analysis_service.py`, routes.  
**Frontend:** `app/(app)/faculty/course/[id]/marks/[examCode]/page.tsx` — **apiClient only**.

---

## 5. CO Attainment Calculation

| Requirement | Backend | Frontend | Mocks / Hardcoded |
|-------------|---------|----------|-------------------|
| Aggregate marks by CO; thresholds | `AttainmentService.calculate_course_outcome_attainments()` — threshold_pct × max_marks per CO; levels from **settings** (attainment_level_3/2_threshold) | `faculty/course/[id]/co-attainment` — `apiClient.getCourseAttainment`, `getWeightedCOAttainment`, `getStudentPerformance` | **None** |
| CO attainment % and level (L1/L2/L3) | DB-driven; Level 3/2/1 from configurable thresholds (default 70%/60%) | Page shows summary, weighted attainment, student performance from API | **None** |

**Backend:** `app/modules/attainment_engine/services/attainment_service.py`, `GET /attainment/course/{id}`, `GET /attainment/weighted/{id}`, `POST /attainment/calculate-co`.  
**Frontend:** `app/(app)/faculty/course/[id]/co-attainment/page.tsx` — **apiClient only**.

---

## 6. PO and PSO Attainment Computation

| Requirement | Backend | Frontend | Mocks / Hardcoded |
|-------------|---------|----------|-------------------|
| CO→PO/PSO mapping | `POST /api/v1/map-co-po`, `map-co-pso` — **SemanticMappingService** (embeddings/similarity); mappings in DB | `faculty/course/[id]/po-pso-attainment` — `apiClient.mapCOToPO`, `mapCOToPSO` | **None** |
| PO/PSO attainment | `POST /api/v1/attainment/calculate-po`, `calculate-pso` — formula using CO attainment × mapping level from DB | `apiClient.calculatePOAttainment`, `calculatePSOAttainment` | **None** |

**Backend:** `AttainmentService`, `SemanticMappingService`, routes.  
**Frontend:** `app/(app)/faculty/course/[id]/po-pso-attainment/page.tsx` — **apiClient only**.

---

## 7. Visualization and Reporting

| Requirement | Backend | Frontend | Mocks / Hardcoded |
|-------------|---------|----------|-------------------|
| CO/PO attainment graphs, student analytics | `GET /api/v1/visualization/{course_id}` — `AttainmentService.get_visualization_data()` from DB | `faculty/course/[id]/reports` — `apiClient.getVisualizationData`, `generateReport`, `downloadReport` | **None** |
| Export PDF / Excel / NBA | `GET /api/v1/reports/{course_id}/download?format=pdf|excel|nba` — **AttainmentService** + **report_export_service** (generate_pdf_report, generate_excel_report, generate_nba_excel_report) from real course_data | Same page: Export PDF, Excel, NBA buttons → apiClient.downloadReport(courseId, format) | **None** |

**Backend:** `app/api/v1/routes.py` (download_report), `app/services/report_export_service.py`, `app/modules/attainment_engine/services/attainment_service.py`.  
**Frontend:** `app/(app)/faculty/course/[id]/reports/page.tsx` — **apiClient only**.

**Celery async report tasks:** PDF/Excel tasks use **real** AttainmentService + report_export_service; download URL is placeholder until MinIO is configured. **NBA Celery task** now uses **real** `CourseLeadService.export_po_attainment_nba(dept_id, ay_id)` (no mock PO data).

---

## OBE Chatbot (Conversational)

| Requirement | Backend | Frontend | Mocks / Hardcoded |
|-------------|---------|----------|-------------------|
| Chat for CO generation, mapping, attainment, reports | `POST /api/v1/chatbot/message` — **ChatbotService** → **LangGraph** `run_obe_workflow` (Rasa NLU + keyword fallback); nodes call CoGenerationService, attainment, etc. | `faculty/course/[id]/chatbot` — `apiClient.sendChatMessage`, `getChatbotState`, `updateChatbotState`, `resetChatbotSession` | **None** |
| Step state (course_info → syllabus → generate → review → save) | State in Redis (`chatbot_state:{user_id}:{course_id}`); workflow in `app/agents/langgraph_workflow.py` | Step dropdown + state display; all via API | **None** |

**Backend:** `app/services/chatbot_service.py`, `app/agents/langgraph_workflow.py`, `app/services/rasa_nlu_client.py` (intent + keyword fallback).  
**Frontend:** `app/(app)/faculty/course/[id]/chatbot/page.tsx` — **apiClient only**.

---

## Summary

- **Faculty flow** under `(app)/faculty/course/[id]/` uses **only apiClient**; no `useDataStore` or mock data.
- **Backend** uses **real** services: LLMClient (CO generation, Bloom, question–CO mapping), AttainmentService (DB-based attainment), CoGenerationService, QuestionAnalysisService, CourseLeadService, report_export_service. No mock services or hardcoded outcome data in these paths.
- **Celery:** Report **content** is real (AttainmentService / CourseLeadService); NBA export task now uses real `export_po_attainment_nba`. Download URLs for async jobs are placeholders until object storage is configured.
- **Algorithms:** Threshold-based CO attainment, weighted CO, PO/PSO formulas, and level thresholds (L1/L2/L3) are configurable via settings and applied dynamically per course/exam/program.

---

## Global Chatbot (Real-Time, All Pages, No Mocks)

| Item | Implementation | Mocks |
|------|-----------------|-------|
| **Chatbot icon on every page** | Floating orb (MessageSquare icon) in `(app)/layout.tsx` via `<AIOrb />`; visible on all app routes. Faculty nav includes "Chat" (MessageSquare) that opens the same panel via `openChat()`. | **None** |
| **Real-time chat** | `AIOrb` uses `apiClient.sendChatMessage({ message, course_id })`. When on `/faculty/course/[id]/...`, `course_id` is sent for course-specific actions; otherwise general OBE help. Replies come from backend only. | **None** |
| **Conversations** | All messages are from backend: `POST /api/v1/chatbot/message` → `ChatbotService` → LangGraph workflow. No hardcoded or mock conversation bubbles. Welcome line is a single static hint; all user/assistant turns after that are live API. | **None** |

**LLM integration (backend):** All conversational and generative paths use real LLM services:
- **Chatbot:** `general_llm_node` uses `LLMClient().generate_completion(context)` (Gemini or Ollama). Intent routing uses Rasa NLU or keyword fallback; worker nodes call real services (CoGenerationService, AttainmentService, etc.) or return structured prompts.
- **CO generation:** `CoGenerationService` uses `LLMClient().generate_completion(prompt)`.
- **Question Bloom / CO mapping:** `QuestionAnalysisService` uses `LLMClient()` for `_batch_bloom_detect_llm` and `_map_question_to_co_llm`.
- **LangGraph nodes:** `detect_bloom_node`, `generate_co_node` (via CoGenerationService), `general_llm_node` all use `LLMClient`; no mock reply strings for conversations.

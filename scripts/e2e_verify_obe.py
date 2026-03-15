import json
import uuid

import requests

base = "http://127.0.0.1:8011/api/v1"
results = []


def add(check: str, status: str, detail: str) -> None:
    results.append({"check": check, "status": status, "detail": str(detail)[:240]})


def safe(check: str, fn):
    try:
        add(check, "PASS", fn())
    except Exception as exc:
        add(check, "FAIL", exc)


def req(method: str, url: str, **kwargs):
    resp = requests.request(method, url, timeout=120, **kwargs)
    if resp.status_code >= 400:
        raise RuntimeError(f"{resp.status_code}: {resp.text[:180]}")
    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        return resp.json()
    return resp


tag = uuid.uuid4().hex[:8]
admin_user = f"adm_{tag}"
faculty_user = f"fac_{tag}"
program_id = f"PRG-{tag[:6]}"
admin_token = None
faculty_token = None
course_id = None
exam_id = None


def register_admin() -> str:
    global admin_token
    data = {
        "username": admin_user,
        "email": f"{admin_user}@example.com",
        "password": "Pass@1234",
        "full_name": "Admin",
        "role": "admin",
    }
    resp = req("POST", f"{base}/auth/register", json=data)
    admin_token = resp.get("access_token")
    return resp.get("role", "")


def register_faculty() -> str:
    global faculty_token
    data = {
        "username": faculty_user,
        "email": f"{faculty_user}@example.com",
        "password": "Pass@1234",
        "full_name": "Faculty",
        "role": "faculty",
    }
    resp = req("POST", f"{base}/auth/register", json=data)
    faculty_token = resp.get("access_token")
    return resp.get("role", "")


safe("auth_register_admin", register_admin)
safe("auth_register_faculty", register_faculty)

if not faculty_token:
    print(json.dumps({"base": base, "pass": 0, "fail": 1, "results": results}, ensure_ascii=True))
    raise SystemExit(0)

headers_faculty = {"Authorization": f"Bearer {faculty_token}"}
headers_admin = {"Authorization": f"Bearer {admin_token}"} if admin_token else headers_faculty


safe(
    "seed_program_po",
    lambda: (
        req("POST", f"{base}/programs/{program_id}/outcomes", headers=headers_admin, json={"code": "PO1", "statement": "Apply computing fundamentals"}),
        req("POST", f"{base}/programs/{program_id}/outcomes", headers=headers_admin, json={"code": "PO2", "statement": "Analyze algorithms"}),
        len(req("GET", f"{base}/programs/{program_id}/outcomes", headers=headers_faculty)),
    )[-1],
)

safe(
    "seed_program_pso",
    lambda: (
        req("POST", f"{base}/programs/{program_id}/pso", headers=headers_admin, json={"code": "PSO1", "statement": "Build AI analytics workflows"}),
        len(req("GET", f"{base}/programs/{program_id}/pso", headers=headers_faculty)),
    )[-1],
)


def create_course() -> str:
    global course_id
    payload = {
        "course_code": f"CS{uuid.uuid4().int % 9000 + 1000}",
        "course_name": "OBE Verification Course",
        "credits": 3,
        "semester": 5,
        "description": "real-service verification",
        "program_id": program_id,
    }
    c = req("POST", f"{base}/courses", headers=headers_faculty, json=payload)
    course_id = c.get("id")
    return str(course_id)


safe("create_course", create_course)

if course_id:

    def fn1() -> str:
        pos = req("GET", f"{base}/programs/{program_id}/outcomes", headers=headers_faculty)
        psos = req("GET", f"{base}/programs/{program_id}/pso", headers=headers_faculty)
        payload = {
            "syllabus": "Unit1 DS Unit2 Algorithms Unit3 Graphs Unit4 Optimization",
            "program_outcomes": pos,
            "program_specific_outcomes": psos,
            "num_cos": 4,
        }
        g = req("POST", f"{base}/courses/{course_id}/generate-co", headers=headers_faculty, json=payload)
        generated = g.get("course_outcomes", g.get("generated_cos", []))
        return f"generated={len(generated)}"

    safe("fn1_co_generation", fn1)

    def fn2() -> str:
        global exam_id
        payload = {
            "assessment_code": "T1",
            "exam_name": "T1 Internal",
            "exam_type": "mid_term",
            "total_marks": 30,
            "duration_minutes": 60,
            "weightage_pct": 10,
            "units_covered": ["U1", "U2"],
            "number_of_questions": 3,
        }
        e = req("POST", f"{base}/courses/{course_id}/exams", headers=headers_faculty, json=payload)
        exam_id = e.get("id")
        return str(exam_id)

    safe("fn2_exam_configuration", fn2)

if course_id and exam_id:

    def fn3() -> str:
        cos = req("GET", f"{base}/courses/{course_id}/outcomes", headers=headers_faculty)
        co_code = cos[0].get("code") if cos else "CO1"
        payload = {
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Explain merge sort complexity",
                    "marks": 10,
                    "question_type": "long_answer",
                    "co_mapped": [co_code],
                    "override_reason": "manual",
                },
                {
                    "question_number": 2,
                    "question_text": "Apply BFS on graph",
                    "marks": 10,
                    "question_type": "long_answer",
                    "co_mapped": [co_code],
                    "override_reason": "manual",
                },
                {
                    "question_number": 3,
                    "question_text": "Design stack evaluator",
                    "marks": 10,
                    "question_type": "long_answer",
                    "co_mapped": [co_code],
                    "override_reason": "manual",
                },
            ]
        }
        added = req("POST", f"{base}/exams/{exam_id}/questions", headers=headers_faculty, json=payload)
        return f"questions_added={added.get('questions_added')}"

    safe("fn3_question_co_mapping", fn3)

    def fn4() -> str:
        payload = {
            "rows": [
                {"student_id": "S001", "marks": {"1": 8, "2": 7, "3": 9}},
                {"student_id": "S002", "marks": {"1": 6, "2": 7, "3": 8}},
                {"student_id": "S003", "marks": {"1": 9, "2": 8, "3": 10}},
            ]
        }
        out = req("POST", f"{base}/exams/{exam_id}/marks", headers=headers_faculty, json=payload)
        return f"rows_processed={out.get('rows_processed')}"

    safe("fn4_student_marks_input", fn4)

    def fn5() -> str:
        out = req("POST", f"{base}/attainment/calculate-co?course_id={course_id}&exam_id={exam_id}&threshold_pct=0.6", headers=headers_faculty)
        return f"co_rows={len(out.get('attainments', []))}"

    safe("fn5_co_attainment", fn5)
else:
    add("fn3_question_co_mapping", "FAIL", "exam/course unavailable")
    add("fn4_student_marks_input", "FAIL", "exam/course unavailable")
    add("fn5_co_attainment", "FAIL", "exam/course unavailable")

if course_id:

    def fn6() -> str:
        m1 = req("POST", f"{base}/map-co-po?course_id={course_id}&program_id={program_id}&threshold=0.25", headers=headers_faculty)
        m2 = req("POST", f"{base}/map-co-pso?course_id={course_id}&program_id={program_id}&threshold=0.25", headers=headers_faculty)
        po = req("POST", f"{base}/attainment/calculate-po?course_id={course_id}&program_id={program_id}", headers=headers_faculty)
        pso = req("POST", f"{base}/attainment/calculate-pso?course_id={course_id}&program_id={program_id}", headers=headers_faculty)
        return (
            f"map_po={m1.get('mappings_created')},map_pso={m2.get('mappings_created')},"
            f"po_rows={len(po.get('attainments', []))},pso_rows={len(pso.get('attainments', []))}"
        )

    safe("fn6_po_pso_attainment", fn6)

    def fn7() -> str:
        req("GET", f"{base}/visualization/{course_id}", headers=headers_faculty)
        pdf = req("GET", f"{base}/reports/{course_id}/download?format=pdf", headers=headers_faculty)
        excel = req("GET", f"{base}/reports/{course_id}/download?format=excel", headers=headers_faculty)
        return f"pdf={pdf.status_code},excel={excel.status_code}"

    safe("fn7_visualization_reporting", fn7)

    def cb1() -> str:
        out = req(
            "POST",
            f"{base}/chatbot/message",
            headers=headers_faculty,
            json={"message": f"map co to po program_id={program_id}", "course_id": course_id},
        )
        return f"intent={out.get('intent')},nlu={out.get('nlu_source')}"

    safe("chatbot_mapping_intent", cb1)

    def cb2() -> str:
        out = req(
            "POST",
            f"{base}/chatbot/message",
            headers=headers_faculty,
            json={"message": f"calculate attainment exam_id={exam_id}", "course_id": course_id},
        )
        return f"intent={out.get('intent')},nlu={out.get('nlu_source')}"

    safe("chatbot_attainment_intent", cb2)

summary = {
    "base": base,
    "program_id": program_id,
    "course_id": course_id,
    "exam_id": exam_id,
    "pass": sum(1 for x in results if x["status"] == "PASS"),
    "fail": sum(1 for x in results if x["status"] == "FAIL"),
    "results": results,
}
print(json.dumps(summary, ensure_ascii=True))

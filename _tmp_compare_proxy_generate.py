import json
import time
import requests

BACKEND = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:3000"
EMAIL = "231fa04a02@gmail.com"
PASSWORD = "Kranthi@123"


def get_token():
    r = requests.post(f"{BACKEND}/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def get_courses(headers):
    r = requests.get(f"{BACKEND}/api/v1/courses", headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def call_generate(base, course_id, headers, syllabus):
    payload = {
        "syllabus": syllabus,
        "num_cos": 5,
        "program_outcomes": [
            {"code": f"PO{i}", "statement": "NBA standard outcome"}
            for i in range(1, 13)
        ],
        "program_specific_outcomes": [
            {"code": "PSO1", "statement": "Department specific outcome"},
            {"code": "PSO2", "statement": "Department specific outcome"},
        ],
    }
    r = requests.post(
        f"{base}/api/v1/courses/{course_id}/generate-co",
        headers=headers,
        json=payload,
        timeout=220,
    )
    body = ""
    try:
        body = json.dumps(r.json())[:240]
    except Exception:
        body = (r.text or "")[:240]
    return r.status_code, body


if __name__ == "__main__":
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    courses = get_courses(headers)
    if not courses:
        raise SystemExit("No courses found")
    course_id = courses[0]["id"]
    print("course_id", course_id)

    for i in range(1, 6):
        syllabus = f"Data Structures and Algorithms iteration {i}. Topics: stacks queues trees graphs sorting searching."
        b_status, b_body = call_generate(BACKEND, course_id, headers, syllabus)
        print(f"[{i}] backend  status={b_status} body={b_body}")
        p_status, p_body = call_generate(FRONTEND, course_id, headers, syllabus)
        print(f"[{i}] proxy    status={p_status} body={p_body}")
        time.sleep(1)

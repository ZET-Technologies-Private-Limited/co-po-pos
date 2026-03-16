import json
import httpx

BASE = "http://127.0.0.1:8000/api/v1"
EMAIL = "231fa04a02@gmail.com"
PASSWORD = "Kranthi@123"
COURSE_ID = "97ce650d-bbcd-4b72-a2f6-5f366d255938"


def main() -> None:
    with httpx.Client(timeout=120.0) as client:
        login_payload = {
            "email": EMAIL,
            "password": PASSWORD,
            "department": "CSE",
            "academic_year": "2025-26",
        }
        login = client.post(f"{BASE}/auth/login", json=login_payload)
        print("LOGIN", login.status_code)
        print(login.text)
        login.raise_for_status()

        token = login.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        course = client.get(f"{BASE}/courses/{COURSE_ID}", headers=headers)
        print("COURSE", course.status_code)
        print(course.text[:400])
        course.raise_for_status()

        syllabus = course.json().get("syllabus") or (
            "Unit 1: Arrays and linked lists. "
            "Unit 2: Stacks and queues. "
            "Unit 3: Trees and BST. "
            "Unit 4: Graphs BFS DFS. "
            "Unit 5: Hashing and sorting."
        )

        nba_pos = [{"code": f"PO{i}", "statement": ""} for i in range(1, 13)]
        payload = {
            "syllabus": syllabus,
            "num_cos": 5,
            "program_outcomes": nba_pos,
            "program_specific_outcomes": [],
        }

        print("GENERATE_PAYLOAD")
        print(json.dumps(payload)[:500])

        resp = client.post(f"{BASE}/courses/{COURSE_ID}/generate-co", json=payload, headers=headers)
        print("GENERATE", resp.status_code)
        print(resp.text)


if __name__ == "__main__":
    main()

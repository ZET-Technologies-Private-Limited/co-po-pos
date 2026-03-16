import json
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

SYLLABUS_TEXT = """UNIT 1: Linear Data Structures (10 hours)
- Arrays: declaration, initialization, operations (insert, delete, search)
- Linked Lists: singly, doubly, circular linked lists
- Stacks: push, pop, applications (expression evaluation, recursion)
- Queues: simple queue, circular queue, priority queue, deque

UNIT 2: Non-Linear Data Structures (10 hours)
- Trees: binary tree, binary search tree, AVL tree, B-tree
- Heaps: min heap, max heap, heap sort
- Graphs: representation (adjacency matrix, adjacency list)
- Graph traversal: BFS, DFS

UNIT 3: Sorting Algorithms (8 hours)
- Bubble sort, Selection sort, Insertion sort
- Quick sort, Merge sort, Heap sort
- Comparison of sorting algorithms

UNIT 4: Searching and Hashing (6 hours)
- Linear search, Binary search
- Hashing techniques: hash functions, collision resolution
- Open addressing, chaining

UNIT 5: Algorithm Design Techniques (8 hours)
- Divide and conquer strategy
- Dynamic programming: knapsack, LCS, matrix chain multiplication
- Greedy algorithms: Kruskal, Prim, Dijkstra
- Time and Space Complexity: Big-O, Omega, Theta notation"""

LOGIN_CANDIDATES = [
    {
        "email": "dr.smith@university.edu",
        "password": "faculty123456",
        "department": "CSE",
        "academic_year": "2025-26",
    },
    {
        "email": "sadwik1409@gmail.com",
        "password": "Test1234!",
        "department": "CSE",
        "academic_year": "2025-26",
    },
]


def login(client: httpx.Client):
    for creds in LOGIN_CANDIDATES:
        r = client.post(f"{BASE_URL}/auth/login", json=creds, timeout=20.0)
        if r.status_code == 200 and r.json().get("access_token"):
            return creds["email"], r.json()["access_token"]
    return None, None


def main():
    with httpx.Client() as client:
        user_email, token = login(client)
        if not token:
            print("LOGIN_FAILED")
            return

        headers = {"Authorization": f"Bearer {token}"}

        r_courses = client.get(f"{BASE_URL}/courses", headers=headers, timeout=20.0)
        if r_courses.status_code != 200:
            print(f"COURSE_FETCH_FAILED {r_courses.status_code} {r_courses.text}")
            return

        courses = r_courses.json() or []
        if not courses:
            print("NO_COURSES_FOUND")
            return

        course_id = courses[0]["id"]
        course_code = courses[0].get("course_code")

        client.post(f"{BASE_URL}/courses/{course_id}/co-unlock", headers=headers, timeout=20.0)

        payload = {
            "syllabus": SYLLABUS_TEXT,
            "program_outcomes": [],
            "program_specific_outcomes": [],
            "num_cos": 5,
        }

        r_gen = client.post(
            f"{BASE_URL}/courses/{course_id}/generate-co",
            headers=headers,
            json=payload,
            timeout=90.0,
        )

        print(f"LOGIN_USER={user_email}")
        print(f"COURSE={course_code} {course_id}")
        print(f"STATUS={r_gen.status_code}")

        try:
            data = r_gen.json()
        except Exception:
            print(r_gen.text)
            return

        cos = data.get("course_outcomes") or data.get("generated_outcomes") or []
        print(f"CO_COUNT={len(cos)}")
        for idx, co in enumerate(cos, start=1):
            code = co.get("code", f"CO{idx}")
            bloom = co.get("bloom_level", "")
            statement = (co.get("statement") or "").strip()
            print(f"{code} | {bloom} | {statement}")

        print("RAW_JSON_START")
        print(json.dumps(data, indent=2))
        print("RAW_JSON_END")


if __name__ == "__main__":
    main()

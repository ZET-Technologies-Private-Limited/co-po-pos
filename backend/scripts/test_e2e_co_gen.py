import httpx
import json

base_url = "http://localhost:8000/api/v1"

def test_co_generation():
    with httpx.Client() as client:
        # 1. Login
        print("Logging in as faculty...")
        login_data = {
            "email": "dr_smith@university.edu",
            "password": "faculty123456",
            "department": "CSE",
            "academic_year": "2025-26"
        }
        res = client.post(f"{base_url}/auth/login", json=login_data)
        if res.status_code != 200:
            print("Login failed:", res.status_code, res.text)
            return
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Check existing courses or create a new one
        print("Fetching courses...")
        res = client.get(f"{base_url}/courses", headers=headers)
        if res.status_code != 200:
            print("Failed to fetch courses:", res.text)
            return
            
        courses = res.json()
        
        course_id = None
        if not courses:
            print("No courses found. Creating a test course...")
            course_data = {
                "course_code": "CS101",
                "course_name": "Data Structures",
                "credits": 3,
                "semester": 1,
                "description": "Intro to Data Structures",
                "department": "CSE"
            }
            res = client.post(f"{base_url}/courses", json=course_data, headers=headers)
            if res.status_code != 200:
                print("Failed to create course:", res.status_code, res.text)
                return
            course_id = res.json()["id"]
        else:
            course_id = courses[0]["id"]
            print(f"Using existing course {courses[0]['course_code']}")
            
            # Unlock COs just in case
            un = client.post(f"{base_url}/courses/{course_id}/co-unlock", headers=headers)
            print("Unlock status:", un.text)
        
        # 3. Test CO Generation
        print("Generating COs from syllabus...")
        generation_payload = {
            "syllabus": "Unit 1: Introduction to Data Structures. Arrays, Linked Lists, Stacks, Queues. Unit 2: Trees. Binary Trees, BST, AVL Trees. Unit 3: Graphs. BFS, DFS, Shortest Paths.",
            "program_outcomes": [
                {"code": "PO1", "statement": "Engineering knowledge"},
                {"code": "PO2", "statement": "Problem analysis"},
                {"code": "PO3", "statement": "Design/development of solutions"}
            ],
            "program_specific_outcomes": [
                {"code": "PSO1", "statement": "Understand software practices"}
            ],
            "num_cos": 4
        }
        res = client.post(f"{base_url}/courses/{course_id}/generate-co", json=generation_payload, headers=headers, timeout=60.0)
        
        if res.status_code == 200:
            print("CO Generation SUCCESS!")
            print(json.dumps(res.json(), indent=2))
        else:
            print("CO Generation FAILED:", res.status_code, res.text)

if __name__ == "__main__":
    test_co_generation()

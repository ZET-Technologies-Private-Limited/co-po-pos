import httpx
import json

base_url = "http://localhost:8000/api/v1"

def test_exam_config_and_mapping():
    with httpx.Client() as client:
        # 1. Login
        print("Logging in as faculty...")
        login_data = {
            "email": "dr.smith@university.edu",
            "password": "faculty123456",
            "department": "Computer Science",
            "academic_year": "2024-25"
        }
        res = client.post(f"{base_url}/auth/login", json=login_data)
        if res.status_code != 200:
            print("Login failed:", res.status_code, res.text)
            return
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get the test course we created
        res = client.get(f"{base_url}/courses", headers=headers)
        if res.status_code != 200 or not res.json():
            print("Failed to fetch courses. Did you run the CO Generation test first?", res.text)
            return
        course_id = res.json()[0]["id"]
        
        # Get COs for this course
        res = client.get(f"{base_url}/courses/{course_id}/outcomes", headers=headers)
        cos = res.json()
        if not cos:
            print("No COs found. Generate COs first.")
            return
            
        print(f"Found {len(cos)} Course Outcomes.")
        
        # 3. Create Exam (Requirement 2)
        print("\n--- Requirement 2: Examination Configuration ---")
        exam_data = {
            "exam_name": "Midterm 1 (T1)",
            "exam_type": "internal",
            "total_marks": 30,
            "duration_minutes": 90,
            "assessment_code": "T1",
            "weightage_pct": 20,
            "number_of_questions": 3
        }
        res = client.post(f"{base_url}/courses/{course_id}/exams", json=exam_data, headers=headers)
        if res.status_code != 200:
            print("Failed to create Exam:", res.status_code, res.text)
            return
            
        exam_id = res.json()["id"]
        print("Successfully created Exam:", json.dumps(res.json(), indent=2))
        
        # 4. Add Questions and Map them (Requirement 3)
        print("\n--- Requirement 3: Question-CO Mapping ---")
        questions_payload = {
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Explain the difference between Arrays and Linked Lists.",
                    "marks": 10,
                    "question_type": "descriptive",
                    "bloom_level": "understand",
                    "mapped_cos": [{"co_id": cos[0]["id"], "co_code": cos[0]["code"]}] # Map to first CO
                },
                {
                    "question_number": 2,
                    "question_text": "Write an algorithm for Binary Search Tree insertion.",
                    "marks": 10,
                    "question_type": "descriptive",
                    "bloom_level": "apply",
                    "mapped_cos": [{"co_id": cos[1]["id"], "co_code": cos[1]["code"]}] # Map to second CO
                },
                {
                    "question_number": 3,
                    "question_text": "Analyze the time complexity of BFS vs DFS.",
                    "marks": 10,
                    "question_type": "descriptive",
                    "bloom_level": "analyze",
                    "mapped_cos": [{"co_id":  cos[2]["id"] if len(cos) > 2 else cos[0]["id"], "co_code": cos[2]["code"] if len(cos) > 2 else cos[0]["code"]}]
                }
            ]
        }
        res = client.post(f"{base_url}/exams/{exam_id}/questions", json=questions_payload, headers=headers)
        if res.status_code == 200:
            print("Successfully added Questions mapped to COs with Bloom's Taxonomy levels!")
            print(json.dumps(res.json(), indent=2))
        else:
            print("Failed to add questions:", res.status_code, res.text)

if __name__ == "__main__":
    test_exam_config_and_mapping()

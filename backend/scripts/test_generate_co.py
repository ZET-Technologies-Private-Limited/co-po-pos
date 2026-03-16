import httpx
import json

base_url = "http://localhost:8000/api/v1"

def test_generate_co():
    try:
        # 1. Login
        login_data = {
            "email": "sadwik1409@gmail.com",
            "password": "Test1234!",
            "department": "CSE",
            "academic_year": "2025-26"
        }
        r = httpx.post(f"{base_url}/auth/login", json=login_data)
        if r.status_code != 200:
            print(f"Login failed: {r.status_code} {r.text}")
            return
        
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get a course ID (let's try to find one first)
        r = httpx.get(f"{base_url}/courses", headers=headers)
        if r.status_code != 200 or not r.json():
            print(f"Failed to get courses or no courses found: {r.status_code}")
            return
        
        course_id = r.json()[0]["id"]
        print(f"Testing with course ID: {course_id}")
        
        # 3. Call generate-co
        payload = {
            "syllabus": "Unit 1: Introduction to Data Structures. Unit 2: Linked Lists. Unit 3: Stacks and Queues.",
            "program_outcomes": [{"code": "PO1", "statement": "Engineering Knowledge"}],
            "program_specific_outcomes": [],
            "num_cos": 5
        }
        
        print("Calling generate-co...")
        r = httpx.post(f"{base_url}/courses/{course_id}/generate-co", json=payload, headers=headers, timeout=40.0)
        print(f"Status Code: {r.status_code}")
        print(f"Response: {r.text}")
        
    except Exception as e:
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":
    test_generate_co()

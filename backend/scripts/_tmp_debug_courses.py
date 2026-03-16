import json
import time
import uuid
import httpx

BASE = "http://127.0.0.1:8000/api/v1"

email = f"debug_{uuid.uuid4().hex[:8]}@example.com"
pwd = "Debug@123456"

reg_payload = {
    "username": f"debug_{uuid.uuid4().hex[:8]}",
    "email": email,
    "password": pwd,
    "full_name": "Debug User",
    "role": "faculty",
    "department": "CSE",
}

print("register payload:", reg_payload)
reg = httpx.post(f"{BASE}/auth/register", json=reg_payload, timeout=20)
print("register status:", reg.status_code)
print("register body:", reg.text)

if reg.status_code not in (200, 201):
    raise SystemExit(1)

token = reg.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

courses = httpx.get(f"{BASE}/courses", headers=headers, timeout=20)
print("courses status:", courses.status_code)
print("courses body:", courses.text[:2000])

# Also probe with semester filter to ensure same route path behavior
courses_sem = httpx.get(f"{BASE}/courses?semester=1", headers=headers, timeout=20)
print("courses sem status:", courses_sem.status_code)
print("courses sem body:", courses_sem.text[:2000])

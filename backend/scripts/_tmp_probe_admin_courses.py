import httpx

BASE = "http://127.0.0.1:8000/api/v1"

login_payload = {
    "email": "admin@university.edu",
    "password": "Admin@123456",
    "department": "ADMIN",
    "academic_year": "2025-26"
}

r = httpx.post(f"{BASE}/auth/login", json=login_payload, timeout=20)
print("login", r.status_code, r.text[:500])
if r.status_code != 200:
    raise SystemExit(1)

token = r.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

c = httpx.get(f"{BASE}/courses", headers=headers, timeout=20)
print("courses", c.status_code)
print(c.text[:4000])

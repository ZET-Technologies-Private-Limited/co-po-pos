import uuid
import httpx

BASE = "http://127.0.0.1:8000/api/v1"

email = f"admindebug_{uuid.uuid4().hex[:8]}@example.com"
password = "Debug@123456"
username = f"admindebug_{uuid.uuid4().hex[:8]}"

reg_payload = {
    "username": username,
    "email": email,
    "password": password,
    "full_name": "Admin Debug",
    "role": "admin",
    "department": "CSE",
}
reg = httpx.post(f"{BASE}/auth/register", json=reg_payload, timeout=20)
print("register", reg.status_code, reg.text[:500])
if reg.status_code != 200:
    raise SystemExit(1)

token = reg.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

c = httpx.get(f"{BASE}/courses", headers=headers, timeout=20)
print("courses", c.status_code)
print(c.text[:4000])

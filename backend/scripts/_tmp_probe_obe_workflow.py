import uuid
import httpx

BASE = "http://127.0.0.1:8000/api/v1"

email = f"obetest_{uuid.uuid4().hex[:8]}@example.com"
password = "Debug@123456"
username = f"obetest_{uuid.uuid4().hex[:8]}"

reg = httpx.post(
    f"{BASE}/auth/register",
    json={
        "username": username,
        "email": email,
        "password": password,
        "full_name": "OBE Probe",
        "role": "admin",
        "department": "CSE",
    },
    timeout=20,
)
print("register", reg.status_code)
print(reg.text[:300])
if reg.status_code != 200:
    raise SystemExit(1)

token = reg.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

courses = httpx.get(f"{BASE}/courses", headers=headers, timeout=20)
print("courses", courses.status_code)
if courses.status_code != 200:
    print(courses.text[:500])
    raise SystemExit(1)

rows = courses.json()
print("course_count", len(rows))
if not rows:
    raise SystemExit(0)

for c in rows[:3]:
    cid = c.get("id")
    code = c.get("course_code")
    wf = httpx.get(f"{BASE}/courses/{cid}/obe-workflow", headers=headers, timeout=30)
    sp = httpx.get(f"{BASE}/attainment/students/{cid}", headers=headers, timeout=30)
    print("---")
    print("course", code, cid)
    print("workflow", wf.status_code)
    if wf.status_code == 200:
        data = wf.json()
        co = data.get("co_attainments") or []
        finals = [float(r.get("final_att", 0) or 0) for r in co]
        directs = [float(r.get("direct_att", 0) or 0) for r in co]
        print("workflow co count", len(co), "nonzero final", sum(1 for v in finals if v > 0), "nonzero direct", sum(1 for v in directs if v > 0))
    else:
        print(wf.text[:500])

    print("students", sp.status_code)
    if sp.status_code == 200:
        st = sp.json().get("students") if isinstance(sp.json(), dict) else sp.json()
        st = st if isinstance(st, list) else []
        print("student count", len(st))
        if st:
            cb = st[0].get("co_breakdown") or {}
            print("sample co breakdown", {k: (v.get('percent') if isinstance(v, dict) else v) for k, v in list(cb.items())[:5]})
    else:
        print(sp.text[:500])

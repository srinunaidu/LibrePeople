"""Interview scheduling CRUD (recruiting lane gap).

What this suite proves
----------------------
* an admin creates an interview for a candidate (optionally tied to a
  requisition) with stage, time and interviewers; the interview is born
  ``Scheduled`` and the interviewers round-trip as a list;
* creating for an unknown candidate or requisition is 404;
* the list filters by candidate, requisition and status;
* an unknown id is 404;
* the status flow holds: Scheduled -> Completed with feedback works, a
  decided interview cannot be reopened (400), its feedback may still
  change, and an unknown status is refused (400);
* the recruiting role gate holds: a non-admin is refused with 403 and an
  anonymous caller with 401.

Run:  python interview_test_suite.py
"""
import datetime
import os
import tempfile

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="interview_test_suite_"), "interview_test_suite.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"  # keep the suite's output readable
os.environ["FIELD_ENCRYPTION_KEYS"] = "lp-test-key:local-test-field-encryption-secret-0123456789"
os.environ["FIELD_ENCRYPTION_ACTIVE_KEY_ID"] = "lp-test-key"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.recruiting import Candidate, JobRequisition  # noqa: E402
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

RESULTS = {"pass": 0, "fail": 0}
FAILURES: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        RESULTS["pass"] += 1
        print(f"  PASS  {name}")
    else:
        RESULTS["fail"] += 1
        FAILURES.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


# --- the fixtures ------------------------------------------------------------

PASSWORD = "InterviewPass123"

db = SessionLocal()
dept = Department(name="Hiring", code="HIR")
db.add(dept)
db.commit()
db.refresh(dept)
job = Job(title="Hiring Analyst", code="HIRING", department_id=dept.id)
db.add(job)
db.commit()
db.refresh(job)

req = JobRequisition(req_number="REQ-IVT-1", title="Backend Engineer", department_id=dept.id, status="Open")
db.add(req)
db.commit()
db.refresh(req)

cand = Candidate(first_name="Ivy", last_name="Candidate", email="ivy.candidate@example.com")
db.add(cand)
db.commit()
db.refresh(cand)

db.add(
    User(
        username="ivt_hr",
        email="ivt_hr@example.com",
        hashed_password=get_password_hash(PASSWORD),
        role="SuperAdmin",
        is_active=True,
        mfa_enabled=True,
    )
)
db.add(
    User(
        username="ivt_assoc",
        email="ivt_assoc@example.com",
        hashed_password=get_password_hash(PASSWORD),
        role="Associate",
        is_active=True,
    )
)
db.commit()
REQ_ID = req.id
CAND_ID = cand.id
db.close()

client = TestClient(app, raise_server_exceptions=False)


def _headers(username: str) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


H_HR = _headers("ivt_hr")
H_ASSOC = _headers("ivt_assoc")
URL = "/api/v1/interviews/"

# ===========================================================================
print("\n[IVT-1] Create: schedule, interviewers round-trip, born Scheduled")
# ===========================================================================
r = client.post(
    URL,
    headers=H_HR,
    json={
        "candidate_id": CAND_ID,
        "requisition_id": REQ_ID,
        "stage": "Technical",
        "scheduled_at": "2026-12-02T10:00:00Z",
        "interviewers": ["lead@example.com", "peer@example.com"],
    },
)
check("create answers 201", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
body = r.json() if r.status_code == 201 else {}
IVT_ID = body.get("id")
check("born Scheduled", body.get("status") == "Scheduled", f"{body}")
check("interviewers round-trip as a list", body.get("interviewers") == ["lead@example.com", "peer@example.com"], f"{body}")

r = client.post(URL, headers=H_HR, json={"candidate_id": 999999})
check("unknown candidate is 404", r.status_code == 404, f"{r.status_code} {r.text[:200]}")

r = client.post(URL, headers=H_HR, json={"candidate_id": CAND_ID, "requisition_id": 999999})
check("unknown requisition is 404", r.status_code == 404, f"{r.status_code} {r.text[:200]}")

# ===========================================================================
print("\n[IVT-2] List and read with filters")
# ===========================================================================
r = client.get(URL, headers=H_HR)
check("list returns the interview", r.status_code == 200 and any(i["id"] == IVT_ID for i in r.json()), f"{r.status_code} {r.text[:200]}")

r = client.get(URL, headers=H_HR, params={"candidate_id": CAND_ID})
check("filter by candidate", r.status_code == 200 and len(r.json()) == 1, f"{r.status_code} {r.text[:200]}")

r = client.get(URL, headers=H_HR, params={"candidate_id": 999999})
check("filter by unknown candidate is empty, not an error", r.status_code == 200 and r.json() == [], f"{r.status_code} {r.text[:200]}")

r = client.get(URL, headers=H_HR, params={"requisition_id": REQ_ID, "status": "Scheduled"})
check("filter by requisition + status", r.status_code == 200 and len(r.json()) == 1, f"{r.status_code} {r.text[:200]}")

r = client.get(f"{URL}{IVT_ID}", headers=H_HR)
check("read back the interview", r.status_code == 200 and r.json()["id"] == IVT_ID, f"{r.status_code} {r.text[:200]}")

r = client.get(f"{URL}999999", headers=H_HR)
check("unknown id is 404", r.status_code == 404, f"{r.status_code} {r.text[:200]}")

# ===========================================================================
print("\n[IVT-3] Status flow: decide, terminal, feedback still editable")
# ===========================================================================
r = client.put(f"{URL}{IVT_ID}", headers=H_HR, json={"status": "Completed", "feedback": "Strong hire."})
check("Scheduled -> Completed with feedback works", r.status_code == 200 and r.json()["status"] == "Completed", f"{r.status_code} {r.text[:200]}")

r = client.put(f"{URL}{IVT_ID}", headers=H_HR, json={"status": "Scheduled"})
check("a decided interview cannot be reopened", r.status_code == 400, f"{r.status_code} {r.text[:200]}")

r = client.put(f"{URL}{IVT_ID}", headers=H_HR, json={"feedback": "Strong hire, confirmed."})
check("feedback on a decided interview may still change", r.status_code == 200 and r.json()["feedback"] == "Strong hire, confirmed.", f"{r.status_code} {r.text[:200]}")

r = client.put(f"{URL}{IVT_ID}", headers=H_HR, json={"status": "Rescheduled"})
check("unknown status is refused", r.status_code == 400, f"{r.status_code} {r.text[:200]}")

r = client.put(f"{URL}999999", headers=H_HR, json={"status": "Completed"})
check("updating an unknown id is 404", r.status_code == 404, f"{r.status_code} {r.text[:200]}")

# ===========================================================================
print("\n[IVT-4] Role gate: recruiting lane stays admin-only")
# ===========================================================================
r = client.get(URL, headers=H_ASSOC)
check("non-admin list is refused", r.status_code == 403, f"{r.status_code} {r.text[:200]}")

r = client.post(URL, headers=H_ASSOC, json={"candidate_id": CAND_ID})
check("non-admin create is refused", r.status_code == 403, f"{r.status_code} {r.text[:200]}")

r = client.get(URL)
check("anonymous list is refused", r.status_code in (401, 403), f"{r.status_code} {r.text[:200]}")

# ===========================================================================
print()
print("----------------------------------------------------------------")
print(f"interview tests: {RESULTS['pass']} passed, {RESULTS['fail']} failed")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("----------------------------------------------------------------")
raise SystemExit(1 if RESULTS["fail"] else 0)

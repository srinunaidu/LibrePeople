"""Local smoke test for Phase 2 (Hire & Onboarding) using SQLite."""
import os

os.environ["DATABASE_URL"] = "sqlite:///./smoke_test2.db"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = "*"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["LOCAL_STORAGE_DIR"] = "/tmp/karmathy-storage-test"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.database import Base, engine, SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.job import Job  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
if not db.query(User).filter(User.username == "admin").first():
    db.add(
        User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("secret123"),
            role="SuperAdmin",
            is_active=True,
        )
    )
dept = db.query(Department).filter(Department.code == "OPS").first()
if not dept:
    dept = Department(name="Operations", code="OPS")
    db.add(dept)
    db.commit()
    db.refresh(dept)
job = db.query(Job).filter(Job.code == "ASSOC").first()
if not job:
    job = Job(title="Associate", code="ASSOC", department_id=dept.id)
    db.add(job)
db.commit()
db.refresh(job)
dept_id = dept.id
job_id = job.id
db.close()

client = TestClient(app)

r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secret123"})
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}

# 1. Requisition
r = client.post(
    "/api/v1/requisitions/",
    headers=H,
    json={
        "req_number": "REQ-001",
        "title": "Associate",
        "department_id": dept_id,
        "job_id": job_id,
        "location": "Hyderabad",
        "openings": 2,
        "status": "Open",
    },
)
print("1. create requisition:", r.status_code, r.json().get("req_number"))
req_id = r.json()["id"]

# 2. Candidate
r = client.post(
    "/api/v1/candidates/",
    headers=H,
    json={
        "first_name": "Priya",
        "last_name": "Sharma",
        "email": "priya.sharma@example.com",
        "phone": "+91-9000000000",
        "source": "Referral",
    },
)
print("2. create candidate:", r.status_code, r.json().get("email"))
cand_id = r.json()["id"]

# 3. Application
r = client.post(
    "/api/v1/applications/",
    headers=H,
    json={
        "requisition_id": req_id,
        "candidate_id": cand_id,
        "applied_date": "2026-10-18",
        "status": "Interview",
    },
)
print("3. create application:", r.status_code, r.json().get("id"))
app_id = r.json()["id"]

# 4. Offer
r = client.post(
    "/api/v1/offers/",
    headers=H,
    json={
        "offer_number": "OFF-001",
        "application_id": app_id,
        "job_id": job_id,
        "salary_offered": 60000,
        "start_date": "2026-11-01",
        "offer_date": "2026-10-18",
        "status": "Draft",
    },
)
print("4. create offer:", r.status_code, r.json().get("offer_number"))
offer_id = r.json()["id"]

# 5. Generate offer letter PDF
r = client.post(f"/api/v1/offers/{offer_id}/letter", headers=H)
print("5. generate letter:", r.status_code, "status:", r.json().get("status"), "url:", r.json().get("letter_url"))
letter_url = r.json()["letter_url"]

# 6. Accept offer
r = client.post(f"/api/v1/offers/{offer_id}/accept", headers=H)
print("6. accept offer:", r.status_code, r.json().get("status"))

# 7. Hire -> employee + checklist
r = client.post(
    f"/api/v1/offers/{offer_id}/hire",
    headers=H,
    json={"employee_id": "EMP1001"},
)
print("7. hire:", r.status_code, "employee_id:", r.json()["employee"]["employee_id"], "tasks:", r.json()["onboarding_tasks_created"])
emp_pk = r.json()["employee"]["id"]

# 8. Onboarding summary
r = client.get(f"/api/v1/onboarding/{emp_pk}/summary", headers=H)
print("8. onboarding summary:", r.status_code, r.json())

# 9. Complete a task
r = client.get(f"/api/v1/onboarding/{emp_pk}/tasks", headers=H)
task_id = r.json()[0]["id"]
r = client.put(f"/api/v1/onboarding/tasks/{task_id}", headers=H, json={"status": "Completed"})
print("9. complete task:", r.status_code, r.json().get("status"))

r = client.get(f"/api/v1/onboarding/{emp_pk}/summary", headers=H)
print("10. updated summary:", r.json())

# 11. Upload a document
files = {"file": ("id_proof.pdf", b"%PDF-1.4 fake", "application/pdf")}
r = client.post(
    f"/api/v1/onboarding/{emp_pk}/documents",
    headers=H,
    data={"document_type": "IDProof"},
    files=files,
)
print("11. upload document:", r.status_code, r.json().get("file_name"), r.json().get("storage_url"))

# 12. Verify letter file was written
disk_path = os.path.join(os.environ["LOCAL_STORAGE_DIR"], f"offers/OFF-001.pdf")
print("12. letter on disk:", os.path.exists(disk_path))

print("\nPHASE 2 SMOKE TEST COMPLETE")

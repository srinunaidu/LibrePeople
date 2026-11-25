"""The offer-to-hire suite.

Audit finding A2-04: *offer→hire is not atomic — the employee and the
checklist commit before the candidate and application status and the
audit row*. A failure in the middle left a half-made hire behind: an
employee the recruiter had to delete by hand, a candidate still marked as
a candidate, and an onboarding checklist that belonged to nobody.

Audit finding A2-16: *the offer letter calls a per-period salary an
"annual compensation"*. The amount is per pay period. A candidate who
reads it as an annual figure has been offered a twelfth of what they will
be paid.

Run:  python hire_test_suite.py
"""
from __future__ import annotations

import os
import tempfile
from datetime import date

DB_PATH = os.path.join(tempfile.mkdtemp(prefix="hire_test_"), "hire_test.db")

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"
os.environ["BACKEND_CORS_ORIGINS"] = ""
os.environ["ALLOW_SELF_REGISTRATION"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"

try:
    os.remove(DB_PATH)
except FileNotFoundError:
    pass

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.employee import Employee  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.onboarding import OnboardingTask  # noqa: E402
from app.models.recruiting import (  # noqa: E402
    Application,
    Candidate,
    JobRequisition,
    Offer,
)
from app.models.user import User  # noqa: E402

Base.metadata.create_all(bind=engine)

session = SessionLocal()
session.add(User(
    username="hire_admin", email="hire_admin@example.com",
    hashed_password=get_password_hash("HirePass12345"),
    role="SuperAdmin", is_active=True, mfa_enabled=True,
))
department = Department(name="Engineering", code="ENG")
session.add(department)
session.flush()
session.add(Job(title="Engineer", code="ENG-JOB", department_id=department.id))
session.flush()
requisition = JobRequisition(
    req_number="REQ-1", title="Engineer", department_id=department.id,
    job_id=session.query(Job).filter(Job.code == "ENG-JOB").first().id,
    status="Open",
)
session.add(requisition)
session.flush()
candidate = Candidate(
    first_name="Ada", last_name="Lovelace", email="ada.hire@example.com",
    status="Offer",
)
session.add(candidate)
session.flush()
application = Application(
    requisition_id=requisition.id, candidate_id=candidate.id,
    status="Offer", applied_date=date(2026, 1, 5),
)
session.add(application)
session.flush()
offer = Offer(
    offer_number="OFF-1", application_id=application.id,
    job_id=requisition.job_id, salary_offered=7500,
    start_date=date(2026, 2, 1), offer_date=date(2026, 1, 20),
    status="Accepted",
)
session.add(offer)
session.commit()
OFFER_ID = offer.id
session.close()

client = TestClient(app, raise_server_exceptions=False)

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


def H() -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"username": "hire_admin", "password": "HirePass12345"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


AUTH = H()


def count(model) -> int:
    db = SessionLocal()
    try:
        return db.query(model).count()
    finally:
        db.close()


def hire(body: dict, headers: dict | None = None):
    return client.post(
        f"/api/v1/offers/{OFFER_ID}/hire",
        headers=headers or AUTH,
        json=body,
    )


# --------------------------------------------------------------------------
print("=" * 68)
print("HIRE — A2-04: the hire is one transaction")
print("=" * 68)

employees_before = count(Employee)
tasks_before = count(OnboardingTask)

response = hire({
    "employee_id": "EMP-HIRE-1",
    "department_id": 1,
    "job_id": 1,
    "hire_date": "2026-02-01",
    "email": "ada.hire@example.com",
    "salary": 7500,
})
check("the hire succeeds", response.status_code == 201, response.text[:300])

check("the employee was created", count(Employee) == employees_before + 1,
      f"{employees_before} -> {count(Employee)}")
check("the checklist was created", count(OnboardingTask) > tasks_before,
      f"{tasks_before} -> {count(OnboardingTask)}")

db = SessionLocal()
try:
    hired = db.query(Employee).filter(Employee.employee_id == "EMP-HIRE-1").first()
    candidate_row = db.query(Candidate).filter(Candidate.email == "ada.hire@example.com").first()
    application_row = db.query(Application).filter(
        Application.candidate_id == candidate_row.id
    ).first()
    audit = db.query(AuditLog).filter(AuditLog.action == "hire_from_offer").count()
finally:
    db.close()

check("the candidate is marked as hired", candidate_row.status == "Hired",
      candidate_row.status)
check("the application is marked as hired", application_row.status == "Hired",
      application_row.status)
check("the audit row was written", audit == 1, str(audit))

# The audit row records what actually happened.
db = SessionLocal()
try:
    row = db.query(AuditLog).filter(AuditLog.action == "hire_from_offer").first()
    details = row.details or ""
finally:
    db.close()
check("the audit row names the employee", "employee_id=EMP-HIRE-1" in details, details)
check("the audit row names the checklist count",
      f"onboarding_tasks={count(OnboardingTask)}" in details, details)

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("HIRE — A2-04: a failure in the middle leaves nothing behind")
print("=" * 68)

import app.api.v1.endpoints.offers as offers_endpoint  # noqa: E402

original_checklist = offers_endpoint.apply_default_checklist


def failing_checklist(db, employee_id, commit=True):
    raise RuntimeError("the checklist could not be created")


db = SessionLocal()
try:
    candidate_row = db.query(Candidate).filter(
        Candidate.email == "ada.hire@example.com"
    ).first()
    candidate_row.status = "Offer"
    db.add(candidate_row)
    application_row = db.query(Application).filter(
        Application.candidate_id == candidate_row.id
    ).first()
    application_row.status = "Offer"
    db.add(application_row)
    db.commit()
finally:
    db.close()

employees_before = count(Employee)
tasks_before = count(OnboardingTask)
audit_before = count(AuditLog)

offers_endpoint.apply_default_checklist = failing_checklist
try:
    response = hire({
        "employee_id": "EMP-HIRE-2",
        "department_id": 1,
        "job_id": 1,
        "hire_date": "2026-02-01",
        "email": "ada.hire@example.com",
    })
finally:
    offers_endpoint.apply_default_checklist = original_checklist

check("the failed hire does not succeed", response.status_code >= 400,
      f"got {response.status_code}")
check("the failed hire created no employee", count(Employee) == employees_before,
      f"{employees_before} -> {count(Employee)}")
check("the failed hire created no checklist", count(OnboardingTask) == tasks_before,
      f"{tasks_before} -> {count(OnboardingTask)}")
check("the failed hire wrote no audit row", count(AuditLog) == audit_before,
      f"{audit_before} -> {count(AuditLog)}")

db = SessionLocal()
try:
    candidate_row = db.query(Candidate).filter(
        Candidate.email == "ada.hire@example.com"
    ).first()
    application_row = db.query(Application).filter(
        Application.candidate_id == candidate_row.id
    ).first()
finally:
    db.close()
check("the candidate's status was not changed", candidate_row.status == "Offer",
      candidate_row.status)
check("the application's status was not changed",
      application_row.status == "Offer", application_row.status)

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("HIRE — A2-04: the hire is idempotent")
print("=" * 68)

employees_before = count(Employee)
key = {"Idempotency-Key": "hire-once-please"}
body = {
    "employee_id": "EMP-HIRE-3",
    "department_id": 1,
    "job_id": 1,
    "hire_date": "2026-02-01",
    "email": "ada.hire3@example.com",
}
first = hire(body, headers={**AUTH, **key})
check("the first hire succeeds", first.status_code == 201, first.text[:300])
after_first = count(Employee)
check("the first hire created one employee", after_first == employees_before + 1,
      f"{employees_before} -> {after_first}")

second = hire(body, headers={**AUTH, **key})
check("the retry is accepted", second.status_code in (200, 201),
      f"got {second.status_code}")
check("the retry created no second employee", count(Employee) == after_first,
      f"{after_first} -> {count(Employee)}")

# A different key with the same employee number is refused, not duplicated.
third = hire(body, headers={**AUTH, "Idempotency-Key": "a-different-key"})
check("a second hire with a different key is refused",
      third.status_code == 400, f"got {third.status_code}")
check("the refused hire created no employee", count(Employee) == after_first,
      f"{after_first} -> {count(Employee)}")

# --------------------------------------------------------------------------
print()
print("=" * 68)
print("HIRE — A2-16: the offer letter says what the salary is")
print("=" * 68)

from app.services.offer_letter import render_offer_letter  # noqa: E402


def pdf_text(pdf: bytes) -> str:
    """The text inside a PDF.

    fpdf2 writes the page content into a compressed stream, so the text is
    not in the file as plain bytes. The streams are inflated and the text
    operators are read out of them.
    """
    import re
    import zlib

    parts: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", pdf, re.S):
        raw = match.group(1)
        try:
            raw = zlib.decompress(raw)
        except Exception:  # noqa: BLE001
            pass
        parts.append(raw.decode("latin-1", errors="replace"))
    return "\n".join(parts)


pdf = render_offer_letter(
    candidate_name="Ada Lovelace",
    job_title="Engineer",
    department_name="Engineering",
    salary=7500,
    start_date=date(2026, 2, 1),
    offer_date=date(2026, 1, 20),
    offer_number="OFF-TEST",
)
check("the letter renders", isinstance(pdf, bytes) and len(pdf) > 0, str(len(pdf)))

text = pdf_text(pdf)
check("the letter does not call a per-period salary an annual figure",
      "annual compensation" not in text.lower(), "found 'annual compensation'")
check("the letter says the figure is not an annual figure",
      "not an annual figure" in text.lower(), "the per-period wording is missing")
check("the letter states the amount", "7,500.00" in text, "the amount is missing")

monthly = render_offer_letter(
    candidate_name="Ada Lovelace",
    job_title="Engineer",
    department_name="Engineering",
    salary=7500,
    start_date=date(2026, 2, 1),
    offer_date=date(2026, 1, 20),
    offer_number="OFF-TEST",
    pay_frequency="Monthly",
)
monthly_text = pdf_text(monthly)
check("the letter names the frequency when it is known",
      "each month" in monthly_text.lower(), "the frequency is missing")

biweekly = render_offer_letter(
    candidate_name="Ada Lovelace",
    job_title="Engineer",
    department_name="Engineering",
    salary=7500,
    start_date=date(2026, 2, 1),
    offer_date=date(2026, 1, 20),
    offer_number="OFF-TEST",
    pay_frequency="Biweekly",
)
check("the letter names a fortnightly frequency",
      "each fortnight" in pdf_text(biweekly).lower(), "the frequency is missing")

# --------------------------------------------------------------------------
print()
print("=" * 68)
print(f"==== HIRE SUITE: {RESULTS['pass']} passed, {RESULTS['fail']} failed ====")
if FAILURES:
    print("\nFailures:")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
print("=" * 68)
raise SystemExit(1 if RESULTS["fail"] else 0)
